# M3 rewards and execution evidence

Spec: PRODUCT_SPEC REQ05–06/09/11/17; user now explicitly brings link/photo/video evidence into scope.

## Task 1: private evidence
RED integration: required policy, safe HTTPS links, photo/video upload + encrypted storage, owner/explicit-current-reviewer reads, no issuer-only read, cross-occurrence rejection, report retry identity, size/quota/expiry cleanup. Implement bounded encrypted PostgreSQL blobs (8MiB/file,3 pieces/report), JSON base64 transport; no remote URL fetching or public media paths. Immutable submitted attempts; staged uploads expire24h. Existing reports/assignments remain compatible. Expected: targeted PostgreSQL tests pass.

## Task 2: rewards
RED integration: encrypted versioned catalogue, scoped manual offered grant + recipient accept/decline, issuer deliver/cancel, immutable transition history, explicit per-assignment versioned automatic policy, approved occurrence yields one grant under retries/concurrent reviewers, pause never retracts earned grants. Grant+notice in approval transaction. Expected: full backend tests pass.

## Task 3: real clients
Generated contracts. Mini App and native Android evidence policy, links, system file picker and protected retrieval; rewards catalogue/manual grant/policy and lifecycle. Real API browser E2E and native behavioral tests, existing luxury world preserved. Expected: browser/native suites and builds pass.

## Task 4: review and delivery
Fresh whole-branch reviewer, RED/GREEN important fixes, full gates, commits and green CI; update actual status and operations. No live Telegram delivery or physical-device claim.
