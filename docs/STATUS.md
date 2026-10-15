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
