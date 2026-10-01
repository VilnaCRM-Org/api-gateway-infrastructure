"""The gateway repository-controls definition (FR-A07, AD-A11, D-A10).

Everything here is pure: payloads, the stack-file variable values and the
diff of a readback against the definition. No account id is a constant
(FR-A09): role ARNs are built from the committed stack files.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import yaml

from _github_environment_controls import (
    environment_is_main_only,
    environment_prevents_self_review,
)

PROJECT = "api-gateway-infrastructure"
STACK_DIR = Path(__file__).resolve().parents[1] / "pulumi"
ACCOUNT_ID = re.compile(r"[0-9]{12}")

# AD-A11: the 14 battery checks, then the 5 guardrail checks. Each name is
# the `name:` of one workflow job; tests/unit/test_repository_controls.py pins
# the list against the workflows in both directions.
REQUIRED_STATUS_CHECKS = (
    "Ruff",
    "Types",
    "Maintainability",
    "Coverage",
    "Bandit",
    "Dependency Audit",
    "Secrets Scan",
    "Actionlint",
    "Zizmor",
    "Yamllint",
    "Hadolint",
    "Dependency Review",
    "CodeQL (python)",
    "CodeQL (actions)",
    "Structural Preview",
    "Destructive Diff Gate",
    "IAM Gate",
    "Policy",
    "Contract Schema",
)

# G22-F01: every required check must come from the GitHub Actions app, so a
# status or check run of the same name from another app cannot satisfy it.
# Verified against GET /apps/github-actions (id 15368).
GITHUB_ACTIONS_APP_ID = 15368

# Per stack, the three environments, the variable that holds that
# environment's role ARN, and the role the ARN names (AD-A1, D-A11).
STACKS = ("test", "prod")
PURPOSES = (
    ("-preview", "AWS_PREVIEW_ROLE_ARN", "GitHubCiPreview"),
    ("", "AWS_APPLY_ROLE_ARN", "GitHubCiApply"),
    ("-drift", "AWS_DRIFT_ROLE_ARN", "GitHubCiDrift"),
)
ENVIRONMENTS = tuple(
    f"{stack}{suffix}" for stack in STACKS for suffix, _, _ in PURPOSES
)
# `@Kravalg` is the sole reviewer of the Apply environments only.
PROTECTED_ENVIRONMENTS = STACKS

MAIN_REF_CONDITION = {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
PULL_REQUEST_PARAMETERS = {
    "allowed_merge_methods": ["squash"],
    "dismiss_stale_reviews_on_push": True,
    "require_code_owner_review": True,
    "require_last_push_approval": True,
    "required_approving_review_count": 1,
    "required_review_thread_resolution": True,
    "required_reviewers": [],
}
BRANCH_POLICY = {"protected_branches": False, "custom_branch_policies": True}
EXPECTED_BRANCH_POLICIES = [{"name": "main", "type": "branch"}]


def ruleset_payload() -> dict[str, Any]:
    """Build the `main` ruleset: no bypass actors, the AD-A11 checks."""
    return {
        "name": "main",
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": MAIN_REF_CONDITION,
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "pull_request", "parameters": dict(PULL_REQUEST_PARAMETERS)},
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {"context": context, "integration_id": GITHUB_ACTIONS_APP_ID}
                        for context in REQUIRED_STATUS_CHECKS
                    ],
                },
            },
        ],
    }


def environment_payload(name: str, reviewer_id: int) -> dict[str, Any]:
    """Build one environment: reviewer-gated for test and prod, else ungated."""
    if name not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment {name!r}.")
    gated = name in PROTECTED_ENVIRONMENTS
    payload: dict[str, Any] = {
        "wait_timer": 0,
        "can_admins_bypass": False,
        "reviewers": [{"type": "User", "id": reviewer_id}] if gated else [],
        "deployment_branch_policy": dict(BRANCH_POLICY),
    }
    if gated:
        payload["prevent_self_review"] = True
    return payload


def _stack_config(stack: str, stack_dir: Path) -> Mapping[str, Any]:
    """Read one committed stack file's config mapping."""
    path = stack_dir / f"Pulumi.{stack}.yaml"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Stack file {path.name} is not readable: {exc}") from exc
    config = document.get("config") if isinstance(document, Mapping) else None
    if not isinstance(config, Mapping):
        raise ValueError(f"Stack file {path.name} has no config mapping.")
    return config


def _config_value(config: Mapping[str, Any], name: str, stack: str) -> str:
    value = config.get(f"{PROJECT}:{name}")
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"Stack {stack} needs a non-empty string for {name}.")
    return value


def environment_variables(
    stack_dir: Path = STACK_DIR,
) -> dict[str, dict[str, str]]:
    """Return every environment's variables, derived from the stack files."""
    result: dict[str, dict[str, str]] = {}
    for stack in STACKS:
        config = _stack_config(stack, stack_dir)
        account = _config_value(config, "awsAccountId", stack)
        if not ACCOUNT_ID.fullmatch(account):
            raise ValueError(f"Stack {stack} awsAccountId must be 12 digits.")
        shared = {
            "PULUMI_BACKEND_URL": _config_value(config, "pulumiBackendUrl", stack),
            "PULUMI_SECRETS_PROVIDER": _config_value(
                config, "pulumiSecretsProvider", stack
            ),
        }
        for suffix, variable, role in PURPOSES:
            arn = f"arn:aws:iam::{account}:role/{role}-{PROJECT}-{stack}"
            result[f"{stack}{suffix}"] = {variable: arn, **shared}
    return result


# --- readback diff ---------------------------------------------------------


def status_check_context(check: object) -> str | None:
    """Return the status-check context from GitHub ruleset metadata."""
    if not isinstance(check, Mapping):
        return None
    check = cast(Mapping[str, Any], check)
    context = check.get("context") or check.get("name")
    return str(context) if context else None


def _from_actions(check: object) -> bool:
    if not isinstance(check, Mapping):
        return False
    app_id = check.get("integration_id")
    return type(app_id) is int and app_id == GITHUB_ACTIONS_APP_ID


def _integration_blockers(items: object) -> list[str]:
    wrong = sorted(
        {
            status_check_context(i) or "<unnamed>"
            for i in (items if isinstance(items, list) else [])
            if not _from_actions(i)
        }
    )
    if not wrong:
        return []
    return [
        "Required checks must come from the GitHub Actions app "
        f"(integration_id {GITHUB_ACTIONS_APP_ID}): {', '.join(wrong)}."
    ]


def _status_check_blockers(rule: Mapping[str, Any]) -> list[str]:
    parameters = rule.get("parameters")
    if not isinstance(parameters, Mapping):
        return ["Required status checks parameters are not an object."]
    items = parameters.get("required_status_checks")
    contexts = (
        [status_check_context(i) for i in items] if isinstance(items, list) else []
    )
    blockers = []
    if parameters.get("strict_required_status_checks_policy") is not True:
        blockers.append("Ruleset must require strict status checks.")
    missing = sorted(set(REQUIRED_STATUS_CHECKS) - set(contexts))
    extra = sorted({c or "<unnamed>" for c in contexts} - set(REQUIRED_STATUS_CHECKS))
    if missing:
        blockers.append(f"Ruleset is missing required checks: {', '.join(missing)}.")
    if extra:
        blockers.append(f"Ruleset has unexpected required checks: {', '.join(extra)}.")
    if len(contexts) != len(set(contexts)):
        blockers.append("Ruleset repeats a required check.")
    return blockers + _integration_blockers(items)


def _pull_request_blockers(rule: Mapping[str, Any]) -> list[str]:
    parameters = rule.get("parameters")
    if not isinstance(parameters, Mapping):
        return ["Pull request rule parameters are not an object."]
    actual = {"required_reviewers": [], **parameters}
    return [
        f"Pull request rule {key} must be {expected!r}."
        for key, expected in PULL_REQUEST_PARAMETERS.items()
        if actual.get(key) != expected or type(actual[key]) is not type(expected)
    ]


def _rule_types_blockers(rules: list[Mapping[str, Any]]) -> list[str]:
    types = [rule.get("type") for rule in rules]
    expected = [rule["type"] for rule in ruleset_payload()["rules"]]
    blockers = [f"Ruleset is missing the {t} rule." for t in expected if t not in types]
    blockers += [
        f"Ruleset has an unexpected {t} rule." for t in types if t not in expected
    ]
    if len(types) != len(set(types)):
        blockers.append("Ruleset repeats a rule type.")
    return blockers


def _rules_blockers(rules: object) -> list[str]:
    if not isinstance(rules, list) or not all(isinstance(r, Mapping) for r in rules):
        return ["Ruleset rules are not readable."]
    blockers = _rule_types_blockers(rules)
    by_type = {rule.get("type"): rule for rule in rules}
    for rule_type, check in (
        ("pull_request", _pull_request_blockers),
        ("required_status_checks", _status_check_blockers),
    ):
        if rule_type in by_type:
            blockers += check(by_type[rule_type])
    return blockers


def ruleset_blockers(ruleset: Mapping[str, Any] | None) -> list[str]:
    """Return the differences between a readback ruleset and the definition."""
    if ruleset is None:
        return ["Active main branch ruleset was not found."]
    blockers = []
    if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
        blockers.append("Ruleset must be an active branch ruleset.")
    if ruleset.get("conditions") != MAIN_REF_CONDITION:
        blockers.append("Ruleset must target only the default branch.")
    bypass = ruleset.get("bypass_actors")
    if not isinstance(bypass, list):
        blockers.append("Ruleset bypass actors were not readable (admin token?).")
    elif bypass:
        blockers.append(f"Ruleset has {len(bypass)} bypass actor(s).")
    return [*blockers, *_rules_blockers(ruleset.get("rules"))]


def reviewer_ids_from_items(items: Sequence[object]) -> set[int]:
    """Return user IDs from reviewer objects in environment metadata."""
    reviewer_ids: set[int] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        item = cast(Mapping[str, Any], item)
        reviewer_id = item.get("id")
        if item.get("type") == "User" and isinstance(reviewer_id, int):
            reviewer_ids.add(reviewer_id)
            continue
        nested_user = item.get("reviewer")
        if isinstance(nested_user, Mapping) and isinstance(nested_user.get("id"), int):
            reviewer_ids.add(nested_user["id"])
    return reviewer_ids


def environment_reviewer_ids(environment: Mapping[str, Any]) -> set[int]:
    """Return required reviewer user IDs from a GitHub environment payload."""
    reviewer_ids: set[int] = set()
    top_level_reviewers = environment.get("reviewers")
    if isinstance(top_level_reviewers, list):
        reviewer_ids.update(reviewer_ids_from_items(top_level_reviewers))
    protection_rules = environment.get("protection_rules")
    if isinstance(protection_rules, list):
        for rule in protection_rules:
            reviewers = rule.get("reviewers") if isinstance(rule, Mapping) else None
            if isinstance(reviewers, list):
                reviewer_ids.update(reviewer_ids_from_items(reviewers))
    return reviewer_ids


def _is_user_reviewer(item: object) -> bool:
    """Validate one direct or nested GitHub reviewer without hiding its type."""
    if not isinstance(item, Mapping) or item.get("type") != "User":
        return False
    person = item.get("reviewer", item)
    if not isinstance(person, Mapping) or person.get("type") != "User":
        return False
    identity = person.get("id")
    if "reviewer" in item and "id" in item:
        if type(item["id"]) is not int or item["id"] != identity:
            return False
    return type(identity) is int and identity > 0


def _protection_rules_ok(rules: object, allowed: set[str]) -> bool:
    return isinstance(rules, list) and all(
        isinstance(rule, Mapping) and rule.get("type") in allowed for rule in rules
    )


def _reviewer_groups(environment: Mapping[str, Any]) -> list[object]:
    """Collect top-level and rule reviewer groups of a rule-checked payload."""
    groups = [environment["reviewers"]] if "reviewers" in environment else []
    groups += [
        rule["reviewers"]
        for rule in environment.get("protection_rules", [])
        if "reviewers" in rule
    ]
    return groups


def _reviewers_are_users(environment: Mapping[str, Any]) -> bool:
    return all(
        isinstance(items, list) and all(_is_user_reviewer(i) for i in items)
        for items in _reviewer_groups(environment)
    )


def _reviewer_blockers(
    name: str, environment: Mapping[str, Any], reviewer_id: int
) -> list[str]:
    gated = name in PROTECTED_ENVIRONMENTS
    blockers = []
    if not _reviewers_are_users(environment):
        blockers.append(f"{name} environment has a malformed or non-user reviewer.")
    expected_ids = {reviewer_id} if gated else set()
    if environment_reviewer_ids(environment) != expected_ids:
        blockers.append(f"{name} environment has the wrong required reviewers.")
    if gated and not environment_prevents_self_review(environment):
        blockers.append(f"{name} environment must prevent self-review.")
    return blockers


def environment_blockers(
    name: str, environment: Mapping[str, Any] | None, reviewer_id: int
) -> list[str]:
    """Return the differences between a readback environment and the definition."""
    if environment is None:
        return [f"{name} environment was not readable."]
    allowed = {"branch_policy"}
    if name in PROTECTED_ENVIRONMENTS:
        allowed.add("required_reviewers")
    if not _protection_rules_ok(environment.get("protection_rules", []), allowed):
        return [f"{name} environment has an unknown or malformed protection rule."]
    blockers = []
    if not environment_is_main_only(environment):
        blockers.append(f"{name} environment must allow only the main branch.")
    if environment.get("can_admins_bypass") is not False:
        blockers.append(f"{name} environment must disable administrator bypass.")
    wait = environment.get("wait_timer", 0)
    if type(wait) is not int or wait != 0:
        blockers.append(f"{name} environment must not have a wait timer.")
    return [*blockers, *_reviewer_blockers(name, environment, reviewer_id)]


def variable_blockers(
    name: str, expected: Mapping[str, str], actual: Mapping[str, str] | None
) -> list[str]:
    """Return the differences between readback variables and the definition."""
    if actual is None:
        return [f"{name} variables were not readable."]
    blockers = []
    for variable, value in expected.items():
        if variable not in actual:
            blockers.append(f"{name} variable {variable} is missing.")
        elif actual[variable] != value:
            blockers.append(f"{name} variable {variable} has the wrong value.")
    blockers += [
        f"{name} has the unexpected variable {variable}."
        for variable in actual
        if variable not in expected
    ]
    return blockers


def entry_count_blockers(name: str, count: int | None) -> list[str]:
    """D-A10 and NFR-A01: no environment holds any secret.

    Takes a count, never names, so the report cannot echo a secret name.
    """
    if type(count) is not int or count < 0:
        return [f"{name} environment secrets were not readable."]
    if count:
        return [f"{name} has {count} environment secret(s); expected none."]
    return []


def readback_blockers(
    readback: Mapping[str, Any],
    reviewer_id: int,
    variables: Mapping[str, Mapping[str, str]],
) -> list[str]:
    """Diff a full readback (ruleset, environments, variables) against the plan."""
    environments = readback.get("environments")
    actual_variables = readback.get("variables")
    entry_counts = readback.get("secrets")
    if (
        not isinstance(environments, Mapping)
        or not isinstance(actual_variables, Mapping)
        or not isinstance(entry_counts, Mapping)
    ):
        return ["Readback must hold environments, variables and secrets objects."]
    blockers = ruleset_blockers(readback.get("ruleset"))
    for name in ENVIRONMENTS:
        blockers += environment_blockers(name, environments.get(name), reviewer_id)
        blockers += variable_blockers(name, variables[name], actual_variables.get(name))
        blockers += entry_count_blockers(name, entry_counts.get(name))
    blockers += [
        f"Readback holds the unexpected environment {name}."
        for name in sorted(
            {*environments, *actual_variables, *entry_counts} - set(ENVIRONMENTS)
        )
    ]
    return blockers
