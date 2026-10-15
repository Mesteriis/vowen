# Ritual scheduler

Compose starts `worker` automatically after migration/API readiness. It runs PostgreSQL
transactions every 15 seconds, locks up to 50 eligible assignments with SKIP LOCKED,
and catches up at most 31 local days per assignment/transaction. Cursor, occurrences
and neutral in-app notices commit together. Crash rollback and unique assignment/day
and request-key constraints prevent duplicate obligations/reports.

Schedules: once, daily or selected weekdays, local hour/minute and IANA timezone.
DST gaps shift by their actual duration; folds use fold=0 (first instant). Timestamps
returned by API are UTC; local occurrence day is separate. Runtime tzdata was checked
inside the backend image for Madrid and Lord Howe.

New assignment start dates cannot be in the past. Report window starts at due time:
default 24 hours, configurable 1–168. Recovery marks expired open slots missed, leaves
submitted reports for review, and creates due notices only for the current local day.
Missed, skipped or paused slots never create discipline. `needs_changes` preserves the
old attempt and renews the configured window from review time for actual resubmission.

Schedule changes produce immutable schedule rows and start tomorrow or later. They
preserve earlier occurrences/reports. Only one future schedule change may be pending.
Timezone is fixed for an assignment; changing it requires a separate assignment (revoke
the old one if replacing it). Clock, cadence, weekdays and window may change in place.

Personal/relationship pause, account disable/re-enable and consent changes synchronously cancel open obligations
and advance cursors. Resume advances again, so worker downtime during a pause cannot
reconstruct paused days. A paused ritual assignment is resumed only by its recipient,
with current issuer scope. Cancelled historical slots are never reopened.

Report retries reuse an occurrence-scoped idempotency key and identical text. Reviews
carry the occurrence revision: incompatible concurrent decisions yield one200/one409.
Only the executor reports; only explicit reviewers with current direct scope review/read.
Authors are not automatically readers of recipients' reports. The issuer may manage
assignment metadata with current direct rituals.assign scope, without report access.

Notifications in this slice are neutral, in-app and ACL-filtered. Telegram `getMe`
identity was checked for the supplied token; ritual Telegram delivery and end-to-end
live authentication/delivery acceptance are not claimed. Rewards are the next M3 slice.
