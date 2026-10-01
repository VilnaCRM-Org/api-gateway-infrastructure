"""The FR-A07 repository-controls definition (G2.2; AD-A11, D-A10, D-A11).

P: the definition equals the committed fixtures. N: a required check with no
workflow job, a PR job that is not required, and a workflow `vars.*` read
with no defined variable all fail the pin tests. E: a readback with an extra
bypass actor or a wrong role ARN fails the diff.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest
import yaml

import _github_repository_controls as rc
import workflow_checks as wc
from stack_fixtures import ROOT, committed_documents, key

FIXTURES = ROOT / "tests" / "fixtures" / "repository-controls"
WF_DIR = ROOT / ".github" / "workflows"
REVIEWER_ID = 9444106


def fixture_text(name: str) -> str:
    """Read a fixture, filling the account placeholders from the stack files."""
    text = (FIXTURES / name).read_text(encoding="utf-8")
    for stack, document in committed_documents().items():
        account = document["config"][key("awsAccountId")]
        text = text.replace("{account:%s}" % stack, account)
    return text


def readback() -> dict:
    return json.loads(fixture_text("readback.json"))


def workflows(directory: Path = WF_DIR) -> dict[str, str]:
    return {
        p.name: p.read_text(encoding="utf-8") for p in sorted(directory.glob("*.yml"))
    }


def runs_on_pull_request(text: str) -> bool:
    """True for every `on:` form that names pull_request; fails closed."""
    doc = wc.load(text, [])
    if doc is None:
        return False
    events = wc.get_events(doc, [])
    return events is None or "pull_request" in events


def pin_problems(required: tuple[str, ...], files: dict[str, str]) -> list[str]:
    """Both directions of the required-check pin (G2.2 N)."""
    names: set[str] = set()
    pull_request_names: set[str] = set()
    for text in files.values():
        job_names = wc.job_check_names(text)
        names.update(job_names)
        if runs_on_pull_request(text):
            pull_request_names.update(job_names)
    problems = [
        f"required check {n!r} has no workflow job" for n in required if n not in names
    ]
    problems += [
        f"pull request job {n!r} is not a required check"
        for n in sorted(pull_request_names - set(required))
    ]
    return problems


VARS_READ = re.compile(r"(?<![\w.-])vars(?![\w-])")
VARS_NAME = re.compile(r"""vars(?:\s*\.\s*(\w+)|\s*\[\s*'(\w+)'\s*\])""")


def vars_problems(defined: set[str], files: dict[str, str]) -> list[str]:
    """One direction of the variable name match: every read is defined.

    Scans `${{ }}` expressions and bare `if:` values (G22-F02).
    """
    problems = []
    for name, text in files.items():
        expressions = wc.EXPRESSION_RE.findall(text)
        doc = wc.load(text, [])
        expressions += [v for v in wc.iter_if_values(doc) if "${{" not in v]
        for expression in expressions:
            reads = [m.start() for m in VARS_READ.finditer(expression)]
            named = VARS_NAME.findall(expression)
            if len(reads) != len(named):
                problems.append(f"{name}: unresolvable vars context in {expression!r}")
            problems += [
                f"{name}: vars.{n} is not a defined variable"
                for n in (a or b for a, b in named)
                if n not in defined
            ]
    return problems


# --- P: payloads equal the fixtures ----------------------------------------


def test_dry_run_payload_equals_the_fixture() -> None:
    expected = json.loads(fixture_text("dry-run.json"))
    actual = {
        "branchPolicies": {
            n: [{"name": "main", "type": "branch"}] for n in rc.ENVIRONMENTS
        },
        "environments": {
            n: rc.environment_payload(n, REVIEWER_ID) for n in rc.ENVIRONMENTS
        },
        "reviewerLogin": "Kravalg",
        "ruleset": rc.ruleset_payload(),
        "variables": rc.environment_variables(),
    }
    assert actual == expected


def test_the_fixture_readback_has_no_difference() -> None:
    assert (
        rc.readback_blockers(readback(), REVIEWER_ID, rc.environment_variables()) == []
    )


def test_required_checks_are_the_nineteen_ad_a11_names() -> None:
    assert len(rc.REQUIRED_STATUS_CHECKS) == 19
    assert len(set(rc.REQUIRED_STATUS_CHECKS)) == 19
    contexts = [
        c["context"]
        for c in rc.ruleset_payload()["rules"][3]["parameters"][
            "required_status_checks"
        ]
    ]
    assert contexts == list(rc.REQUIRED_STATUS_CHECKS)


def test_ruleset_has_no_bypass_and_the_fr_a07_rules() -> None:
    ruleset = rc.ruleset_payload()
    assert ruleset["bypass_actors"] == []
    assert [r["type"] for r in ruleset["rules"]] == [
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_status_checks",
    ]
    assert ruleset["rules"][2]["parameters"] == {
        "allowed_merge_methods": ["squash"],
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": True,
        "require_last_push_approval": True,
        "required_approving_review_count": 1,
        "required_review_thread_resolution": True,
        "required_reviewers": [],
    }


def test_environment_order_and_reviewers() -> None:
    assert rc.ENVIRONMENTS == (
        "test-preview",
        "test",
        "test-drift",
        "prod-preview",
        "prod",
        "prod-drift",
    )
    for name in rc.ENVIRONMENTS:
        payload = rc.environment_payload(name, REVIEWER_ID)
        assert payload["can_admins_bypass"] is False
        gated = name in ("test", "prod")
        assert payload["reviewers"] == (
            [{"type": "User", "id": REVIEWER_ID}] if gated else []
        )
        assert payload.get("prevent_self_review") is (True if gated else None)


def test_unknown_environment_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown environment"):
        rc.environment_payload("governance", REVIEWER_ID)


def test_variables_come_from_the_stack_files() -> None:
    documents = committed_documents()
    variables = rc.environment_variables()
    for stack in ("test", "prod"):
        config = documents[stack]["config"]
        account = config[key("awsAccountId")]
        for suffix, variable, role in rc.PURPOSES:
            env = variables[f"{stack}{suffix}"]
            assert set(env) == {
                variable,
                "PULUMI_BACKEND_URL",
                "PULUMI_SECRETS_PROVIDER",
            }
            assert env[variable] == (
                f"arn:aws:iam::{account}:role/{role}-api-gateway-infrastructure-{stack}"
            )
            assert env["PULUMI_BACKEND_URL"] == config[key("pulumiBackendUrl")]
            assert (
                env["PULUMI_SECRETS_PROVIDER"] == config[key("pulumiSecretsProvider")]
            )


def write_stack(directory: Path, stack: str, document: object) -> None:
    (directory / f"Pulumi.{stack}.yaml").write_text(
        yaml.safe_dump(document), encoding="utf-8"
    )


def valid_stack(stack: str) -> dict:
    return copy.deepcopy(committed_documents()[stack])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda c: c.pop(key("awsAccountId")), "non-empty string"),
        (lambda c: c.__setitem__(key("pulumiBackendUrl"), " x"), "non-empty string"),
        (lambda c: c.__setitem__(key("pulumiSecretsProvider"), ""), "non-empty string"),
        (lambda c: c.__setitem__(key("awsAccountId"), "12345"), "12 digits"),
        (lambda c: c.__setitem__(key("awsAccountId"), "12345678901a"), "12 digits"),
    ],
)
def test_malformed_stack_values_are_refused(tmp_path: Path, mutate, message) -> None:
    for stack in rc.STACKS:
        document = valid_stack(stack)
        if stack == "prod":
            mutate(document["config"])
        write_stack(tmp_path, stack, document)
    with pytest.raises(ValueError, match=message):
        rc.environment_variables(tmp_path)


def test_stack_file_problems_are_value_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not readable"):
        rc.environment_variables(tmp_path)
    (tmp_path / "Pulumi.test.yaml").write_text("a: [", encoding="utf-8")
    with pytest.raises(ValueError, match="not readable"):
        rc.environment_variables(tmp_path)
    write_stack(tmp_path, "test", ["not", "a", "mapping"])
    with pytest.raises(ValueError, match="no config mapping"):
        rc.environment_variables(tmp_path)


# --- N: the pins against the workflows --------------------------------------


def test_every_required_check_is_a_workflow_job_and_the_reverse() -> None:
    assert pin_problems(rc.REQUIRED_STATUS_CHECKS, workflows()) == []


def test_pin_fails_on_a_required_check_without_a_job() -> None:
    required = (*rc.REQUIRED_STATUS_CHECKS, "Phantom Gate")
    assert pin_problems(required, workflows()) == [
        "required check 'Phantom Gate' has no workflow job"
    ]


def test_pin_fails_on_a_pull_request_job_that_is_not_required() -> None:
    required = tuple(c for c in rc.REQUIRED_STATUS_CHECKS if c != "Ruff")
    assert pin_problems(required, workflows()) == [
        "pull request job 'Ruff' is not a required check"
    ]


def test_pin_ignores_jobs_of_workflows_without_a_pull_request_trigger() -> None:
    files = workflows()
    assert "Release" not in rc.REQUIRED_STATUS_CHECKS
    assert any("Release" in wc.job_check_names(t) for t in files.values())
    assert not any(
        runs_on_pull_request(t)
        for t in files.values()
        if "Release" in wc.job_check_names(t)
    )
    assert runs_on_pull_request("on: [push]\njobs: {}\n") is False
    assert runs_on_pull_request("- not a mapping\n") is False


def workflow_reading(expression: str) -> dict[str, str]:
    step = "echo ${{ " + expression + " }}"
    text = (
        f"on: pull_request\njobs:\n  a:\n    name: A\n    steps:\n      - run: {step}\n"
    )
    return {"x.yml": text}


def test_no_workflow_reads_a_variable_yet() -> None:
    defined = {n for env in rc.environment_variables().values() for n in env}
    assert vars_problems(defined, workflows()) == []
    assert not any(VARS_READ.search(t) for t in workflows().values())


def test_name_match_fails_on_an_undefined_variable_read() -> None:
    defined = {n for env in rc.environment_variables().values() for n in env}
    ok = workflow_reading("vars.AWS_APPLY_ROLE_ARN")
    assert vars_problems(defined, ok) == []
    assert vars_problems(defined, workflow_reading("vars['AWS_DRIFT_ROLE_ARN']")) == []
    bad = vars_problems(defined, workflow_reading("vars.AWS_ROLE_ARN"))
    assert bad == ["x.yml: vars.AWS_ROLE_ARN is not a defined variable"]
    bad = vars_problems(defined, workflow_reading("vars['NOPE']"))
    assert bad == ["x.yml: vars.NOPE is not a defined variable"]


def test_name_match_fails_closed_on_an_unresolvable_vars_context() -> None:
    defined = {n for env in rc.environment_variables().values() for n in env}
    for expression in ("toJSON(vars)", "vars[matrix.name]"):
        problems = vars_problems(defined, workflow_reading(expression))
        assert len(problems) == 1 and "unresolvable" in problems[0]


# --- E: the readback diff ----------------------------------------------------


def blockers_for(mutate) -> list[str]:
    data = readback()
    mutate(data)
    return rc.readback_blockers(data, REVIEWER_ID, rc.environment_variables())


def test_extra_bypass_actor_fails() -> None:
    actor = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
    blockers = blockers_for(lambda d: d["ruleset"]["bypass_actors"].append(actor))
    assert blockers == ["Ruleset has 1 bypass actor(s)."]


def test_unreadable_bypass_actors_fail() -> None:
    blockers = blockers_for(lambda d: d["ruleset"].pop("bypass_actors"))
    assert blockers == ["Ruleset bypass actors were not readable (admin token?)."]


def test_wrong_role_arn_fails() -> None:
    def wrong(data: dict) -> None:
        data["variables"]["prod"]["AWS_APPLY_ROLE_ARN"] += "-other"

    assert blockers_for(wrong) == [
        "prod variable AWS_APPLY_ROLE_ARN has the wrong value."
    ]


def test_missing_and_extra_variables_fail() -> None:
    def change(data: dict) -> None:
        del data["variables"]["test"]["PULUMI_BACKEND_URL"]
        data["variables"]["test-drift"]["EXTRA"] = "x"
        data["variables"]["prod-drift"] = None

    assert blockers_for(change) == [
        "test variable PULUMI_BACKEND_URL is missing.",
        "test-drift has the unexpected variable EXTRA.",
        "prod-drift variables were not readable.",
    ]


def test_ruleset_differences_fail() -> None:
    def change(data: dict) -> None:
        ruleset = data["ruleset"]
        ruleset["enforcement"] = "disabled"
        ruleset["conditions"] = {}
        checks = ruleset["rules"][3]["parameters"]
        checks["strict_required_status_checks_policy"] = False
        checks["required_status_checks"].pop()
        checks["required_status_checks"].append({"context": "Extra"})
        checks["required_status_checks"].append({"name": "Ruff"})
        ruleset["rules"][2]["parameters"]["required_approving_review_count"] = True
        del ruleset["rules"][2]["parameters"]["required_reviewers"]
        ruleset["rules"].append({"type": "update"})

    assert blockers_for(change) == [
        "Ruleset must be an active branch ruleset.",
        "Ruleset must target only the default branch.",
        "Ruleset has an unexpected update rule.",
        "Pull request rule required_approving_review_count must be 1.",
        "Ruleset must require strict status checks.",
        "Ruleset is missing required checks: Contract Schema.",
        "Ruleset has unexpected required checks: Extra.",
        "Ruleset repeats a required check.",
        "Required checks must come from the GitHub Actions app "
        "(integration_id 15368): Extra, Ruff.",
    ]


def test_missing_ruleset_and_malformed_rules_fail() -> None:
    assert blockers_for(lambda d: d.__setitem__("ruleset", None)) == [
        "Active main branch ruleset was not found."
    ]
    assert blockers_for(lambda d: d["ruleset"].__setitem__("rules", "x")) == [
        "Ruleset rules are not readable."
    ]

    def change(data: dict) -> None:
        data["ruleset"]["rules"] = [{"type": "deletion"}, {"type": "deletion"}]

    assert blockers_for(change) == [
        "Ruleset is missing the non_fast_forward rule.",
        "Ruleset is missing the pull_request rule.",
        "Ruleset is missing the required_status_checks rule.",
        "Ruleset repeats a rule type.",
    ]

    def parameters(data: dict) -> None:
        data["ruleset"]["rules"][2]["parameters"] = []
        data["ruleset"]["rules"][3]["parameters"] = []

    assert blockers_for(parameters) == [
        "Pull request rule parameters are not an object.",
        "Required status checks parameters are not an object.",
    ]


def test_environment_differences_fail() -> None:
    def change(data: dict) -> None:
        envs = data["environments"]
        envs["test"]["can_admins_bypass"] = True
        envs["test"]["deployment_branch_policies"].append(
            {"id": 8, "name": "release/*", "type": "branch"}
        )
        envs["prod"]["protection_rules"][0]["reviewers"].append(
            {"type": "User", "reviewer": {"id": 3, "type": "User"}}
        )
        envs["prod"]["protection_rules"][0]["prevent_self_review"] = False
        envs["test-drift"]["protection_rules"].append(
            {"type": "required_reviewers", "reviewers": []}
        )
        envs["prod-preview"]["wait_timer"] = 30
        envs["prod-drift"]["can_admins_bypass"] = None
        envs["test-preview"] = None

    assert blockers_for(change) == [
        "test-preview environment was not readable.",
        "test environment must allow only the main branch.",
        "test environment must disable administrator bypass.",
        "test-drift environment has an unknown or malformed protection rule.",
        "prod-preview environment must not have a wait timer.",
        "prod environment has the wrong required reviewers.",
        "prod environment must prevent self-review.",
        "prod-drift environment must disable administrator bypass.",
    ]


@pytest.mark.parametrize(
    "reviewer",
    [
        {"type": "Team", "reviewer": {"id": 1, "type": "Team"}},
        {"type": "User", "reviewer": {"id": REVIEWER_ID, "type": "Team"}},
        {"type": "User", "id": 7, "reviewer": {"id": 8, "type": "User"}},
        {"type": "User", "id": True, "reviewer": {"id": True, "type": "User"}},
        {"type": "User", "reviewer": {"id": True, "type": "User"}},
        {"type": "User", "reviewer": {"id": 0, "type": "User"}},
        {"type": "User", "reviewer": "x"},
        "not a mapping",
    ],
)
def test_malformed_and_team_reviewers_fail(reviewer: object) -> None:
    def change(data: dict) -> None:
        rule = data["environments"]["test"]["protection_rules"][0]
        rule["reviewers"] = [reviewer]

    assert "test environment has a malformed or non-user reviewer." in blockers_for(
        change
    )


def test_reviewer_group_shapes_fail() -> None:
    def change(data: dict) -> None:
        data["environments"]["prod"]["reviewers"] = "x"
        data["environments"]["prod-drift"]["reviewers"] = [
            {"type": "User", "id": REVIEWER_ID}
        ]

    assert blockers_for(change) == [
        "prod environment has a malformed or non-user reviewer.",
        "prod-drift environment has the wrong required reviewers.",
    ]


def test_direct_reviewer_ids_and_wrong_protection_rules() -> None:
    def change(data: dict) -> None:
        data["environments"]["test"]["reviewers"] = [
            {"type": "User", "id": REVIEWER_ID}
        ]
        data["environments"]["prod"]["protection_rules"] = "x"
        data["environments"]["prod-drift"]["protection_rules"] = ["x"]
        data["environments"]["prod-drift"]["wait_timer"] = 0

    assert blockers_for(change) == [
        "prod environment has an unknown or malformed protection rule.",
        "prod-drift environment has an unknown or malformed protection rule.",
    ]


def test_readback_shape_and_unexpected_entries_fail() -> None:
    assert rc.readback_blockers({}, REVIEWER_ID, {}) == [
        "Readback must hold environments, variables and secrets objects."
    ]
    no_secrets = {k: v for k, v in readback().items() if k != "secrets"}
    assert rc.readback_blockers(no_secrets, REVIEWER_ID, {}) == [
        "Readback must hold environments, variables and secrets objects."
    ]

    def change(data: dict) -> None:
        data["environments"]["governance"] = data["environments"]["test"]
        data["variables"]["other"] = {}
        data["secrets"]["third"] = 0

    assert blockers_for(change) == [
        "Readback holds the unexpected environment governance.",
        "Readback holds the unexpected environment other.",
        "Readback holds the unexpected environment third.",
    ]


def test_status_check_context_forms() -> None:
    assert rc.status_check_context({"context": "A"}) == "A"
    assert rc.status_check_context({"name": "B"}) == "B"
    assert rc.status_check_context({"context": ""}) is None
    assert rc.status_check_context("A") is None


def test_reviewer_id_helpers() -> None:
    items = [
        {"type": "User", "id": 1},
        {"type": "Team", "id": 2},
        {"reviewer": {"id": 3}},
        {"reviewer": {"id": "x"}},
        "no",
    ]
    assert rc.reviewer_ids_from_items(items) == {1, 3}
    environment = {
        "reviewers": [{"type": "User", "id": 4}],
        "protection_rules": [
            "no",
            {"type": "wait_timer"},
            {"reviewers": [{"type": "User", "id": 5}]},
        ],
    }
    assert rc.environment_reviewer_ids(environment) == {4, 5}
    assert rc.environment_reviewer_ids({}) == set()


def test_reviewer_with_a_matching_direct_and_nested_id_passes() -> None:
    def change(data: dict) -> None:
        rule = data["environments"]["test"]["protection_rules"][0]
        rule["reviewers"] = [
            {
                "type": "User",
                "id": REVIEWER_ID,
                "reviewer": {"id": REVIEWER_ID, "type": "User"},
            }
        ]

    assert blockers_for(change) == []


# --- G22-F01: the checks are pinned to the GitHub Actions app ----------------


def test_every_required_check_is_pinned_to_the_actions_app() -> None:
    assert rc.GITHUB_ACTIONS_APP_ID == 15368
    checks = rc.ruleset_payload()["rules"][3]["parameters"]["required_status_checks"]
    assert {c["integration_id"] for c in checks} == {15368}
    assert len(checks) == 19


@pytest.mark.parametrize("app_id", [None, "missing", 0, 3, "15368", True, 15368.0])
def test_a_missing_or_other_integration_id_fails(app_id: object) -> None:
    def change(data: dict) -> None:
        check = data["ruleset"]["rules"][3]["parameters"]["required_status_checks"][4]
        if app_id == "missing":
            del check["integration_id"]
        else:
            check["integration_id"] = app_id

    assert blockers_for(change) == [
        "Required checks must come from the GitHub Actions app "
        "(integration_id 15368): Bandit."
    ]


def test_a_non_mapping_check_fails_the_integration_pin() -> None:
    def change(data: dict) -> None:
        checks = data["ruleset"]["rules"][3]["parameters"]["required_status_checks"]
        checks[0] = "Ruff"

    assert any("GitHub Actions app" in b for b in blockers_for(change))


# --- G22-F02: every `on:` form and bare `if:` values -------------------------

JOB = "jobs:\n  a:\n    name: Stray\n    runs-on: x\n    steps:\n      - run: x\n"


@pytest.mark.parametrize(
    "on",
    [
        "on: pull_request\n",
        "on: [push, pull_request]\n",
        "on:\n  push:\n  pull_request:\n",
        "on: 5\n",
    ],
)
def test_pin_covers_string_list_dict_and_unsupported_on_forms(on: str) -> None:
    files = {"x.yml": on + JOB}
    assert runs_on_pull_request(files["x.yml"]) is True
    assert pin_problems(rc.REQUIRED_STATUS_CHECKS, files)[-1] == (
        "pull request job 'Stray' is not a required check"
    )


@pytest.mark.parametrize("on", ["on: push\n", "on: [push]\n", "on:\n  push:\n"])
def test_pin_skips_non_pull_request_on_forms(on: str) -> None:
    assert runs_on_pull_request(on + JOB) is False


def test_bare_if_values_are_scanned_for_vars() -> None:
    defined = {n for env in rc.environment_variables().values() for n in env}
    head = "on: pull_request\njobs:\n  a:\n    steps:\n      - if: "
    ok = {"x.yml": head + "vars.AWS_APPLY_ROLE_ARN != ''\n        run: x\n"}
    assert vars_problems(defined, ok) == []
    bad = {"x.yml": head + "vars.NOPE == 'x'\n        run: x\n"}
    assert vars_problems(defined, bad) == ["x.yml: vars.NOPE is not a defined variable"]
    wrapped = {"x.yml": head + "${{ vars.NOPE }}\n        run: x\n"}
    assert len(vars_problems(defined, wrapped)) == 1
    opaque = {"x.yml": head + "toJSON(vars)\n        run: x\n"}
    assert "unresolvable" in vars_problems(defined, opaque)[0]


# --- G22-F04: no environment secret ----------------------------------------


def test_an_environment_secret_fails_with_a_count_only() -> None:
    def change(data: dict) -> None:
        data["secrets"]["prod"] = 2
        data["secrets"]["test-drift"] = None
        data["secrets"]["test"] = -1
        data["secrets"]["test-preview"] = True

    assert blockers_for(change) == [
        "test-preview environment secrets were not readable.",
        "test environment secrets were not readable.",
        "test-drift environment secrets were not readable.",
        "prod has 2 environment secret(s); expected none.",
    ]
