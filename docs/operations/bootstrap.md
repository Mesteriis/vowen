# Bootstrap operations (technical alpha)

Use synthetic data until M6 backup/restore and independent security review.

## Secrets and first account

Copy `.env.example` to the ignored `.env`. The example database password is for
loopback development only; before deploying choose a long random URL-safe password
and set both POSTGRES_PASSWORD and DATABASE_URL consistently. Changing an environment
variable does not reset a password in an existing PostgreSQL volume.
Run migrations before appctl, and `appctl instance init` to generate a mode-0600
keyring without replacing existing keys. Back up keys independently of the database.
Put only the dedicated instance bot token in `secrets/bot-token` (0600). Do not reuse
an unrelated bot or publish real participant IDs. Configure username, HTTPS origin
and BotFather menu button explicitly. Operator commands do not imply consent.

For containers, set APP_UID and APP_GID in your private `.env` to the owner of
`secrets/`; the API process must read the 0600 keyring. Containers drop capabilities
and use read-only root filesystems. Never put secrets into image build arguments.

## Network boundary

Default Compose ports are loopback 8443/8080; the database is not published.
`compose.dev.yaml` publishes PostgreSQL on loopback 55432 for host development.
Production requires a deliberate external 443/80 port mapping, reachable domain,
DNS and valid certificates; local Caddy certificates are not public trust.

Caddy connects to the API through a dedicated internal proxy_link network alias.
Uvicorn trusts only PROXY_IP (default 10.253.240.2); never expose API:8000 directly
or set wildcard forwarded-header trust. PROXY_SUBNET defaults to 10.253.240.0/29;
change subnet, PROXY_IP and API_PROXY_IP if they conflict with a local network.
Caddy supplies the client address; untrusted direct forwarded headers are ignored.

The limiter is bounded in memory per API process: 20 auth issuance/consume attempts
per minute per client address, 120 status/refresh requests. Keep one API replica;
multiple replicas require a shared limiter design. Restart resets transient buckets.
Bot confirmation is restricted to private chats and the bound Telegram actor.

## Startup and checks

`docker compose up -d --build --wait api proxy` runs Alembic once before API startup.
Readiness verifies database access and the exact migration head; incompatible schema
blocks protected requests. Liveness remains available for diagnosis. Expired challenges,
assertions, access tokens and expired session families are pruned every 60 seconds.
Spent refresh hashes remain until family expiry to detect reuse.

`docker compose --profile telegram up -d bot` explicitly starts real Telegram polling.
No worker is included until M2 provides actual queue work. No sensitive request body
or access logging is configured. Container restarts do not discard persistent DB/keys.

## Backup and restore limitations

Full M6 backup/restore acceptance is pending. Do not call this production-ready.
Database and keyring are both required; loss of needed keys loses encrypted content.
Restore must be to an isolated instance with Telegram delivery disabled and deletion
policies applied before exposing it. No downgrade/restore safety claim is made yet.
