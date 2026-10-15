# Implementation evidence

2026-10-15. M0 in progress, M1 pending; not a production MVP.
All seven archive documents extracted at supplied paths and read completely.
VOWEN_AGENT_BRIEF.md was absent from the supplied archive and Downloads.

- Initial health tests: 2 expected failures (missing routes), then 2 passed.
- PostgreSQL 17.6 development service started and healthy.
- Python dependencies resolved and locked with uv (Python 3.13.15).
- User confirmed Mesteriis as GitHub owner; gh switched accordingly.
- No live Telegram credentials requested or used.

M1.1/M1.2 backend slice: 22 tests passed on dedicated PostgreSQL vowen_test.
Checks cover CLI create/duplicate/disable/enable/revoke, idempotent keyring,
AEAD binding, Telegram freshness/type/signature/reordered replay, no auto-users,
concurrent assertion consumption, refresh rotation/reuse, session ownership,
and live access revocation after disable/re-enable. mypy passed 15 source files.
Remote created at https://github.com/Mesteriis/vowen; first push pending review.

M1.3/M1.4 backend slice: 29 tests passed. Android challenge secrets are hashed,
explicit bot approval is separate from /start, duplicate callbacks are idempotent.
Relations require two exact-version consents; pause/resume and scope expansion
create a new consent round. Policy denies transitive and unrelated targets,
missing object ACL, guest/operator principals, and private-journal actions.
Agreement ciphertext marker absence checked in PostgreSQL. Live bot not tested.
