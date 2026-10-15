# Rewards and private execution evidence

Migrations 0011–0012; apply with `make migrate`. The API/worker schema check requires
0012. Back up PostgreSQL and the independent keyring; attachment bytes now contribute
to DB backup size. No filesystem media volume or public object URLs are used.

## Evidence

An assignment fixes optional/required evidence and allowed kinds (link/photo/video).
The default is optional with all three allowed. Existing assignments receive that
compatible default. Changing the evidence requirement requires a new assignment.
Reports retain text and may add up to three links/files per attempt. HTTPS URLs are
validated, encrypted with report contents, and never fetched, previewed or indexed by
the server. Opening an external link is an explicit member action with no-referrer.

Files: JPEG/PNG photos and MP4/WebM videos, at most 8 MiB decoded per file, three
unsubmitted files per occurrence, 32 MiB per occurrence and 128 MiB per member.
These are implementation defaults, not separately confirmed customer requirements.
The server checks declared kind/type and basic container signatures. It does not
transcode, strip EXIF/location metadata, scan for malware or prove that the file depicts
the task. Original bytes are preserved and clients explicitly download/save them.
Do not describe this as verified real-world completion or metadata removal.

JSON base64 transport has a 12 MiB request limit only at the evidence upload endpoint;
ordinary endpoints retain 512 KiB. Caddy and the API enforce their respective scoped
limits. API upload throttling shares one evidence bucket rather than a bucket per UUID.
PostgreSQL owner/assignment locks serialize quotas and request keys. Ciphertext uses
AES-GCM bound to the evidence UUID/type; body, URLs and file names never enter logs.
The original filename and Android source URI are not stored or transmitted.

`POST /ritual-occurrences/{id}/evidence` creates an occurrence-owned staged upload.
`GET` at the same path restores still-valid staged uploads after closing/reopening the
report, so cancelled dialogs do not strand the quota. Owner-only DELETE discards an
unsubmitted upload. Maintenance removes unsubmitted uploads after 24 hours.
Submission atomically binds files to one immutable report attempt and clears staging
expiry. Bound evidence follows report history retention (no separate expiry or deletion
policy is introduced in this slice). A revised attempt cannot steal a previous attempt's
file; upload again if it needs its own file. Request retry with the same key/text/links/IDs
returns the same report; changed evidence conflicts. Download requires authenticated
executor or explicit reviewer with current direct scope; author/assign-only scope gives
no report/file access. Staged files are owner-only. Each read is checked again; no bearer
file URL can survive permission withdrawal.

Both clients support required policy, links, photo/video choice and protected retrieval.
Android uses OpenDocument and CreateDocument with bounded IO. Pending save metadata
is retained in the ViewModel and bound to origin/session/member; the Activity-root
result callback re-fetches bytes under current authorization after a destination is
chosen. Activity recreation preserves the request; session/instance change cancels it.
No plaintext media is saved in instance state. After process death a new save request
is needed; a late destination result produces a visible error, never silent success.
No storage permission,
source-URI persistence or automatic external media playback. Rejected pending files can be replaced without discarding report text/links, and failures
are visible inside the report dialog. Upload retry preserves its
request key, and report retry preserves the proof list and request key.

## Rewards

Own encrypted catalogue definitions have immutable versions. Manual offers require a
current direct rewards.grant agreement and an explicit recipient. Each grant stores
its exact version, issuer, recipient, source and immutable transition history.
Recipient can accept/decline an offered grant, including during personal pause.
Issuer can mark accepted grants delivered or cancel offered/accepted grants only with
current scope. Delivered/declined/cancelled are final; no silent cancellation after delivery.
Historical grants remain visible to their fixed issuer/recipient after relation withdrawal.

Automatic policy is explicit when creating a ritual assignment, references a reward
version and is snapped to occurrences. Both reviewer approval and configured approval-free
report completion run the same DB effect in the approval transaction. Current issuer
rewards.grant authority is required at that moment; withdrawn authority suppresses a new
offer but never retracts an existing one. Unique `(occurrence_id, reward_policy_id,
recipient_id)` prevents duplicate grants. The DB effect and neutral in-app notices commit
with approval and are rendered in both clients' neutral Updates surface; no network runs inside this transaction. Manual idempotency is issuer/key
scoped and conflicts if the recipient or reward version changes.

No points, streak ledger, automatic punishment or Telegram reward/evidence delivery is
implemented. Live Telegram, physical file-picker behavior, large real-device video
performance and production restore remain separate acceptance work.

## Checks

Run backend PostgreSQL tests before browser E2E, never concurrently against vowen_test:
`make lint typecheck test test-web build-web check-contracts secret-scan`, then
`make test-e2e`; `make build-android` and owned-emulator instrumentation run separately.
After rebuilding Compose, run `python3 scripts/smoke_compose.py` and
`python3 scripts/smoke_evidence_proxy.py`. Their CA bypass is explicitly loopback-only.
