.PHONY: bootstrap dev migrate lint typecheck test test-integration test-web test-e2e build-web build-android check-contracts secret-scan migrate-test contracts
TEST_DATABASE_URL ?= postgresql+psycopg://vowen:vowen@127.0.0.1:55432/vowen_test
bootstrap:
	uv sync --project backend --frozen
	pnpm --dir web install --frozen-lockfile
dev:
	docker compose -f compose.yaml -f compose.dev.yaml up -d --wait db
	$(MAKE) migrate
migrate:
	uv run --project backend alembic -c backend/alembic.ini upgrade head
migrate-test:
	DATABASE_URL='$(TEST_DATABASE_URL)' uv run --project backend alembic -c backend/alembic.ini upgrade head
lint:
	uv run --project backend ruff check backend
	pnpm --dir web lint
typecheck:
	uv run --project backend mypy backend/src
	pnpm --dir web typecheck
test:
	uv run --project backend pytest backend/tests -q
test-integration:
	uv run --project backend pytest backend/tests/integration -q
test-web:
	pnpm --dir web test
test-e2e:
	pnpm --dir web exec playwright test
build-web:
	pnpm --dir web build
build-android:
	cd android && ./gradlew testDebugUnitTest lintDebug assembleDebug assembleDebugAndroidTest
contracts:
	uv run --project backend python scripts/export_contract.py
	uv run --project backend python scripts/android_contract.py
	pnpm --dir web generate-api
check-contracts: contracts
	git diff --exit-code -- contracts/openapi.json contracts/form-schema/schema.json web/src/shared/api.d.ts android/app/src/main/java/org/vowen/app/ApiModels.kt
secret-scan:
	python3 scripts/secret_scan.py
