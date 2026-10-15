# Contributing

Use synthetic fixtures only. Read AGENTS.md and the product/security specifications.
Keep one instance, CLI-only users, Telegram identity, native Android, explicit
consent and nontransitive authority. Working defaults are recorded in ADR 0001.

Run `make bootstrap`, start the development database, migrate a dedicated `_test`
database, then `make lint typecheck test test-web build-web build-android`.
Run `make test-e2e` after installing Chromium (`pnpm --dir web exec playwright install chromium`).
Use tests first for meaningful behavior, focused commits, and current OpenAPI
plus generated native/web types (`make contracts`, `make check-contracts`).
Never bypass production authentication to make tests easier.

A pull request should describe behavior, requirement IDs, tests actually run,
and remaining limitations. Report security problems privately; never put personal
diaries, answers, Telegram identities, bot credentials or server addresses in issues.
