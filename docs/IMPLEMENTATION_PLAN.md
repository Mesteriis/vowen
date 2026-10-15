# Vowen: план реализации

> Для агента: выполнять задачи последовательно с тестовым циклом. Если доступны superpowers, использовать `executing-plans` либо `subagent-driven-development`; при отсутствии этих навыков выполнять тот же цикл штатными инструментами. Это инструкция для будущей разработки, а не отчёт о выполненных тестах.

**Цель:** создать публичный OSS-репозиторий и довести первый вертикальный сценарий до работающих backend, Telegram Mini App и Android-входа, затем реализовать продукт по этапам.

**Архитектура:** single-instance модульный монолит. API, CLI, bot и worker используют общие сервисы; PostgreSQL хранит предметные данные, задания и сессии. Гостевые формы имеют отдельный principal и ограниченный API.

**Стек:** Python/FastAPI, PostgreSQL, Vue/TypeScript, Kotlin/Compose, Docker Compose.

**Спецификация:** `PRODUCT_SPEC.md`, `ARCHITECTURE.md`, `SECURITY.md`. Все значения и инварианты из них обязательны. Изменения документировать в ADR, не прятать в реализации.

## Общие ограничения

- Python 3.13 и PostgreSQL 17 являются выбранными целями совместимости.
- Никаких `POST /users`, `/register`, `/signup` и автоаккаунтов из Telegram.
- Один инстанс, N участников, нетранзитивные контекстные scopes.
- Гость анкеты не получает member-сессию.
- Живые секреты и пользовательские данные не используются в тестах и не публикуются.
- Первый этап включает собираемый нативный Android, не только пустую папку или будущий roadmap.
- Каждая задача завершается тестами и commit; каждый этап имеет работающий сценарий.

## Особое внимание при ревью

| Сложный случай | Где должен быть закреплён тестом |
|---|---|
| Повтор/перестановка Telegram query-параметров, потеря ответа входа | M1.2, `test_telegram_assertion_replay.py` |
| Блокировка пользователя после выдачи токена; гонка refresh | M1.2, `test_session_revocation.py` |
| Пересланная bot-ссылка не даёт владение Android poll-secret | M1.3, `test_android_login.py` |
| Preview страницы и одновременные guest submit/revoke | M2, `test_guest_invitation_races.py` |
| DST, простой worker и повтор события не удваивают награду | M3, `test_occurrence_schedule.py`, `test_reward_idempotency.py` |

## M0. Репозиторий и проверяемый bootstrap

**Результат:** чистое окружение способно установить зависимости, запустить API и собрать оба клиентских проекта. Публичный remote существует только если создание реально выполнено.

**Файлы:** корневые OSS-документы, `.github/workflows/ci.yml`, `Makefile`, `compose.yaml`, `backend/pyproject.toml`, `backend/src/vowen/main.py`, `backend/src/vowen/core/{config,database,clock,errors}.py`, `backend/tests/integration/test_health.py`, `web/src/`, `android/app/`, lockfiles, `docs/adr/0001-architecture.md`.

**Интерфейсы:**

- `create_app(settings: Settings) -> FastAPI` в `main.py`.
- `Clock.now() -> datetime` возвращает aware UTC; тестовый Clock управляемый.
- `GET /health/live`: `200` без обращения к Telegram.
- `GET /health/ready`: `200` только при доступной БД и совместимой схеме, иначе `503`, без секретов в ответе.

- [ ] Проверить каталог/Git, определить подтверждённого remote-owner, создать новый репозиторий или честный локальный fallback.
- [ ] Сохранить спецификации и ADR о Python, single-instance, native Android, opaque sessions и MIT-default.
- [ ] Написать `test_liveness_does_not_need_telegram` и `test_readiness_fails_for_unavailable_database` до реализации health handlers.
- [ ] Запустить эти тесты и зафиксировать ожидаемое падение из-за отсутствующего поведения.
- [ ] Реализовать settings, health, DB lifecycle и стартовую миграцию singleton settings.
- [ ] Поднять development Compose, запустить тесты повторно.
- [ ] Создать web shell с RU/EN и Android shell с экраном адреса инстанса; добавить сборки в CI.
- [ ] Проверить `docker compose config`, backend tests, web build, Android `assembleDebug` при наличии SDK.
- [ ] Добавить `.gitignore`, исключить секреты, выполнить scan staged/истории, создать первый содержательный commit.

**Критерий M0:** не только README. API действительно запускается, readiness корректен, web и Android собираются. Отсутствие локального SDK отдельно отмечается как непроверенная локальная сборка; оно не оправдывает фиктивную отметку «Android готов».

## M1. Закрытый доступ и контекстные отношения

### M1.1. CLI-пользователи и защищённые примитивы хранения

**Файлы:** `backend/src/vowen/modules/identity/{models,schemas,service}.py`, `backend/src/vowen/cli/{main,users,instance}.py`, `backend/src/vowen/core/crypto.py`, миграция users, `backend/tests/integration/test_user_provisioning.py`, `backend/tests/unit/test_crypto.py`.

**Интерфейсы:**

- `ProvisionUserCommand(telegram_id: int, display_name: str)`.
- `create_user(db: AsyncSession, command: ProvisionUserCommand, now: datetime) -> User`.
- `set_user_active(db: AsyncSession, telegram_id: int, active: bool, now: datetime) -> User`.
- `seal_payload(record_type: str, record_id: UUID, schema_version: int, plaintext: bytes) -> EncryptedEnvelope`.
- `open_payload(record_type: str, record_id: UUID, schema_version: int, envelope: EncryptedEnvelope) -> bytes`.
- `EncryptedEnvelope` содержит `key_id`, `nonce`, `ciphertext`, `format_version`; никаких ключей в DTO.

- [ ] Тестами задать создание BIGINT Telegram ID, ошибку дубликата, отключение, идемпотентный `instance init` без замены ключа.
- [ ] Тестами crypto задать round-trip, иной ciphertext при повторном шифровании, отказ при другом record ID/испорченном tag/отсутствующем key ID.
- [ ] Запустить тесты до реализации и убедиться, что проверяется отсутствующая функция, а не случайная ошибка fixture.
- [ ] Реализовать схемы, миграцию, сервисы и CLI, не добавляя публичный endpoint создания пользователя.
- [ ] Повторить проверки, проверить отсутствие plaintext-marker в encrypted columns, сделать commit.

### M1.2. Telegram Mini App, сессии и отзыв

**Файлы:** `backend/src/vowen/modules/auth/{models,schemas,service,router,telegram_validation}.py`, `backend/src/vowen/modules/identity/router.py`, `web/src/features/auth/`, `web/src/features/profile/`, миграции sessions/assertions, `backend/tests/unit/test_telegram_validation.py`, `backend/tests/integration/test_{telegram_assertion_replay,session_revocation}.py`.

**Интерфейсы:**

- `verify_init_data(raw: str, bot_token: str, now: datetime, max_age_seconds: int = 300, future_skew_seconds: int = 30) -> TelegramIdentity`.
- `TelegramIdentity`: `telegram_id`, `auth_date`, `assertion_fingerprint`; все получены из проверенных данных.
- `authenticate_miniapp(db: AsyncSession, raw: str, now: datetime) -> SessionTokens`.
- `resolve_member(db: AsyncSession, access_token: str, now: datetime) -> MemberPrincipal`.
- `rotate_refresh(db: AsyncSession, refresh_token: str, now: datetime) -> SessionTokens`.
- `SessionTokens`: `access_token`, `refresh_token`, `access_expires_at`, `session_id`.

- [ ] Написать fixtures с синтетическим bot token и независимыми проверочными векторами, включая Unicode/URL encoding/дополнительные подписанные поля.
- [ ] Написать тесты invalid hash → `401`; valid unknown/disabled ID → одинаковый `403`; число users не меняется.
- [ ] Написать тесты возраста 301 секунда, будущего сдвига 31 секунда, повторяющихся ключей и перестановки параметров при replay.
- [ ] Написать тесты refresh rotation/reuse и отказа действующего access после disable/revoke commit.
- [ ] Запустить тесты, затем реализовать валидацию, session families, DB-проверки и `/me`.
- [ ] Подключить Mini App к настоящему API: передача raw initData, in-memory token transport, обработка `ACCESS_DENIED`, получение `/me`.
- [ ] Убедиться, что production не имеет альтернативы вида `?telegram_id=...` или `X-Debug-User`.
- [ ] Запустить backend и web тесты, проверить очищенные ошибки/логи, сделать commit.

### M1.3. Android challenge и Telegram bot

**Файлы:** `backend/src/vowen/modules/auth/android_challenge.py`, `backend/src/vowen/integrations/telegram/{bot,handlers}.py`, `android/app/src/main/` с feature auth и core network/security, миграции challenge/processed updates, `backend/tests/integration/test_android_login.py`, Android auth unit tests.

**Интерфейсы:**

- `create_challenge(db, client_nonce: str, device_label: str, now: datetime) -> ChallengeCreated`.
- `ChallengeCreated`: `challenge_id`, `bot_url`, `poll_secret`, `display_code`, `expires_at`.
- `approve_challenge(db, challenge_id: UUID, telegram_actor_id: int, now: datetime) -> None`, вызывается только доверенным Telegram adapter после callback-проверок.
- `consume_challenge(db, challenge_id: UUID, poll_secret: str, client_nonce: str, now: datetime) -> SessionTokens`.

- [ ] Тестами задать pending без session, явное подтверждение, отказ другому Telegram-отправителю, TTL 300 секунд, запрет подмены nonce.
- [ ] Проверить, что start token не подходит для poll/consume и второй конкурентный consume не выпускает session.
- [ ] Проверить повтор Telegram update/callback без повторного эффекта и unknown `/start` без создания users.
- [ ] После ожидаемого падения реализовать bot handlers и транзакционный challenge service.
- [ ] Реализовать Android-экраны выбора сервера, начала входа, ожидающего подтверждения, ошибок и `/me`.
- [ ] Реализовать Keystore-key и encrypted refresh blob; тест смены сервера проверяет, что старый токен не отправляется новому host.
- [ ] Собрать Android, запустить unit tests и backend tests; с доступным токеном отдельно проверить живой flow; сделать commit.

### M1.4. Отношения, согласия и policy

**Файлы:** `backend/src/vowen/modules/relations/{models,schemas,service,policy,router}.py`, миграции relations/agreements/consents, web relationships feature, `backend/tests/integration/test_relation_permissions.py`.

**Интерфейсы:**

- `propose_relation(db, actor: MemberPrincipal | OperatorContext, command: ProposeRelationCommand) -> Relation`.
- `accept_relation(db, actor: MemberPrincipal, relation_version_id: UUID, expected_version: int) -> Relation`.
- `authorize(db, principal: MemberPrincipal | GuestPrincipal, action: Action, context: ResourceContext) -> None` или типизированный отказ.
- `ResourceContext`: загруженный тип/ID объекта, target user и его фактический ACL; не доверять ACL из запроса клиента.

- [ ] Создать fixture из четырёх пользователей D1/D2/S1/S2 и отдельных связей D1 → S1, D2 → S2.
- [ ] Тестами запретить self-relation, активацию с одним согласием, автоматический доступ D1 к S2, транзитивный доступ и guest principal.
- [ ] Тестами закрепить паузу, требование обоих подтверждений для resume и невозможность принять соглашение через OperatorContext.
- [ ] Реализовать сервисы и UI предложить/принять/приостановить, затем повторить проверки и сделать commit.

**Критерий M1:** четыре пользователя создаются CLI; разрешённые пользователи входят через оба клиента; неизвестный не регистрируется; блокировка закрывает новые запросы; отношения действуют только после согласий; межличностные запреты подтверждены тестами. Это закрытый технический alpha, ещё не готовый продукт для хранения реальных анкет.

## M2. Анкеты: внутренний и внешний законченные сценарии

**Требования:** REQ-13–16, 19–21, 23, 26–27. **Зависимости:** M1 и crypto envelope.

**Файлы:** модуль `forms`, `contracts/form-schema`, web forms builder/renderer и guest entry, Android forms renderer, минимальные `outbox`/`notification_deliveries`, `backend/tests/integration/test_{forms_versions,form_audience,guest_invitation_races}.py`, `web/tests/guest-form.spec.ts`.

- [x] Зафиксировать DTO схемы и тесты каждого MVP-типа, limits, неизвестных fields/options и server-side conditional visibility.
- [x] Тестами закрепить неизменяемую опубликованную версию, адресата внутреннего приглашения, скрытый черновик и reader snapshot.
- [x] Реализовать web-конструктор, preview, публикацию, внутреннее приглашение и заполнение в web/Android.
- [x] Создать тесты обмена гостевого секрета, preview GET без расхода, CSRF, expiry/revoke, запрета member endpoints и чужих IDs.
- [x] Реализовать encrypted draft, атомарный submit, idempotency, guest cookie и receipt/delete. Повтор submit не увеличивает число ответов и users.
- [x] Реализовать копирование ссылки и опциональную доставку через bot contact; отсутствие контакта возвращает `manual_delivery_required`.
- [x] Для доставки ввести outbox claim/lease и protected delivery payload; проверить повтор задачи, удаление секрета после завершения и отсутствие тела ответа в уведомлении.
- [x] Выполнить браузерный E2E «создать → пригласить гостя → заполнить → увидеть разрешённым читателем → удалить».
- [x] Проверить concurrent submit против revoke в реальном PostgreSQL, а не последовательным мок-тестом.
- [x] Обновить OpenAPI, таблицу возможностей Android и документацию; сделать commits по завершённым подзадачам.

**Критерий M2:** реальные формы создаются без редактирования JSON вручную; внутренний и внешний ответы доступны только разрешённым сторонам; гостевой сценарий работает без Telegram; автоаккаунтов нет; plaintext ответов отсутствует в логах и основных DB columns.

## M3. Правила, ритуалы и награды

**Требования:** REQ-07–09, 11, 17, 21. **Файлы:** modules rules/rituals/rewards, worker schedules, клиентские features; tests `test_rule_acceptance.py`, `test_occurrence_schedule.py`, `test_ritual_review.py`, `test_reward_idempotency.py`.

- [x] Тестами закрепить принятие версии правила отдельно каждым адресатом и неприменимость новой версии до подтверждения.
- [x] Реализовать правила, назначения и интерфейсы согласования.
- [x] Тестами расписаний закрепить ежедневный/недельный/разовый слот, DST, catch-up и уникальность occurrence.
- [x] Реализовать worker генерации occurrence, отчёт, review/needs_changes, конфликт двух проверяющих и паузу.
- [x] Тестами закрепить отсутствие автоматического наказания при missed/declined/paused.
- [x] Реализовать каталог, ручную выдачу, автоматическую награду после approved и её уникальность при параллельной обработке события.
- [x] Подключить web/Android повседневные сценарии, нейтральные уведомления и списки по ACL. Реализованы ритуалы, награды, in-app и Telegram-уведомления с проверкой актуальных прав и защитой от повторов; живая доставка адресату проверяется отдельно.
- [x] Проверить E2E «правило → принятие → ритуал → отчёт → одобрение → ровно одна награда».

**Критерий M3:** шаблон может иметь нескольких адресатов без смешения отчётов; повторный worker не создаёт новые обязательства/награды; смена времени и простой не удваивают occurrence.

## M4. Дисциплина и дневник

**Требования:** REQ-10, 12, 20, 27. **Файлы:** modules discipline/journal, web/Android features; tests `test_discipline_transitions.py`, `test_journal_privacy.py`.

- [x] Написать таблицу разрешённых переходов дисциплины и тест на каждую запрещённую смену автора/адресата/проверяющего.
- [x] Реализовать версионируемые предложения, согласование, спор, выполнение, подтверждение и отмену.
- [x] Тестами дневника закрепить private default, selected readers, отсутствие доступа у Dominant/OperatorContext и нерасширение аудитории при новом пользователе.
- [x] Реализовать encrypted entries, теги/настроение, безопасный вывод текста, авторское редактирование/удаление.
- [x] Проверить отсутствие утечки через list totals, историю, audit, notifications и export.
- [x] Подключить оба клиента, провести E2E и сделать commits.

**Критерий M4:** приватность работает на сервере, а не только скрывает пункт меню; согласованную дисциплинарную запись нельзя незаметно изменить задним числом.

## M5. Повторные опросы, настройки и завершение клиентских сценариев

**Требования:** REQ-13, 16–18. **Файлы:** survey scheduler, notification settings, RU/EN resources, clients, tests `test_survey_waves.py`, `test_notification_privacy.py`.

- [x] Тестами закрепить новую волну для каждого периода, неизменность старого ответа и отсутствие дубликата по повторному событию.
- [x] Реализовать повтор по поддержанному расписанию и опциональный feedback после approved ритуала.
- [x] Реализовать тихие часы, выбор каналов, blocked-bot handling и нейтральный текст по умолчанию.
- [x] Проверить native Android сценарии правил, ритуалов, дисциплины, дневника, наград и заполнения форм; не заменять их WebView.
- [x] Проверить ошибки сети, loading/empty/error состояния, повторную авторизацию, сохранение серверных черновиков и смену инстанса.
- [x] Подготовить RU/EN, mobile/desktop web layout, safe area Mini App, доступные подписи контролов.

**Критерий M5:** пользовательские сценарии не зависят от CLI, кроме создания/блокировки аккаунтов и технического обслуживания. Отложенный Android-конструктор форм явно отмечен; заполнение форм реализовано нативно.

## M6. Эксплуатация, безопасность и OSS-релиз

**Требования:** REQ-22–27. **Файлы:** deploy, operations runbooks, release CI, security tests, `docs/STATUS.md`.

- [ ] Проверить установку из чистого clone по README и создание первого пользователя только CLI.
- [ ] Прогнать всю матрицу отрицательных тестов SECURITY, dependency/secret scans и CI без production secrets.
- [ ] Проверить retention cleanup и удаление ответов/квитанций/экспортов без plaintext в audit/outbox.
- [ ] Сделать backup синтетической установки и восстановить на отдельном инстансе с правильными и неправильными ключами.
- [ ] Проверить перезапуск bot/worker, падение во время доставки, lease recovery и миграцию с предыдущего этапа.
- [ ] Выпустить backend/web images без secret layers и APK-артефакт. Release-signing key не добавлять в Git; при отсутствии ключа не называть debug APK production release.
- [ ] Добавить release notes, checksums, фактическую матрицу платформ и нерешённые ограничения; проверить лицензию и notices зависимостей.

**Критерий MVP:** M0–M6 завершены с подтверждёнными проверками. Перед использованием реальных чувствительных данных провести отдельное security review; наличие зелёного CI не объявлять независимым аудитом.

## Команды проверки, которые агент должен обеспечить

Ниже целевые интерфейсы будущего Makefile/репозитория. Сейчас это не выполненные команды.

```bash
make bootstrap
make dev
make migrate
make lint
make typecheck
make test
make test-integration
make test-web
make test-e2e
make build-web
make build-android
make check-contracts
make secret-scan
```

Backend-проверки после реализации:

```bash
cd backend
uv run ruff check .
uv run mypy src
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```

Web: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`, `pnpm exec playwright test`. Android: `./gradlew testDebugUnitTest lintDebug assembleDebug`; instrumented tests выполняются отдельно на доступном emulator/device [R11]. Docker: `docker compose config`, затем проверка запуска и healthchecks.

## Трассировка и ограничения объёма

| Требования | Этап |
|---|---|
| REQ-01–04 | M0, M1; поведение клиентов дополняется M2–M5 |
| REQ-05–06 | M1.4 и проверки во всех последующих модулях |
| REQ-07–09, 11 | M3 |
| REQ-10, 12 | M4 |
| REQ-13–16 | M2, повторение в M5 |
| REQ-17–18 | M2–M5 |
| REQ-19–21 | с M1, outbox с M2, расписания с M3 |
| REQ-22 | M0 baseline, M6 полноценная эксплуатация |
| REQ-23–27 | обязательны при вводе соответствующей поверхности, полная проверка M6 |

После MVP отдельные задачи: вложения и безопасный storage, matrix/ranking, acknowledgement signature UI, балльный ledger, нативный конструктор анкет, дополнительные расписания. E2EE и настоящая анонимность требуют самостоятельных design/security reviews; не добавлять их косметическим переключателем.
