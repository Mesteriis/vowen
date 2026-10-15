# Selected dependencies (2026-10-15)

These are implementation defaults, not separately confirmed product preferences.
Exact transitive versions and hashes are in lockfiles; no runtime uses floating `latest`.

- Python 3.13.15; uv 0.12.11; PostgreSQL 17.11 (17.x compatibility target).
- FastAPI 0.143.1; SQLAlchemy 2.0.54; psycopg 3.3.6; Alembic 1.20.0;
  Pydantic 2.13.5; aiogram 3.31.0; cryptography 50.0.2; Typer 0.27.3.
- Node 24.20.0; pnpm 11.5.1; Vue 3.5.44; Vite 8.3.4; TypeScript 5.9.3;
  Vitest 5.0.4; Playwright 1.64.0; openapi-typescript 7.13.0.
- Android Gradle Plugin 8.13.2; Gradle 8.13 (wrapper SHA-256 checked);
  Kotlin 2.2.10; SDK/target 36; build tools 36.0.0; minimum API 26;
  Compose UI 1.9.3; Material3 1.4.0; OkHttp 4.12.0.
- Caddy 2.10.2. Container build/runtime versions are pinned by tag.
- GitHub Actions pinned to commit SHAs verified through GitHub's tag refs.

Installation and compatibility were checked by actual backend tests, web build,
Android JVM tests/lint/APK build and Linux Docker image builds.
`uvx pip-audit --path backend/.venv/lib/python3.13/site-packages` found no known
vulnerabilities in resolved third-party Python dependencies; the local vowen
package is not on PyPI and was not audited by that tool.
`pnpm --dir web audit --prod` found no known vulnerabilities in runtime dependencies.
These scans do not audit Android transitive libraries, container OS packages,
application design, or all future advisories.

Official references checked during implementation:
[Mini App validation](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app),
[bot links](https://core.telegram.org/bots/features#deep-linking),
[SQLAlchemy async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html),
[AESGCM](https://cryptography.io/en/stable/hazmat/primitives/aead/),
[AGP compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes),
[Keystore](https://developer.android.com/privacy-and-security/keystore),
[PostgreSQL 17.11](https://www.postgresql.org/docs/release/17.11/),
[Caddy routing](https://caddyserver.com/docs/caddyfile/directives/handle).
