"""The G3.3 guardrail workflow, its make targets and its offline image.

P: `pulumi-pr-guardrails.yml` has exactly the jobs `Structural Preview`,
`Destructive Diff Gate`, `IAM Gate`, `Policy` and `Contract Schema`; each
runs on every pull request with `contents: read`, no secret,
`persist-credentials: false`, SHA pins and make-only run steps; each make
target runs in the `app-offline` service (no network, no AWS variable).
N: the same shape rules as the G3.2 battery reject a tag pin, a write
permission, a secret, a missing `persist-credentials: false`, an unlisted
command, a token or a filtered `pull_request`.
E: the image preinstalls the `aws` plugin 7.23.0 from a pinned URL with a
SHA-256 per architecture, and disables plugin downloads (G3.1 F02).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

import workflow_checks as wc

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulumi-pr-guardrails.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
LOCK = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
CHECKS = {
    "Structural Preview": "test-structural-preview",
    "Destructive Diff Gate": "test-destructive-diff",
    "IAM Gate": "test-iam-gate",
    "Policy": "test-policy",
    "Contract Schema": "test-contract-schema",
}
PREVIEW_READERS = ("test-destructive-diff", "test-iam-gate")


def recipe(target: str) -> tuple[str, str]:
    """(prerequisites, recipe body) of a Makefile target."""
    match = re.search(
        rf"^{re.escape(target)}:([^\n#]*?)(?:##[^\n]*)?\n((?:[ \t]+.*\n?)+)",
        MAKEFILE,
        re.MULTILINE,
    )
    assert match, target
    return match[1].strip(), match[2]


# --- the real workflow ------------------------------------------------------------


def test_workflow_passes_the_battery_shape_rules() -> None:
    assert wc.check_guardrails(TEXT) == []


def test_jobs_are_exactly_the_five_checks() -> None:
    assert sorted(wc.job_check_names(TEXT)) == sorted(CHECKS)


@pytest.mark.parametrize(("check", "target"), sorted(CHECKS.items()))
def test_each_job_builds_and_runs_its_target(check: str, target: str) -> None:
    jobs = [j for _, j in wc._job_items(wc.load(TEXT, [])) if j["name"] == check]
    (job,) = jobs
    runs = [s["run"] for s in job["steps"] if "run" in s]
    assert runs == ["make build", f"make {target}"]
    checkout = job["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"] == {"persist-credentials": False}
    assert "needs" not in job and "if" not in job


def test_workflow_runs_on_every_pull_request_without_a_token() -> None:
    doc = wc.load(TEXT, [])
    on = doc.get("on", doc.get(True))
    assert on == {"push": {"branches": ["main"]}, "pull_request": None}
    assert doc["permissions"] == {"contents": "read"}
    assert "github.token" not in TEXT
    assert not wc.mentions_secrets(doc)


def test_make_targets_run_offline() -> None:
    assert "RUN_OFFLINE    = $(DOCKER_COMPOSE) run --rm $(OFFLINE)" in MAKEFILE
    assert "OFFLINE        = app-offline" in MAKEFILE
    for target in CHECKS.values():
        _, body = recipe(target)
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        assert lines and all(x.startswith("$(RUN_OFFLINE) ") for x in lines), target
        assert all("uv run --frozen" in x or "$(GUARDRAILS)" in x for x in lines)
    assert "GUARDRAILS = uv run --frozen python scripts/pulumi_ci_guardrails.py" in (
        MAKEFILE
    )


def test_gates_read_the_offline_preview() -> None:
    prereqs, body = recipe("test-structural-preview")
    assert prereqs == ""
    assert "scripts/run_ci_preview.py --json-output $(CI_PREVIEW)" in body
    for target, command in zip(PREVIEW_READERS, ("destructive-gate", "iam-gate")):
        prereqs, body = recipe(target)
        assert prereqs == "test-structural-preview"
        assert f"$(GUARDRAILS) {command} $(CI_PREVIEW)" in body
    _, body = recipe("test-policy")
    assert "scripts/run_ci_preview.py --policy-pack policy" in body
    assert "pytest tests/policies" in body
    _, body = recipe("test-contract-schema")
    assert "scripts/check_contracts.py contracts" in body
    line = re.search(r"^test-guardrails: ([^#]*) ##", MAKEFILE, re.MULTILINE)
    assert line and line[1].split() == list(CHECKS.values())


def test_offline_service_has_no_network_and_no_aws_variable() -> None:
    services = COMPOSE["services"]
    offline = services["app-offline"]
    assert offline["network_mode"] == "none"
    assert offline["image"] == services["app"]["image"]
    assert offline["pull_policy"] == "never"
    assert "build" not in offline
    assert "environment" not in offline and "env_file" not in offline
    assert offline["volumes"] == [".:/workspace"]


def test_preview_artifacts_are_not_committed() -> None:
    assert ".artifacts/" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".artifacts" in (ROOT / ".dockerignore").read_text(encoding="utf-8")


# --- G3.1 F02: the preinstalled aws plugin -------------------------------------------


def arg(name: str) -> str:
    match = re.search(rf"^ARG {name}=(\S+)$", DOCKERFILE, re.MULTILINE)
    assert match, name
    return match[1]


def test_aws_plugin_matches_the_locked_sdk() -> None:
    (sdk,) = [p for p in LOCK["package"] if p["name"] == "pulumi-aws"]
    assert arg("PULUMI_AWS_PLUGIN_VERSION") == sdk["version"] == "7.23.0"


def test_aws_plugin_is_pinned_and_verified_per_architecture() -> None:
    assert arg("PULUMI_AWS_PLUGIN_SHA256_AMD64") == (
        "f5c585152bbacf11a0c02376ade122b7e74095e9b2f98dd291cbec1d880e7b4c"
    )
    assert arg("PULUMI_AWS_PLUGIN_SHA256_ARM64") == (
        "c6070f8d8ae740e617dd8e7de974b39d9f27d4f9703ec67b5413932572034592"
    )
    url = (
        '"https://github.com/pulumi/pulumi-aws/releases/download/'
        "v${PULUMI_AWS_PLUGIN_VERSION}/pulumi-resource-aws-v"
        '${PULUMI_AWS_PLUGIN_VERSION}-linux-${plugin_arch}.tar.gz"'
    )
    assert url in DOCKERFILE
    assert (
        'echo "${plugin_sha256}  /tmp/pulumi-resource-aws.tar.gz" | sha256sum -c -'
        in DOCKERFILE
    )
    assert "plugin install resource aws" in DOCKERFILE
    assert "--file /tmp/pulumi-resource-aws.tar.gz" in DOCKERFILE


def test_image_never_downloads_a_plugin() -> None:
    assert "ENV PULUMI_DISABLE_AUTOMATIC_PLUGIN_ACQUISITION=true" in DOCKERFILE
    assert (
        "COPY --from=tooling --chown=${USERNAME}:${GID} /opt/pulumi-home/plugins "
        "${PULUMI_HOME}/plugins"
    ) in DOCKERFILE
    assert (
        'test -x "${PULUMI_HOME}/plugins/resource-aws-v7.23.0/pulumi-resource-aws"'
        in DOCKERFILE
    )


# --- N: fixtures the guardrail shape check must reject ------------------------------

SHA = "a" * 40
GOOD = f"""name: Guardrails
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  preview:
    name: Structural Preview
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA}  # v1.0.0
        with:
          persist-credentials: false
      - run: make build
      - run: make test-structural-preview
"""


def test_good_fixture_passes() -> None:
    assert wc.check_guardrails(GOOD) == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        (f"checkout@{SHA}", "checkout@v4", "not SHA-pinned"),
        ("contents: read", "contents: write", "contents"),
        ("contents: read", "contents: read\n  id-token: write", "contents"),
        (
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    environment: test\n",
            "keys not allowed",
        ),
        ("          persist-credentials: false\n", "", "persist-credentials"),
        (
            "      - run: make test-structural-preview\n",
            "      - run: make test-ruff\n",
            "allow list",
        ),
        (
            "      - run: make test-structural-preview\n",
            "      - run: make test-structural-preview && curl x\n",
            "allow list",
        ),
        (
            "      - run: make test-structural-preview\n",
            "      - run: pulumi preview --stack ci\n",
            "allow list",
        ),
        (
            "      - run: make test-structural-preview\n",
            "      - run: make test-structural-preview ${{ secrets.X }}\n",
            "secrets",
        ),
        (
            "      - run: make test-structural-preview\n",
            "      - run: make test-structural-preview\n        env:\n"
            "          AWS_PROFILE: x\n",
            "env",
        ),
        ("  pull_request:\n", "  pull_request:\n    branches: [main]\n", "no filters"),
        ("  pull_request:\n", "  pull_request_target:\n", "pull_request"),
    ],
)
def test_guardrail_fixture_rejected(old: str, new: str, needle: str) -> None:
    assert GOOD.count(old) == 1, old
    found = wc.check_guardrails(GOOD.replace(old, new))
    assert any(needle in f for f in found), found


def test_battery_token_exception_does_not_extend_to_guardrails() -> None:
    """The Zizmor online step is a battery exception only."""
    text = GOOD + (
        "  zizmor:\n    name: Zizmor\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - name: Zizmor\n        run: make test-zizmor-online\n"
        "        env:\n          GH_TOKEN: ${{ github.token }}\n"
    )
    assert wc.check_battery(text) == []
    assert any("allow list" in f for f in wc.check_guardrails(text))
