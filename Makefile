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
# Passes the caller's GH_TOKEN by name; used only by test-zizmor-online.
RUN_GH         = $(DOCKER_COMPOSE) run --rm -e GH_TOKEN $(SERVICE)
# G3.3 guardrails: the same image with no network and no AWS variable.
OFFLINE        = app-offline
RUN_OFFLINE    = $(DOCKER_COMPOSE) run --rm $(OFFLINE)

# Misc
.DEFAULT_GOAL  = help
.RECIPEPREFIX  +=
.PHONY: help build start up down sh test test-lockfile clean test-battery \
        test-ruff test-types test-maintainability test-coverage test-bandit \
        test-deps-security test-secrets test-actionlint test-zizmor test-yaml \
        test-dockerfile test-zizmor-online test-guardrails \
        test-structural-preview test-destructive-diff test-iam-gate \
        test-policy test-contract-schema

# G3.2 PR quality battery (AD-A11, FR-A10). Each target is one required check
# and runs inside the development image, exactly as CI runs it. NFR-A09
# covers policy/ too: it joins every Python target once G3.3 adds it.
PYTHON_SOURCES = pulumi scripts $(wildcard policy)

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
	rm -rf .pytest_cache .ruff_cache .coverage .coverage.* htmlcov

test-battery: test-ruff test-types test-maintainability test-coverage test-bandit test-deps-security test-secrets test-actionlint test-zizmor test-yaml test-dockerfile ## Run every local battery check (CodeQL and Dependency Review run only on GitHub).

test-ruff: ## Ruff: lint and format check of every Python source and test.
	$(RUN) uv run --frozen ruff check $(PYTHON_SOURCES) tests
	$(RUN) uv run --frozen ruff format --check $(PYTHON_SOURCES) tests

test-types: ## Types: ty static type check of the program, scripts and policy.
	$(RUN) uv run --frozen ty check --error-on-warning $(PYTHON_SOURCES)

test-maintainability: ## Maintainability: radon report, xenon complexity gate.
	$(RUN) uv run --frozen radon cc -s -a $(PYTHON_SOURCES)
	$(RUN) uv run --frozen radon mi -s $(PYTHON_SOURCES)
	$(RUN) uv run --frozen xenon --max-absolute B --max-modules B --max-average A $(PYTHON_SOURCES)

test-coverage: ## Coverage: every test under tests/ at 100% branch coverage (NFR-A09).
	$(RUN) uv run --frozen coverage erase
	$(RUN) uv run --frozen coverage run -m pytest
	$(RUN) uv run --frozen coverage report

# The tests run bandit with B101 (assert) skipped: pytest asserts are the
# test mechanism and tests never run under `python -O`. No other rule is
# skipped anywhere, and every `# nosec` must name a rule that it suppresses.
test-bandit: ## Bandit: security lint that also fails on stale or malformed nosec comments.
	$(RUN) uv run --frozen python scripts/bandit_gate.py $(PYTHON_SOURCES)
	$(RUN) uv run --frozen python scripts/bandit_gate.py --skip B101 tests

test-deps-security: ## Dependency Audit: pip-audit of every package in the frozen uv.lock.
	$(RUN) bash -o pipefail -c 'uv export --frozen --all-groups --no-emit-project --format requirements-txt --output-file /tmp/requirements.txt >/dev/null \
		&& uv run --frozen pip-audit --strict --disable-pip --require-hashes --requirement /tmp/requirements.txt'

test-secrets: ## Secrets Scan: gitleaks over every commit reachable from HEAD.
	$(RUN) gitleaks git --no-banner --redact --verbose --log-opts=HEAD .

test-actionlint: ## Actionlint: workflow lint with shellcheck on every run script.
	$(RUN) actionlint -verbose

# Locally, zizmor runs its offline audits: no token and no network. CI runs
# test-zizmor-online instead. Every PR job, a fork's included, gets a
# read-only GITHUB_TOKEN (contents: read); the Zizmor job passes it as
# GH_TOKEN to that one step, which adds the online audits (impostor-commit,
# ref-confusion, known-vulnerable-actions and the others). Without a token,
# zizmor silently skips them, so the online target refuses to run without
# one.
test-zizmor: ## Zizmor (local): workflow security audit, offline audits only.
	$(RUN) uv run --frozen zizmor --offline --no-progress .

test-zizmor-online: ## Zizmor (CI): offline and online audits; needs GH_TOKEN.
	@test -n "$$GH_TOKEN" || { echo "test-zizmor-online: GH_TOKEN is not set; zizmor would skip its online audits" >&2; exit 1; }
	$(RUN_GH) uv run --frozen zizmor --no-progress .

test-yaml: ## Yamllint: every YAML file, warnings fail.
	$(RUN) uv run --frozen yamllint --strict -c .yamllint.yml .

test-dockerfile: ## Hadolint: Dockerfile lint.
	$(RUN) hadolint --config .hadolint.yaml Dockerfile

# G3.3 guardrails (AD-A10, AD-A11, AD-A15, FR-A11). Each target is one
# required check. They run in the app-offline service, so no target can reach
# AWS, Pulumi Cloud or a plugin download: the preview uses a fresh local file
# backend, the `ci` stack's empty passphrase and the image's preinstalled
# `aws` plugin. A gate re-runs the preview it reads, so each CI job stands
# alone; one `make test-guardrails` runs it once.
CI_PREVIEW = .artifacts/pulumi-preview/ci.json
GUARDRAILS = uv run --frozen python scripts/pulumi_ci_guardrails.py

test-guardrails: test-structural-preview test-destructive-diff test-iam-gate test-policy test-contract-schema ## Run every G3.3 guardrail check.

test-structural-preview: ## Structural Preview: offline `pulumi preview --stack ci`, no credentials, no network.
	$(RUN_OFFLINE) uv run --frozen python scripts/run_ci_preview.py --json-output $(CI_PREVIEW)
	$(RUN_OFFLINE) $(GUARDRAILS) summarize $(CI_PREVIEW)

test-destructive-diff: test-structural-preview ## Destructive Diff Gate: no delete or replace of a critical type.
	$(RUN_OFFLINE) $(GUARDRAILS) destructive-gate $(CI_PREVIEW)

test-iam-gate: test-structural-preview ## IAM Gate: no aws:iam/* resource in the plan.
	$(RUN_OFFLINE) $(GUARDRAILS) iam-gate $(CI_PREVIEW)

test-policy: ## Policy: the CrossGuard pack on the offline `ci` preview, then its fixture tests.
	$(RUN_OFFLINE) uv run --frozen python scripts/run_ci_preview.py --policy-pack policy
	$(RUN_OFFLINE) uv run --frozen pytest tests/policies

test-contract-schema: ## Contract Schema: the schema and every file under contracts/.
	$(RUN_OFFLINE) uv run --frozen python scripts/check_contracts.py contracts
