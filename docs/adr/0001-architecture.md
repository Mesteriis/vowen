# ADR 0001: bootstrap defaults

Accepted for implementation, 2026-10-15. Product invariants come from the supplied specification.
Python 3.13 / async SQLAlchemy / PostgreSQL 17, Vue 3, native Kotlin Compose,
MIT, the working name Vowen, and the documented TTLs are starting defaults,
not separately confirmed customer preferences. No trademark/domain check performed.
Keep one instance, CLI-only provisioning, Telegram authentication, nontransitive
contextual authority and explicit consent. No self-registration or SaaS.

Ruling: the archive contains seven files, no VOWEN_AGENT_BRIEF.md. Preserve all
seven at their supplied paths and execute START_HERE.md as explicitly requested.
Ruling: GitHub connector and CLI resolve different personal accounts; use the
explicitly permitted local fallback until publication owner is unambiguous.
Ruling: readiness reports unavailable/mismatched database; liveness remains
available for diagnosis. Protected DB work cannot run against a mismatched schema.
Ruling: execute the supplied milestone checklist directly; track evidence in
STATUS.md rather than reformatting it into another implementation plan.

User later explicitly confirmed Mesteriis and authorized switching gh; the remote
was created under that account. Fixed proxy/API addresses share a configurable
internal subnet; Caddy alone is trusted to supply client addresses. One API replica
uses bounded in-memory throttling; multi-replica deployment needs shared rate limits.
Expiry maintenance runs in the API process; the business outbox worker begins in M2.

M1 completion, 2026-10-15: profile preferences initially include display name,
RU/EN language, IANA timezone and optional dominant/submissive/switch self-labels.
Defaults are EN/UTC/empty labels; labels never grant authority. Preferences are
private; participant selection exposes only UUID/name/labels. Updates require
profile_version and never accept operator-owned identity/activation fields.
CLI agreement text is read from a UTF-8 file to avoid putting intimate text in
shell history. CLI can only propose, and cannot consent for a participant.
Direct runtime accepts BOT_API_TOKEN/TELEGRAM_BOT_TOKEN as SecretStr; configured
TELEGRAM_BOT_TOKEN_FILE takes precedence and Compose continues to use files.
