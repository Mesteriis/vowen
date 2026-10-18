# Local development login

`DEBUG_AUTH=false` is the default. Production configuration never enables this mode.
For isolated local UI development, explicitly set all of:

```sh
APP_ENV=development
DEBUG_AUTH=true
PUBLIC_BASE_URL=http://127.0.0.1:5176
DATABASE_URL=postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_dev
```

Create the separate `vowen_dev` database first using your local PostgreSQL operator
account, run `make migrate` with that DATABASE_URL and
provision synthetic participants with the existing CLI described in
[bootstrap.md](bootstrap.md). A fresh database requires no payload keyring; never copy production data
or credentials. No participant or agreement is created automatically.

Run the API bound to loopback and the Vite dev proxy:

```sh
uv run --project backend uvicorn vowen.main:app --host 127.0.0.1 --port 8002
VOWEN_API_URL=http://127.0.0.1:8002 pnpm --dir web dev --port 5176 --strictPort
```

The environment above must be supplied to the API and migration commands (through
an isolated local environment file or shell exports). The Mini App login page then
shows a **DEBUG · Local development** participant selector. Choose an existing
active synthetic participant and press **Sign in**. Telegram is not needed.
The server settings determine availability; no frontend-only flag grants access.

Only Telegram identity verification is bypassed. The resulting session uses the
normal hashed bearer/refresh tokens, rotation, expiry, revocation and user blocking.
All relationship, version, consent, pause, diary and resource permissions remain
in force. Tokens stay in browser memory. Signing in does not accept proposals.

The API refuses startup if DEBUG_AUTH is enabled outside APP_ENV=development,
with a public non-loopback URL, or with a non-loopback database or a database name
without `_dev`/`_test`. Database URL parameters are rejected in this mode because
libpq host/service parameters could redirect a seemingly local connection.
Do not forward this development server through a public reverse proxy or tunnel.

`GET /api/v1/auth/debug/users` lists only active local participants' IDs and names;
`POST /api/v1/auth/debug` accepts `{ "user_id": "<uuid>" }` and returns normal
SessionTokens. Requests require a loopback peer and Host; a supplied Origin must
match PUBLIC_BASE_URL, and POST requires that Origin. Cross-site fetches and
nonlocal forwarded addresses are denied. Disabled or nonlocal debug endpoints
return 404 before accessing the database. No bot token is required for debug login.

This mode is for the local web workflow. Native Android keeps its existing secure
Telegram login flow; its network origin restrictions are unchanged.
