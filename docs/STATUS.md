# Actual implementation status — 2026-10-15

Public repository: https://github.com/Mesteriis/vowen (owner explicitly confirmed by user).
Initial implementation branch: `feat/m0-m1`; commit identity uses the confirmed
account's GitHub noreply address. Working name, MIT, stack and TTLs remain
implementation defaults, not separately confirmed customer preferences.

The supplied archive contained START_HERE.md, AGENTS.md and five docs. All seven
were extracted at their supplied paths and read completely. It did not contain
VOWEN_AGENT_BRIEF.md; no separate matching brief was found beside the archive.

## Milestones

- **M0: implemented and locally verified.** API, PostgreSQL/Alembic, Vue shell,
  native Compose Android, dependency locks, HTTPS Compose bootstrap, OSS documents
  and CI configuration. Clean locked dependency installation and Linux image builds ran.
- **M1: substantial working technical alpha; live acceptance pending.** CLI members,
  Mini App authentication, Android bot confirmation, sessions and contextual relations
  are implemented. Both client projects build; the browser flow ran against actual
  API/PostgreSQL with synthetic signed Telegram data.
- **M2–M6: not implemented.** No forms, guest access, diary, ritual, discipline,
  reward or notification feature claims. No fake success endpoints for these modules.

## Implemented behavior

CLI create/list/disable/enable/revoke-sessions; BIGINT Telegram IDs and duplicate rejection.
Idempotent mode-0600 keyring initialization; AES-256-GCM envelopes bound to record UUID,
type and schema version. Encrypted agreement text, independent keys outside database.

Mini App raw initData HMAC validation, duplicate-query rejection, freshness checks,
strict identity types, one session family per canonical signed assertion; no provisioning
from login. Unknown and disabled IDs have the same denial code.
Opaque hashed tokens, 15-minute access TTL, atomic refresh rotation/reuse revocation,
family expiry, `/me`, own session list/revoke/logout, immediate denial after disable.
Expiry cleanup runs every 60 seconds; spent refresh hashes survive until family expiry.

Android independent hashed start/poll/nonce proofs, private-chat bot prompt, bound
actor and explicit approval/rejection, idempotent callback decisions, atomic single
consume. API and bot auth throttling, body limits and sanitized error payloads.
Native HTTPS origin selection, challenge screens, `/me`, pause/logout, serialized
refresh/retry, AES-GCM refresh blob with Keystore key, no backup and instance switching.

Directed relations, no self-links/transitivity, immutable encrypted agreement versions,
explicit scope allowlist, two exact-version consents, optimistic conflict checks,
pause/revoke, new consent round on resume or scope change, personal pause.
Central policy additionally requires an object's server-loaded ACL. It denies
private-journal actions, guest/operator authority and unrelated targets; this is
policy coverage, **not an implemented journal feature**.

Mini App uses volatile tokens only. RU/EN profile, sessions, participants and relationship
proposal/accept/pause/resume/revoke screens; explicit refresh retrieves another member's
updated consent. Native Android currently covers auth/profile/personal pause; its
relationship editor and full session management UI remain follow-up work.

## Commands actually run

| Command | Actual outcome |
|---|---|
| `make bootstrap` | Locked Python/web installation succeeded |
| `make migrate`, `make migrate-test` | Alembic upgrades through 0005 succeeded on PostgreSQL |
| `make lint` | Ruff + web ESLint passed |
| `make typecheck` | Strict mypy (24 source files) + vue-tsc passed |
| `make test` | 37 backend unit/integration/contract tests passed on PostgreSQL 17.11 |
| `make test-web` | 3 Vitest tests passed |
| `make build-web` | Vite production build succeeded |
| `make test-e2e` | 2 Playwright browser scenarios passed against actual API/PostgreSQL |
| `make build-android` | 4 JVM tests, lintDebug and assembleDebug succeeded |
| `make contracts check-contracts` | OpenAPI/web/native generated contracts checked |
| `docker compose config --quiet` | Passed |
| `docker compose -f compose.yaml -f compose.dev.yaml up -d --build --wait api proxy` | Linux images built; migration exited successfully; API/database healthy; proxy HTTPS smoke passed |
| `python3 scripts/smoke_compose.py` | Real loopback HTTPS API/static routing and CSP passed; local CA trust explicitly bypassed by this test only |
| `uvx pip-audit --path backend/.venv/lib/python3.13/site-packages` | No known third-party Python vulnerabilities; local vowen package skipped |
| `pnpm --dir web audit --prod` | No known runtime web vulnerabilities |
| `make secret-scan`, `git diff --check` | Passed before publication; heuristic scan plus staged/history review |

Tests were introduced before implementation of each slice. Initial RED evidence
includes missing health routes, absent provisioning/auth/challenge/relations functions,
missing native auth state/refresh API, absent expiry cleanup, missing bot throttling,
incorrect native fetch receiver, missing refresh UI and incorrect validation-error contract.
All relevant suites were subsequently run green. Browser/Android framework warnings
were not treated as failed tests or hidden; Android's SDK metadata warning and Gradle
compiler-option deprecation do not prove device compatibility.

Screenshots were inspected at 390px mobile width; no horizontal overflow was found.
Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk` (not a release APK).

## Review and decisions

One fresh read-only reviewer inspected the full implementation. Two Important findings
were fixed with regression checks: Android expired access refresh/retry; independent
rate-limit client identity behind an explicitly trusted proxy. Expiry cleanup gap fixed.
Runtime validation also found and fixed Caddy SPA fallback rewriting API requests and
native browser fetch receiver binding. Final full suites passed after the fixes.

Rulings: supplied milestone checklist is executed directly with this evidence ledger;
readiness remains diagnostic while mismatched schemas block protected DB operations;
worker/outbox begins in M2 rather than advertising an idle worker; one API replica with
bounded in-memory throttling; isolated proxy subnet and fixed proxy/API addresses are
configurable to avoid deployment collisions. API must not be directly exposed.
User resolved initial GitHub identity mismatch in favor of Mesteriis. PostgreSQL 17.11
replaced the initial 17.6 bootstrap image after checking official current 17.x fixes.

## Not verified / not finished

- No live bot token used: actual Telegram menu initData, bot messages and Android sign-in
  have not been accepted with real Telegram. Bot adapter tests replace only network I/O.
- APK not installed on a device; Android Keystore, process death, backup behavior and
  UX are implemented by source/build but not proven on hardware/emulator.
- Public DNS/HTTPS deployment and certificate trust on Android not tested. Compose
  defaults bind loopback and use a local CA. No global trust-store changes were made.
- CI configuration exists; its remote result must be checked separately after push.
- No independent security audit, container/Android advisory audit, full backup/restore,
  key rotation batch command or production release signing.
- M1 operator relation-proposal CLI, preference/profile editing and native relationship/
  session screens are not implemented. Core operator user lifecycle is implemented.

Next concrete step: configure a **dedicated instance bot and reachable HTTPS origin**,
provision four explicitly selected accounts through CLI, install the debug APK on a
selected test device/emulator and verify both live login paths, revoke/disable and
cross-instance isolation. Then close remaining M1 UI/CLI acceptance before M2 forms.

Local run commands and production boundary details: README.md and
`docs/operations/bootstrap.md`. This is not the completed product or production MVP.

## Publication / remote CI follow-up

Implementation published to `main`. First Linux backend/web job passed its combined
install/migration/lint/typecheck/tests/build/contracts/secret-scan step. Android job
failed in SDK setup before Gradle: setup-android's default obsolete `tools` package
was unavailable. Workflow now requests `platform-tools` explicitly, pins Ubuntu 24.04
and uses current Node-24 action generations. This is a CI infrastructure correction;
local Android acceptance remains four JVM tests + lint + APK build.

Final remote verification: [CI run 38714636060](https://github.com/Mesteriis/vowen/actions/runs/38714636060)
completed **successfully for both backend-web and Android**, testing code commit
`3769ede4cdeaf710ea2237bce12d2bb0e07bf78a` on clean Ubuntu 24.04 runners.
This includes locked install, PostgreSQL migrations/tests, lint/types, web build,
contracts/secret scan, Playwright E2E, native Android tests/lint/assembleDebug.
The final evidence-only documentation commit uses `[skip ci]`; it changes no code,
configuration, dependencies or checks. Live Telegram/device limitations remain open.
