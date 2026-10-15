# Vowen

Self-hosted приложение для совершеннолетних участников согласованных отношений.
Один инстанс, N участников, контекстные полномочия и явные согласия. Пользователей
создаёт только оператор через CLI; вход через Telegram. Саморегистрации нет.

**Техническая alpha.** Реализованы инфраструктура M0 и значительная часть M1:
CLI, серверная проверка Mini App, сессии, подтверждение Android-входа в боте,
отношения и паузы. Живой Telegram и Android на устройстве не проверены.
Анкеты, дневник, ритуалы, дисциплина, награды и уведомления ещё не реализованы.
[Фактический статус](docs/STATUS.md). [Подробные команды](README.md).

Название Vowen, MIT и выбранный стек — стартовые defaults из задания, а не
отдельно подтверждённые пожелания заказчика. Бренд и домены не проверялись.
Отображаемое имя задаётся `APP_DISPLAY_NAME`. Шифрование на сервере не является
E2EE и не защищает от владельца сервера с root-доступом и ключами.

```sh
cp .env.example .env
make bootstrap
make dev
uv run --project backend appctl instance init
# Только синтетический пример:
uv run --project backend appctl users create --telegram-id 100000000001 --display-name 'Демо'
uv run --project backend uvicorn vowen.main:app --host 127.0.0.1 --port 8000 --no-access-log
# В другом терминале:
pnpm --dir web dev
```

Для реального входа настройте отдельного бота, token-файл с правами 0600,
`TELEGRAM_BOT_USERNAME`, HTTPS и menu button в BotFather. Android принимает адрес
HTTPS-инстанса; требует явного подтверждения собственного входа с совпадающим кодом.
Смена инстанса удаляет прежние токены. Refresh хранится зашифрованным ключом Keystore.

Проверки используют отдельную PostgreSQL-базу с суффиксом `_test` и удаляют её
синтетические данные. Не запускайте backend integration и E2E одновременно.

```sh
docker compose exec -T db createdb -U vowen vowen_test # один раз
make migrate-test
make lint typecheck test test-web build-web
pnpm --dir web exec playwright install chromium
make test-e2e
make build-android
make contracts check-contracts secret-scan
```

`make build-android` требует JDK 17, SDK 36 и build-tools 36.0.0.
APK: `android/app/build/outputs/apk/debug/app-debug.apk`; это debug APK.
[Эксплуатация](docs/operations/bootstrap.md), [безопасность](SECURITY.md).

Задачи M1 по интерфейсам реализованы: Android поддерживает предложения и новые
версии отношений, рассмотрение точной версии, согласие, паузу, возобновление,
отзыв и управление собственными сессиями. Отзыв текущей сессии удаляет локальные
учётные данные. В обоих клиентах редактируются имя, RU/EN, IANA timezone и метки
самоописания; метки не предоставляют полномочий.

Оператор предлагает соглашение из UTF-8-файла (`appctl relations propose`,
`--dominant-id`, `--submissive-id`, повторяемый `--scope`, `--agreement-file`).
Подтверждение за участника через CLI отсутствует. Полная команда — в README.md.
Токен `BOT_API_TOKEN` в игнорируемом `.env` поддержан для запуска на хосте;
Compose продолжает читать `TELEGRAM_BOT_TOKEN_FILE`. Живой Telegram тестами не вызывается.

## M2: анкеты и ответы

В Mini App работают визуальный конструктор, условия, предпросмотр, публикация версий,
внутренние и гостевые приглашения с явным списком читателей, черновики, проверка перед
отправкой, результаты и удаление. Нативный Android поддерживает базовое создание анкет,
публикацию, приглашения и заполнение; редактор условий остаётся в Mini App.

Гость открывает секретную ссылку `/f/<id>#token=<secret>` без Telegram и создания аккаунта.
После отправки можно сохранить независимую квитанцию `/r/<id>#token=<secret>` для чтения
и удаления своего ответа. Ответы не анонимны и не E2EE. Нативный гостевой сеанс хранится
только в памяти: сохраните квитанцию до закрытия; потеря сеанса черновика требует нового
приглашения. [Матрица Android](docs/ANDROID_CAPABILITIES.md).

CLI: `appctl forms invite FORM_UUID --reader-id READER_UUID --recipient-id MEMBER_UUID`.
Без `--recipient-id` создаётся гостевое приглашение. stdout содержит секретную ссылку,
stderr — статус доставки. `--deliver --contact-telegram-id TELEGRAM_ID` допускает доставку
гостю только при разрешённом контакте бота. `/notifications_on` и `/notifications_off`
не создают аккаунт. Живую доставку пока не проверяли.

Для локального HTTPS-прокси нужен `PUBLIC_BASE_URL=https://localhost:8443`; при размещении
задайте реальный HTTPS origin. Он используется также для проверки Origin гостевых запросов.
