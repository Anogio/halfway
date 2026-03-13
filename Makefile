.PHONY: doctor setup build-offline release-v1 test e2e run-backend run-frontend run-browser-backend run-browser-frontend lint format baseline

doctor:
	@echo "Checking required tools..."
	@command -v uv >/dev/null || (echo "uv is required" && exit 1)
	@command -v python3 >/dev/null || (echo "python3 is required" && exit 1)
	@PY_VERSION=$$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'); \
	python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' || \
		(echo "python3 >= 3.13 required, found $$PY_VERSION" && exit 1)
	@command -v node >/dev/null || (echo "node is required" && exit 1)
	@command -v npm >/dev/null || (echo "npm is required" && exit 1)
	@UV_VERSION=$$(uv --version | awk '{print $$2}'); \
	REQ_MAJOR=0; REQ_MINOR=10; \
	MAJOR=$$(echo $$UV_VERSION | cut -d. -f1); \
	MINOR=$$(echo $$UV_VERSION | cut -d. -f2); \
	if [ $$MAJOR -lt $$REQ_MAJOR ] || { [ $$MAJOR -eq $$REQ_MAJOR ] && [ $$MINOR -lt $$REQ_MINOR ]; }; then \
		echo "uv >= 0.10 required, found $$UV_VERSION"; exit 1; \
	fi
	@echo "uv version: $$(uv --version)"
	@echo "python3 version: $$(python3 --version)"
	@echo "node version: $$(node --version)"
	@echo "npm version: $$(npm --version)"

setup:
	$(MAKE) -C backend setup
	$(MAKE) -C backend/offline setup
	$(MAKE) -C frontend setup

build-offline:
	@test -n "$(CITY)" || (echo "CITY is required (example: CITY=paris make build-offline)" && exit 1)
	$(MAKE) -C backend/offline build-all CITY=$(CITY)

release-v1:
	@test -n "$(CITY)" || (echo "CITY is required (example: CITY=paris make release-v1)" && exit 1)
	@python3 -c 'import sys,tomllib;city=sys.argv[1];d=tomllib.load(open("backend/config/settings.toml","rb"));assert city in d.get("cities",{}),f"unknown city: {city}";v=d["cities"][city]["artifact_version"];assert v=="v1",f"{city} artifact_version must be v1 (found {v})";print("artifact_version is v1 for city",city)' "$(CITY)"
	$(MAKE) build-offline CITY=$(CITY)
	@python3 -c 'import json,sys;from pathlib import Path;city=sys.argv[1];m=Path(f"backend/offline/data/artifacts/{city}/manifest_v1.json");assert m.exists(),f"{m} not found after build";obj=json.loads(m.read_text(encoding="utf-8"));print("release manifest:",m);print("city:",obj.get("city"));print("profile:",obj.get("profile"));print("counts:",obj.get("counts"))' "$(CITY)"

test:
	$(MAKE) -C backend/offline test
	$(MAKE) -C backend test
	$(MAKE) -C frontend test

e2e:
	$(MAKE) -C frontend e2e

lint:
	$(MAKE) -C backend lint
	$(MAKE) -C backend/offline lint
	$(MAKE) -C frontend lint

format:
	$(MAKE) -C backend format
	$(MAKE) -C backend/offline format
	$(MAKE) -C frontend format

baseline:
	$(MAKE) -C backend baseline

run-backend:
	$(MAKE) -C backend run

run-frontend:
	$(MAKE) -C frontend dev

run-browser-backend:
	$(MAKE) -C backend run-browser-check

run-browser-frontend:
	@cd frontend && npm run dev:browser-check
