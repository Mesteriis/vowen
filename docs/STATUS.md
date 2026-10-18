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
- **M3: rules, rituals, rewards and Telegram delivery implemented; live recipient acceptance pending.** See dated evidence below.
- **M4: implemented and locally verified.** Discipline and private diary, server ACL, encrypted versions/content and Mini App/native Android screens. See latest evidence below.
- **M5: implemented, deployed and own-account live survey notifications verified.** Repeated internal surveys, approved-ritual feedback, personal channels/quiet hours and both clients. See M5 evidence below.
- **M6: in progress.** Reproducible release artifacts and scheduled encrypted backups are implemented; remaining operational/security acceptance is open. Dedicated M5 deployment is recorded below.

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
individual recipient/manager selection, exact text confirmation, decline, pause/revoke,
assignment history and explicit author-only template version history. Server remains authoritative. OpenAPI and TS/Kotlin DTOs updated.

Verified locally: 91 backend tests on PostgreSQL, 3 Vitest, 6 real API/browser E2E,
10 Android JVM tests and 16 Compose tests on the owned Android 16 AVD; ruff, mypy,
ESLint, vue-tsc, web production build, native lint/debug APK/instrumentation APK,
contract regeneration and heuristic secret scan. Full-suite fault injection previously
restored hardcoded schema 0008; it now restores the actual original revision.

Scope decision: M3 ships in domain slices; this closes its first two checklist items,
not the whole milestone. Schedules/DST/catch-up, rituals/reports/reviews, rewards and
M3 notifications are still absent. Next concrete slice: deterministic occurrence scheduling
and per-recipient rituals with concurrent report/review tests. Live Telegram and physical
Android/native-to-server acceptance remain separate and unverified. No new dependencies.

Whole-branch review findings were fixed with observed regressions: author version history
in both clients, scrolling to the end of a 10k-capable native review body, immediate pause
presentation and refreshed assignment state, removal of the recipient from manager selection,
and correct previous-assignment revocation time while preserving original acceptance time.
The first remote run failed in the browser due to cross-page ordering: recipient refreshed
before sender assignment completed. E2E now waits for the sender's server-backed pending
assignment before refreshing the recipient; no production behavior or check was bypassed.

State-model decisions: accepting an explicit published version atomically replaces only the
same recipient's active assignment. Acceptance need not follow publication order; the UI shows
the exact text/ID and replacement warning. Paused/declined/revoked assignments cannot be
silently resumed or reissued for the same version: a new version/consent is required. The cost
is an additional proposal instead of a resume shortcut. Live Telegram and physical-device
acceptance are still excluded, so test success is not delivery or real-device proof.

Remote verification: [CI run 38733136234](https://github.com/Mesteriis/vowen/actions/runs/38733136234)
passed both `backend-web` and `android` for code commit
`7cb5f4f4a9fa6a26fac5ecc06a064d630216b0a5`, including the review fixes and browser
ordering regression. The same implementation is fast-forwarded to `main`. This final
evidence-only documentation commit uses `[skip ci]`; it changes no code or test configuration.
Final rebuilt Compose API/proxy/migration are healthy and the loopback HTTPS smoke passed.
Remote CI compiles Compose instrumentation; the 16 actual instrumentation tests ran locally
on the owned Android 16 AVD, now stopped. No live bot request was made.


## M3 / rituals and brand assets — 2026-10-15

Alembic 0010 adds immutable encrypted ritual versions, per-recipient assignments,
versioned once/daily/weekly schedules, unique local-day occurrences, encrypted report
attempts and explicit reviewer decisions. The worker bounds recovery (50 assignments,
31 days per transaction), handles DST gaps/folds including half-hour transitions,
keeps submitted reports available for review and suppresses old due-notice bursts.
Concurrent retries preserve one assignment/report/slot; incompatible reviewers return
one success and one revision conflict. Authors do not gain access to reports by authoring
or assigning. Issuers with current assign-only scope can manage assignment metadata.

Mini App and native Compose Android implement creation/publication/version history,
individual assignment/schedule editing, pause/resume/revoke, reports, revisions, review
and history. User-supplied gold crest and velvet startup art are bundled locally in both
clients. Startup follows actual loading and releases after failure, without a timed delay.
The dark gold/burgundy direction comes from the supplied showcase; screen contents are
real ACL-visible records, with no fabricated participants, progress or reward data.
Android uses selected tabs on phone and a sidebar at expanded width. The same locally
bundled OFL Cormorant Garamond display face supplies headings/wordmarks in both clients;
system body/control fonts remain readable. State labels are RU/EN and times explicitly
use the member profile timezone. Mobile first occurrence title/state viewport assertions
cover the compact top area.

Verified locally on the final implementation: 107 backend tests on PostgreSQL, 3 Vitest,
8 real API/browser E2E, 10 Android JVM tests, native lint/debug/instrumentation APK build,
and 21 Compose instrumentation tests on the owned Android 16 AVD. Real MainActivity
phone/tablet viewport screenshots use an AndroidTest-only synthetic transport; they
prove native layout/navigation/insets, not native-to-live-server authentication.
Ruff, strict mypy, ESLint, vue-tsc, web build, contract regeneration and heuristic secret
scan passed. No runtime dependencies were added.

Whole-branch review fixes have observed RED-to-GREEN regressions: assignment resume
skips the paused interval even when worker was stopped; assign-only issuers retain
metadata management without report access; native checkboxes have explicit accessible
names. A further regression covers account disable/re-enable during worker downtime.
Personal, relationship, assignment and account withdrawal cancel open slots and advance
watermarks, so disabled days cannot become retrospective obligations. Submitted history
is retained. No automatic punishment exists.

Scheduling decisions (implementation defaults, not separately confirmed preferences):
report window 24h, configurable 1–168; needs_changes renews that same window from review
time; future schedule edits start tomorrow or later; only one pending edit; timezone
changes require a separate assignment. Paused/disabled days are never replayed. These
tradeoffs and operational commands are in operations/rituals.md.

Live Telegram acceptance is limited to Bot API getMe for the supplied token. No bot
message, real member login or ritual delivery is claimed. Ritual notifications are
neutral in-app records. Rewards, Telegram ritual delivery, attachments, physical-device
performance and production backup/restore remain unverified or unimplemented; attachments
remain outside the initial MVP. Next concrete M3 slice: reward catalogue and manual grant,
then an idempotent automatic grant from approved occurrence with a PostgreSQL race test
and the full rule → ritual → approval → exactly-one-reward E2E.

The first final CI found a pre-existing internal-form E2E ordering race: the preview
already displayed the answer before submission committed, so the author's refresh
could happen too early. A 500ms injected submit delay reproduced the failure locally.
The test now waits for the recipient's server-loaded result article before the author
refreshes, and waits for deletion to finish before checking reader withdrawal. No
production behavior, timeout, retry or CI check was relaxed.

Final remote verification: [CI run 38747181628](https://github.com/Mesteriis/vowen/actions/runs/38747181628)
passed both backend-web and android for implementation/test commit
`d6dd97db05e1c0c4c19f160716efbb79811bc847`. Remote Android runs JVM/lint/build
and compiles instrumentation; 21 actual Compose tests ran locally on the owned
Android 16 AVD, now stopped. Final rebuilt API/worker/proxy are healthy, loopback
HTTPS smoke passed, and served crest/velvet/font bytes match the repository assets.
The local-CA bypass belongs only to the loopback smoke script. This evidence-only
follow-up uses [skip ci]; the identical checked implementation is fast-forwarded
to main. No production release, live Telegram delivery or physical-device claim.


## M3 / rewards and execution evidence — 2026-10-15

The user's direct follow-up brings HTTPS link/photo/video proof into this slice,
overriding the original attachment deferral for ritual reports. Alembic 0011 stores
bounded AES-GCM encrypted media in PostgreSQL, with occurrence/owner/report binding,
unique request keys, serialized quotas and 24-hour cleanup of unsubmitted uploads.
Assignments fix required/optional proof and allowed kinds. Reports keep immutable
attempts, encrypted links and attached proof; retry with changed proof conflicts.
Closing/reopening a report restores staged uploads; owners can discard them.
Downloads recheck report ACL each time; author/assign-only authority does not read
proof. URLs are never fetched or embedded. JPEG/PNG/MP4/WebM basic signatures are
checked; original metadata is preserved and no antivirus/transcoding claim is made.

Alembic 0012 adds encrypted immutable reward versions, explicit assignment policies,
unique manual/automatic grants and append-only transition history. Recipient accepts
or declines an offer; issuer delivers an accepted offer or cancels an undelivered one
with current rewards.grant scope. Delivered/declined/cancelled are final. Earned history
survives pauses and relationship withdrawal. Both approval paths (explicit reviewer and
configured approval-free completion) atomically offer the exact policy version with
neutral in-app notices. Current direct grant scope is required for a new automatic offer;
existing earned grants are never retracted. Concurrent decisions and duplicate events
cannot create another grant for the same occurrence/policy/recipient.

Both Mini App and native Compose Android implement catalogue/version creation, manual
offers, automatic reward choice at assignment, transitions/history, proof requirements,
HTTPS links, photo/video upload and protected download/save. Android uses system
OpenDocument/CreateDocument, bounded off-main-thread IO and no stored source URI.
Native grant actions lead ahead of the author catalogue. Existing supplied artwork,
local serif and adaptive navigation are preserved.

Local evidence: 116 backend tests on PostgreSQL, 3 Vitest, 8 real API/browser E2E,
11 JVM tests and 23 Compose tests on the owned Android 16 AVD. The combined browser
path accepts a rule, assigns a ritual with required proof/reward, uploads/restores a
photo, submits/revises/approves, verifies byte-identical authenticated download and one
automatic grant, accepts/delivers it, then creates and declines a manual offer.
Native screen tests check required-proof gating/callback fields and earned acceptance
while paused; actual MainActivity screenshots cover phone/tablet proof dialogs and
reward navigation with an AndroidTest-only synthetic transport. They do not prove
native-to-real-server auth, physical picker/Keystore behavior or real-device video IO.

Implementation defaults: optional proof/all types unless author selects otherwise;
8 MiB/file, three proofs/report, 32 MiB/occurrence, 128 MiB/member; 24h staged expiry.
Base64 transport increases transfer/memory overhead, and encrypted DB blobs enlarge
backups. Bound proof follows report history without a separate expiry/deletion policy.
Automatic policy is fixed for an assignment and requires current grant scope at approval;
changing proof/reward policy requires a new assignment. These are starting decisions,
not separately confirmed preferences. Operational details: operations/rewards-evidence.md.

Remaining: neutral Telegram delivery for rituals/rewards, real Telegram login/delivery,
physical file-picker/video performance and production backup/restore acceptance. No points,
E2EE, automatic punishment, in-app video player or verification of real-world proof is claimed.


Final review corrections: native grant cards now identify issuer/recipient, rejected
pending uploads can be replaced without losing report text/links, successful catalogue
save closes the editor, and pending file saves survive Activity recreation as metadata
bound to origin/session/member. Bytes are re-fetched under current authorization after
choosing a destination; instance change cancels saving. Both clients now fetch/render
neutral reward Updates. Ordinary report/staged lists project metadata without loading
ciphertext blobs. An isolated worker import revealed missing reward-model registration;
concrete FK targets now register it for standalone worker/CLI execution.

Observed regressions cover every correction (including isolated subprocess failure,
SQL projection, native HTTP422 recovery, editor completion, Activity recreation and
instance switch). Updated local totals: 118 backend, 3 Vitest, 8 browser E2E, 11 JVM,
27 Compose instrumentation tests. Both CI jobs (backend-web, android) passed for
final code 9958ae1fffc2a85527a1a934c5b642c625982fa0:
https://github.com/Mesteriis/vowen/actions/runs/38757822831.
Final actual MainActivity phone/tablet captures passed their screenshot tests and
the scored visual corrections were accepted. For stable recaptures only, animations
were temporarily disabled on the owned AVD and their original settings restored;
no physical device was changed. This is visual evidence using synthetic test transport,
not proof of native-to-production file transfer or live Telegram delivery.

## 2026-10-15 — M3 Telegram ritual/reward delivery

Implemented neutral Telegram delivery for new ritual assignment/due/report/review
notices and reward lifecycle notices. Migrations 0013–0014 add unique transactional
member-delivery rows, fenced leases, consent generations, direct relation revision
snapshots and durable in-flight cancellation. No historical backfill. Contacts remain
separate from provisioned members; opt-in, active/unpaused membership and current
explicit domain authority are checked again before sending. Rapid pause/resume,
assignment pause and opt-out/on cannot resurrect cancelled queued events, including
uncommitted enqueue and delayed429 interleavings. Earned in-app history is retained.

Successful delivery is terminal. Only explicit429 rejection retries after retry_after,
at most three attempts. Timeout/crash after starting a send is uncertain and is never
automatically resent; Forbidden disables the contact. No network transaction or
private resource content in Telegram. Both queues run independently each tick; keyring
failure is isolated to forms and recovers on a later tick. Operational behavior and
starting limits: [telegram-notifications](operations/telegram-notifications.md).

Fresh review found four Important cases, all reproduced RED and fixed with regressions;
no Critical/minor findings. A related relation-restore race was also reproduced and
fixed. 27 focused PostgreSQL notification tests pass. Final local gates passed:
145 backend tests, 3 Vitest, 8 real API/browser E2E, Ruff/ESLint, strict Python/TS
types, web build, generated contract drift check and heuristic secret scan. Rebuilt
Compose API/worker/proxy are healthy; HTTPS routing and scoped evidence-body smokes
pass. The isolated bot image imports and resolves all model dependencies. Android
source is unchanged in this slice; its CI build/tests run with the final code below.

Both CI jobs (backend-web, android) passed for final code
03434d70d92ef84f30af096b0146e03b5b26f38b:
https://github.com/Mesteriis/vowen/actions/runs/38763081842.

Live getMe accepted the .env token and matched the configured bot username. The local
instance has zero active, unpaused, opted-in linked members; no message was sent to an
inferred recipient or synthetic Telegram ID. Actual Telegram receipt remains unverified,
as do production restore and physical-device acceptance. Quiet hours and additional
channel settings remain open; form-delivery retry semantics are unchanged.

## Dedicated deployment — 2026-10-15

Application source `b0356dd` built and running in a fresh dedicated unprivileged
PVE LXC. nginx-ui issued a managed HTTP01 certificate; public and LAN HTTPS
readiness/static checks passed without bypass. API/db/ritual worker healthy;
Telegram poller running separately from local development. Default bot menu
read back successfully with the public Web App URL. BotFather UI readback confirms Menu Button Enabled, direct app link
`t.me/Vowen_Bot/vowen` created, and Same-Origin Restriction enabled. Main App
remains Disabled (also confirmed by Bot API); menu/direct-link launch is configured.
Native separate-window clicks were unreliable, so the owner saved the direct app.

`python3 scripts/check_deployment.py https://vowen.sh-inc.ru` passed TLS,
readiness, static Mini App, guest CSP, secret-file denial, session denial,
invalid Telegram signature and ordinary 512KiB body cap. Guest restart restored
services; guest-only nft boundary validated, origin ingress denied from Mac,
allowed from edge; private egress denied and public HTTPS allowed. PVE-only ICMP
health probes prevent false automatic recovery. Initial PostgreSQL dump restored
into an isolated scratch DB: Alembic `0014`, zero users. Same-host backup exists;
off-host encrypted backup and real participant flows remain unverified.

See [deployment operations](DEPLOYMENT_PVE.md). This is deployment evidence,
not acceptance of real Telegram ritual/reward notifications or participant consent.

Native Telegram screenshot also confirms the deployed Mini App opens and displays
ACCESS_DENIED for the unprovisioned participant. This is the expected boundary
on the fresh zero-user instance; successful participant login is not yet verified.

## 2026-10-15 — M4 discipline and private diary

Implemented discipline records with optional exact accepted rule-version and
recipient-bound ritual-occurrence links, fixed author/recipient/explicit reviewer
set, immutable encrypted content versions and encrypted transition comments.
Recipient-only acceptance/start/completion, reviewer-only confirmation, dispute,
decline and cancellation follow the documented [matrix](M4.md). New versions
require fresh acceptance; terminal records cannot be rewritten. Current direct
scopes, active/unpaused membership, optimistic revisions and PostgreSQL locks are
checked on mutations. Authority reads refresh previously loaded membership under
lock; a reproduced stale ORM pause case is covered. Conflicting reviews yield one
success and one conflict. Author-scoped idempotent creation rejects changed retries.

Recipients cannot edit assigned rule text or discipline conditions. Personal pause,
dispute, decline and withdrawal remain available without dominant confirmation.
No automatic discipline, physical-action generation, escalation or presumed finding
of violation was introduced. No real participant rules or disciplinary records
were imported or created by this work.

Diary entries default to private drafts, with encrypted date/title/body/mood/tags,
explicit readers and all-current-member snapshots. Unrelated new members never
join a snapshot through content editing. Only the author edits/deletes or explicitly
refreshes an audience. Shared detail/list/search/tag/export checks current ACL;
paused/inactive readers cannot read. Existing paused readership does not block
owner editing/removal and cannot be re-added while inactive. Deleted entries lose
ciphertext and reader rows. There are no plaintext search indexes, diary history
copies or diary notification/outbox bodies. Relationships and operator context do
not grant diary access. This remains server-side encryption, not E2EE.

Mini App and native Compose Android provide proposals, exact-version review,
transitions/comments/history and diary CRUD/audience/filtering. Mini App supports
ACL-filtered JSON file export; native diary file export remains unimplemented.
Both clients expose RU/EN labels. Actual shipped MainActivity navigation and screen
captures ran with synthetic AndroidTest-only transport; they do not prove live
Android-to-production or Telegram delivery. No physical device was modified.

Validation after final corrections: **171 backend tests**, **3 Vitest tests**,
**10 real API/PostgreSQL/browser E2E**, **12 Android JVM tests**, and **34 Android
instrumentation tests** on the dedicated Android 16 AVD. Ruff/ESLint, mypy/vue-tsc,
web build, Android lint/debug APK/test APK build, generated contract drift check,
heuristic secret scan and diff whitespace check passed. Earlier concurrent test
runs sharing the disposable database interfered; those failed runs were discarded
and the complete suites rerun sequentially. Browser fixtures now use separate
synthetic M4 participants, preserving the original M1–M3 tests.

Migrations 0015/0016 were applied to the disposable PostgreSQL test database.
No production migration or deployment was performed. Live Telegram, physical
Android acceptance, production backup/restore and independent security review
remain separate. Remote CI is run on `feat/m4`; its final immutable SHA/run result
is reported in the task delivery rather than inferred from these local checks.

## 2026-10-15 — M4 deployment and data-preservation acceptance

Deployed application source **859908ceec4de98dd58c6e085b5659d0c44ff357**, whose
backend-web and Android CI passed at
https://github.com/Mesteriis/vowen/actions/runs/38775635431.
The archive deployment has no `.git`; 265 tracked file hashes matched the exact
release archive, excluding four intentionally preserved machine-local edge files.

API, worker and Telegram poller were stopped for a consistent backup and schema
change. Backed up PostgreSQL custom dump, keyring/token/configuration and original
source; preserved pre-M4 image tags. A separate authenticated AES-256-GCM encrypted
backup was copied off the server, with its recovery key stored separately under
owner-only permissions. AEAD roundtrip and dump-header checks passed.

Restored the dump into an isolated scratch DB. Every table fingerprint matched;
existing encrypted content decrypted with the backed-up keyring. Rehearsed
0014 → 0016 → 0014 before the production migration: existing rows remained
identical and the six new M4 tables were empty. Applied 0015/0016 to production
while writers remained stopped. ALL pre-existing table fingerprints, except the
expected Alembic revision row, were identical; encrypted content remained readable.
After startup, identity/profile/relationship/version/consent/rule/response/report/
reward fingerprints still matched. No participant sessions were impersonated,
new permissions granted or consents accepted by the operator.

API/db/worker healthy; proxy and bot running with zero restarts at acceptance.
Public TLS/readiness/static/CSP/body-cap/secret-denial checks passed. Live M4
list/export endpoints reject missing or invalid bearer tokens with 401. Public
Mini App assets contain the M4 discipline/diary code. Live Telegram `getMe` matched
the configured bot identity; no test message sent. Guest nftables isolation and
Docker services remained active; local Telegram poller remains off.

**31 M4/rules authorization and privacy tests passed on the server** using a
separate migrated disposable test DB, synthetic identities/keys and frozen dev
locks. This is server-side acceptance, not a real-participant Android/Mini App
session or a Telegram notification receipt test. New discipline scopes still
require each participant's personal agreement. Ongoing scheduled backup policy,
physical Android acceptance and independent security review remain separate.


## 2026-10-15 — M5 surveys, notifications and client completion

Immutable survey plans pin a published form version, one internal recipient and
explicit readers. Once/daily/selected-weekday schedules create new invitations and
server drafts per wave, leaving old answers unchanged. PostgreSQL uniqueness plus
plan locks fence concurrent ticks/manual retries. Downtime processing is bounded;
expired, paused and before-creation periods are recorded as skipped. Feedback binds
an assignment/direct authority revision and creates one wave after approval.
Revocation is checked at generation and before queued invitation delivery. Author
and recipient independently control their own pause. No participant consent or
relationship scope was created/confirmed by this work. Automatic guest subscriptions
remain outside this slice; fresh manual guest invitation/receipt flows are preserved.

Personal in-app/Telegram choices and timezone-aware quiet intervals now cover member
and form outboxes. Quiet deferrals consume no send attempts, including settings
changed after claim; editing quiet hours re-evaluates deferrals without removing real
retry backoff. Telegram off/on generations prevent cancelled and late-committing
outboxes from resurrecting. Selecting a channel cannot opt into the bot. Neutral
blocked-bot handling and existing uncertain-send fencing remain. In-flight sends
cannot be recalled; form notices retain bounded at-least-once retry semantics.

Mini App and native Compose have periodic/approved-ritual creation, reader selection,
manual wave, independent pauses, history and notification editors. Android also has
editable invitation lifetime/retention/delivery, invitation revoke, reader removal
and form archive. Device-local light/dark/system themes cover member/guest entry.
Stale refresh responses cannot clear or replace a newer login. Permanent web auth
failure unmounts private panels and requests reopening through
Telegram, preserving assertion replay protection. Native advanced conditional form
editing/preview, diary file export and automatic App Links remain explicitly deferred
in ANDROID_CAPABILITIES.md; no WebView or fake success was added.

Local gates: **198 PostgreSQL/backend tests**, **5 Vitest**, **13 browser E2E**,
**14 JVM tests**, **39 Compose instrumentation tests** on the dedicated Android 16
AVD. Ruff/ESLint, mypy/vue-tsc, web/Android builds and Android lint passed. Contracts
regenerated without drift; tracked-tree/history secret heuristic passed. Migration
0017/0018 upgrade/downgrade rehearsal preserved existing synthetic profiles, forms
and encrypted journal rows, followed by a real API read/decryption. DST regressions
cover fold/gap waves and quiet boundaries through both repeated intervals.

Browser E2E now launches a fresh synthetic API/database seed per feature file. The
expanded suite exceeded the genuine 20/minute localhost login limit in one shared
server; production limiter/replay checks remain unchanged. All feature files are
discovered and failures preserve their exit code. Failed test-auth reuse/selectors
and missing test flush/defaults were corrected rather than weakening checks.

Production deployment and own-account live survey delivery were subsequently
verified below. Physical Android and partner ritual/reward acceptance remain open.
Detailed behavior/rollback: M5.md.


## 2026-10-15 — M5 production deployment and live survey acceptance

Deployed application source **f60013de8b0df7c96309b1ccf42213edcf13c867**, schema
**0018**. Both CI jobs passed for that exact source:
https://github.com/Mesteriis/vowen/actions/runs/38791252067.
Documentation-only follow-up commits do not change the deployed application SHA.

Stopped API/worker/bot writers before the PostgreSQL custom dump; backed up original
source, keyring/token/configuration and table fingerprints with root-only access.
An authenticated AES-256-GCM off-host copy was recovered in memory, using a separate
owner-only recovery key. Restore into a disposable database reproduced every original
table fingerprint and decrypted the existing encrypted content with the backed-up
keyring. Rehearsed 0016 → 0018 → 0016: upgrade preserved every original column and
created empty plan/wave tables; downgrade reproduced the full baseline exactly.
Production 0017/0018 migration then preserved all legacy-column fingerprints.
Existing edge configuration and secret/key hashes remained unchanged.

Public TLS/readiness/static/CSP/body-cap/secret-denial checks passed. Unauthenticated
notification settings and survey-plan endpoints return 401. The served Mini App
contains M5 code. API/db/worker healthy, proxy/bot running, zero restarts at acceptance.
Only the production bot poller runs. **198 backend tests passed on the server** in a
separate migrated disposable database with frozen dev dependencies, synthetic keys
and no production secrets mounted. An initial QA harness lacked contracts and inherited
token-file configuration; correcting the harness yielded the full passing suite.

The owner personally approved a Telegram login on the selected personal account.
A synthetic, self-recipient survey with no readers or submitted answers exercised:

- Quiet deferral: pending with zero send attempts; restoring normal settings delivered
  exactly one neutral notice. Retrying the same manual wave returned the same wave.
- Bot `/notifications_off`, then `/notifications_on`: the queued old notice remained
  cancelled, with zero send attempts and its encrypted payload cleared.
- Telegram channel off/on in the application: the queued notice remained cancelled
  without altering bot opt-in.
- Pausing the owner's technical plan: the queued notice remained cancelled.

Bounded chat observation found exactly one notice across the four test invitations.
Final outbox states: one delivered (one attempt), three manual-delivery-required
(zero attempts); all payloads cleared. Original logical channel/quiet settings and
bot opt-in were restored; cancellation generation fences intentionally advanced.
The technical plan is paused, its form archived, invitations revoked and acceptance
session revoked. Technical history remains for audit; no participant answers were
created. Both disposable databases were removed.

After cleanup, original data across **22 business tables** still matched baseline
projections and existing encrypted content decrypted. Relationship scopes and personal
consents were unchanged; no new permissions or partner consent were accepted.
Live partner ritual/reward delivery, global relationship revocation and physical
Android acceptance are not proven by this own-account test. Automated authorization
coverage passed; those live scenarios, recurring backup policy and independent security
review remain separate acceptance work.


## 2026-10-15 — M6 reproducible artifacts and automatic backups

This slice implements release artifact generation and automated backups; it does
not declare every M6 acceptance item complete. See [operator commands](M6.md).

Release builds use clean committed Git archives, frozen locks, digest-pinned base
images, an exact dependency-free uv_build backend and pinned BuildKit. Source/web
archives normalize metadata. Both linux/amd64 OCI images are built twice without
layer cache and compared by digest. Release Android runs unit tests/lint in two clean
builds and compares unsigned APK hashes. Release versionCode comes from the commit
epoch in minutes; versionName includes the source revision. Manifests and SHA256SUMS
accompany artifacts. CI uploads public unsigned artifacts for14days without production
or signing secrets; it does not implicitly push a registry or publish a GitHub release.

Local uncached image repeat builds and clean unsigned APK repeat builds passed.
The first image comparison correctly failed: uv's random cache directories and
source-ctime cache hints were included in the image. No-cache installation and
removal of build-only cache hints plus their RECORD entries corrected the cause;
runtime package records remain intact. The Java action rejected a four-component
version; the workflow now installs the exact official Temurin archive by checksum
through its jdkfile provider, rather than selecting a floating Java release.

The owner had no prior signing key and requested personal use. A separate personal
release key was generated outside the repository, with an owner-only password file.
A release APK was signed and verified; repeated signing produced identical bytes.
The key/password have a separate encrypted owner-only backup, recovered in memory.
Neither private signing material nor the password entered Git or CI. This is a
personal release signature, not a store release or physical-device acceptance.

**17 operations tests passed locally**, including real restic encryption/restore,
wrong-password rejection, actual calendar retention, preservation of another host/tag,
no pruning after capture/check/restore failure, private credential permissions,
reproducible tar archives and safe off-host failure recovery. Existing API contracts
regenerated without drift; secret heuristic and diff checks passed. Standard CI and
release artifact CI are recorded separately for the exact accepted revisions.

Installed the daily backup timer on the PVE host and an hourly encrypted-repository
pull job on the owner's Mac. The backup repository is on a separate backup disk,
outside the LXC. Default schedule03:45 Europe/Madrid plus0–5min jitter, persistent
catch-up; retention is keep-last3 plus7daily/4weekly/6monthly calendar buckets, scoped
to the instance/tag. These are starter operator defaults. The job captures a consistent
online PostgreSQL dump and stable source/configuration/original keys, creates an
encrypted snapshot, checks it, restores and compares the archive hash before pruning.
It checks the repository again after pruning. Source/key changes or any unverified
capture abort before retention. Application writers continue running.

The first real service run succeeded; its encrypted repository was copied to the Mac,
checked and restored there. Every captured manifest hash matched. That off-host dump
was then restored into a separate server database: schema0018 and **22 business-table
fingerprints matched the live instance**; its original backed-up keyring decrypted
existing content. The scratch DB and temporary server restore material were removed.
The daily timer is enabled/active; the Mac launchd job completed its first run with0.
Off-host replication depends on Mac/network availability, not an always-on remote vault.
Failure exits are visible in systemd/launchd; external alert delivery is not configured.

The deployed application remains M5 sourcef60013d/schema0018. This work installs
backup tooling without changing relations, consents, keys or the running application.
Remaining M6 scope includes full clean-install/negative/security and fault-injection
acceptance, independent security review, license/notices inventory and a published
versioned OSS release. Physical Android and partner ritual/reward acceptance remain open.

## Local development authentication (2026-10-15)

Implemented explicit DEBUG_AUTH, disabled by default. It requires
APP_ENV=development, a loopback public URL and an isolated loopback `_dev`/`_test`
database. The server rejects unsafe startup settings; disabled/nonlocal debug
endpoints return 404 before database access. Existing active CLI participants can
obtain a normal revocable/rotating session without Telegram. No provisioning,
relationship consent or authorization bypass is performed.

Local validation: **210 backend tests passed**, including debug configuration,
local peer/Host/Origin checks, denied identities, refresh/revocation/user blocking,
bilateral consent, scope and pause boundaries. Ruff and mypy passed. The client
session test covers debug login and denied replacement. Web participant selection
and the role-dependent visual workspace are being integrated on feat/ui-context;
this is local development work, not a production deployment or live Telegram proof.

## Contextual web interface — integration in progress

The real Mini App now has a shared day, a relationship selector, desktop sidebar
and mobile bottom navigation. Contextual roles derive from relationship endpoints;
profile labels grant no permissions. Assignment/proposal controls use current
bilateral consents and scopes; API authorization remains authoritative. Personal
pause, consent withdrawal, diary and sessions remain reachable. Existing recurring
surveys remain available within Forms & surveys.

Added supplied branding, a separate plain velvet page background, and a feathered
render of the original embossed emblem. Automatic Telegram entry keeps the startup
screen until authentication and profile loading finish, without mounting a login
form in between. Outside Telegram, normal/manual and guarded local DEBUG_AUTH entry
remain available. Current visual work is the Vue slice; Android design is pending.
See root design-qa.md for evidence and remaining acceptance, rather than treating
local build success as visual or live Telegram proof.

## Dark-only product decision (2026-10-15)

The owner explicitly removed light/system themes. Web member and guest entry now
force dark appearance and normalize legacy stored choices; there is no theme
selector or light palette. Native Android likewise uses only the dark palette,
clears the legacy preference and keeps light-content system bars. Updated browser
and instrumentation regression scenarios cover legacy light preferences.

Local web lint/typecheck/unit tests/build passed. Android testDebugUnitTest,
lintDebug, assembleDebug and assembleDebugAndroidTest passed. Instrumentation
scenarios were compiled, not executed on a device for this slice.

## Compact controls and responsive web acceptance (2026-10-15)

Owner feedback replaced oversized card/list spacing with a denser application
rhythm. Web actions use outlines, smaller typography and reduced padding. Native
primary actions now share a compact OutlinedButton with unchanged callbacks/tags.
Touch targets remain44px; compact session actions paint a smaller outline within
that target. Session rows show name/status/time and an adjacent revoke action,
identify the current device and collapse revoked/expired records into history.
Personal pages omit the irrelevant relationship selector while preserving pause,
refresh and sign-out. Recurring surveys render once within Forms & surveys.

Local checks:210 backend tests,12 web unit tests,18 real-API browser scenarios passed;
the browser suite traverses all11 sections at390/768/1024 widths, verifies overflow
and touch targets, distinguishes home load failures from empty data, checks automatic
Telegram entry and revokes another session through the compact list. M4 regressions
were fixed: confirmation completion is awaited before refreshing authority, and
confirmation dialogs are centered within the viewport. Native unit/lint/APK and
instrumentation-APK builds passed; native instrumentation was not executed here.
Exact-commit CI results will be recorded after the final integration run.

Final web visual acceptance: all11 pages were inspected again on phone and tablet;
root design-qa.md now records a passed result limited to the Mini App. Exact390/768/
1024 browser checks cover33 section/viewport pairs. The integration39c3e72 checks CI
passed backend-web and Android:
https://github.com/Mesteriis/vowen/actions/runs/38813788301
A final time-field layout fix passed the complete18-scenario browser suite locally
and is submitted with the QA report to the same CI workflow. Native physical-device
visual acceptance and live Telegram remain pending; production is unchanged.

## Entry screen annotation cleanup (2026-10-16)

Removed the six owner-selected elements only from the signed-out web entry:
crest/wordmark link, entry card heading, operator-provisioning explanation,
debug explanation, technical privacy footer and language toggle. Telegram and
server-gated local login remain functional; profile language and member workspace
are unchanged. Browser inspection confirmed the removed elements are absent.
Web lint, typecheck/production build, 12 unit tests and diff whitespace check passed.
No backend, schema, Android or production changes were made for this slice.

Entry follow-up: removed the signed-out slogan. When server-gated DEBUG_AUTH is
active, only local login is offered; the Telegram button remains in normal mode.
Removed the now-unused divider above the debug form. Verified local debug rendering;
web lint, production build/typecheck and 12 unit tests passed. Live Telegram and CI
for this follow-up were not checked here.

## Selected compact local-login design (2026-10-16)

Implemented the owner's first displayed visual option: subdued DEBUG metadata,
a labeled participant selector and adjacent outlined Sign in action. Desktop block
is about131px high, controls retain44px hit areas. Scoped desktop/source comparison
and mobile overflow inspection passed; actual local login opened the selected
member workspace. Web lint, typecheck/build and12 unit tests passed. Production
and native Android are unchanged. CI for this slice is not yet checked.

Entry polish: local member select now uses the existing Tabler chevron with a12px
right inset and reserved text padding; the native select/keyboard behavior remains.
The entry emblem uses lighten blending over the velvet, removing its dark rectangular
backdrop without changing the source asset or dimensions. Browser selection and
44px control height verified. Web lint, build/typecheck and12 unit tests passed.
CI and other browser engines were not checked for this small slice.

## Relationship economy and contextual rituals (2026-10-16)

Implemented migration0019: append-only encrypted currency history, a wallet per
directed relationship, priced shop listings, atomic purchases and multiple pinned
ritual reward versions plus currency. The wallet belongs to the subordinate;
Dominant manages that participant's coins, never a personal balance. Switch has a
wallet only in an incoming subordinate relationship. Credits require a positive
amount and comment. Automatic awards occur after approval (or successful reporting
when approval is not required); retries cannot duplicate grants or ledger entries.
Revocation/pause stops new operations while preserving earned assets/history.
New reward policies apply to future, not already-created occurrences. Legacy single
reward policies/grants survive migration; rollback refuses to discard new economy.

Mini App now separates assigned rituals, review queue and own executions by directed
context. Dominant sees subordinates' schedule, with templates/settings collapsed.
New ritual creation continues directly to schedule/assignment. Shop supports credits,
listing creation/hiding, purchases and history. Rule versions include discipline
terms, preserving old-client edits and accepted snapshots. Global personal-pause
buttons were removed; server pause/consent protections remain. Native Android includes
the contextual shop, multi-reward assignment and rule discipline fields.

Verified locally:218 backend tests,13 web unit tests,19 API-backed browser scenarios;
Android16 unit tests, lint, debug APK and instrumentation APK builds. Browser shop
checks cover purchase/history and390px overflow; local Dominant preview explicitly
labels Luna's coins. Additional ownership assertions are included in the shop/API
regressions. Ruff, mypy and heuristic secret scan passed. CI result is recorded below
after the committed revision completes. Local synthetic preview was backed up before
0019 migration; production and live Telegram were not touched.

Remaining: diary date-only/current-day flow and stylus input; full native contextual
home/ritual navigation redesign and device acceptance; tighter today-only home agenda.
Legacy offer controls remain behind the catalogue for compatibility. Shop price edits
exist through API, with creation/hiding in UI; wallet history displays latest500 entries.
Currency-only credits have no dedicated Telegram notification. No refunds, transfers,
real money or automatic rule-period bonuses are implemented.

Integration revision3778ec1 passed both backend-web and Android CI:
https://github.com/Mesteriis/vowen/actions/runs/38888467656
Ownership regressions also passed locally:7 economy API tests and the shop E2E
asserting Dominant cannot buy and subordinate cannot credit themselves.

Local preview recovery: its keyring had incorrectly shared the E2E output directory;
after E2E cleanup and restart, the old synthetic records could no longer decrypt.
The old database/dump were preserved, and a fresh synthetic design database was
seeded through normal APIs. Preview keyring now resides outside test output, and a
subsequent restart/login/context switch succeeded. No production data was affected.

## Selected home redesign (2026-10-16)

Implemented the first displayed home direction in Mini App and native Android:
chronological day agenda, review backlog, compact relationship selector, private
diary shortcut and a supplementary review/upcoming column when width allows.
Removed the large hero, counter tiles and duplicate relationship banner on Home.
Subsequent owner refinements remove phone greetings/taglines and use16px task titles,
12–13px supporting text and compact outlined actions with44px touch targets.
Empty upcoming sections and the redundant home footer are omitted.

Today is computed from due_at in the viewer's timezone; historical pending reviews
remain independently accessible. Contexts remain directed and server capabilities
govern reports/reviews. Home opens the selected occurrence's report/review screen,
not just a generic ritual list. Native now starts on Home when rituals are available,
with phone bottom navigation and wider navigation/agenda layouts. Other sections
retain their existing layouts. No backend schema/API or production change.

Local checks:15 web unit tests,19 real-API browser scenarios (including690px fold
layout and review deep link),18 native unit tests, Android lint/debug APK and
instrumentation APK builds. Synthetic Home component instrumentation passed at
390x844,834x1194 and690x828 emulator sizes; six native navigation/consent/profile
regressions passed. These are emulator/component checks, not a physical Fold7 or
live Telegram acceptance. Local preview remains at127.0.0.1:5176/#home.
The scoped visual comparison with the selected source and subsequent owner refinements
is recorded in design-qa.md. Implementation CI is running for this committed slice;
its final outcome is reported in the session handoff rather than assumed here.

## Relationship picker follow-up (2026-10-16)

Replaced the browser-native relationship select with an app-owned dark combobox:
compact trigger, separate participant/role/status lines, selected checkmark, pause
color and scrollable options. Arrow/Home/End, Enter/Space, Escape/Tab and outside
pointer closing preserve keyboard/pointer access. Directional context/permissions
are unchanged. Web-only component; Android retains its native dark menu.

Web lint/build and15 unit tests passed; shop real-API regression verifies keyboard
selection/Escape and contextual balances; seven responsive/auth/session browser
scenarios passed at390/690/768/1024 widths. Local opened-menu captures confirm
readable dark options without OS white/blue surfaces. No backend/schema/deployment
changes. CI outcome is reported against the final pushed revision.

## Ritual interface, selected direction 3 (2026-10-16)

Mini App and native Android now separate assigned rituals, pending review and
reusable templates. Assignments are grouped by daily/weekly/once cadence. Wider
layouts show the selected ritual beside the list; phones open a separate settings
screen. Creation, schedule and reward editors no longer expand the entire list.
Duplicate relationship banners/slogans and manual refresh chrome were removed
from this page. Existing report/evidence/review/history workflows remain.

Following owner feedback, schedule, reward and pause/resume actions use compact
44px/dp icon buttons with accessible names (web also has hover titles). Revocation
remains under More actions. Native now supports editing future reward bundles;
local schedule presentation preserves the schedule timezone and selected weekdays.
Permissions continue to come from directed relationships and server capabilities.
No backend/schema, production or live Telegram change.

Verified locally: web lint/typecheck/build, 16 unit tests; all 19 real-API E2E
scenarios, followed by the updated ritual regression covering phone settings →
schedule/reward editor and unchanged bundle save. Android 20 unit tests, lint,
debug and instrumentation APK builds; eight focused instrumentation tests,
including actual MainActivity navigation. Compact inspector interactions also
pass on emulator viewports 390x844, 690x828 and 834x1194. Visual evidence and owner
amendments are recorded in design-qa.md. Physical devices and live Telegram remain
unverified. Final CI outcome is checked against the pushed commit in the handoff.

### Ritual masthead density follow-up (2026-10-16)

Removed the separate creation-button row. Tabs and creation now share one row;
phone creation is a labelled 44px plus icon. Title/profile share a compact row,
with context immediately below; redundant mobile brand and date are omitted on
this page. Feedback appears below navigation so successful operations do not
push the controls apart. Tabs have short color/underline transitions and content
enters over 160ms; reduced-motion disables both. Native ritual title/crest/create
also share one 44dp row. No authorization or API changes.

Verified web lint/build/16 unit tests, real-API ritual scenario (including header
height and creation alignment at 390/690/834px, reduced-motion and mobile editor
transitions), Android 20 unit tests/lint/debug and instrumentation builds. Native
header was compiled, not rerun on an emulator in this follow-up. Normal local
Mini App inspected on phone and wide viewports; no physical-device or Telegram
acceptance claim. CI outcome is reported for the final pushed revision.

### Relationship avatars in ritual header (2026-10-16)

The ritual header now contains an avatar pair context picker instead of a wide
relationship toolbar: viewer initial, directed D/s arrow, partner initial.
Paused/revoked/proposed states have distinct symbols; shared day has a group icon.
Opening the menu still exposes full participant names, exact contextual role and
status, with the existing keyboard/listbox behavior. Other pages keep their text
picker; profile remains available through navigation. Native ritual header uses
the same avatar-pair/menu arrangement. Profile data has no photo/avatar field, so
these are initials, not fetched Telegram pictures. No API/permission changes.

Verified Mini App build/lint, real-API ritual workflow with both directed roles,
keyboard selection/Escape, two avatars, absent toolbar, and390/690/834px bounds.
Android unit/lint/APK builds pass; this avatar follow-up has not been run on an
emulator or physical device. Final CI is checked against the pushed revision.

### Ritual review cards (2026-10-16)

Review queue now uses bounded charcoal cards with participant initial, title/status,
latest report preview (four lines), submitted time and evidence count. The complete
report/evidence still opens in the existing decision dialog; every prior attempt
remains in expandable history. Review heading/history share a compact row. Phone
uses a single column, wider views wrap cards into a grid. Native occurrences also
use outlined cards and expose the latest review text/evidence count. No changes
to review authority, optimistic revisions, evidence access or notification effects.

Web lint/build/16 unit tests and real-API ritual regression passed, including
submitted preview/evidence count,390/690/1280 card bounds, request changes, revised
report, approval, history and attachment download. Android20 unit tests/lint/debug
and instrumentation APK builds passed. Native card appearance has not been rerun
on an emulator in this follow-up. Final CI is checked for the pushed revision.

### Ritual template catalogue cards (2026-10-16)

Templates/drafts now use compact charcoal cards with status, three-line description
preview and44px icon actions (edit/new version, publish, assign, history, archive).
The redundant expandable catalogue wrapper is removed. Version history opens in a
bounded scrollable modal; complete version descriptions remain available there.
Editing an existing template preserves the Templates tab after cancellation/save.
The same card/action/history structure is implemented in native Android. No API,
permission, schedule snapshot or version lifecycle changes.

Web build/lint/16 unit tests and real-API ritual regression passed: four published
icon actions expose accessible names/44px bounds, history content/Escape, existing
version editor and assignment editor, tab preservation,390/690/1280 card bounds,
and the previous report/review/evidence workflow. Android20 unit tests/lint/debug
and instrumentation APK builds pass; updated native instrumentation locator uses
icon contentDescription, but emulator execution was not repeated in this follow-up.
Final CI outcome is checked against the pushed revision in the session handoff.

### Review density correction and avatar centering (2026-10-16)

Replaced review cards with compact bounded rows: title/status, single-line preview,
recipient/submission metadata and one44px icon. Removed the nested preview panel,
expanded history and large text action from the list. Full reports, decisions,
comments, links and photo/video downloads are now in the existing bounded dialog.
Approved/history rows open that dialog read-only; decision controls require the
server-provided can_review flag and an unpaused viewer. Own execution history is
unchanged. Native uses the same compact rows/full-history dialog pattern.

Avatar circles use a single centered line box without padding; native ritual
initials exclude Android font padding. Actual local Cyrillic А/Л glyph raster
bounds were within1px of their circle centers (antialiasing/pixel rounding).

Verified web build/lint/16 unit tests and real-API ritual regression: review rows
<=140px high at390/690/1280,44px icon actions, full two-attempt history, no approval
button in read-only history, exact attachment download and prior review/rewards
workflow. Android20 unit tests/lint/debug/instrumentation builds passed.
No new emulator, physical device, deployment or live Telegram verification.

### Uncommitted dev UI iteration: glass button and velvet parallax (2026-10-16)

Mini App action buttons share a dark translucent/backdrop-blurred surface,
including icon actions and modal actions; selected/danger/disabled action states
retain distinct tints. Tabs, navigation, avatar/context selectors, quiet controls
and selectable ritual rows retain their original surfaces without blur.
A shared clipped texture layer provides scroll parallax on all web pages via a
passive listener/requestAnimationFrame, with reduced-motion disabling movement.
Checked in a separate local browser tab:178px page scroll moves texture32px;
reduced-motion yields no transform, no horizontal overflow or console errors.
Per owner request: no build, automated suite, commit, push or CI for this iteration.
Native Android effect parity is not implemented/verified in this web-only slice.

### Uncommitted dev UI iteration: own ritual executions (2026-10-16)

Own executions now use compact bounded cards (about98px in inspected desktop and
390px phone views), short local dates/deadlines and44px info/report/skip icons.
Full instructions and existing report history are available in a read-only details
view; the report editor also shows instructions/deadline. Backend capabilities,
request keys, report submission, skip and evidence handling are unchanged.
Manually inspected local synthetic own-execution context: no horizontal overflow,
details opens with full description, no console errors. No build, commit or CI;
Android parity and automated regression checks deferred to the agreed batch.

### Ritual workspace padding annotation (2026-10-16)

Removed the redundant 24px inner workspace padding in the existing 761–1100px
ritual layout breakpoint. Outer page spacing and phone safe margins remain.
Verified rendered padding is 0px at 1007px with no horizontal overflow.
No build, commit or CI run for this visual adjustment. Approval workflows remain
pending implementation; this spacing adjustment does not implement them.

### Recipient change requests and dominant decisions (2026-10-16)

Implemented persisted requests for ritual skip/planned pause and rule add/edit/
removal. Requests bind the direct issuer/recipient relation, exact agreement and
resource revisions; only that issuer can approve/reject. Recipient can withdraw.
Reasons, proposed content, target title and decision comments use encrypted
payloads. Creation keys, pending uniqueness and serialized decisions prevent
repeated effects. Revoked scopes hide issuer access; stale versions/agreements,
personal pause and expired occurrences prevent approval. Personal pause and
consent withdrawal remain immediate. Rule removal revokes only that assignment;
add/edit creates a published version pending the recipient's separate acceptance.
Existing explicit managers are preserved and checked again. Planned ritual
pauses record their author so the issuer can resume their own pause; legacy pauses
retain recipient resume. Paused intervals are not replayed, notices are suppressed.

Added compact web request editor/queue/history and Android DTO/API/state/actions/
request screens. Web queues refresh on section activation and returning focus.
Updated OpenAPI and generated web/native contracts. Behavior and endpoints are
recorded in docs/features/change-requests.md. No Telegram request-delivery adapter
was added; requests are presented within the relevant application sections.

Verification: 226 backend tests passed (including PostgreSQL concurrency, rights,
version/expiry conflicts, encryption, notifications and contract equality); Ruff
passed and mypy passed on 72 source files. Web typecheck and 16 existing unit tests
passed. In separate real local browser sessions verified recipient submission,
issuer-only decision controls, target unchanged while pending, persistence after
API restart and withdrawal. Test request was withdrawn; prior demo rituals were
not altered. Dialog measured 358x303 at390px and480x303 at690px; no horizontal
page overflow. No Android build/emulator/device or live Telegram verification.

Alembic0020 applied to disposable test and local vowen_design_test databases.
Before the design migration saved artifacts/deployment/ui-context/backups/
before-0020.dump. Preserved counts across migration:12 users,3 relations,
4 ritual assignments,0 rule assignments,0 journal entries. Local API restarted
without seeding and continues on8002, Vite on5176. Production was not changed.
Per owner request: no build, commit, push or CI run.

### Journal timeline and persistent digital ink (2026-10-16)

Owner selected journal main concept1 and focused handwriting concept3, then
explicitly reiterated phone support. Implemented date timeline, compact expanded
entry/preview, overflow actions, private reader settings and separate fullscreen
writing sheet. Phone is one column with tools below the paper; tablet and wide
Fold views use side tools. Back/keyboard returns to the text editor with focus.
Removed search/tag/date inputs; old tags/mood are preserved. Existing public query
parameters remain compatible. New entries must use today's date in the author's
profile timezone; an existing date cannot be moved.

Handwriting is a bounded versioned normalized stroke document inside the existing
encrypted journal payload. Supports handwriting-only entries, stylus pressure,
whole-stroke eraser, undo/redo, nib widths, opt-in finger drawing and consistent
page geometry on resize. Explicit save and unsaved-change warning; no OCR or
crash-proof autosave claim. Legacy clients omitting handwriting on text edits do
not erase existing ink. Sharing/reader snapshots and diary authorization stay
unchanged. No schema migration required. OpenAPI/web/native DTOs regenerated.
Native journal source now has the same API and ink view; a session-bound in-memory
ViewModel draft preserves editing state through configuration/fold changes without
serializing diary contents to disk. Native source has not been built or run.

Verified full backend229 tests passed, then final targeted journal4 tests passed
including profile-timezone boundary. Web typecheck,18 unit tests, backend Ruff and
mypy72 source files passed. Real local browser: separate synthetic Demo10 entry
saved with text+stroke, reopened in a fresh session, erase/undo/redo checked. Demo
entry remains clearly labelled Local handwriting check; no owner's diary content
created or changed. Phone390x844, tablet834x1194 and Fold-sized690x780 inspected;
no horizontal overflow, correct bottom/side tools. Physical S Pen/palm handling,
Android compilation/device execution and real mobile keyboard remain unverified.
Design comparison and resolved findings appended to design-qa.md. Screenshots and
selected references saved in artifacts/design/ui-context/journal-*.png.

Local API restarted without seeding; normal user diary remains open on5176/#journal.
No production deployment, build, commit, push or CI run, per owner instruction.

### 2026-10-16 — Rules accordion and punishment selection (local UI iteration)

- Implemented selected Rules design option 1 in web: compact relationship avatar header, underline tabs, one expanded charcoal rule card, icon actions, version/consent disclosure, bounded editors/history/assignment/review dialogs; narrow-phone create/edit uses full screen, tablet/Fold uses up to 540 CSS px.
- User clarified punishment selection comes from existing authorized discipline records, not a new library. New `PunishmentPicker` copies the selected current version's conditions into the encrypted rule content / change-request content. It does not start a punishment or grant access to a source record; later source revisions do not change a saved rule. Legacy conditions are preserved unless explicitly replaced/cleared. API/schema unchanged in this slice.
- Renamed the visible navigation/page to «Наказания» / Punishments while retaining compatible internal discipline routes and API identifiers.
- Native Android source mirrors accordion, compact icon actions, adaptive editors, existing-record picker and navigation label. Existing Compose tests were adapted for collapsed cards. Android compilation/device tests intentionally not run, per owner instruction against builds.
- Browser QA on synthetic local data: created a QA-labelled punishment record and rule, selected/saved conditions, published template, sent assignment which remains pending recipient consent; preserved the user's other draft. Checked web at 390×844, 834×1194 and 690×780 CSS px with no horizontal overflow; phone editor fills viewport, tablet/Fold dialog width 540 px. Site zoom 130% was accounted for in CDP viewport dimensions. Screenshots: `artifacts/design/ui-context/rules-*.png`.
- Checks: web typecheck passed; 18 web unit tests passed; git diff whitespace check passed. No production build, commit, push, deployment or real Telegram/device validation.

### 2026-10-16 — Rewards marketplace and explicit item audience (local)

- Implemented selected marketplace option 1: photo product shelves/carousels, compact avatar context/header, shopper balance and confirmed purchase sheet; owner add/edit/credit controls; separate received/grants tab and author library. Phone, tablet and Fold responsive layouts use the existing dark theme and supplied brand assets. Four generated selectable covers are bundled locally in web and Android.
- Reward version cover/category is persisted in existing encrypted payload with backwards-compatible defaults. OpenAPI, web types and native DTO generator updated. No schema migration required.
- User added «Кому доступен товар»: explicit multi-recipient availability per exact reward version, implemented via atomic GET/POST shop availability endpoints. Current direct authority checked for every changed relationship, globally ordered party locks and version/listing locks, full revision snapshot, stale/conflicting writes rejected; hidden items cannot be bought. Separate balances retained. New concurrency/rollback/ACL/versioned-cover integration tests added.
- Verified local browser flow with synthetic participants: created breakfast/walk demo definitions/listings, hid breakfast through recipient checkbox and confirmed absence for buyer, restored it, credited 120 with demo comment, bought breakfast for 80; balance 40→160→80, reward visible as accepted in Received. No real payments, Telegram delivery, production data or physical device actions.
- Browser sizes: 390×844, 834×1194 and 690×780 CSS px, no horizontal page overflow; horizontal shelf navigation works with keyboard and reduced motion; purchaser sees no management fields; dominant sees no own coin balance. Images loaded. Phone purchase sheet and Fold audience dialog checked visually. Captures under `artifacts/design/ui-context/rewards-*.png`.
- Verification: all 232 backend tests passed, Ruff passed, Mypy passed (72 sources), web typecheck and 18 web tests passed, diff whitespace check passed. One initial full run found inconsistent POST/GET row ordering in the new endpoint; deterministic response ordering corrected and full suite rerun successfully.
- Native Android sources mirror marketplace, photo shelves, editor, audience, coin and purchase dialogs; not compiled or device-tested per owner ban on builds. No build, commit, push or deploy was performed. Synthetic preview DB was preserved across API restarts; disposable test DB remains separate.
- Existing Android reward UI tests were adapted for Received disclosure, explicit relationship selection and library/editor navigation. They remain unrun under the no-build instruction.
# 2026-10-16 — фикстуры магазина для локального интерфейса

- Четыре примера товаров вынесены в `scripts/fixtures/rewards.json`.
- `scripts/import_reward_fixtures.py` читает файл и импортирует недостающие товары
  через API локального DEBUG-сервера. Существующие лоты и финансовая история
  сохраняются; production-запуск не подключён к фикстурам.
- В текущем синтетическом магазине добавлен один недостающий товар, три сохранены.
  Повторный импорт: 0 новых определений, 0 новых лотов, 4 сохранённых.
- Проверка импортера: 1 unit-тест прошёл, ruff прошёл. Сборки и коммиты не выполнялись.

## 2026-10-16 — общий каталог наград

- Реализован режим «Доступен всем» для всего пространства. Доминант с активным
  согласованным контекстом видит чужие активные лоты независимо от их аудитории;
  управление остаётся автору. Общий каталог показывается без выбора партнёра.
- Общая видимость не создаёт общий баланс: покупка требует активных согласованных
  отношений с автором и `rewards.grant`, списание идёт из соответствующего кошелька.
  ID чужих отношений, кошельки и история покупок через каталог не раскрываются.
- Alembic0021 применена к локальным vowen_test и vowen_design_test без сброса данных.
  Существующие лоты сохраняют закрытую аудиторию по умолчанию. Для синтетического
  «Вечер вместе · демо» общий доступ включён через интерфейс; фикстура обновлена.
- Проверено: 234 backend-теста прошли; 18 web-тестов прошли, web typecheck,
  Ruff и Mypy (72 исходника) прошли. Добавлен сценарий общего/закрытого каталога,
  запрета чужого редактирования, сокрытия чужих relationship IDs и повторной покупки
  общего лота через отдельные отношения без смешивания балансов.
- В браузере проверены общий каталог и сохранение флага из общего контекста;
  геометрия при ширине390 и690 CSS px не имеет горизонтального переполнения.
  Снимок настройки: artifacts/design/ui-context/rewards-public-access.png.
- Android DTO, запросы, каталог, покупка и выбор аудитории обновлены в исходниках;
  сборка и проверка на устройстве не выполнялись. Сборок, коммитов и деплоя нет.

## 2026-10-16 — обычные названия товаров из фикстур

- У четырёх товаров убраны «· демо» и фраза «Демонстрационный лот» из названий
  и описаний в JSON-фикстуре и локальной витрине. Участники не переименовывались.
- Локальные товары обновлены через обычные API версий и доступности. Цены,
  аудитории, кошельки, покупки и выданные награды сохранены. Старые версии скрыты,
  не удалены; история сохраняет исходный снимок товара.
- Каталог не показывает скрытые устаревшие версии рядом с новой версией товара.
  Импортер распознаёт прежние названия при повторном запуске и не создаёт дублей.
- Проверка: 12 тестов экономики и импортера прошли; Ruff прошёл; повторный импорт
  сохранил четыре лота без добавлений. Обычные названия проверены в открытой вкладке.
  Сборки и коммиты не выполнялись.

## 2026-10-16 — 100 товаров в фикстурах магазина

- `scripts/fixtures/rewards.json` содержит ровно100 уникальных товаров: название,
  описание, условия, обложка, категория, цена и доступность. Полки:63 совместных
  занятия и37 позиций заботы/подарков. Названия и описания без пометок «демо».
- Сгенерированы96 индивидуальных PNG-обложек через встроенный ImageGen; четыре
  прежние обложки сохранены. Точные промпты и manifest исходных имён сохранены
  рядом с фикстурами. Все100 изображений различны по SHA-256, PNG-размеры не менее
  512px; Android-копии совпадают побайтно. Изображения хранятся внутри проекта.
- Импорт в синтетический dev-магазин:96 новых определений и лотов,4 сохранённых.
  Повтор:0 новых определений/лотов,100 сохранённых. Балансы, покупки, цены и
  аудитории существующих лотов сохранены. Исправлена старая обложка «Выбор фильма»
  через новую версию и замену лота; прежняя версия и история не удалялись.
- Сервер принимает только локальные известные идентификаторы обложек, отклоняет
  URL, пути и идентификаторы вне диапазона. Контракт и клиентские DTO обновлены.
  Импортер проверяет наличие и PNG-заголовки всех картинок до изменения данных.
- Web показывает счётчики63/37, сохраняет новую обложку при редактировании.
  Android исходники используют LazyRow и декодирование обложек с ограниченным
  размером вместо загрузки всех полноразмерных картинок в карусели.
- Проверено:242 backend-теста,18 web-тестов, Ruff, Mypy72 исходника и web typecheck
  прошли. В отдельной локальной галерее100/100 изображений загружены; все обложки
  просмотрены в двух обзорах. Основная страница магазина показывает100 товаров
  через карусели и счётчики. Снимок:artifacts/design/ui-context/rewards-100-products.png.
- Android не собирался и не проверялся на устройстве. Сборок, коммитов, пушей,
  production-изменений и live Telegram не было.

## 2026-10-16 — все 100 товаров доступны всем

- По прямому указанию владельца все 100 JSON-фикстур имеют `audience_all=true`.
- В локальном магазине обычным API обновлены три оставшихся закрытых товара;
  цены и балансы не менялись. Под непривязанным синтетическим пользователем
  подтверждены все100 товаров с общим доступом. Правила оплаты остаются прежними.
- В тесте фикстур закреплено требование общего доступа для каждой позиции.
  Восемь unit-тестов фикстур прошли. Сборок и коммитов нет.

## 2026-10-16 — роли магазина и покупки с разрешением

- Реализована каноническая роль магазина, контролируемая оператором; метки
  профиля не повышают полномочия. Alembic 0022 применён к тестовой и локальной
  design-базе; перед изменением design-базы сохранён pg_dump. Сброса данных нет.
- Dominant управляет любыми товарами, включая чужие фикстуры; выключенные видны
  чёрно-белыми. Switch только просматривает и переключает доступ своего низа,
  никогда не покупает. Bottom запрашивает покупку. Личные права и согласия
  отношений проверяются дополнительно; чужие кошельки/дневники не открываются.
- Запрос резервирует цену, уведомляет верх отношений и ожидает разрешения.
  Одобрение списывает монеты, отказ/отзыв освобождает резерв. Погасить после
  выполнения может любой участник покупки. Цена/условия старых заявок неизменны.
  Старые оплаченные покупки совместимы; конкурентные повторы защищены.
- Web и Android исходники/DTO обновлены. Импортер переведён на канонического
  доминанта и общий каталог: повтор сохранил 100 товаров, ничего не добавил.
- Проверено: 246 backend-тестов и 18 web-тестов прошли; Ruff, Mypy (76 файлов),
  web typecheck и diff-check прошли. Дополнительные проверки приватных товаров
  и актуализации ролей под блокировкой: 15 тестов магазина/экономики прошли.
  Один первоначальный запуск pytest из корня захватил архивные копии тестов в
  artifacts и завершился ошибкой collection; правильный запуск backend/tests
  прошёл. Проверки не удалялись.
- В браузере: Alex-switch имеет только доступ для Luna; Sasha-dominant видит
  чужую фикстуру и её редактор; глобальное выключение даёт чёрно-белую обложку.
  Все переключатели после проверки возвращены во включённое состояние.
  Luna-bottom запросила товар за45: доступно35, резерв45; Alex увидел заявку с
  разрешением/отказом. Заявка отозвана, резерв снят, исходные80 монет сохранены.
  История тестового запроса сохранена. Снимки shop-*.png в artifacts/design/ui-context.
- Сборки, коммиты, пуши, production и live Telegram не выполнялись. Android
  на физическом устройстве не проверялся. Подробности: docs/features/rewards-marketplace.md.

## 2026-10-16 — уточнение покупок для switch

- Последнее уточнение владельца заменяет предыдущий запрет: switch может покупать
  в собственных отношениях с верхним. В отношениях со своим низом переключает
  доступность товаров; глобальное управление товарами по-прежнему недоступно.
- Сервер разрешает запрос и одобрение покупки для получателя switch. Контекст
  кошелька строго выбранный; общий каталог использует единственные подходящие
  отношения с верхним и не смешивает их с переключателем доступа своего низа.
- Web и Android исходники показывают баланс и покупку для switch в нижнем
  контексте. При смене отношений web сбрасывает прежний баланс до загрузки нового.
- Проверено:16 тестов магазина/экономики, Ruff, Mypy76 файлов, web typecheck и
  diff-check прошли. В браузере Alex→Sasha показывает «Купить», Alex→Luna — «Доступ».
  Баланс Alex→Sasha равен0, тестовые начисления в design-базу не делались.
- Новая регрессия проверяет резерв, одобрение, списание и погашение switch,
  запрет покупки в собственном верхнем контексте и раздельность кошельков.
  Снимок:artifacts/design/ui-context/shop-switch-buy.png. Без сборок и коммитов;
  Android на устройстве не запускался.

## 2026-10-16 — компактный фото-список наград, автолента и три товара

- Реализован выбранный третий вариант последней тройки: лента миниатюр и строки
  товаров без тяжёлых карточек. Цена и44px иконка покупки/доступа/редактирования
  соответствуют серверным правам. Категории показывают4/3 товара, раскрываются
  порциями по8 и сворачиваются. На широком экране — две колонки.
- Верхние миниатюры увеличены вдвое по последнему указанию владельца. Добавлена
  спокойная круговая прокрутка12px/сек с явной паузой, остановкой при контакте,
  фокусе, просмотре товара, скрытой странице и reduced-motion. Проверен переход
  через конец ленты:10605→1355 при длине цикла10608, без пустого края.
- Добавлены3 общедоступные фикстуры: Чухи-чухи30, Массаж60, Выбор свидания100.
  Сгенерированы3 обложки встроенным ImageGen; web/Android копии совпадают.
  Всего103 уникальных PNG и103 полные фикстуры. Импорт3/100; повтор0/103.
  Промпты/manifest сохранены. OpenAPI/web/Android DTO обновлены для cover101..103.
- Web проверен в браузере: телефон примерно390×844, Fold730×844,
  планшет1024×1194, обычное окно. Нет горизонтального переполнения, действия44px.
  Проверены вкладки, окно товара, недостаточный баланс, раскрытие7→15→7 строк,
  пауза/возобновление, reduced-motion и отсутствие ошибок консоли. На телефоне
  товар открывается снизу; на широком экране — в ограниченном центральном окне.
- 18 web-тестов, web typecheck,14 тестов магазина/фикстур/контракта и Ruff прошли;
  git diff --check прошёл. Полный backend-набор заново не запускался: бизнес-логика
  покупок не менялась. Android исходники обновлены без сборки/запуска на устройстве.
- Design QA: сравнение выбранного макета и реализации сохранено, шумный фон
  приглушён в магазине, кнопки получили золотой акцент; финальная проверка passed.
  Evidence:artifacts/design/ui-context/rewards-list-*.png, design-qa.md.
  Сборок, коммитов, пушей, production и живого Telegram не было.

### 2026-10-16 — категории и поиск магазина

- 103 публичных товара распределены по 12 категориям; редакторы Web/Android используют те же категории. Старый `together` поддерживается для существующих пользовательских товаров.
- Явный `scripts/import_reward_fixtures.py --sync-categories` обновляет только категории, копируя текущие описания, условия, обложки, цены и аудиторию через версионированный API. На локальной design-базе: 92 обновления, повторный запуск — 0; новые товары не создавались. Перед обновлением сделан локальный dump.
- Поиск по названию и описанию в уже разрешённом сервером каталоге: все слова запроса, без учёта регистра, `ё`/`е`; очистка, счётчик и пустой результат. Карусель скрыта во время поиска. Web и Android source.
- Проверено: Web typecheck, 21 Vitest; 10 backend fixture/contract tests, 5 PostgreSQL shop tests; scoped Ruff. Браузер: 12 полок, поиск «массаж» — 2 товара, пустой запрос/очистка, телефон 389 CSS px без горизонтального overflow. Планшет 1024 CSS px — 2 колонки, без overflow (категории). Android не собирался и не запускался.
- Без сборок, коммитов и деплоя. Снимки: `artifacts/design/ui-context/rewards-categories.png`, `rewards-categories-phone.png`, `rewards-search-phone.png`.

### 2026-10-17 — типы наказаний и справочники отношений

Реализованы `physical` (девайс, часть тела, количество, сила 1–10), `ban` (описание + дни), `other` (описание). Добавлены зашифрованные справочники девайсов и частей тела, API чтения/добавления и миграция 0023. Права проверяются по прямым отношениям и текущим scopes, запись редактирует верхний автор; нижний сохраняет личное согласие/отказ/отзыв. Старая история читается, новая версия требует нового согласия.

Web: поля по типу, добавление в справочники, параметры при подтверждении и в истории, дополнительные настройки свёрнуты, форма адаптируется к телефону/планшету. Android: исходники API, DTO, редактора и истории обновлены; сборка/устройство не проверялись.

Проверено: 34 backend теста (discipline, параметры, контракт), Ruff, scoped mypy; Web typecheck и 22 Vitest. В браузере — формы physical/ban/other, добавление «Флоггер» в Алекс → Луна; телефон 389 CSS px и планшет 1024 CSS px без горизонтального overflow. Снимки `artifacts/design/ui-context/punishment-types-desktop.png`, `punishment-types-phone.png`.

Локальная design-БД сохранена перед миграцией (`before-punishment-types.dump`), миграция применена; API `/health/ready` отвечает ready. Начальные неудачные запуски интеграционных тестов были вызваны несовпадением ревизии schema guard после миграции; после обновления до 0023 указанные 34 теста проходят. Без сборок, коммитов и деплоя. Подробности: `docs/features/punishment-types.md`.

### 2026-10-17 — наказания без отдельного согласия

По уточнению владельца отдельное согласование наказания удалено: создание/правка → `planned`, затем исполнитель начинает, отмечает выполнение, проверяющий подтверждает результат. `accept`/`decline`/`dispute` удалены из команд API и интерфейсов Web/Android. Отмена записи — только автором. Ранее сохранённые статусы/события не переписываются; старые `proposed` и `accepted` допускают прямое начало. Общие полномочия и настройки отношений не изменены.

Миграция 0024 расширяет ограничение статусов БД; schema guard 0024, OpenAPI и клиентские DTO обновлены. Локальная design-БД сохранена в `before-punishment-planning.dump`, миграция применена. API перезапущен. Проверено: 37 backend-тестов discipline/параметры/контракт, Ruff, scoped mypy; Web typecheck, 22 Vitest. В браузере проверены обновлённая запись и форма с кнопкой «Запланировать наказание», без подтверждения согласия. Android-тесты обновлены в исходниках, не запускались. Без сборок и коммитов.

### 2026-10-17 — отступы стрелок выпадающих списков

В Web все обычные native single-select получили единый Tabler chevron с отступом 14 px справа и резервом 44 px под стрелку. Debug-переключатель сохраняет свой Vue-значок без дублирования, компактный выбор толщины пера сохраняет узкую ширину, native listbox/multiple не изменены; forced-colors возвращает системную стрелку. Проверено в живом локальном интерфейсе редактора наказаний: три селектора на большом экране и телефоне 389 CSS px, выбор значения работает, горизонтального overflow нет. Снимки: `artifacts/design/ui-context/dropdown-inset-desktop.png`, `dropdown-inset-phone.png`. Сборки и коммиты не выполнялись.

### 2026-10-17 — нижняя граница карточек каталога наказаний

Уточнён селектор рамки `.punishment-template-list > .punishment-template-row`: общий `article:last-child { border-bottom: 0 }` больше не убирает нижнюю сторону у последней/единственной карточки. Толщина и цвет берутся из той же рамки, что сверху, включая выделенное состояние; правило действует на всех ширинах. Проверена специфичность CSS; в текущем каталоге нет сохранённых вариантов для повторного визуального снимка. Сборки и коммиты не выполнялись.

### 2026-10-17 — «Отношения», выбранный вариант 2

Web: полоса партнёров, компактный верх с аватарами, открытый профиль на бархате, соглашение и полномочия в двух колонках либо вертикально на телефоне. Отдельный редактор предложения и окна действий работают с существующим API и точной версией отношений. Существующие данные и серверные полномочия не менялись. Анимации учитывают reduced motion, сенсорные цели от 44 px.

Проверены переключение контекста, статус паузы и отмена возобновления, сворачивание прав, заполнение/закрытие формы без отправки; 1440, 1024, 854 и 389 CSS px без горизонтального overflow, ошибок браузера нет. Web typecheck и 22 Vitest проходят; scoped diff whitespace check проходит. Визуальные сравнения и исправления двух замечаний по адаптации — в `design-qa.md`. Android и его instrumentation-тесты обновлены в исходниках, сборка/устройство не проверялись. Без сборок, коммитов и деплоя. Подробности: `docs/features/relationships-interface.md`.

### 2026-10-17 — «Уведомления», выбранный вариант 2

Web: две открытые зоны настроек, компактный верх с одним личным аватаром, переключатели каналов и тихих часов, независимый статус Telegram, раскрываемые пояснения. На телефоне зоны вертикальны, обновление находится рядом с аватаром; сохранение не перекрывается нижним меню на 389×844. Сохранены существующие API, optimistic revision и бизнес-логика доставки.

Проверено сохранение неизменённых настроек с ответом «Сохранено», валидация одинаковых границ и интервала через полночь, недоступность времени при выключенном режиме, подсказки и перезагрузка. Исходные значения каналов/тихих часов сохранены; реальных сообщений и подключений бота не выполнялось. Четыре CSS-размера без overflow; консоль без ошибок, typecheck и 22 Vitest проходят. Визуальный отчёт — `design-qa.md`. Android и его regression-test source обновлены без сборки/запуска. Без сборок, коммитов и деплоя. Подробности: `docs/features/notifications-interface.md`.

### 2026-10-17 — «Профиль», выбранный вариант 1

Web: табы «Профиль» / «Настройки», боковой индекс Общие/Уведомления/Сессии на большом экране и горизонтальный на телефоне. Имя и самоописание отделены от языка и часового пояса. Уведомления и сессии перенесены из основного меню в настройки; старые ссылки совместимы. Существующие API и серверные проверки сохранены. Перед отзывом сессии есть подтверждение, выход и обновление доступны на телефоне.

Проверены обе формы сохранения на неизменённых значениях, сохранность локального черновика при переключении, уведомления, отмена отзыва текущей сессии, клавиатурные табы и мобильное меню. Четыре размера без горизонтального overflow. Web typecheck и 26 Vitest проходят. Android и инструментальные тесты изменены только в исходниках, сборка и устройство не проверялись. Без сборок, коммитов и деплоя. Подробности: `docs/features/profile-interface.md`.

### 2026-10-17 — отдельные профиль и настройки, независимые администраторы

Предыдущая структура «Профиль / Настройки» заменена по уточнению пользователя. Профиль открывается личной аватаркой (включая шапки с контекстом отношений), содержит личные данные/язык/часовой пояс, уведомления и сессии. Настройки — отдельная ссылка внизу бокового меню и в конце мобильного «Ещё», только для администраторов. Пока там только назначение дополнительного администратора или передача своих прав.

Сервер: независимый `users.is_admin`, первый provisioned user получает права автоматически, новые участники — по назначению. Миграция 0026 для существующей базы назначает самого раннего участника. Проверки текущих полномочий, optimistic revision, DB-блокировка, атомарные изменения/аудит. D/s и метки не назначают администратора; административная роль не открывает чужие личные данные. Обновлены OpenAPI и Web/Android DTO.

30 PostgreSQL/contract-проверок и 28 Vitest проходят; scoped mypy/ruff и typecheck проходят. В браузере проверены обе роли, отмена обоих окон, профиль/меню/прямая ссылка и 4 размера без overflow. Существующим участникам при UI-QA права не передавались. Android — исходники, без сборки/устройства. Подробности: `docs/features/profile-interface.md`.

Локальная design-база обновлена до 0026 без сброса данных и с резервной копией. Ошибочная первая миграция 0026 в локальную базу vowen отменена до 0025; резервная копия сохранена в игнорируемом runtime-каталоге. Прод/удалённые серверы не затронуты. Без сборок, коммитов и деплоя.

### 2026-10-17 — справочники и стандартные часовые пояса

Реализованы пять отдельных PostgreSQL-таблиц с uid/name/description/icon/extra, стабильные JSON-фикстуры и повторный импорт без перезаписи. Биологический пол 3, гендер 7, практики 12, часовые пояса 24, виды отношений 8 — 54 записи. Предпочтения по полу/гендеру исключены по уточнению пользователя; таблицы отношений/личные значения не менялись.

Настройки → Справочники: просмотр и раскрытие всех атрибутов; добавление практики с дополнительным JSON. GET — участникам, POST практики — администратору с серверной проверкой; конкурентные дубли и недопустимые поля отклоняются. Обновлены OpenAPI/Web/Android DTO. Android UI/API — исходники без сборки и устройства.

Миграции 0027/0028 применены к design-базе после резервных копий без сброса. По просьбе пользователя 598 зон заменены на 24 основных IANA; UTC/Madrid сохранены, технические алиасы убраны. Обратимость сокращения 24→598→24 проверена в vowen_test, практики сохранены. Основная локальная база vowen и удалённые серверы этой задачей не менялись.

33 PostgreSQL/API/contract-проверки, 28 Vitest, typecheck и scoped mypy/ruff проходят. Браузер: атрибуты, валидность JSON, отмена формы, 24 зоны и 3 размера без overflow. Без сборок, коммитов и деплоя. Документ: `docs/features/reference-catalogues.md`; фикстуры: `backend/src/vowen/modules/references/fixtures/`.

### 2026-10-18 — 100 практик и URL справочников

- Добавлены активные JSON-фикстуры v2: 100 практик, всего 142 записи в пяти справочниках. Исходные 12 практик и их UID сохранены.
- Alembic 0029 добавляет nullable TEXT url каждой таблице и дополняет практики без перезаписи записей. Все URL пока null. Исторические фикстуры/миграции сохранены. API, Web и Android DTO/отображение обновлены.
- 5 unit/PostgreSQL/API/contract тестов прошли; Web typecheck, scoped ruff и mypy прошли. Живой браузер показывает 100 практик и url «Нет», снимок artifacts/design/ui-context/reference-100-practices.png.
- vowen_test и vowen_design_test обновлены до 0029; перед design-миграцией сделана закрытая резервная копия. Основная vowen и удалённые базы не менялись. Без сборок и коммитов; Android только исходники.

### 2026-10-18 — Исправлен предмет справочника практик

- Активный v3: 100 сексуальных/BDSM-практик с нейтральными описаниями и пустыми url. Общие занятия заменены по уточнению пользователя.
- Alembic 0030 меняет только неизменённые старые фикстуры; пользовательские записи/правки сохраняет, пересекающимся понятиям оставляет UID. Исторические v1/v2 сохранены.
- 6 unit/PostgreSQL/API/contract тестов прошли, включая сохранность пользовательских правок и повторный запуск замены; scoped ruff прошёл. vowen_test/design_test обновлены после резервной копии design. Основная vowen и удалённые базы не менялись. Без сборок и коммитов.

### 2026-10-18 — Отдельный справочник категорий практик

- v4: 6 справочников, 144 фикстуры. Категории «Секс»/«BDSM» — отдельная таблица; 100 практик связаны category_uid через PostgreSQL FK, категория убрана из description/extra.
- Alembic 0031 сохраняет пользовательские правки; API проверяет категорию при создании практики, Web/Android исходники отображают/выбирают категорию.
- 8 unit/PostgreSQL/API/contract тестов, typecheck Web и scoped ruff/mypy прошли. В браузере проверены новый справочник и отдельная категория практики; артефакты artifacts/design/ui-context/practice-categories.png и practice-category-links.png. В design-БД 50+50 связанных практик, строк с категорией в description/extra нет.
- Локальные vowen_test/design_test обновлены до 0031 после закрытой копии design. Основная vowen/удалённые базы не менялись. Без сборок/коммитов; Android source-only.

### 2026-10-18 — Подробные категории и альтернативные названия практик

- v5: 89 практик, 12 категорий (143 фикстуры во всех справочниках); 8 вариантов объединены через aliases, 3 общих заголовка заменены категориями. UID оставшихся записей сохранены.
- Alembic 0032 работает только с неизменёнными старыми фикстурами, сохраняет пользовательские правки и используемые категории. Поиск Web/Android исходники учитывает синонимы и категорию, добавлен совместимый фильтр. Личные предпочтения не менялись.
- 10 backend unit/PostgreSQL/API/contract тестов; 3 Vitest поиска; typecheck Web и scoped ruff прошли. Браузер: синоним «минет» → «Фелляция», фильтр категории 4/89, телефон без горизонтального overflow. Снимки artifacts/design/ui-context/practice-alias-search.png, practice-search-phone.png, practice-refined-categories.png.
- vowen_test/design_test до 0032; перед design сделана закрытая копия. Основная vowen/удалённые базы не менялись. Без сборок и коммитов, Android source-only.

### 2026-10-18 — Состав участников и групповые практики

- Новый справочник reference_participant_compositions: 10 записей, МЖМ/ММЖ — каноническое имя/синоним. Состав независим от практики и не назначает участникам роли, пол, гендер или предпочтения.
- v6: 93 практики, 13 категорий, 158 фикстур в семи справочниках. Добавлены секс втроём, групповой секс, обмен партнёрами и свинг; category_uid — FK. Alembic 0033, OpenAPI/Web-типы и Web/Android исходники обновлены. URL/icon null.
- 12 backend unit/PostgreSQL/API/contract тестов и 4 Vitest поиска прошли; typecheck Web, scoped ruff/mypy прошли. Проверен 0033→0032→0033 на тестовой БД с сохранением пользовательского описания практики. Браузер: 10 составов, поиск по синонимам, телефон без горизонтального overflow; снимки artifacts/design/ui-context/participant-compositions.png и participant-compositions-phone.png.
- vowen_test/design_test до 0033 после закрытой копии design. Основная vowen и удалённые базы не менялись. Без сборок/коммитов, Android source-only.

### 2026-10-18 — Общие справочники и отключение шифрования payload

- v7: 24 девайса, 23 части тела, всего 205 справочных записей; 21+11 M:N связей практик с FK. Web/Android DTO и исходники отображают/выбирают связи, сервер проверяет UUID и атомарность. Общие значения наказаний читаются из таблиц, личные дополнения отношений сохраняют область доступа. Alembic 0034.
- По явному запросу владельца новые прикладные payload открытые; 0035 расшифровывает все 15 типов старых записей атомарно. Для новых/переведённых записей keyring не нужен. Legacy-имена колонок/интерфейс сохранены; AES — только декодер старых данных. Политика REQ-27, README и эксплуатационные инструкции обновлены. Auth/hash/HTTPS/Keystore и резервное копирование не ослаблялись.
- Полный backend: 287 passed; затем 16 целевых тестов после правки проверки дневника без keyring. Web: 32 Vitest passed, typecheck passed; scoped mypy/ruff passed. Тестируется конвертация 15 типов, повтор без ключа, полный rollback при повреждении и восстановление ledger-trigger.
- Локальная design-БД после закрытой копии переведена 0033→0035, зашифрованных payload осталось 0; API перезапущен. Основная vowen и удалённые серверы не менялись. Снимок справочника artifacts/design/ui-context/shared-devices.png. Без сборок и коммитов; Android source-only, живой Telegram не проверялся.

### 2026-10-18 — Материалы, сценарии, форматы и места

- v8: добавлены материалы (15), ролевые сценарии (12), форматы взаимодействия (3), места проведения (6). Итого 13 справочников, 241 фикстура. Стандартные поля, icon/url null, aliases для поиска. Существующие данные/связи не менялись, профили и анкеты вне этой задачи.
- Alembic 0036, API whitelist, OpenAPI и Web/Android исходники обновлены. 15 backend unit/PostgreSQL/API/contract тестов и 5 Vitest прошли; Web typecheck и scoped mypy/ruff прошли. Проверен 0036→0035→0036 на тестовой базе и повторный импорт с сохранением пользовательских правок.
- Браузер: все четыре набора, «экокожа» → «Искусственная кожа», телефон 389 CSS px без overflow. Артефакты artifacts/design/ui-context/materials-alias-search.png и reference-venues-phone.png.
- vowen_test/design_test до 0036; перед design сделана закрытая копия. Основная vowen и удалённые базы не менялись. Без сборок/коммитов, Android source-only.

### 2026-10-18 — Заболевания/состояния и аллергены

- v9: 23 заболевания/состояния и 16 аллергенов, всего 15 справочников/280 записей. Термины сверены с NHS/клиническими источниками; provenance в docs/features/health-reference-catalogues.md. URL/icon null; персональные диагнозы, допуски к практикам, тяжесть и авто-противопоказания не добавлялись.
- Alembic 0037, API whitelist/OpenAPI и Web/Android исходники обновлены. 16 backend unit/PostgreSQL/API/contract тестов и 6 Vitest прошли; Web typecheck и scoped ruff/mypy прошли. 0037→0036→0037 проверен на тестовой базе.
- Живой UI: 23/16 записей, поиск «ПТСР» и «латекс», телефон без overflow; снимки artifacts/design/ui-context/health-conditions-search.png, allergen-catalogue.png, allergens-phone.png.
- vowen_test/design_test до 0037 после закрытой копии design. Основная vowen и удалённые базы не менялись. Без сборок/коммитов, Android source-only.

### 2026-10-18 — Структура фиксации и заботы внутри существующих справочников

- v10 без новых таблиц/записей: верёвка+манжеты → «Средства фиксации», ошейник+поводок → «Аксессуары динамики». Прежняя категория care/UID → «Восстановление и забота»; массаж и aftercare распределены по группам. По-прежнему 15 справочников, 280 записей, 21+11 M:N связей.
- Web/Android исходники показывают и фильтруют extra.group совместно с поиском/категорией. Миграция 0038 меняет восемь точных старых фикстур, сохраняет личные правки/UID/связи; проверен откат/повтор.
- 18 backend unit/PostgreSQL/API/contract тестов, 8 Vitest, Web typecheck и scoped ruff прошли. Живой UI: фиксация 2/24, забота 3/93; телефон 390 CSS px без overflow. Артефакты artifacts/design/ui-context/fixation-existing-group.png, care-existing-category.png, care-existing-phone.png.
- vowen_test/design_test до 0038 после закрытой копии design. Основная vowen и удалённые базы не менялись. Без сборок/коммитов, Android source-only.

### 2026-10-18 — Пробы стиля миниатюр справочников

- Built-in image_gen: четыре финальные миниатюры существующего элемента «Верёвка» — фото, скульптурное 3D, золотая гравюра, живописная иллюстрация. Ориентиры: reward-072.png и breakfast.png. 3D/гравюра уточнены после первого прохода для явного различия стилей.
- Финальные PNG 1254×1254 сохранены в artifacts/design/reference-thumbnails/; README содержит референсы и полный набор промптов. Визуально проверены. Поля icon, фикстуры и интерфейс не менялись: это только варианты для выбора. Без сборок/коммитов.

### 2026-10-18 — thumbnail отдельно от icon

- Добавлено nullable thumbnail во все 15 справочников (Alembic 0039), API, Web/Android типы и формы. icon не переименован и в фикстурах остаётся null. v11: 280 записей с thumbnail null, прежние UID и связи сохранены. Массовая генерация изображений ещё не выполнена.
- 17 reference unit/PostgreSQL/API тестов и 1 OpenAPI contract тест прошли; Web typecheck и scoped ruff прошли. Проверен откат/повтор 0039 на vowen_test; дизайн-БД обновлена после резервного копирования. Android сборка, все остальные сборки и коммиты не выполнялись.

### 2026-10-18 — генерация миниатюр справочников, в работе

- Пользователь изменил формат на прозрачный PNG. Гравировка золотыми штрихами, без фоновой подложки; `icon` по-прежнему null. Промпты всех 280 записей и сохранённый прогресс: `artifacts/design/reference-thumbnails/catalogue/manifest.json`; built-in imagegen, без CLI/API runner.
- Первые 24 девайса готовы в прозрачном варианте; материалы продолжают генерироваться. До смены формата создана отдельная партия непрозрачных черновиков, она не является финальным результатом.
- Альфа проверяется read-only аудитом (`audit.py`, bundled Pillow); выбранный образец осмотрен на трёх фонах. Готовые пути подставлены только в пустые thumbnail локальной `vowen_design_test` после резервной копии, реальные миниатюры видны в Settings → Справочники → Девайсы. Полные v12 фикстуры/миграция ещё не активированы: генерация не завершена. Сборок и коммитов нет.

### 2026-10-18 — пользователь остановил текущую партию частей тела

- Последняя правка направления: стройные взрослые женские силуэты, более эротичный кружевной комплект вместо утилитарного белья. Массовый генератор остановлен по слову «Стоп»; в фоне генерация не продолжается.
- Создан один v3 образец `artifacts/design/reference-thumbnails/catalogue/body-slim-lace-v3-transparent.png`, точный промпт рядом; реальный альфа-канал проверен. Образец пока не опубликован в фикстурах/БД. Состояние остановки и исходный файл отмечены в `catalogue/run-state.json`.
- 49 прозрачных изображений вне раздела частей тела сохраняются. V1/V2 изображения частей тела являются промежуточными/заменяемыми; полные v12 фикстуры и миграция 0040 всё ещё не активированы. Для продолжения надо применить новое направление ко всем 23 body-parts, не запускать старые V2 промпты. Без сборок и коммитов.

### 2026-10-18 — возобновление, нейтральные боди и разнообразие поз

- Пользователь подтвердил продолжение. Генератор отклонил пакет кружевного белья по safety/sexual; повторов этой серии и обхода через CLI не делали. Пользователь выбрал другой вариант: стройные взрослые женские силуэты в нейтральном облегающем боди.
- Создан нейтральный спортивный образец v4 с непрозрачным цельным боди. По следующему уточнению пользователя v5 добавляет разные естественные позы: шаг, профиль, три четверти, открытые ладони. Уже готовы голова, спина, кисти, ноги; остальные body-parts ещё генерируются. Золотая гравировка и реальная прозрачность сохранены.
- Активное направление и прогресс лежат в catalogue/run-state.json и manifest.json. Исторические отклонённые v1-v3 и промежуточные v4 не считать итоговыми. Полная фиксация v12 и миграция ещё ожидают завершения всех 280 записей.

### 2026-10-18 — индивидуальное кадрирование частей тела

- Пользователь добавил кадрирование. V6: отдельные рамки для всех 23 body-parts, выбранные естественные позы и непрозрачное спортивное боди сохранены. Готовые крупные фрагменты кистей, спины, ног, головы, лица, волос и шеи опубликованы в локальном preview; остальные в работе.
- Для close-up углы могут занимать сами плечи/ткань, поэтому corner alpha теперь диагностическое поле, а не требование пустых четырёх углов. Подлинная прозрачность проверяется по RGBA, наличию полностью прозрачных пикселей (>5%), видимым штрихам и уникальным хешам. Аудит/preview публикуются атомарно, sync использует только проверенные пути. При смене этапа два checkpoint остановились на прежнем требовании прозрачных углов у крупного кадра шеи; после уточнения корректного критерия повторный аудит пройден.

### 2026-10-18 — кадрирование всех частей тела завершено

- Все 23 body-parts готовы в варианте v6: индивидуальное крупное кадрирование, разные естественные позы, нейтральное непрозрачное боди, золотая гравировка и реальный alpha-канал. Проверены галереи на светлом и тёмном фоне; локальный preview использует новые миниатюры.
- Остальные справочники продолжают генерироваться: на момент записи 150 из 280 изображений сохранены в manifest.json. Полная фиксация v12 и миграция 0040 ещё не выполнены; это не завершение всей генерации. Сборок и коммитов нет.

### 2026-10-18 — миниатюры всех справочников завершены (v12 / 0040)

- Сохранены 280 отдельных прозрачных PNG для 15 справочников; thumbnail заполнен в неизменяемых v12 и снимке миграции 0040, icon/url null. UID, содержимое записей и связи сохранены. Товары магазина явно исключены, их изображения не менялись.
- Body-parts: все 23 кадра v6, разные позы и индивидуальное кадрирование в нейтральном непрозрачном боди. У падла, плети и колеса Вартенберга исправлена форма. 26 неиспользуемых прежних вариантов перенесены в локальный runtime-архив после проверки отсутствия ссылок в design-БД; исходники генератора сохранены.
- Большие очереди частично зависали без результата: незавершённые запросы остановлены, оставшиеся 18 успешно выполнены партиями по три. В manifest нет незавершённых записей; run-state complete.
- Проверки: 20 reference unit/PostgreSQL/API/contract тестов прошли; 0040→0039→0040 на vowen_test и повтор миграционного теста (1 passed); scoped ruff и Web typecheck прошли. 280/280 PNG прошли decode/RGBA/alpha/hash аудит, 280/280 HTTP HEAD — image/png с правильной длиной. Web desktop и 390 CSS px проверены; снимки completed-gallery.png, settings-mobile.png, health-gallery.png.
- Design-БД обновлена после закрытой копии before-reference-thumbnails-0040.dump; preview API перезапущен без повторного seed участников. Основная vowen и удалённые БД не менялись. Android source-only; сборок, коммитов и push не выполнялось.

### 2026-10-18 — расширение девайсов завершено (v13 / 0041)

- Добавлены 24 девайса: всего 48, включая группу «Секс-машины» из четырёх записей. Все справочники: 304 записи и 304 прозрачные миниатюры. Старые 280 записей, UUID и связи сохранены; icon/url null. Магазин не менялся.
- Исправлена форма виброседла. По подтверждённому выбору пользователя три машины изображены только корпусом и пультом, фаллоимитатор на присоске — только креплением. Четыре неверных прежних изображения перенесены в runtime-архив после проверки отсутствия ссылок; исходники генератора сохранены.
- Фикстуры v13 и замороженный снимок миграции 0041 активированы. Откат сохраняет изменённые и связанные записи, повторное применение не перезаписывает пользовательские правки и совпадающие имена.
- 27 backend unit/PostgreSQL/API/contract тестов прошли, scoped ruff прошёл. Реальный 0041→0040→0041 и повтор двух миграционных тестов прошли. 304 PNG и 304 HTTP HEAD проверены. В живом Web 48 девайсов, фильтр «Секс-машины» показывает 4/48. Галерея: artifacts/design/reference-thumbnails/catalogue/devices-v13-gallery.png.
- Design-БД до 0041 после закрытой копии before-extra-devices-0041.dump; preview API перезапущен без seed участников. Основная vowen и удалённые БД не менялись. Мобильный интерфейс заново не проверялся, Android не собирался. Сборок, коммитов и push нет.

### 2026-10-18 — одна секс-машина и восемь игрушек (v14 / 0042)

- Три машинных варианта объединены в одну «Секс-машину» с сохранением канонического UUID и синонимов. Виброседло отдельно. Добавлены восемь игрушек с отдельными прозрачными золотыми миниатюрами: теперь 54 девайса, 310 справочных записей. Магазин не менялся.
- Миграция 0042 сохраняет пользовательские правки, переносит связи неизменённых вариантов на общий UUID без дублей. Изменённые варианты не удаляются. При откате связи остаются на каноническом UUID; прежняя детализация не восстанавливается. Исторические фикстуры сохранены.
- Проверено: 30 backend тестов, scoped ruff, реальный откат/повтор 0042→0041→0042, 310 PNG и HTTP HEAD. В приложении видны 54 девайса и новые записи; галерея catalogue/toys-v14-gallery.png. Design-БД обновлена после before-toys-0042.dump, API перезапущен без seed участников. Без сборок, коммитов и push; мобильный/Android повторно не проверялись.
- Исправлена ошибка подключения при первом запуске Alembic: VOWEN_DATABASE_URL игнорировалась, поэтому пустая основная локальная vowen обновилась до 0042. После проверки 0 users и 0 строк всех чувствительных payload-таблиц сохранена закрытая accidental-main-upgrade-0042.dump, база возвращена до прежней 0025. Далее использована явная DATABASE_URL; vowen_test/design_test на 0042. Удалённые базы не затрагивались.

### 2026-10-18 — игрушки и опоры добавлены (v15 / 0043)

- Добавлены 5 игрушек и 3 позиционные опоры в существующий справочник девайсов, с группой «Мебель и опоры». Всего 62 девайса и 318 записей. Каждому дополнению назначена отдельная прозрачная золотая миниатюра; icon/url null. Старые записи, UUID, изображения и связи сохранены; магазин не менялся.
- 0043 не перезаписывает пользовательские правки/совпадающие имена; откат сохраняет изменённые и связанные записи. Исторические миграционные тесты используют фиксированные версии данных.
- 33 backend теста и scoped ruff прошли; реальный 0043→0042→0043 на vowen_test прошёл. 318 PNG и HTTP HEAD проверены. Живой Web: «Мебель и опоры» 3/62. Галерея: artifacts/design/reference-thumbnails/catalogue/toys-supports-v15-gallery.png; промпты/источники: generated-toys-v15.json в том же каталоге.
- Design-БД обновлена до 0043 после закрытой before-toys-supports-0043.dump; preview API перезапущен без seed участников. Основная vowen проверена на 0025 и не менялась в этом обновлении, удалённые базы не затрагивались. Мобильный/Android повторно не проверялись. Без сборок, коммитов и push.

### 2026-10-18 — все справочники загружены в основную локальную БД

- По явному запросу пользователя основная локальная vowen обновлена Alembic с 0025 до 0043. Перед миграцией подтверждены 0 users и создана закрытая runtime-копия before-full-reference-load-0043.dump. Удалённые базы не затрагивались.
- Seed v15 выполнен в vowen и vowen_design_test: в каждой 318 записей в 15 справочниках, 62 девайса, 21 связь practice-device и 11 practice-body-part. Проверено наличие каждого fixture UUID. Повторный seed не меняет количества и не создаёт дублей; штатная appctl references seed на основной базе тоже прошла.
- Подготовлен artifacts/fixtures/reference-catalogues-v15.tar.gz: 17 JSON наборов (15 таблиц и 2 набора связей), manifest.json с SHA256 данных/миниатюр и README. Все 19 элементов архива прочитаны обратно и сверены с исходниками. PNG остаются в web/public/references, в архив данных не включены; пользовательских данных и DB-backup в нём нет. SHA256 архива лежит рядом.
- Отчёт загрузки: artifacts/design/reference-thumbnails/catalogue/database-load-v15.json. Preview продолжает работать с vowen_design_test. Контейнеры не пересобирались и не обновлялись; совместимость их прежнего образа с новой схемой не подтверждалась. Сборок, коммитов и push нет.

### 2026-10-18 — изображения приложения перенесены в static и включены в Git

- Общий корень static/: 430 Web-изображений в static/web и 107 Android-изображений в static/android/res/drawable-nodpi. Все 537 изображений добавлены в индекс Git, не игнорируются и не ссылаются наружу. Всего перенесён 551 статический ресурс, байты проверены по SHA256; ничего из каталога генератора для работы приложения не требуется.
- Vite publicDir, Docker Web, Gradle Android source set и импортёр товаров используют новые каталоги. URL в БД и фикстурах сохранены. Аудит 318 миниатюр перенесён в scripts/fixtures/reference-thumbnails-v15.json, чтобы тесты работали без игнорируемых QA-артефактов. JSON-архив фикстур и SHA256 обновлены с новой инструкцией размещения PNG.
- Проверено: 12 unit-тестов ресурсов/фикстур, scoped ruff, Web typecheck; 444 локальных HTTP-ответа сверены с файлами по SHA256. Итоговая проверка Git подтверждает наличие всех изображений в индексе. Android и Docker не собирались; сборок, коммитов и push нет. Скриншоты QA и дизайн-макеты остаются служебными артефактами.

### 2026-10-18 — проверка и сборка накопленных изменений перед публикацией

- Объём: согласования правил/ритуалов, дневник с рукописью, магазин и ролевые покупки, наказания, профиль/администраторы, 15 справочников, фикстуры v15 и общая static/. Подготовлено к публикации в существующей ветке feat/ui-context; удалённые сервисы не развёртывались.
- Прошли: make lint/typecheck (ruff, ESLint, mypy 87 файлов, Web vue-tsc), 304 backend-теста, 17 ops-тестов, 36 Vitest, 20 Android unit-тестов. Контракты повторно сгенерированы без дрейфа, make check-contracts прошёл. Git diff --check и эвристический secret scan прошли. На отдельной временной чистой PostgreSQL-базе проверены 0001→0043 и seed 318 строк; проверочная база удалена.
- Собраны Web production dist, Python wheel/sdist, Android debug APK и инструментальный APK, пять Docker Compose образов api/worker/bot/migrate/proxy. В backend-образе подтверждены схема 0043 и все 318 фикстур (62 девайса); в proxy присутствуют бренд, магазин и миниатюры. Android lintDebug прошёл с предупреждениями; APK на устройстве не запускались. Подписанного release APK/AAB и push Docker-образов не было.
- Во время сборки исправлены реальные ошибки Android: nullable context магазина и nullable текст дневника, вывод типа списка читателей, получение ширины до вложенного Compose DSL, позиционный конструктор Member в HomeScreenTest и неоднозначные отступы else в редакторе заявок. Проверки не отключались.
- Ограничение: make test-e2e завершился ошибкой в первом closed-access.spec.ts (3 passed, 4 failed). Сценарии используют старые селекторы Propose a relationship и прежнюю навигацию профиля/уведомлений/сессий; последующие шесть spec-файлов make не запускал. E2E не объявляются зелёными и не удалены; обновление сценариев остаётся отдельной незавершённой работой.
- Локальные результаты, APK, контрольные суммы и полные логи: artifacts/release/local-2026-10-18/report.json и подкаталоги android/backend/logs (игнорируются Git). Web dist — web/dist. Секреты, runtime и QA-скриншоты в коммит не включаются.

### 2026-10-18 — main обновлён, слитые ветки удалены

- По запросу пользователя main продвинут fast-forward до 6143f3c; этот коммит подтверждён в origin/main. Все локальные и удалённые feature tips входят в его историю, включая прежние локальные опережающие документационные коммиты.
- Удалены 11 удалённых и 9 локальных слитых feat/* веток. Удалённые refs удалены атомарно с проверкой точного ожидаемого SHA; локальные — через git branch -d после проверки ancestry. Остался main, данные коммитов не потеряны.
- CI для кода 6143f3c: Android success; backend-web failure на make test-e2e. Это ранее зафиксированные четыре сценария со старыми селекторами. Зелёный полный CI не заявляется. Новых изменений кода, развёртывания или повторных сборок при слиянии нет.
