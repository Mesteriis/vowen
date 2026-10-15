# M3, первый законченный срез: правила

Основание: PRODUCT_SPEC REQ-05–08, IMPLEMENTATION_PLAN M3, первые два пункта.
Следующий срез: расписания и ритуалы, затем награды; этот срез не закрывает M3 целиком.

## Task 1: версии и назначения
- RED: PostgreSQL API tests отдельного принятия, новой версии, ACL, паузы и гонок.
- GREEN: encrypted versions, immutable published content, explicit per-assignment managers,
  exact-version consent, pending replacement retains old active assignment until acceptance.
- Lists/history available to recipient, manager requires current direct scope, author sees template only.
- Test: backend pytest; expected all green. Commit feature.

## Task 2: клиенты
- RED: browser scenario create/edit/publish/assign/accept/revise/decline/pause; native Compose tests.
- GREEN: Mini App and native Android rule authoring/assignments/history; generated contracts.
- Tests: make lint typecheck test test-web test-e2e build-web build-android check-contracts secret-scan.
- Expected: all pass. Commit clients.

## Task 3: review and delivery
- Fresh read-only whole-branch review, regression tests for important findings.
- Update STATUS and capabilities with exact evidence, publish commits, verify CI.

Review focus: author not automatic manager, denied managers cannot read old assignments;
recipient pause/revoke remains possible; concurrent acceptance/replacement; archive doesn't
silently remove prior consent; no auto punishment; no plaintext rule text in DB/logs.
