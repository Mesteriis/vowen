# Архитектура и технические контракты

Этот документ задаёт выбранную реализацию. Точные защитные протоколы находятся в `SECURITY.md`; описание функций и идентификаторы требований в `PRODUCT_SPEC.md`.

## 1. Модульный монолит

```text
Telegram Mini App ──┐
                   ├── HTTPS / REST ── Reverse proxy ── FastAPI ── PostgreSQL
Android native ────┘                         │                  │
                                            │             domain services
Guest browser ── /f + guest API ─────────────┘                  │
                                                               │
Telegram Bot API ←── bot process ───────────────────────────────┤
                                                               │
                   worker / schedules / outbox ─────────────────┘
```

API, CLI, bot и worker используют один Python-пакет и предметные сервисы. Это разные процессы одного приложения, не микросервисы. Бот не дублирует бизнес-логику и не вызывает публичные endpoints для обхода прав. Клиенты не подключаются к БД.

Не нужны Redis, Celery, RabbitMQ, Kafka, Kubernetes, service discovery, отдельный auth-server или event sourcing. Уведомления и расписания исполняются отдельным PostgreSQL-backed worker. Вводить новый инфраструктурный компонент можно только отдельным ADR с измеримой необходимостью.

## 2. Стек и совместимость

| Область | Выбранный подход |
|---|---|
| Backend | Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2 async, psycopg 3 async, Alembic |
| CLI | Typer, entrypoint `appctl` |
| Bot | aiogram 3; long polling одним процессом |
| Worker | asyncio loop, расписания и lease-задания в PostgreSQL |
| Web | Vue 3, TypeScript strict, Vite, Vue Router; управление состоянием без копии серверных правил |
| Android | Kotlin, Compose, coroutines, ViewModel; HTTP-клиент с типизированными DTO |
| Contracts | OpenAPI из backend; фиксированная схема и проверяемая генерация клиентских типов |
| Tests | pytest/httpx, реальный PostgreSQL, Vitest, Playwright, Android unit/UI tests |
| Development | uv и lockfile; pnpm и lockfile; Gradle wrapper и version catalog |
| Deployment | Docker Compose; reverse proxy, API, bot, worker, PostgreSQL |

FastAPI предоставляет OpenAPI-интеграцию; async API SQLAlchemy описан в документации соответствующей ветки [R9, R10]. Конкретные версии пакетов и генератора API агент проверяет при bootstrap и фиксирует. Не использовать неизвестные методы библиотек «по памяти».

Одна `AsyncSession` принадлежит одному запросу или одной задаче, не разделяется между параллельными coroutine [R10]. Минимальная Android-версия по умолчанию: API 26; compile/target SDK выбирать по реально установленному стабильному toolchain и фиксировать. Поддержка выбранного toolchain проверяется сборкой, а не названием версии в README.

## 3. Структура будущего репозитория

```text
vowen/
├── AGENTS.md
├── README.md
├── README.ru.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── Makefile
├── compose.yaml
├── .env.example
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── backend/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/vowen/
│   │   ├── main.py
│   │   ├── core/           # config, clock, DB, crypto, errors
│   │   ├── modules/
│   │   │   ├── identity/   # users, provisioning, profiles
│   │   │   ├── auth/       # Telegram assertions, sessions, Android challenges
│   │   │   ├── relations/  # agreements, consent, policy checks, pause
│   │   │   ├── rules/
│   │   │   ├── rituals/
│   │   │   ├── discipline/
│   │   │   ├── rewards/
│   │   │   ├── journal/
│   │   │   ├── forms/
│   │   │   ├── notifications/
│   │   │   └── audit/
│   │   ├── integrations/telegram/
│   │   ├── cli/
│   │   └── worker/
│   └── tests/{unit,integration,contract}/
├── web/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── src/{app,features,shared}/
│   ├── src/entry-miniapp.ts
│   ├── src/entry-guest.ts
│   └── tests/
├── android/
│   ├── gradlew
│   ├── gradle/
│   └── app/
├── contracts/
│   ├── openapi.json
│   └── form-schema/
├── deploy/
│   ├── proxy/
│   ├── Dockerfile.backend
│   └── Dockerfile.web
└── docs/
    ├── PRODUCT_SPEC.md
    ├── ARCHITECTURE.md
    ├── SECURITY.md
    ├── IMPLEMENTATION_PLAN.md
    ├── REFERENCES.md
    ├── STATUS.md
    ├── adr/
    └── operations/
```

Внутри предметного модуля: `models.py`, `schemas.py`, `service.py`, `policy.py`, `router.py`; `repository.py` вводить при полезном разделении, а не ради пустой прослойки. Не создавать заранее сотни пустых файлов для roadmap-функций. Guest entrypoint не загружает Telegram SDK и внутреннюю навигацию. Оба web-entrypoint можно обслуживать с одного origin.

## 4. Модель данных

**REQ-19.** В БД нет `tenant_id`, `couple_id` и повсеместного `dynamic_id`. Единственная строка `instance_settings` имеет `id=1` и CHECK-ограничение. Обычные внутренние ID: UUID. `telegram_id`: уникальный BIGINT; это внешний идентификатор, а не пароль и не PK предметных таблиц. Время событий: `timestamptz`; timezone расписания отдельным IANA-именем.

| Группа | Основные таблицы и смысл |
|---|---|
| Identity | `users`, `user_preferences`, `instance_capabilities`; `users.is_active`, профиль и Telegram ID |
| Auth | `sessions`, `access_tokens`, `refresh_tokens`, `telegram_assertions`, `android_login_challenges` |
| Bot | `bot_contacts`, `processed_bot_updates`; контакт и дедупликация отдельно от аккаунта |
| Relationships | `authority_relations`, `relation_versions`, `agreement_versions`, `agreement_consents`, `user_pauses` |
| Rules | `rules`, `rule_versions`, `rule_assignments`, `rule_assignment_consents` |
| Rituals | `rituals`, `ritual_versions`, `ritual_assignments`, `ritual_assignment_reviewers`, `ritual_occurrences`, `ritual_reports` |
| Discipline | `discipline_records`, `discipline_versions`, `discipline_transitions`, `discipline_reviewers` |
| Rewards | `reward_definitions`, `reward_definition_versions`, `ritual_reward_policies`, `reward_grants` |
| Journal | `journal_entries`, `journal_entry_readers`, `journal_tags` |
| Forms | `forms`, `form_versions`, `form_invitations`, `form_invitation_readers`, `form_submissions`, `guest_sessions`, `submission_receipts` |
| Surveys, M5 | `survey_schedules`, `survey_waves` |
| Operations | `outbox_events`, `scheduled_jobs`, `notification_deliveries`, `audit_events`, `idempotency_records` |

Таблицы создаются по этапам, не все сразу. Любое внешнее отношение обеспечивается FK. Список адресатов API отображается на отдельные строки назначения. Не хранить единственный статус выполнения в шаблоне, если исполнителей несколько.

От прежней идеи универсальной таблицы `Assignments(object_type, object_id)` отказаться: для MVP использовать типизированные назначения с FK. Общий алгоритм проверки адресата/полномочий переиспользуется в сервисах, но не уничтожает целостность схемы.

Ключевые ограничения:

- уникальный `users.telegram_id`; запрет `dominant_user_id=submissive_user_id`;
- одна действующая версия направленной связи;
- уникальность назначения конкретной версии пользователю;
- уникальность occurrence по `(assignment_id, local_date, slot_key)`;
- уникальность автоматической выдачи по `(occurrence_id, reward_policy_version_id, recipient_user_id)`;
- одно итоговое submission на приглашение;
- внутреннее приглашение требует `recipient_user_id`; гостевое запрещает его;
- `start_token_hash`, `poll_secret_hash`, хэши сессионных/гостевых секретов уникальны в своей области;
- `version` для optimistic concurrency на редактируемых объектах;
- опубликованную версию нельзя UPDATE через предметный API.

JSONB подходит для схемы формы, условий и несекретных структурных параметров. Ответы и чувствительные тексты шифруются в отдельном payload. Нельзя одновременно обещать шифрование на уровне приложения и хранить те же ответы открытым `answers_jsonb` для удобства отчётов. Преобразование ciphertext обратно в типизированный JSON происходит только после авторизации.

## 5. Авторизация и видимость

**REQ-20.** Реализовать центральную policy-функцию, вызываемую предметными сервисами. Её вход: principal, действие, объект/целевой пользователь, текущая версия связей и ACL. Она используется одинаково API, ботом и worker. `deny by default`; системная роль не заменяет предметное разрешение [R4].

Principal-типов два: `MemberPrincipal` и `GuestPrincipal`. CLI получает отдельный `OperatorContext`, который не является пользователем со всеми D/s-правами. Гостевой principal запрещён в member-endpoints независимо от совпадения ID.

Объект сначала выбирается в разрешённой области. Фильтрация после загрузки всей группы не должна приводить к утечке через пагинацию, `total`, export или ошибки. Проверка ACL применяется к связанным комментариям, ревизиям и будущим вложениям.

## 6. Контракты API

Версия API: `/api/v1`. Только JSON, кроме будущих загрузок файлов. Команды, зависящие от текущего состояния, передают `expected_version`. Для создания submission, отчёта и выдачи использовать `Idempotency-Key`, ограниченный principal + route + hash тела запроса. Повтор ключа с другим телом: `409`.

| Раздел | Начальные маршруты |
|---|---|
| Health | `GET /health/live`, `GET /health/ready` вне `/api/v1` |
| Telegram auth | `POST /auth/telegram/miniapp` |
| Android auth | `POST /auth/android/challenges`, `POST /auth/android/challenges/{id}/status`, `POST /auth/android/challenges/{id}/consume` |
| Sessions | `POST /auth/refresh`, `POST /auth/logout`, `GET /sessions`, `DELETE /sessions/{id}` |
| Profile | `GET /me`, `PATCH /me/preferences`, `GET /participants` |
| Relations | `POST /relations`, `GET /relations`, `POST /relations/{id}/accept`, `/pause`, `/resume`, `/revoke` |
| Personal pause | `POST /me/pause`, `POST /me/resume` |
| Rules | `/rules`, `/rules/{id}/versions`, `/rule-assignments`, `/rule-assignments/{id}/accept` |
| Rituals | `/rituals`, `/ritual-assignments`, `/ritual-occurrences`, `/ritual-occurrences/{id}/submit`, `/review` |
| Discipline | `/discipline-records`, `/discipline-records/{id}/transitions` |
| Rewards | `/rewards`, `/reward-grants`, `/reward-grants/{id}/transitions` |
| Journal | `/journal`, `/journal/{id}`, `/journal/{id}/readers` |
| Forms management | `/forms`, `/forms/{id}/versions`, `/forms/{id}/publish`, `/form-invitations`, `/form-invitations/{id}/revoke` |
| Internal responses | `/my/form-invitations`, `/my/form-invitations/{id}/draft`, `/submit`, `/form-submissions/{id}` |
| Guest | `POST /guest/invitations/exchange`, `GET /guest/form`, `PUT /guest/draft`, `POST /guest/submit`, `DELETE /guest/submission` |
| Guest receipt | `POST /guest/receipts/exchange` |
| Export | `POST /me/exports`, `GET /me/exports/{id}`; restricted by current ACL |

Маршруты таблицы без метода означают REST-коллекцию с явно разрешёнными операциями, а не разрешение на произвольный CRUD. Перед реализацией этапа описать точные DTO и методы в OpenAPI. `/register`, `/signup`, `POST /users` и callback с автопровижинингом отсутствуют.

Ошибка:

```json
{"error":{"code":"ACCESS_DENIED","message":"Недостаточно прав","request_id":"..."}}
```

`401`: нет действующей аутентификации; `403`: аутентифицированный субъект не допущен к операции; `404`: объект отсутствует либо скрыт от этого субъекта; `409`: конфликт версии/идемпотентности; `422`: ошибка данных; `429`: ограничение частоты. Невалидная Telegram-подпись даёт `401`; валидный Telegram без активного локального пользователя даёт одинаковый `403 ACCESS_DENIED` для неизвестного и отключённого аккаунта.

`GET /participants` доступен только активному member и возвращает минимальный список активных участников для выбора стороны связи: UUID, display name, необязательные профильные метки. Telegram ID, сессии, приватные записи и скрытые отношения не выдаются. Списки доступных адресатов конкретного действия дополнительно фильтруются policy.

Публичная форма страницы `/f/{public_id}` не является API-чтением формы: до предъявления секрета отдаётся только нейтральная оболочка.

## 7. CLI

Требуемые интерфейсы будущей утилиты, не утверждение о существующих командах:

```bash
appctl instance init
appctl users create --telegram-id 100000000001 --display-name "Demo D1"
appctl users list
appctl users disable --telegram-id 100000000001
appctl users enable --telegram-id 100000000001
appctl users revoke-sessions --telegram-id 100000000001
appctl users grant-capability --telegram-id 100000000001 --capability forms.create
appctl relations propose --dominant-id USER_UUID_A --submissive-id USER_UUID_B
appctl forms invite --form FORM_UUID --user USER_UUID --expires-in 7d
appctl forms invite --form FORM_UUID --external --expires-in 7d
appctl forms invite --form FORM_UUID --external --telegram-id 100000000099 --expires-in 7d
appctl forms revoke-invitation --invitation INVITATION_UUID
appctl jobs inspect
appctl doctor
```

Числа и имена примера синтетические. `forms invite` выполняет те же проверки согласованной аудитории, что UI. `--telegram-id` для внешней доставки адресует контакт, не создаёт аккаунт и не подтверждает личность отвечающего по bearer-ссылке. `instance init` идемпотентен и не заменяет ключи существующей установки. Повтор создания пользователя завершается понятной ошибкой без изменения существующего аккаунта.

## 8. События, задачи и транзакции

**REQ-21.** Доменные события внутри монолита: `relation.activated`, `relation.paused`, `rule.accepted`, `ritual.submitted`, `ritual.approved`, `reward.granted`, `form.submitted`. Изменение бизнес-состояния и запись outbox происходят в одной DB-транзакции.

Worker атомарно забирает пачку задач через `FOR UPDATE SKIP LOCKED`, записывает lease и фиксирует транзакцию до сетевого вызова. PostgreSQL документирует этот механизм как подходящий для queue-like таблиц, не как универсальный согласованный snapshot [R7].

Начальные настройки проекта: lease 120 секунд; продление при длительной работе; максимум 8 попыток; backoff с jitter и потолком 1 час. После исчерпания попыток задача получает `failed`, видима оператору и может быть повторена вручную. Нужны обработка `retry_after` Telegram, метрики без чувствительных меток и повторная проверка актуальных разрешений.

Гарантия обработки: at-least-once с идемпотентными эффектами в БД. Не заявлять exactly-once отправку Telegram: при падении между отправкой и фиксацией результата повторное сообщение возможно. Для наград и итоговых ответов дубликаты запрещены DB-ограничениями.

Событие содержит ID и минимальные метаданные, а не полный дневник/ответ. Секретную ссылку приглашения для отложенной доставки допустимо положить только в зашифрованный краткоживущий payload доставки, удаляемый после отправки/истечения срока. Проверочный секрет самого приглашения остаётся только в хэшированном виде. Не создавать plaintext-копию ради worker.

## 9. Время и расписания

Системные моменты времени сохраняются в UTC, локальный день occurrence сохраняется отдельно. Тесты используют внедряемый Clock, а не реальные часы.

MVP-политика DST: если локальное время отсутствует при переходе вперёд, сдвинуть его на длительность разрыва; при повторяющемся времени выбрать первое вхождение (`fold=0`). Например, событие не должно появляться дважды только из-за перевода часов назад. Правило показывается в настройках и покрывается timezone-тестами.

При простое восстановить отсутствующие occurrence от сохранённого watermark до текущего дня, не перегенерировать существующие. Истёкшие получают `missed`; уведомления за давно прошедшие слоты не отправлять пачкой. Ограничить объём catch-up одной итерации и продолжать следующей. Изменение расписания создаёт новую версию и затрагивает только ещё не начатые будущие occurrence.

## 10. Self-hosting и эксплуатация

**REQ-22.** Один Compose-проект: proxy, api, bot, worker, db и одноразовый service миграций. Persistent volumes для PostgreSQL и будущих файлов. База не публикуется на внешний интерфейс. API не стартует с несовместимой схемой. Секреты читаются из защищённых файлов/environment, никогда не включаются в image или web runtime config.

Настройки: `PUBLIC_BASE_URL`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN_FILE`, `DATA_KEYRING_FILE`, `APP_DISPLAY_NAME`, `DEFAULT_TIMEZONE`, `LOG_LEVEL`. Не включать пользовательский Telegram ID в публичный пример конфигурации.

HTTPS обязателен для production. Адрес должен быть достижим клиентами; гостю вне домашней сети требуется достижимый адрес или настроенный доступ к сети. Self-hosting не означает автоматическую работу публичных приглашений на недоступном LAN-адресе. Бот по умолчанию использует исходящий long polling; публичный Telegram webhook не нужен.

Обязательны healthchecks, graceful shutdown, минимальные privileges контейнеров, лимиты запросов и размеров тела. Настройки доступа к FastAPI docs/OpenAPI в production отделить от необходимости иметь публичный `contracts/openapi.json` в OSS-репозитории.

До объявления MVP рабочим нужны проверенные инструкции backup/restore: БД, вложения при наличии и ключи с независимым защищённым хранением. Восстановление проверяется на отдельной установке синтетическим зашифрованным ответом. Обновление включает backup, миграцию и описанную стратегию возврата через восстановление; не обещать безопасный downgrade любой миграции.
