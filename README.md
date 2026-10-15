# Vowen

Self-hosted, single-instance workspace for consenting adult relationship participants.
N participants, explicit contextual authority, Telegram identity and operator-only
account provisioning. No registration, multi-tenancy or public social network.

**Technical alpha.** M0 infrastructure and substantial M1 code are implemented;
live Telegram and real-device acceptance remain open. Forms, journal, rituals,
discipline, rewards and notifications are later milestones, not working features.
See [actual evidence and gaps](docs/STATUS.md). [Русский](README.ru.md).

Python 3.13, PostgreSQL 17, Vue/TypeScript and native Kotlin/Compose. MIT and the
working name are starting defaults; branding/domain availability has not been checked.
The server operator can access data; encryption is not E2EE.

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
