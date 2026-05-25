# Dispatch — task runner. `make` to see all targets.

SHELL          := /usr/bin/env bash
.DEFAULT_GOAL  := help

BACKEND_DIR    := apps/backend
FRONTEND_DIR   := apps/frontend
VENV           := $(BACKEND_DIR)/.venv
PY             := $(VENV)/bin/python
PIP            := $(VENV)/bin/pip
UVICORN        := $(VENV)/bin/uvicorn
PYTEST         := $(VENV)/bin/pytest
HOST_PORT      ?= 8080

# ---------- help ----------

.PHONY: help
help: ## Show this menu
	@awk 'BEGIN {FS = ":.*?## "; printf "\nDispatch — available targets:\n\n"} \
	      /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2} \
	      /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)}' $(MAKEFILE_LIST)
	@echo

##@ Stack (docker compose)

.PHONY: bootstrap
bootstrap: ## One-command bring-up: generate key, build, start, backfill
	@./scripts/bootstrap.sh

.PHONY: up
up: ## Build and start the compose stack in the background
	@docker compose up -d --build

.PHONY: down
down: ## Stop the compose stack (keeps volumes)
	@docker compose down

.PHONY: restart
restart: ## Restart the backend container
	@docker compose restart dispatch-backend

.PHONY: logs
logs: ## Tail logs from all services
	@docker compose logs -f --tail=100

.PHONY: ps
ps: ## Show running services
	@docker compose ps

.PHONY: nuke
nuke: ## Stop the stack AND delete volumes (destructive — wipes the DB)
	@docker compose down -v

##@ Development

.PHONY: install
install: install-backend install-frontend ## Install backend + frontend deps

.PHONY: install-backend
install-backend: ## Create venv and install backend deps
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install -q -r $(BACKEND_DIR)/dispatch/requirements.txt

.PHONY: install-frontend
install-frontend: ## Install frontend deps
	@cd $(FRONTEND_DIR) && npm install

.PHONY: dev
dev: ## Run backend (uvicorn) + frontend (vite) together
	@trap 'kill 0' EXIT INT TERM; \
	  $(MAKE) --no-print-directory dev-backend & \
	  $(MAKE) --no-print-directory dev-frontend & \
	  wait

.PHONY: dev-backend
dev-backend: ## Run the FastAPI backend with --reload
	@cd $(BACKEND_DIR) && set -a && [ -f .env ] && source .env; set +a; \
	  ../../$(UVICORN) dispatch.main:app --reload --host 0.0.0.0 --port 10060

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server (proxies /api to backend)
	@cd $(FRONTEND_DIR) && npm run dev

##@ Quality

.PHONY: test
test: ## Run backend pytest suite
	@cd $(BACKEND_DIR) && ../../$(PYTEST)

.PHONY: test-e2e
test-e2e: ## Run frontend Playwright e2e suite
	@cd $(FRONTEND_DIR) && npm run test:e2e

.PHONY: lint
lint: ## Lint the frontend
	@cd $(FRONTEND_DIR) && npm run lint

.PHONY: format
format: ## Format the frontend
	@cd $(FRONTEND_DIR) && npm run format

.PHONY: typecheck
typecheck: ## Typecheck the frontend
	@cd $(FRONTEND_DIR) && npm run typecheck

.PHONY: build
build: ## Production build of the frontend
	@cd $(FRONTEND_DIR) && npm run build

##@ Utilities

.PHONY: key
key: ## Print a fresh DISPATCH_MASTER_KEY (does not write to .env)
	@python3 -c "import secrets; print(secrets.token_urlsafe(32))"

.PHONY: backfill
backfill: ## Trigger a 30-day ingest + look-back backfill against the running stack
	@curl -fsS -X POST "http://localhost:$(HOST_PORT)/api/admin/system/backfill" \
	  -H "Content-Type: application/json" \
	  -d '{"max_days": 30, "ingest": true}' | python3 -m json.tool

.PHONY: clean
clean: ## Remove venv, node_modules, and build artifacts
	@rm -rf $(VENV) $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist
