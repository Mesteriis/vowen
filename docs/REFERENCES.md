# Первичные источники и границы проверенного

Проверено при подготовке задания: 15 октября 2026 года. Ссылки ниже используются для технических ограничений и API-поведения. Они не означают, что приложение уже реализовано или проверено с этими библиотеками.

Архитектура, числовые TTL, limits, выбор MIT, рабочее название и порядок этапов являются решениями этого задания. Это не требования внешних платформ. Агент повторно проверяет актуальные документы при реализации, особенно версии зависимостей и Android toolchain.

## R1. Telegram Mini Apps

Официальная документация: `https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app`

Подтверждает передачу исходного `initData` на backend, проверку HMAC, использование `auth_date` против устаревших данных и запрет доверия к `initDataUnsafe`. Не задаёт выбранный здесь TTL 300 секунд. Не смешивать процедуру с отдельно описанной third-party Ed25519-проверкой.

## R2. Telegram Bot Features: deep linking

Официальная документация: `https://core.telegram.org/bots/features#deep-linking`

Подтверждает start payload, разрешённый алфавит и максимум 64 символа. Собственный Android challenge-flow является проектным протоколом поверх этих механизмов, не официальным Telegram OAuth flow.

## R3. Telegram Bots: ограничения начала разговора

Официальная документация: `https://core.telegram.org/bots#how-are-bots-different-from-users`

Описывает ограничение начала диалога ботом. Приложение не должно считать один Telegram ID достаточным для произвольной личной доставки. Возможность писать проверяется по реальному разрешённому контексту взаимодействия.

## R4. OWASP Authorization Cheat Sheet

Первичный источник рекомендаций OWASP: `https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html`

Основание для deny-by-default, проверки полномочий на каждом запросе и relationship/attribute-based подхода. Конкретные D/s-scopes и ACL-модель являются проектным решением.

## R5. OWASP Session Management Cheat Sheet

Первичный источник: `https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html`

Описывает жизненный цикл session identifiers, угрозы их утечки и cookie-защиту. Volatile bearer transport Mini App выбран в задании как отдельный компромисс; OWASP не цитируется как универсальное одобрение хранения refresh token в JavaScript.

## R6. Android Keystore

Официальная документация: `https://developer.android.com/privacy-and-security/keystore`

Keystore управляет криптографическими ключами и их использованием. Поэтому приложение шифрует refresh token ключом Keystore и сохраняет encrypted blob отдельно, а не «кладёт строку токена в Keystore».

Дополнительная официальная документация алгоритмов: `https://developer.android.com/privacy-and-security/cryptography`

## R7. PostgreSQL 17: SELECT и SKIP LOCKED

Официальная документация: `https://www.postgresql.org/docs/17/sql-select.html#SQL-FOR-UPDATE-SHARE`

Описывает пропуск заблокированных строк и применимость к нескольким потребителям queue-like таблицы. Она не даёт exactly-once гарантии для внешней Telegram-доставки; lease, дедупликация и идемпотентность задаются приложением.

## R8. cryptography: AEAD

Документация разработчиков: `https://cryptography.io/en/stable/hazmat/primitives/aead/`

Описывает AESGCM, nonce, associated data и отказ проверки при несоответствии ключа/данных. Для реализации использовать проверенную стабильную версию, записанную в lockfile; не привязывать проект к плавающей dev-ветке документации.

## R9. FastAPI

Официальная документация: `https://fastapi.tiangolo.com/`

Основание для выбранного web framework, OpenAPI и схем запросов/ответов. Не является результатом сравнительного benchmark Python и Go для этого проекта.

## R10. SQLAlchemy 2 asyncio

Официальная документация: `https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html`

Описывает async engine/session и ограничения совместного использования session в параллельных задачах. Поддержку выбранного DB driver и сочетания версий агент проверяет фактическими интеграционными тестами.

## R11. Android command-line builds

Официальная документация: `https://developer.android.com/build/building-cmdline`

Основание для сборки через Gradle wrapper и различения debug/release APK. Наличие файлов Gradle не доказывает успешную сборку: нужен результат запуска toolchain.

## R12. MIT license template

Официальный для сервиса выбора лицензии шаблон GitHub: `https://choosealicense.com/licenses/mit/`

Использовать полный стандартный текст MIT. Выбор MIT предложен для этого задания; заказчик отдельно не выбирал лицензию. Не добавлять в текст лицензии собственные ограничения аудитории, которые изменят стандартную лицензию. Функциональные ограничения продукта описывать отдельно.

## Что здесь не проверено

- Занятость Vowen как бренда, домена, repository slug или имени в магазинах.
- Реальная идентичность/юридическое имя будущего владельца репозитория.
- Наличие у исполняющего агента GitHub write permissions, Telegram token, домена и Android SDK.
- Допустимость и условия публикации приложения в конкретном магазине.
- Правовые обязанности конкретного оператора в конкретной юрисдикции.
- Фактическая безопасность, сборка и тесты будущего приложения: исходный код ещё должен быть создан.

### Plain velvet interface background (2026-10-15)

`web/public/brand/vowen-velvet-texture.webp` is a generated texture created using the
built-in image generation tool; it is not a participant photo. Final prompt:

> Seamless repeating website background texture. Square flat edge-to-edge macro
> photograph of very dark black velvet, dense soft short pile, fine irregular
> directional fibers, subtle charcoal highlights and deep black shadows. Uniform
> small-scale matte texture, orthographic straight-on diffuse grazing light,
> tileable edges. No emblem, logo, text, objects, people, folds, spotlight or vignette.

The owner-supplied velvet emblem remains unchanged. Its outer background is softly
masked in CSS so it blends into this separate page texture, without scaling the
emblem to fill the viewport. The generated emblem edit was rejected because it
changed the original motif; it is not used by the app.
