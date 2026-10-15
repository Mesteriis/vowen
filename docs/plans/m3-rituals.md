# M3 rituals and schedules

Spec: PRODUCT_SPEC REQ05–06/09/17; ARCHITECTURE §9. User supplied luxury dark/gold/burgundy interface reference.

## Task 1: deterministic scheduling
RED/GREEN tests: once/daily/weekdays, timezone validation, spring gaps shift by gap,
autumn fold0, including non-hour DST. UTC due times, local slot unique, bounded catch-up watermark.

## Task 2: real PostgreSQL workflows
Encrypted immutable template versions; separate assignments/schedule revisions/occurrences/reports.
Explicit assign/review scopes and reviewers; executor-only reports; preserve needs_changes attempts,
optimistic review conflicts, idempotent report retries, pause and no automatic discipline.
Dedicated PostgreSQL worker; downtime recovery and unique generation under concurrent workers.
Schedule edit applies to future unstarted slots only. ACL-filtered lists/history and neutral in-app notices.

## Task 3: clients and reference
Real Mini App and native Android authoring, recipient/schedule/reviewer choice, occurrences and
report/review history. Adopt supplied reference materials and typography without inventing group data,
points, online status or reward capabilities. Contracts, browser/native regressions, visual QA.

## Task 4: review and delivery
Fresh whole-branch review; important fixes RED/GREEN; full gates and green CI; publish commits.
Rewards are next slice, not part of this request. Live Telegram identity read can be verified without
sending unsolicited messages; live delivery proof requires an opted-in test target.
