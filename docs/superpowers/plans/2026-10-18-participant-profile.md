# Participant Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development only if the user selects delegation. Steps use checkbox syntax for tracking. User selected native execution in this session.

**Goal:** Реализовать личный паспорт участника и необязательный шестишаговый мастер, использующие существующие справочники и единые приватные данные.

**Architecture:** Новый модуль participant_profiles владеет предпочтениями, черновиком и видимостью. User/UserPreferences остаются источником имени, меток и настроек аккаунта. Web и Android используют один серверный контракт; публикация и авторизация выполняются только backend.

**Tech Stack:** Python, FastAPI, SQLAlchemy async, PostgreSQL, Alembic, Vue 3/TypeScript, Kotlin/Compose; существующие зависимости без новых пакетов.

**Spec:** `docs/superpowers/specs/2026-10-18-participant-profile-design.md`

## Global Constraints

- «По умолчанию все новые разделы приватны»; черновик всегда доступен только владельцу.
- «Администратор и Dominant не обходят эти проверки»; полномочия не транзитивны.
- «Неуказанное предпочтение не означает согласия на действие».
- «Фотозагрузка аватара не входит в этот срез»: используется существующая монограмма.
- «Web: телефон 390px, планшет 768–1024px, desktop 1440px»; сенсорные зоны от 44px.
- API prefix `/api/v1`; DTO/контракты Web и Android обновляются вместе.
- Без автоматических коммитов, push, production-деплоя и сборок приложения. Проверки исходников и тесты разрешены; Android Gradle-тесты выполняются только если пользователь разрешит необходимую компиляцию. Пропущенные проверки явно отражаются в отчёте.

## Review Focus

1. Две вкладки редактируют старое имя и новый профиль: stale publication должна дать 409 и сохранить прежние данные (Task 2).
2. Отношение приостановлено между открытием формы и сохранением доступа: нельзя открыть раздел устаревшему читателю (Task 3).
3. Пользователь меняет шаг при сбое сети: введённый текст остаётся в форме, переход не создаёт ложное «Сохранено» (Task 5).
4. В справочнике изменена категория практики: сохранённые UUID остаются корректны, забота не зависит от строкового имени категории (Task 1/2).
5. Мобильная клавиатура и длинные подписи: нижнее действие и поля остаются доступны, страница не переполняется (Task 6/7).

## Общие договоры данных

Предлагаемые имена ниже фиксируются планом, это новые интерфейсы.

- `ProfileDocument`: шесть разделов `identity`, `dynamics`, `preferences`, `boundaries`, `health`, `visibility`.
- `identity`: `display_name` (существующий лимит 100), `bio` (2000), `biological_sex_uid?`, `gender_uid?`.
- `dynamics`: `profile_labels` (существующий набор); `sex_preference` и `gender_preference` = `{mode: not_specified|any|selected, uids: UUID[]}`; UUID-списки `relationship_type_uids`, `composition_uids`, `interaction_format_uids`.
- `preferences.practices`: `{practice_uid, attitude: not_specified|like|want_to_try|conditional|taboo, experience: not_specified|none|tried|experienced, participation: not_specified|give|receive|both, conditions}`. conditions до 2000 символов.
- Предметные выборки `devices`, `body_parts`, `materials`, `role_scenarios`, `venues`: элементы `{uid, attitude, conditions}`, без experience/participation.
- `boundaries.notes` до 4000; табу/условия по практикам вычисляются из preferences, не хранятся повторно.
- `health`: `condition_uids`, `allergen_uids`, `care_practice_uids`, `notes` до 4000. Забота выбирается из практик без зависимости от названия категории; категория служит фильтром интерфейса, не медицинской проверкой.
- `visibility`: список `{section: identity|dynamics|preferences|boundaries|health, reader_ids: UUID[]}`; пустые читатели означают только владельца. Не более 500 записей на список; дубли отвергаются.
- `ProfileView`: опубликованный `document`, `version`, текущий `account_version`, прогресс `{step:1..6, deferred:bool, completed:bool}`, `draft_version?`.
- `ProfileDraftView`: `document`, `version`, `base_profile_version`, `base_account_version`, `step`, `deferred`.
- `ProfileDraftPatch`: `expected_version` (0 для первого), `section?`, `value?`, `step`, `deferred`; section/value либо оба отсутствуют, либо оба присутствуют.
- `ProfilePublish`: `expected_draft_version`; `SharedProfileView`: owner UUID, разрешённые разделы и их содержимое, без полей черновика/скрытых счётчиков.

## Task 1: Хранение и нормализованные связи

**Files:** Create `backend/src/vowen/modules/participant_profiles/{__init__,models,schemas}.py`, `backend/migrations/versions/0044_participant_profiles.py`, `backend/tests/integration/test_participant_profile_storage.py`. Modify `backend/src/vowen/core/database.py` только если регистрация новых моделей требует этого после проверки существующего механизма.

**Interfaces:** Produces Pydantic-типы из договора выше и SQLAlchemy-модели Profile, ProfileDraft, ProfileSectionReader, PracticePreference; отдельные FK-таблицы выбранных справочников, без polymorphic FK.

- [ ] Написать `test_profile_reference_integrity`: assert FK отвергает отсутствующий UUID, уникальность отвергает повтор owner/practice, удаление владельца не оставляет чувствительные строки.
- [ ] Запустить тест на отдельной PostgreSQL test-БД; ожидается FAIL до создания таблиц. Не использовать preview/main DB или SQLite.
- [ ] Реализовать модели, constraints и миграцию 0044. Profile хранит version; draft хранит bounded JSONB и base_profile/account versions; опубликованные выборки нормализованы. Имя и метки не копируются в опубликованную таблицу профиля.
- [ ] Применить миграцию к одноразовой БД с 0043; проверить upgrade/downgrade и повторный upgrade. Старые users сохраняются, новые поля необязательны.
- [ ] Запустить storage-тест; ожидается PASS. Изменение имени категории не разрушает FK-связь выбранной практики.

## Task 2: Черновик, валидация и атомарная публикация

**Files:** Create `backend/src/vowen/modules/participant_profiles/service.py`, `backend/tests/integration/test_participant_profile_draft.py`. Read `identity/models.py`, `auth/router.py` и `references/models.py` для существующих значений и account-version semantics.

**Interfaces:** Consumes Task 1. Produces async `get_own_profile(db: AsyncSession, owner_id: UUID) -> ProfileView`, `save_draft(db: AsyncSession, owner_id: UUID, patch: ProfileDraftPatch) -> ProfileDraftView`, `publish_draft(db: AsyncSession, owner_id: UUID, data: ProfilePublish) -> ProfileView`, `discard_draft(db: AsyncSession, owner_id: UUID, expected_version: int) -> None`.

- [ ] Написать тесты: `test_draft_resume_without_publish`, `test_skip_preserves_values`, `test_publish_updates_identity_atomically`, `test_unknown_wrong_kind_duplicate_uuid_rejected`, `test_concurrent_draft_updates`, `test_stale_account_version_blocks_publish`.
- [ ] Assert: после нового чтения step и document совпадают; партнёр до publish видит старые значения; одновременные записи дают [200,409]; stale account не перезаписан; invalid UUID не меняет ни имя, ни предпочтения.
- [ ] Запустить draft-тесты, зафиксировать ожидаемое FAIL до реализации.
- [ ] Реализовать сервис: SELECT FOR UPDATE владельца и версии в одном согласованном порядке с существующим обновлением аккаунта; проверить версии, UUID/виды/лимиты, читателей; заменять нормализованные выборки транзакционно. account_version увеличивается только при фактическом изменении имени/меток.
- [ ] PATCH раздела различает omitted и очистку; повторная публикация использованной версии даёт 409, черновик не публикуется дважды. completed и deferred относятся к мастеру, а не оценке ответов.
- [ ] Запустить storage+draft тесты; ожидается PASS, включая сохранение/чтение через новые DB sessions.

## Task 3: Авторизованный API и приватность

**Files:** Create `backend/src/vowen/modules/participant_profiles/{policy,router}.py`, `backend/tests/integration/test_participant_profile_access.py`. Modify `backend/src/vowen/main.py` для регистрации router.

**Interfaces:** Produces async `read_shared_profile(db: AsyncSession, viewer_id: UUID, owner_id: UUID) -> SharedProfileView`. Routes GET `/me/profile`, GET/PUT/DELETE `/me/profile/draft`, POST `/me/profile/publish`, GET `/participants/{id}/profile`; DELETE требует expected_version query.

- [ ] Написать `test_owner_only_draft`, `test_selected_direct_reader_only`, `test_pause_revocation_and_stale_reader`, `test_admin_dominant_no_bypass`, `test_shared_response_omits_hidden_metadata`, `test_profile_labels_do_not_grant_authority`.
- [ ] Assert 401 без auth; 404 постороннему и для несуществующего чужого UUID; приватные разделы, draft и hidden counts отсутствуют; A→B→C не открывает A для C; paused/revoked relation немедленно закрывает чтение и новый grant даёт 422.
- [ ] Запустить access-тесты до реализации; ожидается FAIL.
- [ ] Реализовать policy на действующих прямых отношениях с проверкой текущего статуса/версии; использовать Member/DB зависимости auth, own ID только из principal. Проверять чтение независимо от текущей страницы клиента.
- [ ] Ограничить ошибки 422 полем, не отражать чувствительные значения; исключить request bodies из логов. Не расширять ParticipantView профилем.
- [ ] Запустить profile storage/draft/access и существующий `backend/tests/integration/test_profile.py`; ожидается PASS.

## Task 4: Контракты и клиентские вызовы

**Files:** Modify `scripts/android_contract.py`, `contracts/openapi.json`, `web/src/shared/api.d.ts`, `android/app/src/main/java/org/vowen/app/{ApiModels,Api}.kt`. Create `web/src/features/profile/profile-api.ts`, `android/app/src/test/java/org/vowen/app/ParticipantProfileApiTest.kt`; update `backend/tests/contract/test_openapi.py`.

**Interfaces:** Web `createProfileApi(client)` returns `getOwn()`, `getDraft()`, `saveDraft(patch)`, `publish(version)`, `discard(version)`, `getShared(ownerId)` с типами Task 1. Android Api получает аналогичные suspend-методы с именами `participantProfile`, `profileDraft`, `saveProfileDraft`, `publishProfileDraft`, `discardProfileDraft`, `sharedParticipantProfile`.

- [ ] Contract-тест: assert все шесть маршрутов, expected-version поля, enum-значения и nullable UID присутствуют, ParticipantView не раскрывает новые поля.
- [ ] Сгенерировать OpenAPI/DTO существующими `scripts/export_contract.py`, `scripts/android_contract.py`, `pnpm --dir web generate-api`; не писать generated-файлы вручную.
- [ ] Реализовать typed wrappers через существующий auth client; не добавлять отдельный token store.
- [ ] Написать Android MockWebServer-тест: resume DTO, PUT body с version и explicit clear, POST publish, 409 без скрытого retry, DELETE query version.
- [ ] Выполнить backend contract-тест и `pnpm --dir web typecheck`; Android тест отметить непроверенным, пока нет разрешения на Gradle-компиляцию.

## Task 5: Web-состояние редактора и мастера

**Files:** Create `web/src/features/profile/{useParticipantProfile,profile-fields}.ts`, `web/tests/participant-profile.test.ts`.

**Interfaces:** `useParticipantProfile(api)` exposes published, draft, step, loading, saving, error, dirty; methods `load()`, `saveSection(section,value)`, `goToStep(step)`, `defer()`, `discard()`, `publish()`. `saveSection` сохраняет черновик; publish — единственная публикация. UI-редактор использует этот же draft.

- [ ] Тесты fake API: `resumeServerDraft`, `failedSaveRetainsEditsAndStep`, `skipKeepsAnswers`, `conflictNeedsReload`, `tabooHasSingleSource`, `publishRefreshesAccount`.
- [ ] Assert: rejected PUT не очищает input/dirty и не продвигает step; 409 не вызывает retry; список taboos ссылается на practice attitude; language/timezone/notifications не затронуты.
- [ ] Запустить `pnpm --dir web test -- tests/participant-profile.test.ts`; ожидается FAIL до реализации.
- [ ] Реализовать composable без localStorage чувствительных данных, с защитой от позднего ответа предыдущего пользователя и повторного publish. Сохранение перед навигацией шага обязательно; отказ сети оставляет текущий шаг.
- [ ] Повторить scoped Vitest; ожидается PASS.

## Task 6: Web-паспорт и адаптивный мастер

**Files:** Create `web/src/features/profile/{ParticipantProfile,ProfileOverview,ProfileWizard,ProfileSectionEditor,PracticePreferences,ProfileVisibility}.vue`, `web/src/features/profile/profile.css`, `web/e2e/participant-profile.spec.ts`. Modify `web/src/App.vue`, `ProfilePanel.vue`, `ProfileSettings.vue` только для подключения/сохранения настроек языка и timezone.

**Interfaces:** ParticipantProfile получает client/member/ru и emits saved(MemberView). Дочерние компоненты используют Task 5; ProfileSectionEditor выбирает шесть предметных разделов. Все кнопки явного сохранения вызывают publish после сохранения draft, без фоновой публикации.

- [ ] Добавить E2E: новый владелец начинает мастер, выбирает практику/опыт/участие, сохраняет и выходит, reload возобновляет; skip; publish; обычный редактор показывает те же данные.
- [ ] Добавить проверки account tabs и 390/768/1024/1440 widths, длинных текстов, ошибок API и клавиатурного фокуса. Assert scrollWidth <= clientWidth у страницы; отдельный таб-скроллер допустим.
- [ ] Реализовать паспорт по выбранному PNG: открытые секции, 2 колонки desktop/1 mobile, монограмма, restrained banner, inner tabs и существующие внешние account tabs.
- [ ] Реализовать searchable catalogue selector с category UUID, reference thumbnails и независимыми attitude/experience/participation; boundaries использует ту же практику, visibility выбирает реальных прямых партнёров.
- [ ] Реализовать отдельное состояние мастера с шестью шагами, clear/back/skip/save-exit/publish. Touch >=44px, sticky actions с safe-area, reduced-motion, aria labels, focus restoration. Не использовать PNG как интерфейс.
- [ ] Запустить typecheck, scoped Vitest и новый Playwright spec через штатный изолированный test API. Снять реальные desktop/mobile screenshots; проверить видимость бархата и доступность кнопок при малой высоте.

## Task 7: Native Android

**Files:** Create `android/app/src/main/java/org/vowen/app/{NativeParticipantProfileScreen,NativeProfileWizard,ParticipantProfileState}.kt`; modify `NativeAccountScreen.kt`, `WorkspaceState.kt`, `WorkspaceScreen.kt` и точку создания WorkspaceActions, найденную по ссылкам перед редактированием. Add `android/app/src/androidTest/java/org/vowen/app/ParticipantProfileScreenTest.kt`.

**Interfaces:** ParticipantProfileState содержит Task 5-эквивалент для Task 4 Api, без дублирования backend policy. NativeParticipantProfileScreen получает state/actions и сохраняет существующие уведомления/сессии в NativeAccountScreen.

- [ ] Добавить Compose-сценарии draft resume, independent practice axes, skip, 409 и длинной подписи; действия testTag `profile-wizard-next`, `profile-wizard-skip`, `profile-publish`.
- [ ] Реализовать passport/step layouts с LazyColumn, scrollable tabs, imePadding/navigationBarsPadding; не удерживать чувствительный draft в persistent device store.
- [ ] Повторный вход загружает server draft; logout очищает state. Offline-save остаётся видимым несохранённым, публикация без сети не симулируется.
- [ ] Проверить исходники и DTO. Gradle unit/instrumented tests и устройство выполнять только после разрешения необходимой компиляции; иначе явно сообщить Android source-only, без заявления о проверенном экране.

## Task 8: Интеграция и визуальная приёмка

**Files:** Update `docs/STATUS.md`; create root `design-qa.md` по product-design design-qa workflow. Product code исправлять только по воспроизводимым результатам проверок.

- [ ] Проверить diff: scope, скрытые данные, старые account preferences, повторная публикация, FK и версии; никаких фото/профилей в static/logs.
- [ ] Запустить scoped ruff/mypy, Web lint/typecheck/Vitest, backend profile+contract tests на отдельной PostgreSQL. При новых сбоях расширять релевантные проверки, не пересобирать приложения автоматически.
- [ ] Проверить регенерацию контрактов на отсутствие дополнительного дрейфа; ожидаемые изменения текущей задачи не считать ошибкой `git diff --exit-code` против HEAD.
- [ ] Сопоставить фактический Web с выбранным макетом при одинаковых viewport, записать screenshots и исправить P0–P2. Не писать passed в design-qa до фактической проверки.
- [ ] Записать в STATUS что реализовано, реально проверено, что пропущено из-за запрета сборок; прежние unrelated E2E failures не скрывать и не чинить вне scope.
- [ ] Отдать работающий локальный Web для проверки пользователю. Не делать commit/push/build/deploy без отдельного запроса.

## Self-review

Все разделы спецификации распределены по задачам 1–8. Сигнатуры и DTO определены один раз выше; Web/Android не определяют собственную политику доступа. Учтены Review Focus, старые версии аккаунта, приватный черновик и отсутствие транзитивного доступа. Запрет автоматических сборок сохранён; ограничения нативной проверки отражаются явно.

Статус: backend и Web реализованы и проверены; Android исходники и тесты добавлены, Gradle/device проверки не выполнялись по запрету сборок. Фактические результаты и отклонения: docs/design/participant-profile-implementation.md.
