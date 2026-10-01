#!/usr/bin/env python3
"""Print, apply or check the gateway's GitHub repository controls (FR-A07).

Default and `--dry-run` print the payloads and variable values without
touching GitHub (offline when `--reviewer-id` is given). `--apply` needs a
repository admin token and is the XP-A3 step. `--check` reads back the
ruleset, the six environments and their variables, and fails on any
difference from the definition; `--readback-file` diffs a saved readback
instead of calling GitHub.
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import _github_repository_controls as _controls
from _github_environment_controls import complete_branch_policies

REQUIRED_STATUS_CHECKS = _controls.REQUIRED_STATUS_CHECKS
ENVIRONMENTS = _controls.ENVIRONMENTS
DEFAULT_REVIEWER = "Kravalg"
MAIN_POLICY = {"name": "main", "type": "branch"}


def _run_gh_api(
    args: Sequence[str], *, input_payload: Mapping[str, Any] | None = None
) -> dict[str, Any] | list[Any]:
    """Run gh api and parse the JSON response."""
    command = ["gh", "api", *args]
    input_text = None
    if input_payload is not None:
        command.extend(["--input", "-"])
        input_text = json.dumps(input_payload)
    result = subprocess.run(command, input=input_text, capture_output=True, text=True)  # nosec B603
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "gh api failed"
        raise RuntimeError(detail)
    if not result.stdout.strip():
        return {}
    parsed = json.loads(result.stdout)
    if isinstance(parsed, (dict, list)):
        return parsed
    return {}


def _main_ruleset(repo: str) -> dict[str, Any] | None:
    """Return the full main ruleset when it exists."""
    rulesets = _run_gh_api([f"repos/{repo}/rulesets"])
    if not isinstance(rulesets, list):
        return None
    for ruleset in rulesets:
        if not isinstance(ruleset, Mapping):
            continue
        if ruleset.get("name") == "main" and ruleset.get("target") == "branch":
            ruleset_id = ruleset.get("id")
            if isinstance(ruleset_id, int):
                full_ruleset = _run_gh_api([f"repos/{repo}/rulesets/{ruleset_id}"])
                return dict(full_ruleset) if isinstance(full_ruleset, Mapping) else None
    return None


def _github_user_id(login: str) -> int:
    """Resolve a GitHub login to a numeric user id."""
    user = _run_gh_api([f"users/{login}"])
    if isinstance(user, Mapping) and isinstance(user.get("id"), int):
        return user["id"]
    raise ValueError(f"Could not resolve GitHub user id for {login!r}.")


def _repo_admin_allowed(repo: str) -> bool:
    """Return whether the current gh token can administer the repository."""
    payload = _run_gh_api([f"repos/{repo}"])
    if not isinstance(payload, Mapping):
        return False
    permissions = payload.get("permissions")
    return isinstance(permissions, Mapping) and permissions.get("admin") is True


def _read_environment(repo: str, name: str) -> dict[str, Any] | None:
    """Read one environment with its complete branch policies, or None."""
    endpoint = f"repos/{repo}/environments/{name}"
    try:
        environment = _run_gh_api([endpoint])
        policies = _run_gh_api([f"{endpoint}/deployment-branch-policies"])
    except RuntimeError:
        return None
    if not isinstance(environment, Mapping):
        return None
    return {
        **environment,
        "deployment_branch_policies": complete_branch_policies(policies),
    }


def _listing_rows(response: object, key: str) -> list[Mapping[str, Any]] | None:
    """Return the rows of a complete page of a GitHub listing, else None."""
    if not isinstance(response, Mapping):
        return None
    rows = response.get(key)
    count = response.get("total_count")
    if not isinstance(rows, list) or type(count) is not int or count != len(rows):
        return None
    if not all(isinstance(row, Mapping) for row in rows):
        return None
    return rows


def _read_variables(repo: str, name: str) -> dict[str, str] | None:
    """Read one environment's complete variable list as name to value."""
    try:
        response = _run_gh_api(
            [f"repos/{repo}/environments/{name}/variables?per_page=100"]
        )
    except RuntimeError:
        return None
    rows = _listing_rows(response, "variables")
    if rows is None:
        return None
    variables = {str(row.get("name")): row.get("value") for row in rows}
    if len(variables) != len(rows) or not all(
        isinstance(value, str) for value in variables.values()
    ):
        return None
    return {name: str(value) for name, value in variables.items()}


def _read_secret_names(repo: str, name: str) -> list[str] | None:
    """Read one environment's secret names (metadata only, never values)."""
    try:
        response = _run_gh_api(
            [f"repos/{repo}/environments/{name}/secrets?per_page=100"]
        )
    except RuntimeError:
        return None
    rows = _listing_rows(response, "secrets")
    names = [row.get("name") for row in rows or []]
    if rows is None or not all(isinstance(n, str) for n in names):
        return None
    return [str(n) for n in names]


def read_live(repo: str) -> dict[str, Any]:
    """Read the ruleset, every environment and its variables from GitHub."""
    return {
        "ruleset": _main_ruleset(repo),
        "environments": {n: _read_environment(repo, n) for n in ENVIRONMENTS},
        "variables": {n: _read_variables(repo, n) for n in ENVIRONMENTS},
        "secrets": {n: _read_secret_names(repo, n) for n in ENVIRONMENTS},
    }


def _validated_branch_policies(response: object) -> list[dict[str, Any]]:
    """Validate the whole listing before any policy mutation."""
    policies = complete_branch_policies(response)
    if policies is None:
        raise ValueError("Environment branch-policy listing is incomplete.")
    result = [dict(p) for p in policies if isinstance(p, Mapping)]
    ids = [p.get("id") for p in result]
    if len(result) != len(policies) or not all(type(i) is int and i > 0 for i in ids):
        raise ValueError("Environment branch-policy records are malformed.")
    if len(set(ids)) != len(ids):
        raise ValueError("Environment branch-policy ids must be unique.")
    return sorted(result, key=lambda policy: policy["id"])


def _configure_main_branch_policy(endpoint: str) -> None:
    """Converge validated policies to one main rule, keeping its smallest ID."""
    policies = _validated_branch_policies(
        _run_gh_api([f"{endpoint}/deployment-branch-policies"])
    )
    main_exists = False
    for policy in policies:
        if (
            not main_exists
            and policy.get("name") == "main"
            and (policy.get("type") == "branch")
        ):
            main_exists = True
        else:
            _run_gh_api(
                [
                    f"{endpoint}/deployment-branch-policies/{policy['id']}",
                    "--method",
                    "DELETE",
                ]
            )
    if not main_exists:
        _run_gh_api(
            [f"{endpoint}/deployment-branch-policies", "--method", "POST"],
            input_payload=MAIN_POLICY,
        )


def _apply_ruleset(repo: str, existing: Mapping[str, Any] | None) -> None:
    """Update the discovered ruleset or create one when none exists."""
    if existing and isinstance(existing.get("id"), int):
        endpoint, method = f"repos/{repo}/rulesets/{existing['id']}", "PUT"
    else:
        endpoint, method = f"repos/{repo}/rulesets", "POST"
    _run_gh_api(
        [endpoint, "--method", method], input_payload=_controls.ruleset_payload()
    )


def _apply_variables(repo: str, name: str, wanted: Mapping[str, str]) -> None:
    """Create or update each wanted variable; never delete another one."""
    existing = _read_variables(repo, name)
    if existing is None:
        raise RuntimeError(f"{name} variables were not readable before apply.")
    for variable, value in wanted.items():
        endpoint = f"repos/{repo}/environments/{name}/variables"
        if variable in existing:
            endpoint = f"{endpoint}/{variable}"
            method = "PATCH"
        else:
            method = "POST"
        _run_gh_api(
            [endpoint, "--method", method],
            input_payload={"name": variable, "value": value},
        )


def _reviewer_id(reviewer: str, reviewer_id: int | None) -> int:
    return reviewer_id if reviewer_id is not None else _github_user_id(reviewer)


def _dry_run_payloads(
    reviewer: str, reviewer_id: int, variables: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "branchPolicies": {name: [MAIN_POLICY] for name in ENVIRONMENTS},
        "environments": {
            name: _controls.environment_payload(name, reviewer_id)
            for name in ENVIRONMENTS
        },
        "reviewerLogin": reviewer,
        "ruleset": _controls.ruleset_payload(),
        "variables": variables,
    }


def _check_blockers(
    readback: Mapping[str, Any], reviewer_id: int, stack_dir: Path
) -> list[str]:
    return _controls.readback_blockers(
        readback, reviewer_id, _controls.environment_variables(stack_dir)
    )


def _guard_ruleset_replacement(
    existing: Mapping[str, Any] | None, *, replace: bool
) -> None:
    """G22-F03: refuse to overwrite a differing main ruleset without --replace."""
    if existing is None:
        return
    differences = _controls.ruleset_blockers(existing)
    if not differences:
        return
    print(
        "The existing main ruleset differs; apply would replace it:\n- "
        + "\n- ".join(differences),
        file=sys.stderr,
    )
    if not replace:
        raise RuntimeError(
            "refusing to replace the main ruleset; review the differences and "
            "pass --replace."
        )


def _apply_controls(
    repo: str,
    payloads: Mapping[str, Any],
    variables: Mapping[str, Mapping[str, str]],
    *,
    replace: bool,
) -> None:
    existing = _main_ruleset(repo)
    _guard_ruleset_replacement(existing, replace=replace)
    _apply_ruleset(repo, existing)
    for name in ENVIRONMENTS:
        endpoint = f"repos/{repo}/environments/{name}"
        _run_gh_api(
            [endpoint, "--method", "PUT"],
            input_payload=payloads["environments"][name],
        )
        _configure_main_branch_policy(endpoint)
        _apply_variables(repo, name, variables[name])


def configure(
    repo: str,
    reviewer: str,
    *,
    apply: bool,
    reviewer_id: int | None = None,
    replace: bool = False,
    stack_dir: Path = _controls.STACK_DIR,
) -> None:
    """Print the payloads, and with `apply` converge GitHub to them."""
    variables = _controls.environment_variables(stack_dir)
    if apply and not _repo_admin_allowed(repo):
        raise RuntimeError(
            "repository admin rights are required to update branch rulesets, "
            "protected environments and variables."
        )
    resolved = _reviewer_id(reviewer, reviewer_id)
    payloads = _dry_run_payloads(reviewer, resolved, variables)
    if apply:
        _apply_controls(repo, payloads, variables, replace=replace)
        blockers = _check_blockers(read_live(repo), resolved, stack_dir)
        if blockers:
            raise RuntimeError(" ".join(blockers))
        payloads["verified"] = True
    print(json.dumps(payloads, indent=2, sort_keys=True))


def check(
    repo: str,
    reviewer: str,
    *,
    reviewer_id: int | None = None,
    readback_file: Path | None = None,
    stack_dir: Path = _controls.STACK_DIR,
) -> list[str]:
    """Read back (live or from a file) and return every difference."""
    resolved = _reviewer_id(reviewer, reviewer_id)
    if readback_file is None:
        readback = read_live(repo)
    else:
        readback = json.loads(readback_file.read_text(encoding="utf-8"))
    if not isinstance(readback, Mapping):
        raise ValueError("Readback must be a JSON object.")
    return _check_blockers(readback, resolved, stack_dir)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Print, apply or check the gateway GitHub repository controls."
    )
    parser.add_argument("--repo", required=True, help="Repository in owner/name form.")
    parser.add_argument(
        "--prod-reviewer",
        default=DEFAULT_REVIEWER,
        help="GitHub login required to approve test and prod deployments.",
    )
    parser.add_argument(
        "--reviewer-id",
        type=int,
        help="Numeric id of the reviewer; skips the GitHub user lookup.",
    )
    parser.add_argument(
        "--readback-file",
        type=Path,
        help="With --check, diff this saved readback JSON instead of GitHub.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="With --apply, allow replacing a main ruleset that differs.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply with gh api.")
    mode.add_argument("--dry-run", action="store_true", help="Print the payloads.")
    mode.add_argument(
        "--check",
        action="store_true",
        help="Read back rulesets, environments and variables and diff them.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface."""
    args = build_parser().parse_args(argv)
    try:
        if args.readback_file is not None and not args.check:
            raise ValueError("--readback-file is only valid with --check.")
        if args.replace and not args.apply:
            raise ValueError("--replace is only valid with --apply.")
        if args.check:
            blockers = check(
                args.repo,
                args.prod_reviewer,
                reviewer_id=args.reviewer_id,
                readback_file=args.readback_file,
            )
            print(json.dumps({"check": {"differences": blockers}}, indent=2))
            return 1 if blockers else 0
        configure(
            args.repo,
            args.prod_reviewer,
            apply=args.apply,
            reviewer_id=args.reviewer_id,
            replace=args.replace,
        )
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
