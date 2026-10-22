# Wiki Knowledge Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Общая Wiki с деревом знаний, энциклопедическими карточками и статьями, административной редактурой и чтением на компьютере и телефоне.

**Architecture:** Отдельный модуль Wiki существующего монолита. Неизменяемые редакции и раздельные указатели черновика/публикации обеспечивают чтение согласованного снимка; ссылки используют конкретные FK справочников. Web и Android используют единый API без фильтра отношений.

**Tech Stack:** FastAPI/Pydantic, SQLAlchemy async, PostgreSQL/Alembic, Vue/TypeScript, Kotlin/Compose; CommonMark без HTML и внешних изображений.

**Spec:** [Согласованная спецификация](../specs/2026-10-21-wiki-knowledge-tree-design.md).

## Global Constraints

- Только локальная реализация и проверки: без сборок, коммитов, push и удалённого развёртывания. Прежние изменения справочников сохранить.
- Чтение — активным участникам; мутации, черновики, архив и история — только администраторам. D/s-роль и выбранные отношения не определяют доступ.
- Глубина разделов 8; заголовок 160, summary 600, Markdown 100 000 символов; 50 связей каждого вида, 20 источников.
- Поиск: запрос до 200 символов, выдача до 50 записей за страницу. Ни скрытые данные, ни их счётчики читателю не возвращаются.
- Источники только http/https без credentials; миниатюры — существующая локальная статика. Никаких загрузок, удалённых изображений и серверного обхода URL.
- Черновики в памяти клиента; без localStorage/IndexedDB. Ошибка сети/403/409 не стирает ввод.
- Блокировки записи: AdministrationState → WikiTreeState → WikiPage; повторная проверка администратора после первой блокировки.
- Web проверяется на 390/768/1024/1440 px; касания ≥44 CSS px, keyboard/reduced-motion/safe-area. Android пока source-only.
- Перед миграцией preview-БД — закрытая резервная копия. PostgreSQL тестов отделён от preview и production.

## Review Focus

1. Черновик переместили и переименовали: читатель продолжает видеть прежнюю публикацию, её раздел, ссылки и счётчики — Task 2.
2. Два администратора одновременно сохраняют или создают цикл дерева: одна операция получает 409/422, состояние целостно — Task 3.
3. Административную роль отозвали во время редактирования: следующая запись 403, клиент сохраняет текст — Tasks 3/6.
4. Повторили импорт после ручной правки или архивирования: обе записи остаются неизменными, новых дубликатов нет — Task 4.
5. Устаревший поисковый ответ приходит после нового; Back и закрытие мобильного дерева не теряют выбранную страницу — Task 5.

---

## Карта файлов и границы

Новые Python-файлы в `backend/src/vowen/modules/wiki/`: `models.py` — хранение; `schemas.py` — DTO/лимиты; `queries.py` — опубликованные проекции; `pages.py` — редакции; `sections.py` — дерево; `seed.py` — импорт; `router.py` — HTTP; `__init__.py` — пакет. Нет универсального репозитория.
Новые Web-файлы в `web/src/features/wiki/`: `WikiPanel.vue` — экран; `WikiTree.vue` — дерево/drawer; `WikiReader.vue` — чтение; `WikiEditor.vue` — форма; `WikiSections.vue` — управление разделами; `api.ts`, `state.ts`, `markdown.ts`, `wiki.css` — соответствующие обязанности.
Android: новые `WikiApi.kt`, `WikiState.kt`, `WikiMarkdown.kt`, `NativeWikiScreen.kt`, `NativeWikiEditor.kt`, `NativeWikiSections.kt`; существующие общие файлы меняются только для DTO, зависимости и навигации.
Точные тестовые файлы перечислены в задачах. Публичную документацию добавить в `docs/features/wiki.md`; статус — в существующем `docs/STATUS.md`.

### Task 1: Хранение и ограничения PostgreSQL

**Files:** Create `backend/migrations/versions/0051_wiki.py`, `backend/src/vowen/modules/wiki/{__init__,models,schemas}.py`; Modify `backend/src/vowen/core/database.py`; Test `backend/tests/integration/test_wiki_storage.py`, `backend/tests/unit/test_wiki_schemas.py`.

**Interfaces:**
- Produces ORM `WikiSection`, `WikiTreeState`, `WikiPage`, `WikiRevision`, `WikiRevisionPractice`, `WikiRevisionPose`, `WikiRevisionDevice`.
- Produces DTO `WikiDocument(section_uid: UUID, title: str, summary: str, body: str, thumbnail: str | None, practice_uids: list[UUID], pose_uids: list[UUID], device_uids: list[UUID], sources: list[WikiSource])`; `WikiSource(name: str | None, url: str)`.
- Produces `WikiPageCreate(kind: Literal['encyclopedia','article'], practice_uid: UUID | None, pose_uid: UUID | None, device_uid: UUID | None, document: WikiDocument)` and `WikiPageSave(expected_version: int, document: WikiDocument)`.

- [ ] Написать red-тесты: статья без основного объекта допустима; энциклопедия с 0/2 основными объектами запрещена; повторный основной FK запрещён; удаление основного объекта RESTRICT; указатель на редакцию чужой страницы запрещён; лимит+1 отклоняется; внешняя/несуществующая миниатюра и credential URL отклоняются.
- [ ] Запустить `TEST_DATABASE_URL=$WIKI_TEST_DATABASE_URL uv run --project backend pytest backend/tests/integration/test_wiki_storage.py backend/tests/unit/test_wiki_schemas.py -q`; ожидается FAIL до реализации.
- [ ] Создать таблицы: sections(uid,parent_uid,title,description,sort_order,version); singleton tree_state(id=1,version); pages(uid,kind,practice_uid,pose_uid,device_uid,draft_revision_uid,published_revision_uid,archived_at,version); revisions(uid,page_uid,section_uid,title,summary,body,thumbnail,sources JSONB,author_id,created_at,published_at). Основной объект после создания неизменяем. Сохранённые поля редакций неизменяемы; published_at устанавливается однократно при первой публикации.
- [ ] Добавить CHECK one-of, unique основных FK, составные FK указателей (page_uid,revision_uid), FK разделов и авторов RESTRICT, три revision-link таблицы с составными PK и конкретными FK. Пустота раздела учитывает исторические редакции: сначала перенести активное содержимое, исторически использованный раздел не удалять, вернуть 409 с объяснением.
- [ ] Миграция создаёт только Wiki-таблицы и четыре корня со стабильными UUID; карточки не импортирует. Проверить head=0050 перед назначением 0051, обновить SCHEMA_REVISION после проверки миграции. Выполнить upgrade/downgrade/upgrade на отдельной PostgreSQL БД, сравнить прежние таблицы до/после; повторить тесты до PASS.

### Task 2: Чтение, дерево и поиск без утечки черновиков

**Files:** Create `backend/src/vowen/modules/wiki/{queries,router}.py`, `backend/tests/integration/test_wiki_read.py`; Modify `backend/src/vowen/main.py`, `backend/src/vowen/modules/wiki/schemas.py`.

**Interfaces:**
- `published_page(db: AsyncSession, uid: UUID) -> WikiPageView`; `wiki_tree(db: AsyncSession) -> WikiTreeView`; `search_pages(db: AsyncSession, q: str, section_uid: UUID | None, offset: int, limit: int) -> WikiSearchView` in queries.py.
- `WikiPageView`: uid,kind,version,main reference fields,revision_uid,document,author_id,created_at,published_at,related_pages. `WikiPageSummary`: uid,kind,title,summary,section_uid,thumbnail,published_at. `WikiTreeView`: version,sections (uid,parent_uid,title,description,sort_order,version),pages (summaries). `WikiSearchView`: items,total,offset,limit.
- Member HTTP: `GET /api/v1/wiki/tree`, `/pages/{uid}`, `/search?q=&section_uid=&offset=0&limit=50`.

- [ ] Написать `test_published_projection_never_uses_draft`: опубликовать A, сохранить B с другим названием/разделом/связями; page/tree/search/related_pages содержат только A, поиск B даёт 0. `test_hidden_pages_return_404` проверяет draft/archive прямым запросом, включая администратора в member endpoint. Без сессии 401; inactive отказ; личная/отношенческая пауза не закрывает Wiki.
- [ ] Запустить `TEST_DATABASE_URL=$WIKI_TEST_DATABASE_URL uv run --project backend pytest backend/tests/integration/test_wiki_read.py -q`; ожидать FAIL.
- [ ] Реализовать одну опубликованную SQL-проекцию: archived_at IS NULL + JOIN published_revision_uid; использовать её для всех четырёх поверхностей и total. Связанные страницы — публикации с пересечением reference UID, не более 20, стабильный порядок uid. Текущее справочное описание загружать через уже существующий references API.
- [ ] Поиск literal case-insensitive substring по title/summary/body, без интерпретации `%`/`_` как пользовательских wildcard; стабильный порядок title,uid. Пустой q выводит опубликованный список; фильтр раздела включает потомков. Лимиты 200/50, offset≥0, ошибок с echo входного текста нет.
- [ ] Подключить router через Member/DB проекта; не логировать q/body. Проверить пустые разделы без скрытых счётчиков, Unicode, пагинацию, пределы и отсутствие journal/profile данных; повторить тесты до PASS.

### Task 3: Административная редактура и конкурентные изменения

**Files:** Create `backend/src/vowen/modules/wiki/{pages,sections}.py`, `backend/tests/integration/test_wiki_admin.py`, `backend/tests/integration/test_wiki_concurrency.py`; Modify Wiki router/schemas.

**Interfaces:**
- pages.py: `create_page(db, actor_id, command: WikiPageCreate) -> WikiEditView`; `save_page(db, actor_id, uid, command: WikiPageSave) -> WikiEditView`; `publish_page(db, actor_id, uid, command: WikiPublish) -> WikiEditView`; `set_archived(db, actor_id, uid, command: WikiArchive) -> WikiEditView`. db: AsyncSession; IDs UUID; actor_id UUID.
- `WikiPublish(expected_version: int, revision_uid: UUID)`; `WikiArchive(expected_version: int, archived: bool)`; `WikiEditView(uid,kind,version,main reference fields,draft_revision_uid,published_revision_uid,archived_at,document)`.
- sections.py: `save_section(db: AsyncSession, actor_id: UUID, uid: UUID | None, command: WikiSectionSave) -> WikiTreeView`; `delete_section(db, actor_id, uid, expected_version: int, expected_tree_version: int) -> WikiTreeView`.
- `WikiSectionSave(title,description,parent_uid,sort_order,expected_version: int | None,expected_tree_version: int)`; section titles160/descriptions600.
- Admin HTTP prefix `/api/v1/wiki/admin`: POST /pages, GET /pages?state=drafts|published|archived (paginated), GET/PATCH /pages/{uid}, POST /pages/{uid}/publish, POST /pages/{uid}/archive, GET /pages/{uid}/revisions, GET /pages/{uid}/revisions/{revision_uid}, POST /sections, PATCH/DELETE /sections/{uid}. Revision detail returns saved document, author/time; history paginated≤50.

- [ ] Написать red-тесты: member403 для каждой admin операции; save создаёт редакцию без изменения публикации; publish принимает только принадлежащую странице сохранённую редакцию с непустыми title/body; archive/restore сохраняет оба указателя; старый expected_version409.
- [ ] Запустить `TEST_DATABASE_URL=$WIKI_TEST_DATABASE_URL uv run --project backend pytest backend/tests/integration/test_wiki_admin.py backend/tests/integration/test_wiki_concurrency.py -q`; ожидать FAIL.
- [ ] Реализовать подписи pages.py; в каждой мутации сначала lock AdministrationState и administrator(db,actor_id), затем tree_state и страницу; обновлять version один раз за успешную мутацию. Все операции в существующей request transaction; никаких внутренних commit или внешних вызовов.
- [ ] Реализовать подписи sections.py и атомарный обход предков/потомков под tree lock; запретить self/descendant, 9-й уровень и перемещение поддерева с превышением8. Delete непустого/исторически используемого узла409. Порядок siblings: sort_order,uid. GET admin требует administrator(), не выдаёт данные до проверки.
- [ ] Написать/выполнить конкурентные PG-тесты отдельными session: два save одной version→ровно1успех+1конфликт; перекрёстные move→нет цикла; publish против save→цель публикации не подменяется; отзыв админа, завершившийся перед получением admin lock,→403 и нет новой редакции. Повторить оба файла до PASS.

### Task 4: Явное идемпотентное наполнение

**Files:** Create `backend/src/vowen/modules/wiki/seed.py`, `backend/tests/integration/test_wiki_seed.py`; Modify Wiki router/schemas.

**Interfaces:** `seed_reference_pages(db: AsyncSession, actor_id: UUID) -> WikiSeedResult(created: int, skipped: int)`; POST `/api/v1/wiki/admin/seed-references` без клиентского текста.

- [ ] Написать `test_seed_is_idempotent_and_preserves_edits_and_archives`: исходный fixture snapshot→261 создано (93/106/62); повтор→0; отредактировать и архивировать разные страницы, повтор→оба неизменны. Добавленный пользователем reference→ровно1 новая карточка. Member403.
- [ ] Запустить `TEST_DATABASE_URL=$WIKI_TEST_DATABASE_URL uv run --project backend pytest backend/tests/integration/test_wiki_seed.py -q`; ожидать FAIL.
- [ ] Импортировать текущие записи конкретных таблиц под общей admin/tree блокировкой, UUIDv5 с постоянным namespace Wiki и ключом kind:reference_uid. Создавать отсутствующие страницы и первую опубликованную редакцию; основные FK unique защищают повтор. Разделы категорий создавать со стабильными UUID под соответствующими корнями; девайсы без категории — в корне.
- [ ] Текст брать из существующего description с пометкой «Краткая справочная карточка»; сохранять редакционное происхождение и ограниченные безопасные источники, без расширения сексуальных описаний и выдуманных медицинских рекомендаций. Невалидный исходный thumbnail/URL пропускать, источник не скачивать. Не обновлять существующие страницы, включая архив.
- [ ] Проверить одновременный двойной импорт и rollback на искусственном сбое; повторить тесты до PASS. Сам импорт preview выполнять только явно при приёмке Task8.

### Task 5: Web — чтение и адаптивная навигация

**Files:** Create `web/src/features/wiki/{api.ts,state.ts,markdown.ts,WikiPanel.vue,WikiTree.vue,WikiReader.vue,wiki.css}`, `web/tests/wiki-state.test.ts`, `web/tests/wiki-markdown.test.ts`; Modify `web/src/features/workspace/context.ts`, `web/src/App.vue`, `web/package.json`, `web/pnpm-lock.yaml`; contract outputs `contracts/openapi.json`, `web/src/shared/api.d.ts`, `android/app/src/main/java/org/vowen/app/ApiModels.kt`.

**Interfaces:** api.ts consumes generated Wiki DTOs and existing client; exports `createWikiApi(client)` with tree(),page(uid),search(q,sectionUid,offset),admin methods matching Tasks3/4. state.ts exports `useWikiState(api)` exposing pageUid,sectionUid,query,tree,page,results,error,loading,openPage(uid),openSection(uid),search(q),restore(location). markdown.ts exports `parseWikiMarkdown(source: string): {tokens: Token[], headings: {id:string,text:string,level:number}[]}`.

- [ ] Написать red-тесты state: поздний ответ старого поиска игнорируется, ошибка не стирает предыдущую страницу; restore восстанавливает node/query; repeated headings имеют уникальные anchor ID. Markdown `<script>`, iframe, javascript/data/file URLs и `![x](https://...)` не создают исполняемые/загружаемые узлы; текст экранирован.
- [ ] Запустить `pnpm --dir web test -- tests/wiki-state.test.ts tests/wiki-markdown.test.ts`; ожидать FAIL.
- [ ] Выполнить `make contracts` и contract-тест после появления API. Добавить pinned markdown-it 14.1.0 + совместимые типы с lockfile. CommonMark mode, HTML/linkify/typographer off; image tokens только текст, URL allowlist http/https без credentials либо локальные #anchors. Tokens отрисовывать Vue-узлами с escaped text, без v-html; поддержать paragraphs/headings/emphasis/strong/lists/quotes/code/links/thematic breaks. Остальные tokens — текст.
- [ ] Реализовать WikiReader и дерево как вложенные disclosure-списки с кнопками, breadcrumbs, источниками, связанными страницами и текущими справочными панелями. Формировать slug из порядка heading (`heading-1` и т.д.), одинаково на обеих платформах. Читать максимум70ch; TOC сбоку только при достаточной ширине.
- [ ] Добавить Section='wiki', label/icon и WikiPanel в App; без глобальной смены CSS. Hash-навигация `#wiki?page=UUID&section=UUID&q=...`, push для нового перехода и корректный browser Back. Drawer «Разделы» закрывается после выбора/по Escape, возвращает фокус; phone через «Ещё»; не привязываться к выбранным отношениям.
- [ ] Использовать контейнерные пороги 48rem для tree+reader и 78rem для дополнительного TOC; подтвердить по реальному доступному контейнеру, скорректировать только Wiki CSS при визуальной проверке. Переход150ms, reduced-motion0, safe-area и touch44. Повторить тесты до PASS, выполнить `pnpm --dir web typecheck` и `pnpm --dir web lint`.

### Task 6: Web — редактор, разделы, история и импорт

**Files:** Create `web/src/features/wiki/{WikiEditor.vue,WikiSections.vue,editor.ts}`, `web/tests/wiki-editor.test.ts`; Modify WikiPanel/api/state.

**Interfaces:** editor.ts exports `useWikiEditor(api)` with document,version,dirty,error,saving,load(uid),save(),publish(),archive(bool),reload(); consumes WikiEditView/commands; keeps state in memory. WikiEditor emits saved/close; WikiSections emits changed and consumes tree.version/section.version.

- [ ] Написать red-тесты: save409/403/network оставляет document и dirty, publish сначала сохраняет изменённый ввод и отправляет именно возвращённый revision_uid; отмена unsaved navigation оставляет редактор; смена admin на member убирает команды без стирания формы.
- [ ] Запустить `pnpm --dir web test -- tests/wiki-editor.test.ts`; ожидать FAIL.
- [ ] Реализовать поля, pickers existing references, toolbar/preview с Task5 renderer, лимиты Task1; отдельные «Сохранить черновик»/«Опубликовать». Режимы черновики/архив, история редакций с read-only preview, archive/restore. 409 предлагает явно загрузить свежую версию; обычный refresh её автоматически не заменяет.
- [ ] Реализовать создание/правку/перемещение разделов через picker+кнопки и явное сохранение; показать server conflict/cycle/depth/nonempty errors. Добавить admin-кнопку первичного импорта с created/skipped и перезагрузкой дерева.
- [ ] Подключить единый unsaved guard внутренних переходов, browser Back и beforeunload; после подтверждённого ухода очистить память. На телефоне формы single-column, действия не перекрываются клавиатурой. Повторить unit-тесты до PASS; ролевой end-to-end цикл входит в Task8.

### Task 7: Native Android — тот же контракт и сценарии

**Files:** Create `android/app/src/main/java/org/vowen/app/{WikiApi.kt,WikiState.kt,WikiMarkdown.kt,NativeWikiScreen.kt,NativeWikiEditor.kt,NativeWikiSections.kt}`, `android/app/src/test/java/org/vowen/app/WikiStateTest.kt`; Modify `WorkspaceScreen.kt`, `ApiModels.kt`, `android/gradle/libs.versions.toml`, `android/app/build.gradle.kts` и dependency locks при разрешённом последующем Gradle-запуске.

**Interfaces:** suspend extension methods Api.wikiTree(),wikiPage(uid:String),wikiSearch(q:String,sectionUid:String?,offset:Int),admin methods mirror Task3/4 DTO; WikiState owns selection/query/draft in memory. `@Composable NativeWikiScreen(api: Api, isAdmin: Boolean, ru: Boolean)` owns responsive reader/editor/tree. `parseWikiMarkdown(source:String): List<WikiBlock>` in WikiMarkdown.kt produces typed plain-text/heading/list/quote/code/link nodes for Compose, no WebView.

- [ ] Добавить regression source/JUnit cases late search, in-memory error retention, navigation restoration и shared Markdown payloads Task5. Пометить тесты unrun до разрешения сборок; не выдавать добавление тестов за выполнение.
- [ ] Добавить pinned org.commonmark:commonmark:0.24.0, AST→Compose allowlist с теми же links/images/HTML правилами; mapping DTO из contract outputs, сеть только через существующий Api транспорт.
- [ ] Интегрировать Wiki во все варианты WorkspaceScreen, More на телефоне; дерево drawer, breadcrumbs/TOC, reader width, back handling. Admin editor/sections/history/import повторяют Task6; lower роли получают только чтение. Не включать Wiki в общий eager workspace() загрузчик.
- [ ] Проверить исходники/DTO генератором и source contract assertions; зафиксировать Android source-only: compile, JUnit/device/screenshot и dependency-lock resolution не проверены, пока сборки запрещены. Не запускать Gradle ради скрытой сборки.

### Task 8: Контракт, локальная приёмка и документация

**Files:** Create `backend/tests/contract/test_wiki.py`, `docs/features/wiki.md`; Modify `docs/STATUS.md`. Evidence only ignored `artifacts/deployment/wiki-20261021/`.

**Interfaces:** проверяет полностью Tasks1–7; не создаёт новых продуктовых API.

- [ ] Добавить contract assertions всех путей/DTO, одинаковые лимиты, canonical OpenAPI==app.openapi(); проверить fixture ownership, API права и полный цикл save→publish→draft edit→archive→restore через localAPI.
- [ ] Запустить backend Wiki unit/integration/contract tests на выделенной PostgreSQL, ruff/mypy затронутого модуля; Web tests/typecheck/lint. `make contracts` выполнить повторно, сравнить generated output byte-for-byte с первым результатом; не применять baseline-dependent make check-contracts как ложный провал из-за прежнего uncommitted diff.
- [ ] Перед preview upgrade использовать backup_database из scripts/seed_debug_space.py; сохранить backup приватно в ignored .superpowers/debug-backups. Применить только0051 к preview, перезапустить локальный API для SCHEMA_REVISION, проверить ready и сохранность3debug участников/справочников. Выполнить admin seed и повтор:261/0 на исходных fixture данных, точные live количества записать.
- [ ] Через браузер с настоящим API проверить desktop+390/768/1024/1440: чтение, поиск, дерево, empty states, mobile More/drawer/Back, editor/publish/history/section move/archive/restore; member403, конфликт двух редакторов, потерю роли, network failure без потери ввода. Проверить клавиатуру/focus/reduced-motion, screenshots в ignored evidence. Изменения админов для проверки восстановить.
- [ ] Просмотреть diff на границы задачи и утечки. Обновить wiki.md (маршруты, права, import, ограничения, миграция/rollback) и STATUS точными результатами; отдельно указать Android source-only и любые unrun checks. Никаких production изменений, сборок, коммитов или push.

## Проверки и окружение выполнения

`WIKI_TEST_DATABASE_URL` — только выделенная локальная PostgreSQL тестов; предварительно проверить имя БД, conftest очищает таблицы. Preview БД не использовать в pytest. Операции миграции: `DATABASE_URL=$WIKI_TEST_DATABASE_URL uv run --project backend alembic -c backend/alembic.ini upgrade head`; обратный переход проверять только scratch БД. Секреты/токены в вывод не печатать.
Две новые Markdown-зависимости выбраны по существующим upstream релизам: [markdown-it14.1.0](https://github.com/markdown-it/markdown-it/releases/tag/14.1.0), [commonmark-java0.24.0](https://github.com/commonmark/commonmark-java/releases/tag/commonmark-parent-0.24.0). Это не заявление об отсутствии уязвимостей; перед установкой проверить актуальные advisories и безопасную совместимую версию, изменение pin отразить здесь и в lockfile.

## Самопроверка плана

Покрытие: spec1–3→Tasks1/2/4; spec4→5/7; spec5→3/6/7; spec6→1–3/5–7; spec7–8→8; spec9 сохранён Global Constraints. Все пять Review Focus назначены тестам. DTO и endpoint имена едины, пропуски реализации не скрыты под зелёными проверками. План проверен до передачи пользователю; продуктовый код пока не изменён.

## Выполнение 2026-10-21

Tasks1–6 реализованы; backend/schema/contract/Web unit проверки выполнены.
Task7 реализован в исходниках и DTO; Android compilation/JUnit/device/Gradle locks
не выполнялись по запрету сборок. Task8: миграции/локальный импорт/155static assets,
364backend+17scripts+53Web tests, typecheck/lint/ruff/mypy и независимый финальный
разбор завершены. Browser: UI publish/read/tree,390pxdrawer, поиск, новый discard dialog с
сохранением текста при отмене, начальный фокус, Back/Forward и реальные
390/768/1024/1440CSSpx проверены после снятия native confirm. Физические устройства
и системный reduced-motion не проверялись. Точный отчёт в docs/STATUS.md, рабочий ledger сохранён локально.
Решения относительно плана: markdown-it15.0.3 с собственными типами вместо14.1.0;
public WikiPageView без mutable version; NativeWikiScreen принимает remembered
WikiState с WikiApi поверх existing Api; локальный async dialog вместо confirm.
Без коммитов/сборок/публикации; checkout и scratch evidence сохранены.
