"""The G3.2 PR quality battery (AD-A11, FR-A08, FR-A10, NFR-A09, NFR-A11).

P: every AD-A11 battery check is a job of a battery workflow that runs on
every pull request with ``contents: read`` and no secret, through a Makefile
target. N: branch coverage below 100% fails ``Coverage``; a tag-pinned
action, a write permission, ``id-token: write``, a secret, an unpinned
checkout credential or an unlisted run command fails the shape test.
E: a PR from a fork runs the battery: ``pull_request`` has no filter and no
job needs a secret, an environment or a write token.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404
import sys
import tomllib
from pathlib import Path

import pytest

import workflow_checks as wc

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / ".github" / "workflows"
BATTERY_FILES = ("python-quality.yml", "security-scans.yml", "codeql.yml")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")

# AD-A11 required checks that G3.2 owns. `Structural Preview`, `Destructive
# Diff Gate`, `IAM Gate`, `Policy` and `Contract Schema` arrive in G3.3; the
# G2.2 test pins the full list against the workflows.
BATTERY_CHECKS = {
    "Ruff": "test-ruff",
    "Types": "test-types",
    "Maintainability": "test-maintainability",
    "Coverage": "test-coverage",
    "Bandit": "test-bandit",
    "Dependency Audit": "test-deps-security",
    "Secrets Scan": "test-secrets",
    "Actionlint": "test-actionlint",
    "Zizmor": "test-zizmor",
    "Yamllint": "test-yaml",
    "Hadolint": "test-dockerfile",
    "Dependency Review": None,
    "CodeQL (python)": None,
    "CodeQL (actions)": None,
}
G33_CHECKS = {
    "Structural Preview",
    "Destructive Diff Gate",
    "IAM Gate",
    "Policy",
    "Contract Schema",
}


def battery_text(name: str) -> str:
    return (WF_DIR / name).read_text(encoding="utf-8")


def recipe(target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:.*?\n((?:[ \t]+.*\n?)+)", MAKEFILE, re.MULTILINE
    )
    assert match, target
    return match[1]


# --- the real workflows ----------------------------------------------------


@pytest.mark.parametrize("name", BATTERY_FILES)
def test_battery_workflow_shape(name: str) -> None:
    assert wc.check_battery(battery_text(name)) == []


def test_battery_jobs_are_exactly_the_ad_a11_checks() -> None:
    names = [n for f in BATTERY_FILES for n in wc.job_check_names(battery_text(f))]
    assert sorted(names) == sorted(BATTERY_CHECKS)


def test_no_workflow_yet_claims_a_g33_check() -> None:
    names = {
        n for wf in WF_DIR.glob("*.y*ml") for n in wc.job_check_names(wf.read_text())
    }
    assert not names & G33_CHECKS


@pytest.mark.parametrize(("check", "target"), sorted(BATTERY_CHECKS.items()))
def test_each_local_check_runs_its_make_target(check: str, target: str) -> None:
    if target is None:
        return
    jobs = [
        job
        for f in BATTERY_FILES
        for _, job in wc._job_items(wc.load(battery_text(f), []))
        if job.get("name") == check
    ]
    assert len(jobs) == 1
    runs = [step.get("run") for step in jobs[0]["steps"] if "run" in step]
    assert runs == ["make build", f"make {target}"]
    battery = re.search(r"^test-battery: (.*?) ##", MAKEFILE, re.MULTILINE)
    assert battery and target in battery[1].split()


def test_github_only_checks() -> None:
    codeql = battery_text("codeql.yml")
    assert "upload: never" in codeql
    assert "upload-database: false" in codeql
    assert 'scripts/codeql_sarif_gate.py "$RUNNER_TEMP/codeql-results"' in codeql
    assert "output: ${{ runner.temp }}/codeql-results" in codeql
    review = wc.load(battery_text("security-scans.yml"), [])["jobs"][
        "dependency_review"
    ]
    assert review["if"] == "github.event_name == 'pull_request'"
    assert [s["uses"].split("@")[0] for s in review["steps"]] == [
        "actions/dependency-review-action"
    ]
    assert "with" not in review["steps"][0]


def test_every_uses_is_sha_pinned() -> None:
    """AGENTS.md rule 3: a full 40-hex commit SHA; a `# vX.Y.Z` comment is
    allowed, not required (G3.2 F05)."""
    for wf in WF_DIR.glob("*.y*ml"):
        for line in wf.read_text(encoding="utf-8").splitlines():
            if re.match(r"\s*(-\s+)?uses:", line):
                assert re.search(r"@[0-9a-f]{40}(\s+#.*)?$", line), line


# --- Makefile targets ------------------------------------------------------


def test_battery_targets_run_in_the_development_image() -> None:
    for target in filter(None, BATTERY_CHECKS.values()):
        lines = [x.strip() for x in recipe(target).splitlines() if x.strip()]
        commands = [x for x in lines if not x.startswith(("&&", "--"))]
        assert all(x.startswith("$(RUN) ") for x in commands), (target, lines)
        flags = re.findall(r"\buv run (\S+)", recipe(target))
        assert all(flag == "--frozen" for flag in flags), (target, flags)


def test_python_targets_cover_pulumi_scripts_and_policy() -> None:
    assert "PYTHON_SOURCES = pulumi scripts $(wildcard policy)" in MAKEFILE
    for target in ("test-ruff", "test-types", "test-maintainability", "test-bandit"):
        assert "$(PYTHON_SOURCES)" in recipe(target), target


def test_thresholds_are_the_ported_ones() -> None:
    assert "xenon --max-absolute B --max-modules B --max-average A" in recipe(
        "test-maintainability"
    )
    ruff = PYPROJECT["tool"]["ruff"]
    assert ruff["lint"]["select"] == ["C90", "E", "F", "I"]
    assert ruff["lint"]["mccabe"]["max-complexity"] == 10
    assert ruff["line-length"] == 88
    assert "--strict" in recipe("test-yaml")
    assert "--strict" in recipe("test-deps-security")
    assert "--require-hashes" in recipe("test-deps-security")
    assert "--error-on-warning" in recipe("test-types")


def test_ruff_first_party_modules() -> None:
    isort = PYPROJECT["tool"]["ruff"]["lint"]["isort"]
    assert isort["known-third-party"] == ["pulumi", "pulumi_aws"]
    local = {p.stem for d in ("scripts", "tests") for p in (ROOT / d).glob("*.py")}
    local -= {"conftest"}
    local = {m for m in local if not m.startswith("test_")}
    packages = {
        p.name for p in (ROOT / "pulumi").iterdir() if (p / "__init__.py").exists()
    }
    assert set(isort["known-first-party"]) == local | packages


def test_no_bandit_skip_beyond_b101_in_tests() -> None:
    assert "skips" not in PYPROJECT["tool"]["bandit"]
    assert "baseline" not in MAKEFILE
    gate_lines = [x for x in MAKEFILE.splitlines() if "bandit_gate.py" in x]
    assert [("--skip" in x, x.split()[-1]) for x in gate_lines] == [
        (False, "$(PYTHON_SOURCES)"),
        (True, "tests"),
    ]
    assert "--skip B101 tests" in gate_lines[1]


def test_zizmor_requires_a_hash_pin_for_every_action() -> None:
    config = wc.load((ROOT / ".github" / "zizmor.yml").read_text(encoding="utf-8"), [])
    policies = config["rules"]["unpinned-uses"]["config"]["policies"]
    assert policies == {"*": "hash-pin"}


def test_zizmor_runs_offline_and_secrets_scan_reads_history() -> None:
    assert "zizmor --offline" in recipe("test-zizmor")
    assert "gitleaks git" in recipe("test-secrets")
    assert "--log-opts=HEAD" in recipe("test-secrets")
    job = wc.load(battery_text("security-scans.yml"), [])["jobs"]["secrets_scan"]
    assert job["steps"][0]["with"] == {"fetch-depth": 0, "persist-credentials": False}


def test_battery_binaries_are_pinned_in_the_image() -> None:
    for tool in ("ACTIONLINT", "SHELLCHECK", "GITLEAKS", "HADOLINT"):
        assert re.search(rf"^ARG {tool}_VERSION=", DOCKERFILE, re.MULTILINE), tool
        assert f"--from=tooling /usr/local/bin/{tool.lower()} " in DOCKERFILE


def test_battery_python_tools_are_locked_dev_dependencies() -> None:
    dev = " ".join(PYPROJECT["dependency-groups"]["dev"])
    for tool in ("bandit", "pip-audit", "radon", "ruff", "ty", "xenon", "yamllint"):
        assert re.search(rf"\b{tool}\b", dev), tool
    assert "zizmor" in dev


def test_poetry_era_lint_files_are_gone() -> None:
    assert not (ROOT / "pulumi" / ".flake8").exists()
    assert not (ROOT / "pulumi" / ".pre-commit-config.yaml").exists()
    assert (ROOT / ".yamllint.yml").exists()


# --- coverage gate (NFR-A09) -----------------------------------------------


def test_coverage_measures_every_source_directory() -> None:
    run = PYPROJECT["tool"]["coverage"]["run"]
    assert run["branch"] is True
    expected = {"pulumi", "scripts"} | (
        {"policy"} if (ROOT / "policy").is_dir() else set()
    )
    assert set(run["source"]) == expected
    assert PYPROJECT["tool"]["coverage"]["report"]["fail_under"] == 100


def test_coverage_target_uses_the_configured_threshold() -> None:
    body = recipe("test-coverage")
    assert "coverage run -m pytest" in body
    assert "coverage report" in body
    assert "fail-under" not in body
    assert "omit" not in str(PYPROJECT["tool"]["coverage"])
    assert "BRANCH_COVERAGE" not in MAKEFILE


def run_coverage(tmp_path: Path, call: str) -> int:
    module = tmp_path / "mod.py"
    module.write_text(
        f"def f(x):\n    y = 0\n    if x:\n        y = 1\n    return y\n\n\n{call}\n",
        encoding="utf-8",
    )
    data = ["--data-file", str(tmp_path / ".cov")]
    base = [sys.executable, "-m", "coverage"]
    opts = {"cwd": tmp_path, "capture_output": True, "text": True, "check": False}
    measure = [*base, "run", "--branch", *data, str(module)]
    report = [*base, "report", *data, "--fail-under=100"]
    subprocess.run(measure, **opts)  # nosec B603
    return subprocess.run(report, **opts).returncode  # nosec B603


def test_branch_coverage_below_100_fails(tmp_path: Path) -> None:
    # f(True) runs every statement; only the `if x` false branch is missed.
    assert run_coverage(tmp_path, "f(True)") == 2


def test_full_branch_coverage_passes(tmp_path: Path) -> None:
    assert run_coverage(tmp_path, "f(True)\nf(False)") == 0


# --- fixtures the battery shape test must reject -------------------------

SHA = "a" * 40
GOOD = f"""name: Battery
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA}  # v1.0.0
        with:
          persist-credentials: false
      - run: make build
      - run: make test-lint
"""


def rejected(text: str, needle: str = "") -> None:
    found = wc.check_battery(text)
    assert found, "fixture was not rejected"
    assert any(needle in f for f in found), found


def test_good_fixture_passes() -> None:
    assert wc.check_battery(GOOD) == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        (f"checkout@{SHA}", "checkout@v4", "not SHA-pinned"),
        ("contents: read", "contents: write", "contents"),
        ("contents: read", "contents: read\n  id-token: write", "contents"),
        ("permissions:\n  contents: read\n", "permissions: {}\n", "exactly contents"),
        (
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    permissions:\n      contents: read\n",
            "keys not allowed",
        ),
        (
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    environment: test\n",
            "keys not allowed",
        ),
        (
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    container: alpine\n",
            "keys not allowed",
        ),
        ("    runs-on: ubuntu-latest\n", "    runs-on: self-hosted\n", "runs-on"),
        ("    name: Lint\n", "", "check name"),
        ("          persist-credentials: false\n", "", "persist-credentials"),
        (
            "          persist-credentials: false\n",
            "          persist-credentials: 'false'\n",
            "persist-credentials",
        ),
        (
            "          persist-credentials: false\n",
            "          persist-credentials: false\n          token: x\n",
            "with keys",
        ),
        (
            "          persist-credentials: false\n",
            "          persist-credentials: false\n          fetch-depth: 1\n",
            "fetch-depth",
        ),
        (
            "      - run: make test-lint\n",
            "      - run: make test-lint && curl x\n",
            "allow list",
        ),
        (
            "      - run: make test-lint\n",
            "      - run: echo ${{ github.head_ref }}\n",
            "interpolate",
        ),
        (
            "      - run: make test-lint\n",
            "      - run: make test-lint\n        env: {A: b}\n",
            "env",
        ),
        (
            "      - run: make test-lint\n",
            "      - run: make test-lint ${{ secrets.X }}\n",
            "secrets",
        ),
        (
            "      - run: make test-lint\n",
            "      - run: make test-lint\n        if: github.token\n",
            "github.token",
        ),
        ("  pull_request:\n", "  pull_request:\n    branches: [main]\n", "no filters"),
        ("  pull_request:\n", "  pull_request_target:\n", "pull_request"),
        ("  pull_request:\n", "  workflow_dispatch:\n", "pull_request"),
        ("    branches: [main]\n", "    branches: [dev]\n", "push filters"),
        ("permissions:", "env: {A: b}\npermissions:", "top-level env"),
    ],
)
def test_battery_fixture_rejected(old: str, new: str, needle: str) -> None:
    assert GOOD.count(old) == 1, old
    rejected(GOOD.replace(old, new), needle)


def test_unparseable_battery_fixture_rejected() -> None:
    rejected("on: [\n", "unparseable")


def test_job_check_names_expand_the_matrix() -> None:
    text = GOOD.replace(
        "    name: Lint\n",
        "    name: Lint (${{ matrix.a }}, ${{ matrix.b }})\n"
        "    strategy:\n      matrix:\n        a: [x, y]\n        b: [1]\n",
    )
    assert wc.job_check_names(text) == ["Lint (x, 1)", "Lint (y, 1)"]
    assert wc.job_check_names("on: [\n") == []


@pytest.mark.parametrize(
    "matrix",
    ["include: [{a: z}]", "exclude: [{a: x}]", "a: ${{ fromJSON('[1]') }}"],
)
def test_job_check_names_refuse_matrices_they_cannot_expand(matrix: str) -> None:
    text = GOOD.replace(
        "    name: Lint\n",
        f"    name: Lint (${{{{ matrix.a }}}})\n"
        f"    strategy:\n      matrix:\n        {matrix}\n",
    )
    with pytest.raises(ValueError):
        wc.job_check_names(text)
