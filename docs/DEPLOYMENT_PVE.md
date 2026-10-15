# Dedicated PVE deployment

The owner deployment uses an unprivileged Debian 13 LXC with Docker, a private
HTTP Caddy origin, and a separate nginx-ui HTTPS edge. The application source
was deployed from `b0356dd`; no development database or users were copied.

The files in `deploy/pve` are an example for this topology. Before reuse, replace
the reserved example domain `vowen.example.test`, TEST-NET origin/edge/PVE/DNS addresses consistently, including Caddy's trusted proxy.
Compose paths resolve against the first Compose file, at the repository root:

```sh
docker compose -f compose.yaml -f deploy/pve/compose.edge.yaml config --quiet
docker compose -f compose.yaml -f deploy/pve/compose.edge.yaml --profile telegram up -d --build
python3 scripts/check_deployment.py https://YOUR_DOMAIN
```

Provision `.env` with a strong independent `POSTGRES_PASSWORD`,
`PUBLIC_BASE_URL=https://YOUR_DOMAIN`, and the verified `TELEGRAM_BOT_USERNAME`.
Provision `secrets/bot-token` and an independent `secrets/keyring.json` using
`vowen.core.crypto.init_keyring`. Files must be 0600 and readable by the Compose
application UID (default 1000); the secrets directory must be 0700. Never print
resolved Compose configuration, credentials or Telegram request URLs. Keep
only one poller per bot token; the local Telegram profile must remain stopped.

Install `vowen-boundary.nft` as `/etc/nftables.conf` and enable nftables. It flushes
only its own table, leaving Docker rules intact. Disable guest IPv6 unless an
equivalent IPv6 boundary is provisioned. Permit PVE ICMP monitoring or explicitly
exclude the guest from automatic ping-based recovery before enabling isolation.
HTTP ingress is allowed only from nginx. Private egress is denied except the
configured DNS resolver. Public HTTPS egress supports Telegram and registries.

This boundary is inside the guest. Guest root can alter it; it is not a
router-enforced DMZ. The deployment does not enable the global PVE firewall or
change OPNsense. Management uses authenticated PVE `pct exec`, with guest SSH
disabled and no additional credentials created.

Before editing the edge, save its current sites configuration in a root-only
archive outside sites-available. Create the new vhost with HTTP challenge and
maintenance responses first. In nginx-ui's site editor, enable TLS and use the
existing ACME user with HTTP01. The standalone certificate form uses DNS01.
After issuance, apply `nginx-vowen.conf`, check `nginx -t`, then reload. Certificate
renewal belongs to nginx-ui; preserve its HTTP challenge route. Verify public
Cloudflare and LAN origin TLS without bypassing validation. nginx overwrites
forwarded headers; Caddy trusts only nginx, and Uvicorn trusts only Caddy's
separate proxy network. Preserve the 512KiB ordinary/12MiB evidence body limits.

Back up PostgreSQL with `pg_dump -Fc` and separately back up `.env` and the
keyring/token directory with root-only permissions. Restore the dump into a
separate scratch database and verify migration revision and records before
claiming restore acceptance. Store encrypted off-host backups before collecting
real participant data; a same-host initial backup only protects against local
configuration mistakes. Never replace the keyring while restoring encrypted data.

Rollback: restore only the new vhost's saved file, run `nginx -t`, reload, and stop
the Vowen Compose services if needed. Preserve the database volume and secrets.
Do not delete the LXC or shared edge configuration as a routine rollback.

Telegram: set the default chat menu button to a Web App at the public HTTPS URL;
read it back with `getChatMenuButton`. Configure Main Mini App in BotFather as a
separate step. Provision participants explicitly through the CLI; Telegram
contact/start does not create an application user. Consent and notification
opt-in must come from each participant. End-to-end ritual/reward/revocation
acceptance needs distinct real participants and remains separate from deployment.
