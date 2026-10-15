# M3 Telegram ritual/reward notifications

Spec: PRODUCT_SPEC REQ06/09/11/17; user authorizes bot notification delivery, tests, commits and green CI. Existing in-app notices remain authoritative. No content, evidence or capability tokens in Telegram.

## Task 1: transactional queue and current authorization
RED PostgreSQL tests: one delivery per newly-created notice, transaction rollback, concurrent claims, active linked member + explicit BotContact opt-in only, pause/disable/contact opt-out, withdrawn assignment/reviewer/reward scopes, stale occurrence/reward revision and age expiry. Implement migration 0013 and domain hooks that enqueue atomically; no historical backfill. Expected: focused PG tests pass; commit.

## Task 2: delivery recovery and bot integration
RED tests: second authorization after claim, lease fencing, successful delivery never repeats, explicit429 bounded delayed retry, blocked bot disables contact, timeout/crash ambiguous sends never auto-resend, no DB transaction during network, neutral localized text and previews disabled. Wire existing bot worker without starving form deliveries. Expected: full backend suite/lint/types pass; commit.

## Task 3: verification and delivery
Fresh whole-branch review with focus on missed/stale events, consent revocation races, ambiguous Telegram outcomes and secrets. One RED/GREEN important fix pass. Run full gates and E2E sequentially, Compose smoke. Verify token using getMe without printing secrets; live send only to an already-linked opted-in eligible member, never synthetic IDs or an inferred identity. Document unverified outcomes. Commits and green exact-code CI, then authorized main integration.
