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
- **M2: implemented and locally verified; remote CI acceptance below.** Versioned forms,
  member/guest answers, receipts, encrypted drafts, reader snapshots and delivery outbox.
- **M3–M6: not implemented.** No diary, ritual, discipline or reward feature claims.

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

## M1 completion continuation — 2026-10-15

The earlier list of missing M1 UI/CLI tasks is superseded by this section.

Implemented: native relationship proposals and new agreement versions; exact-version
review/accept, pause, resumption and revocation; own session list with current-session
marker, creation/expiry/status and targeted revoke confirmation. Self-revoke immediately
clears local access, encrypted refresh and workspace state. No WebView wrapper.

Both clients now edit private profile preferences: display name, EN/RU, IANA timezone,
and self-description labels. `PATCH /me/preferences` binds the authenticated user,
requires profile_version, rejects privileged/unknown/null fields, and remains available
on personal pause. Participant DTOs expose no language/timezone/session/Telegram ID.
Migration 0006 backfills existing members and new CLI users get preferences atomically.

`appctl relations propose` uses OperatorContext and the shared relation service. It
reads UTF-8 agreement text from a bounded file, prints only UUID, creates zero consents,
and rejects duplicates/invalid scope/files. No CLI acceptance command exists.

Native contract tests found a previous positional-DTo bug: nonce and poll_secret were
reversed. Named arguments now bind both independently; the regression test failed
before the fix and passed after. User-supplied BOT_API_TOKEN in ignored .env is recognized
without printing it; Settings uses SecretStr and file precedence. Compose still uses
file-based secrets. Live Telegram remains explicitly excluded from this continuation.

Evidence: 51 backend tests on PostgreSQL, 6 native JVM tests, 3 web unit tests and 3
browser E2E; strict mypy/ruff/vue-tsc/ESLint; web production build; Android lint,
assembleDebug and assembleDebugAndroidTest. Five native Compose tests passed on an
isolated Android 16 emulator (proposal, exact-version consent, new-version editor,
selected self-session confirmation, profile form). They use synthetic rendering state
and typed API transport tests; this does not prove live Telegram or real-device Keystore.
GitHub CI additionally compiles the instrumentation APK; device tests were run locally.

A fresh read-only review found no Critical/Important issue in this completion slice.
M1's requested remaining implementation tasks are closed; live Telegram acceptance
and real-device credential lifecycle remain separate. M2 forms have not started.

Remote acceptance: [CI run 38718797091](https://github.com/Mesteriis/vowen/actions/runs/38718797091)
passed both `backend-web` and `android` for commit
`f0a226421bcebf74c5213c08469fa20633a0b6f7`. The same commit was fast-forwarded to
`main`, without code changes. This evidence-only follow-up uses `[skip ci]`.

## M2 forms continuation — 2026-10-15

Supersedes the historical M2 and native-client limitations above. M2 now implements
versioned questionnaires/surveys and all ten MVP question kinds. Publication freezes
schema bodies; edits create a new version. Previous-question conditions (`all/any`,
`equals/not_equals/contains/answered`) are interpreted without code execution.
The server drops hidden answers and validates visible required values and bounds.

Internal invitations bind one member and one immutable version. Guest invitations
activate only on explicit POST; GET/HEAD previews remain neutral. Separate hashed
invitation/session/receipt secrets, Secure HttpOnly host cookies, Origin + synchronizer
CSRF and expiry/revocation checks restrict guests to their response. Receipt sessions
cannot write drafts or submit. No authentication or invitation path creates users.

Drafts and final answers use the existing AES-256-GCM envelope, with record-specific
AAD. Authors cannot read others' drafts or inherit result access. Reader IDs are
snapshotted at invitation creation, can only be reduced, and are shown to respondents.
Respondents retain access to their submitted answers until retention expiry; withdrawal
clears ciphertext/nonce/key metadata and closes reader access. Cleanup prunes expired
drafts and retained bodies. Offline backups still follow operator retention policy.

Mini App: visual builder, conditions/options, preview, publication/new versions,
internal/guest invitations, secret-link copy, reader removal, revocation, drafts,
explicit review/submit, results and withdrawal. Standalone /f and /r guest pages load
no Telegram script or trackers; deployed CSP excludes external scripts and framing.

Android: native basic template creation/editing/publication, invitation/reader selection,
member drafts/review/submit/results/withdrawal, and guest form/receipt entry by pasting
an HTTPS link. No WebView. Native guest transport never shares member bearer tokens.
Guest credentials and unsaved input survive activity recreation in a memory-only ViewModel; save the independent receipt before closing;
a lost draft session requires sender revocation and a new invitation. Conditional
editing, custom invitation TTL/retention, archive and reader reduction use Mini App;
Android preserves and renders existing conditions. See docs/ANDROID_CAPABILITIES.md.

`appctl forms invite` issues published-form invitations through the same service;
stdout is a sensitive capability link, stderr reports delivery status. Optional bot
contacts require explicit private-chat /notifications_on and can opt out. The durable
notification_deliveries table serves as the transactional outbox, with SKIP LOCKED
claim, lease ownership, bounded retries, protected link payload and terminal cleanup.
Submission notifications contain neutral text, never answer/question/title content.
Bot worker rechecks current contact, invitation/reader and response state. Telegram
network delivery has not been exercised; synthetic bot transport/worker tests passed.

Local evidence: 86 backend tests on PostgreSQL; strict ruff/mypy/vue-tsc/ESLint;
3 Vitest tests; 5 browser E2E (including complete internal and guest lifecycles);
10 Android JVM tests; 11 Compose tests on the dedicated Android 16 emulator; Android
lint/debug APK/instrumentation APK; production web build; regenerated OpenAPI, TS,
Kotlin and standalone form-schema contracts. Compose rebuilt/migrated and actual
loopback HTTPS API/static/guest CSP routing passed (local CA trust explicitly bypassed
only in the smoke script). Live Telegram and physical-device credential lifecycle
remain unverified. M3–M6 are not implemented. Remote CI result is recorded separately.

Final whole-branch review identified five issues, all fixed with observed RED→GREEN
regressions: Android activity recreation preserves route/transport/input/idempotency;
native editor target switching resets state; interactive non-persisting preview covers
conditions and review; default retention is 90 days after submission (independent of
invitation/draft expiry); a different live guest capability cannot silently replace the
cookie and restored receipt URLs are bound to their actual receipt context. Replacement
requires an explicit warning, same-origin request and current synchronizer CSRF.
Migration 0008 adds the retention duration and clears draft retention dates; any
pre-release submitted row retains its existing expiry rather than inventing a timestamp.

A fault-injected COMMIT regression also exposed the pre-existing request-scoped yield
transaction: success/cookie could be sent before a failing commit. The shared dependency
now has function scope, committing before response transmission; the failure test returns
503 without Set-Cookie. Full auth/session/relations/forms regression suite was rerun.

Remote acceptance: [CI run 38727788915](https://github.com/Mesteriis/vowen/actions/runs/38727788915)
passed both `backend-web` and `android` on clean Ubuntu runners for commit
`39dddce0c6ea1921ce79f69b2ac66dca7f4798a0`. The identical commit was fast-forwarded
to `main`. This final evidence-only documentation commit uses `[skip ci]` and changes
no implementation or validation configuration. Native instrumentation ran locally;
remote CI runs JVM/lint/build gates and compiles the instrumentation APK.

The final multi-tab regression also covers declining capability replacement and then
saving the original tab's still-visible input. A stale synchronizer token now triggers
one refresh/retry only if the server session identity and scope still match that page.
Replacement exchanges are excluded from automatic retry. The five browser E2E pass
with this case; no guest input is dropped or silently sent to a different capability.

Final remote verification including the multi-tab fix:
[CI run 38729308233](https://github.com/Mesteriis/vowen/actions/runs/38729308233)
passed `backend-web` and `android` for code commit
`3a5b1e826d0d03e5ae9163c1835e4790e8b3aa1e`. The implementation is fast-forwarded
unchanged to `main`; this evidence-only follow-up uses `[skip ci]`.

## M3 / rules slice — 2026-10-15

Implemented rule templates with encrypted title/description, draft editing, publication,
new immutable versions and archival (Alembic 0009). Separate assignments carry exact
version consent, recipient, explicit managers, optimistic revision and decision times.
Recipient acceptance/decline is independent; acceptance atomically replaces only that
recipient's prior active version. Duplicate assignment and conflicting decisions return
409. Published text cannot be mutated. Old consent remains in assignment history.
Author-only version history is separate from assignment access; authors are not
implicitly managers. Each assignment is created individually, returning its own status
or error rather than a batch-wide success. Managers need a current direct `rules.assign`
relation on each read/change. Personal or relationship pause disables effective authority;
recipients retain history and the ability to pause/revoke/decline. No punishment is created.

Mini App and native Android support authoring/editing/publication/new version/archive,
individual recipient/manager selection, exact text confirmation, decline, pause/revoke
and assignment history. Server remains authoritative. OpenAPI and TS/Kotlin DTOs updated.

Verified locally: 90 backend tests on PostgreSQL, 3 Vitest, 6 real API/browser E2E,
10 Android JVM tests and 14 Compose tests on the owned Android 16 AVD; ruff, mypy,
ESLint, vue-tsc, web production build, native lint/debug APK/instrumentation APK,
contract regeneration and heuristic secret scan. Full-suite fault injection previously
restored hardcoded schema 0008; it now restores the actual original revision.

Scope decision: M3 ships in domain slices; this closes its first two checklist items,
not the whole milestone. Schedules/DST/catch-up, rituals/reports/reviews, rewards and
M3 notifications are still absent. Next concrete slice: deterministic occurrence scheduling
and per-recipient rituals with concurrent report/review tests. Live Telegram and physical
Android/native-to-server acceptance remain separate and unverified. No new dependencies.
