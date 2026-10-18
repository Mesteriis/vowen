# Vowen

Self-hosted, single-instance workspace for consenting adult relationship participants.
N participants, explicit contextual authority, Telegram identity and operator-only
account provisioning. No registration, multi-tenancy or public social network.

**Technical alpha.** M0–M5 are implemented: CLI provisioning, authentication,
contextual relationships, forms, rules, rituals/evidence, rewards, discipline and
private diary, with Mini App and native Android screens. Telegram ritual/reward
delivery is implemented; live delivery and physical-device acceptance remain open.
Recurring surveys, quiet hours and channel settings are implemented. M6 release
acceptance remains open. M5 is deployed with schema 0018; own-account live survey
notifications, quiet deferral and cancellation checks passed. Partner ritual/reward
acceptance remains separate.
See [actual evidence and gaps](docs/STATUS.md), [M4 behavior](docs/M4.md), [M5 behavior and limits](docs/M5.md).
[Русский](README.ru.md).
[Release artifacts and automatic backups](docs/M6.md).

Python 3.13, PostgreSQL 17, Vue/TypeScript and native Kotlin/Compose. MIT and the
working name are starting defaults; branding/domain availability has not been checked.
Application payloads are stored without encryption as of schema 0035. API access checks
still apply; the server operator can read the database. Existing encrypted databases
are converted with their original keyring: see [plaintext migration](docs/operations/plain-payloads.md).

## Local development

Requires uv, Node 24/corepack with pnpm 11.5.1, Docker Compose. Android requires JDK
17, Android SDK platform 36 and build-tools 36.0.0. Versions are locked in
`backend/uv.lock`, `web/pnpm-lock.yaml`, Android version catalog/lockfile and wrapper.

```sh
cp .env.example .env
make bootstrap
make dev
uv run --project backend appctl instance init
# Synthetic example only. Use your own explicitly selected ID for an actual account.
uv run --project backend appctl users create --telegram-id 100000000001 --display-name 'Demo D1'
uv run --project backend uvicorn vowen.main:app --host 127.0.0.1 --port 8000 --no-access-log
# In a second terminal:
pnpm --dir web dev
```

API: http://127.0.0.1:8000/health/ready. Web: http://127.0.0.1:5173.
A normal browser shows the closed sign-in screen; it cannot fabricate Telegram identity.
For an actual Mini App, configure a dedicated bot and publicly reachable HTTPS
origin, put its token in `secrets/bot-token` with mode 0600, set the bot username
and token path, configure BotFather's menu button, then run:

```sh
uv run --project backend python -m vowen.integrations.telegram.bot
```

The bot verifies that its token matches the configured username. Android accepts
HTTPS instance origins only. Its bot challenge must be explicitly approved by an
allowlisted account; `/start` alone never issues a session.

## Tests and builds

Tests **truncate only a dedicated database ending `_test`**. Never point them at
real records. Do not run backend integration and browser E2E simultaneously.

```sh
docker compose exec -T db createdb -U vowen vowen_test # once
make migrate-test
make lint typecheck test test-web build-web
pnpm --dir web exec playwright install chromium
make test-e2e
# Set ANDROID_HOME to your installed SDK; do not commit local.properties.
make build-android
make contracts check-contracts secret-scan
```

APK: `android/app/build/outputs/apk/debug/app-debug.apk`; a debug build, not a
signed production release. Android UI/Keystore device tests and live Telegram
are separate from JVM unit tests and synthetic backend/browser tests.

## Container bootstrap

```sh
# Set APP_UID/APP_GID to the owner of secrets/ in your untracked .env.
docker compose up -d --build --wait api proxy
# Opt in only after configuring the dedicated bot:
docker compose --profile telegram up -d bot
```

The proxy binds loopback HTTPS 8443 and HTTP 8080 for local validation. Local
Caddy certificates require trusting its local CA. Production needs a reachable
domain, valid HTTPS, protected keys and a deliberate port/firewall configuration;
see [operations](docs/operations/bootstrap.md). Database is private by default;
only `compose.dev.yaml` adds a loopback port. No worker service is advertised
before the M2 outbox is implemented.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Specification](docs/PRODUCT_SPEC.md)

## M1 member controls

Both clients support profile preferences (display name, RU/EN, IANA timezone and
self-description labels). Labels confer no authority. Android now also provides
relationship proposal/revision/review/accept/pause/resume/revoke and own-session
management; revoking the current session clears local credentials immediately.
New agreement versions and resumption still require separate consent from both.

Operators can propose an agreement, never accept on someone's behalf:

```sh
uv run --project backend appctl relations propose \
  --dominant-id USER_UUID_A --submissive-id USER_UUID_B \
  --scope rules.assign --scope rituals.review \
  --agreement-file /private/path/agreement.txt
```

The command prints only the relation UUID. Keep agreement files outside Git.
Direct host runtime additionally accepts `BOT_API_TOKEN` or `TELEGRAM_BOT_TOKEN`
in the ignored `.env`; it is masked in settings representations. A configured
`TELEGRAM_BOT_TOKEN_FILE` takes precedence. Compose retains file-based secrets.
No bot is started by the test suite. Live Telegram is a separate acceptance step.

`make build-android` also builds the instrumentation APK. Native UI tests can be run
on an explicitly selected **disposable emulator** with
`ANDROID_SERIAL=emulator-NNNN ./gradlew connectedDebugAndroidTest` from `android/`.
Do not run device tests without an explicit target.

## M2 questionnaires and guest responses

Members can create forms visually, preview, publish immutable versions and issue
invitations with an explicit results-reader list. Mini App supports conditional editing
and advanced invitation management; native Android supports a basic builder and filling.
The standalone `/f/<id>#token=<secret>` guest entry requires no Telegram or account.
Guests review readers/retention, save encrypted drafts, explicitly submit, and retain
read/delete access through an independent `/r/<id>#token=<secret>` receipt link.
Links and receipt secrets are sensitive. Responses are not anonymous or E2EE.

```sh
appctl forms invite FORM_UUID --reader-id READER_UUID --recipient-id MEMBER_UUID
# Omit --recipient-id for a guest. Optional delivery requires an opted-in bot contact:
appctl forms invite FORM_UUID --reader-id READER_UUID --deliver --contact-telegram-id TELEGRAM_ID
```

CLI stdout contains the secret link; do not redirect it to public logs. Stderr reports
`manual_delivery_required` if automatic delivery is unavailable. Private bot commands
`/notifications_on` and `/notifications_off` control contacts without creating members.
The bot process drains the transactional outbox; live delivery is a separate acceptance.
Use `PUBLIC_BASE_URL=https://localhost:8443` for the default local proxy, or the actual
public HTTPS origin for deployment. It must match the guest browser Origin.

[Android capability matrix](docs/ANDROID_CAPABILITIES.md) documents native limits,
including volatile guest sessions and deferred conditional editing. [Status](docs/STATUS.md)
separates automated evidence from live Telegram and physical-device checks.
