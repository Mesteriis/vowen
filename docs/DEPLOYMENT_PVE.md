# Dedicated PVE deployment

The owner deployment uses an unprivileged Debian 13 LXC with Docker, a private
HTTP Caddy origin, and a separate nginx-ui HTTPS edge. The application source
was initially deployed from `b0356dd`; the current application deployment is
`33e70c9` with schema 0045 (2026-10-19), following M5 `f60013d`/0018. Existing
participants and data were preserved; reference and shop fixtures were imported,
without copying development accounts. See dated deployment evidence
in [STATUS](STATUS.md).

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
Provision `secrets/bot-token`. Fresh databases need no data keyring; when upgrading
an encrypted database, mount its original keyring for migration 0035 (see
[conversion](operations/plain-payloads.md)). Secret files must be 0600 and readable by the Compose
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

## Updating an archive deployment

Read the current schema/service health and `.deployed-revision`; an archive checkout
has no Git metadata. Preserve machine-local edge files and secret/config hashes.
Stop API/worker/poller for the final consistent dump, restore it into a separate
DB with the backed-up keyring, then rehearse both upgrade and downgrade. Compare
all existing table fingerprints before resuming writers; only the Alembic version
and explicitly added empty tables may differ for 0015/0016. For 0017/0018, compare
existing rows projected onto their original columns: new notification columns
have preserving defaults, so full-row hashes legitimately change. Verify the new
plan/wave tables separately and decrypt existing encrypted content with the backed-up
keyring. Keep original source and old image tags until acceptance. Never downgrade
after new milestone data is written without a separate preservation/rollback decision.

A second `compose run api` conflicts with the running API's fixed proxy-network
address. Use the `migrate` service for one-off backend jobs instead. Read-only
crypto verification needs an explicit read-only keyring bind; synthetic acceptance
tests use their own DB and generated keys, with no production secret bind. Ensure
commands cannot consume the remainder of a streamed shell script: execute a saved
script, or disable stdin on commands that do not need it. Never print resolved
Compose configuration or database URLs.

## Scheduled backups and release artifacts

See [M6 operator procedures](M6.md) for the PVE systemd timer, encrypted restic
repository, scoped retention, conditional off-host replication and artifact builds.
Use the same exclusive backup lock for deployments and key rotation. The automation
does not replace a restore rehearsal before a schema migration.


## 2026-10-19 update: participant profiles and current catalogues

Application revision `33e70c9` is deployed at the existing HTTPS origin with schema
0045. The two existing server participants were retained. The migration rehearsal
restored the stopped-writer 0018 database into a separate scratch database, compared
all original columns and decrypted payload hashes, upgraded to 0045, compared them
again, and imported the shop fixtures there before modifying the application DB.
The same comparison passed on the application DB before importing products.

Migration 0035 converts payloads to plaintext as previously requested by the owner.
Rollback to an old AES-only binary requires restoring the original database and
keyring, not only Alembic downgrade. The private pre-update dump, configuration,
source archive and old image tags remain on the server; the previous source tree
is retained separately. Machine-local edge files and secret/configuration hashes
were preserved. Hold the PVE backup lock for subsequent deployments too.

All 318 reference fixture UUIDs and thumbnail paths were verified. The 103 shop
products from `scripts/fixtures/rewards.json` were imported atomically under an
existing active dominant author, with their cover, category, price and public
audience attributes. Existing accounts, balances and purchase history were not
reset. The debug scenario in `scripts/fixtures/debug-space.json` is repository
fixture data only; it was not applied to this server. Production debug login remains
disabled.

Public HTTPS checks passed for readiness, authorization boundaries, CSP and body
limits. All 448 Web static manifest entries matched repository SHA256 values over
HTTPS, and served JavaScript/CSS matched the exact application build. Evidence:
`artifacts/deployment/profile-20261019/static-verification.json` and dated STATUS.
This does not claim physical Android or live Telegram workflow acceptance.
