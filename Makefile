# Parameters
PROJECT        = api-gateway-infrastructure
UID           ?= $(shell id -u 2>/dev/null || echo 1000)
GID           ?= $(shell id -g 2>/dev/null || echo 1000)

export UID
export GID

# Executables: local only
DOCKER_COMPOSE = docker compose
SERVICE        = app
RUN            = $(DOCKER_COMPOSE) run --rm $(SERVICE)

# Misc
.DEFAULT_GOAL  = help
.RECIPEPREFIX  +=
.PHONY: help build start up down sh test test-lockfile clean

help: ## Display the available Make targets.
	@printf "\033[33mUsage:\033[0m\n  make [target] [arg=\"val\"...]\n\n\033[33mTargets:\033[0m\n"
	@grep -E '^[-a-zA-Z0-9_\.\/]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the development image (pinned, checksum-verified tools).
	$(DOCKER_COMPOSE) build $(SERVICE)

start: ## Build the image and start the development container.
	$(DOCKER_COMPOSE) up -d --build $(SERVICE)

up: ## Start the development container.
	$(DOCKER_COMPOSE) up --detach $(SERVICE)

down: ## Stop the development container.
	$(DOCKER_COMPOSE) down --remove-orphans

sh: ## Open a shell in the running development container (after make start).
	$(DOCKER_COMPOSE) exec $(SERVICE) bash

test: ## Run every test under tests/ on the frozen lockfile.
	$(RUN) uv run --frozen pytest

test-lockfile: ## Fail when pyproject.toml and uv.lock disagree.
	$(RUN) uv lock --check

clean: ## Remove containers, Python caches and coverage data.
	$(DOCKER_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage .coverage.* htmlcov
