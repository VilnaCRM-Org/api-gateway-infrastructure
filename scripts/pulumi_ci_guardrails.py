"""Pulumi preview summaries, the destructive-diff gate and the IAM gate (G3.3).

Ported from the BI/USI `scripts/pulumi_ci_guardrails.py` (AD-A10, AD-A11,
FR-A11) and adapted to the gateway:

- the destructive gate blocks `delete`, `replace` and `delete-replaced` of a
  critical type. `CRITICAL_TYPE_PATTERNS` adds `aws:apigateway/`,
  `aws:apigatewayv2/`, `aws:wafv2/`, `aws:acm/` and `aws:cloudwatch/logGroup`
  to the ported list. There is one allowance and no label override: an
  `aws:apigateway/deployment:Deployment` may be replaced when the replacement
  is create-before-delete and the stage that used the old deployment moves to
  the new one in the same plan;
- the IAM gate fails on any `aws:iam/*` resource in the plan. This repository
  declares no IAM (architecture section 4), so the ported Access Analyzer
  validation, which needs AWS credentials, is not ported;
- the ported cost proxy is not ported: AD-A10 names no cost gate.

Every command reads `pulumi preview --json` documents, so it needs neither
credentials nor network.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DESTRUCTIVE_OPS = frozenset({"delete", "replace", "delete-replaced"})
CRITICAL_TYPE_PATTERNS = (
    # Ported unchanged from BI/USI.
    "aws:ec2/vpc:",
    "aws:ec2/internetGateway:",
    "aws:ec2/natGateway:",
    "aws:ec2/routeTable:",
    "aws:iam/",
    "aws:kms/",
    "aws:s3/bucket:Bucket",
    "aws:cloudtrail/trail:Trail",
    "aws:rds/",
    "aws:secretsmanager/",
    "aws:route53/",
    "aws:eks/",
    # AD-A10 extensions for the gateway.
    "aws:apigateway/",
    "aws:apigatewayv2/",
    "aws:wafv2/",
    "aws:acm/",
    "aws:cloudwatch/logGroup",
)
IAM_TYPE_PREFIX = "aws:iam/"
DEPLOYMENT_TYPE = "aws:apigateway/deployment:Deployment"
STAGE_TYPE = "aws:apigateway/stage:Stage"
# The steps of a create-before-delete replacement in `pulumi preview --json
# --show-replacement-steps` (pulumi 3.223.0): the new deployment is created,
# the resource is replaced, and the old one is deleted last, after every
# other step; its `replace` step marks the old state `delete: true`. A
# delete-before-replace replacement lists `delete-replaced` first.
CREATE_BEFORE_DELETE_OPS = ("create-replacement", "replace", "delete-replaced")
# The pulumi-aws 7.23.0 Stage input that names its deployment.
STAGE_DEPLOYMENT_KEY = "deployment"
GENERATED_PREVIEW_ARTIFACT_NAMES = frozenset({"iam-inputs.json"})
COUNT_TABLE_SEPARATOR = "| --- | ---: |"


def load_preview(path: Path) -> dict[str, Any]:
    """Load a Pulumi JSON preview artifact from disk."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise ValueError(f"{path} must contain a JSON object preview artifact.")


def preview_input_files(paths: Sequence[Path]) -> list[Path]:
    """Return Pulumi preview artifacts, excluding generated helper JSON files."""
    return [path for path in paths if path.name not in GENERATED_PREVIEW_ARTIFACT_NAMES]


def preview_steps(preview: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the preview steps; a document without a step list fails closed."""
    steps = preview.get("steps")
    if not isinstance(steps, list) or not all(isinstance(s, dict) for s in steps):
        raise ValueError("The preview has no 'steps' list of step objects.")
    return steps


def step_resource_type(step: Mapping[str, Any]) -> str:
    """Return the best available resource type for a preview step."""
    for key in ("newState", "oldState"):
        state = step.get(key)
        if isinstance(state, dict) and isinstance(state.get("type"), str):
            return state["type"]
    urn = step.get("urn")
    if isinstance(urn, str) and urn.count("::") >= 3:
        return urn.split("::")[2].rsplit("$", 1)[-1]
    return ""


def _is_critical(resource_type: str) -> bool:
    return any(pattern in resource_type for pattern in CRITICAL_TYPE_PATTERNS)


def _state_value(step: Mapping[str, Any], state: str, *path: str) -> object:
    node: object = step.get(state)
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _changed_keys(step: Mapping[str, Any]) -> set[str]:
    keys = set(step.get("diffReasons") or [])
    detailed = step.get("detailedDiff")
    if isinstance(detailed, dict):
        keys.update(detailed)
    return keys


def _old_deployment_id(steps: Sequence[Mapping[str, Any]]) -> str | None:
    ids = {_state_value(step, "oldState", "id") for step in steps}
    ids.discard(None)
    if len(ids) == 1:
        (value,) = ids
        if isinstance(value, str) and value:
            return value
    return None


def _stage_moves(step: Mapping[str, Any], old_id: str) -> bool:
    """True when `step` updates a stage away from the deployment `old_id`."""
    if step.get("op") != "update" or step_resource_type(step) != STAGE_TYPE:
        return False
    old = _state_value(step, "oldState", "inputs", STAGE_DEPLOYMENT_KEY)
    new = _state_value(step, "newState", "inputs", STAGE_DEPLOYMENT_KEY)
    return (
        old == old_id and new != old_id and STAGE_DEPLOYMENT_KEY in _changed_keys(step)
    )


def _deployment_steps(
    steps: Sequence[Mapping[str, Any]],
) -> dict[str, list[tuple[int, Mapping[str, Any]]]]:
    """Each Deployment URN's (index, step) pairs, in plan order."""
    by_urn: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for index, step in enumerate(steps):
        if step_resource_type(step) == DEPLOYMENT_TYPE:
            by_urn.setdefault(str(step.get("urn", "")), []).append((index, step))
    return by_urn


def _create_before_delete(
    indexed: Sequence[tuple[int, Mapping[str, Any]]],
) -> tuple[str, int] | None:
    """(old id, index of `delete-replaced`) of a create-before-delete replace."""
    if tuple(step.get("op") for _, step in indexed) != CREATE_BEFORE_DELETE_OPS:
        return None
    if _state_value(indexed[1][1], "oldState", "delete") is not True:
        return None
    old_id = _old_deployment_id([step for _, step in indexed[1:]])
    return None if old_id is None else (old_id, indexed[-1][0])


def allowed_deployment_replacements(steps: Sequence[Mapping[str, Any]]) -> set[str]:
    """URNs of Deployment replacements that pass the AD-A10 allowance.

    A replacement passes only when its steps are exactly
    `create-replacement`, `replace`, `delete-replaced` in that order (create
    before delete), the `replace` step marks the old state for a later
    delete, and a stage that used the old deployment is updated to a new
    deployment in the same plan, before the old deployment is deleted.
    """
    allowed: set[str] = set()
    for urn, indexed in _deployment_steps(steps).items():
        replacement = _create_before_delete(indexed)
        if replacement is None:
            continue
        old_id, delete_index = replacement
        if any(_stage_moves(step, old_id) for step in steps[:delete_index]):
            allowed.add(urn)
    return allowed


def find_destructive_steps(steps: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return destructive steps on critical types, minus the one allowance."""
    allowed = allowed_deployment_replacements(steps)
    return [
        step
        for step in steps
        if step.get("op") in DESTRUCTIVE_OPS
        and _is_critical(step_resource_type(step))
        and str(step.get("urn", "")) not in allowed
    ]


def find_iam_steps(steps: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every step, of any operation, on an `aws:iam/*` resource."""
    return [
        step for step in steps if step_resource_type(step).startswith(IAM_TYPE_PREFIX)
    ]


def summarize_preview(path: Path, *, stack: str | None = None) -> str:
    """Render a compact Markdown summary for a preview artifact."""
    preview = load_preview(path)
    steps = preview_steps(preview)
    summary = preview.get("changeSummary", {})
    lines = [
        f"### Pulumi Preview: {stack or path.stem}",
        "",
        "| Operation | Count |",
        COUNT_TABLE_SEPARATOR,
    ]
    if isinstance(summary, dict) and summary:
        for operation in sorted(summary):
            lines.append(f"| {operation} | {summary[operation]} |")
    else:
        lines.append("| none | 0 |")

    destructive = find_destructive_steps(steps)
    lines.extend(["", f"Destructive-step count: `{len(destructive)}`"])
    if destructive:
        lines.extend(["", "Critical destructive candidates:"])
        for step in destructive:
            lines.append(f"- `{step.get('op')}` `{step_resource_type(step)}`")
    allowed = sorted(allowed_deployment_replacements(steps))
    if allowed:
        lines.extend(["", "Allowed create-before-delete Deployment replacements:"])
        lines.extend(f"- `{urn}`" for urn in allowed)
    lines.extend(["", f"IAM resource count: `{len(find_iam_steps(steps))}`", ""])
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    """Construct the CLI parser for the guardrail helper entrypoints."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("summarize", "destructive-gate", "iam-gate"):
        subparsers.add_parser(name).add_argument("preview_files", nargs="+", type=Path)
    return parser


def _run_summarize(preview_files: Sequence[Path]) -> int:
    """Print Markdown summaries for each preview artifact."""
    for preview_file in preview_input_files(preview_files):
        sys.stdout.write(summarize_preview(preview_file))
    return 0


def _report(findings: Sequence[str], kind: str, advice: str) -> int:
    if not findings:
        print(f"{kind}: no blocked change.")
        return 0
    for finding in findings:
        print(f"{kind} blocked: {finding}", file=sys.stderr)
    print(advice, file=sys.stderr)
    return 1


def _gate(preview_files: Sequence[Path], finder: Any) -> list[str]:
    files = preview_input_files(preview_files)
    if not files:
        raise ValueError("No Pulumi preview file was given.")
    findings: list[str] = []
    for preview_file in files:
        for step in finder(preview_steps(load_preview(preview_file))):
            findings.append(
                f"{step.get('op')} {step_resource_type(step)} {step.get('urn', '')}"
            )
    return findings


def _run_destructive_gate(preview_files: Sequence[Path]) -> int:
    """Reject critical destructive steps; there is no label override."""
    return _report(
        _gate(preview_files, find_destructive_steps),
        "destructive change",
        "Remove the critical destructive change from this plan.",
    )


def _run_iam_gate(preview_files: Sequence[Path]) -> int:
    """Reject any `aws:iam/*` resource; IAM belongs to BI (AD-A1, AD-A10)."""
    return _report(
        _gate(preview_files, find_iam_steps),
        "IAM resource",
        "This repository declares no IAM; identity changes go through BI.",
    )


def cli(argv: Sequence[str] | None = None) -> int:
    """Run the requested guardrail helper command."""
    args = _build_parser().parse_args(argv)
    commands = {
        "summarize": _run_summarize,
        "destructive-gate": _run_destructive_gate,
        "iam-gate": _run_iam_gate,
    }
    try:
        return commands[args.command](args.preview_files)
    except (OSError, ValueError) as error:
        print(f"{args.command}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
