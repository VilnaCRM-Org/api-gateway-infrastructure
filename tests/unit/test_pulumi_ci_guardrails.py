"""Destructive Diff Gate and IAM Gate (G3.3, AD-A10, FR-A11).

P: a create-only plan passes both gates. N: a `delete`, a `replace` and a
`delete-replaced` of a critical type fail the destructive gate; any
`aws:iam/*` resource fails the IAM gate. E: a Deployment replace passes only
as create-before-delete with the stage moved in the same plan.

The `tests/fixtures/previews/*.json` documents are trimmed from real
offline `pulumi preview --json` runs (pulumi 3.223.0, pulumi-aws 7.23.0;
G3.3 evidence), so the step order and field names are the engine's.
"""

from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path

import pytest

import pulumi_ci_guardrails as gr

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "previews"
P = "urn:pulumi:ci::api-gateway-infrastructure::"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def step(op: str, type_: str, name: str = "r", **extra) -> dict:
    state = {"type": type_}
    key = "oldState" if op in {"delete", "delete-replaced"} else "newState"
    return {"op": op, "urn": f"{P}{type_}::{name}", key: state, **extra}


def write(tmp_path: Path, document: object, name: str = "ci.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def destructive(document: dict) -> list[dict]:
    return gr.find_destructive_steps(gr.preview_steps(document))


# --- P ------------------------------------------------------------------------------

CI_CREATE_ONLY = {
    "steps": [step("create", "pulumi:pulumi:Stack", "api-gateway-infrastructure-ci")],
    "changeSummary": {"create": 1},
}


@pytest.mark.parametrize("document", [CI_CREATE_ONLY, fixture("front-door-create")])
def test_p_create_only_plan_passes_both_gates(document: dict, tmp_path: Path) -> None:
    path = write(tmp_path, document)
    assert gr.cli(["destructive-gate", str(path)]) == 0
    assert gr.cli(["iam-gate", str(path)]) == 0


# --- N: destructive gate ------------------------------------------------------------

AD_A10_EXTENSIONS = (
    "aws:apigateway/restApi:RestApi",
    "aws:apigateway/stage:Stage",
    "aws:apigateway/deployment:Deployment",
    "aws:apigateway/domainName:DomainName",
    "aws:apigateway/basePathMapping:BasePathMapping",
    "aws:apigatewayv2/vpcLink:VpcLink",
    "aws:wafv2/webAcl:WebAcl",
    "aws:wafv2/webAclAssociation:WebAclAssociation",
    "aws:acm/certificate:Certificate",
    "aws:acm/certificateValidation:CertificateValidation",
    "aws:cloudwatch/logGroup:LogGroup",
    "aws:route53/record:Record",
    "aws:kms/key:Key",
)


@pytest.mark.parametrize("op", sorted(gr.DESTRUCTIVE_OPS))
@pytest.mark.parametrize("type_", AD_A10_EXTENSIONS)
def test_n_destructive_op_on_a_critical_type_fails(
    op: str, type_: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, {"steps": [step(op, type_)]})
    assert gr.cli(["destructive-gate", str(path)]) == 1
    assert f"destructive change blocked: {op} {type_}" in capsys.readouterr().err


def test_critical_patterns_are_the_ported_list_plus_ad_a10() -> None:
    assert gr.CRITICAL_TYPE_PATTERNS[-5:] == (
        "aws:apigateway/",
        "aws:apigatewayv2/",
        "aws:wafv2/",
        "aws:acm/",
        "aws:cloudwatch/logGroup",
    )
    assert {"aws:route53/", "aws:kms/", "aws:iam/"} <= set(gr.CRITICAL_TYPE_PATTERNS)
    assert gr.DESTRUCTIVE_OPS == {"delete", "replace", "delete-replaced"}


@pytest.mark.parametrize(
    "op", ["create", "update", "same", "create-replacement", "read", "refresh"]
)
def test_non_destructive_ops_pass(op: str) -> None:
    assert destructive({"steps": [step(op, "aws:apigateway/restApi:RestApi")]}) == []


def test_destructive_op_on_a_non_critical_type_passes() -> None:
    """AD-A10 keeps the ported scope: only critical types are blocked."""
    plan = {"steps": [step("delete", "aws:sns/topic:Topic")]}
    assert destructive(plan) == []


def test_there_is_no_label_override(tmp_path: Path) -> None:
    event = write(tmp_path, {"pull_request": {"labels": [{"name": "allow"}]}}, "e.json")
    plan = write(tmp_path, {"steps": [step("delete", "aws:acm/certificate:X")]})
    with pytest.raises(SystemExit):
        gr.cli(["destructive-gate", str(plan), "--event-path", str(event)])
    assert gr.cli(["destructive-gate", str(plan)]) == 1


# --- E: the Deployment allowance ------------------------------------------------------

CBD = fixture("deployment-replace-cbd")
DEPLOYMENT_URN = next(
    s["urn"] for s in CBD["steps"] if s["urn"].endswith(gr.DEPLOYMENT_TYPE + "::dep")
)


def test_e_real_create_before_delete_replace_with_stage_moved_passes(
    tmp_path: Path,
) -> None:
    ops = [(s["op"], s["urn"].rsplit("::", 1)[1]) for s in CBD["steps"]]
    assert ops[2:] == [
        ("create-replacement", "dep"),
        ("replace", "dep"),
        ("update", "st"),
        ("delete-replaced", "dep"),
    ]
    assert gr.allowed_deployment_replacements(CBD["steps"]) == {DEPLOYMENT_URN}
    assert gr.cli(["destructive-gate", str(write(tmp_path, CBD))]) == 0


@pytest.mark.parametrize(
    "name", ["deployment-replace-dbr", "deployment-replace-collapsed"]
)
def test_e_real_delete_before_replace_or_unordered_replace_fails(
    name: str, tmp_path: Path
) -> None:
    """Delete-before-replace, or a plan without the replacement steps."""
    assert gr.cli(["destructive-gate", str(write(tmp_path, fixture(name)))]) == 1


def cbd_steps() -> list[dict]:
    return copy.deepcopy(CBD["steps"])


def stage_step(steps: list[dict]) -> dict:
    return next(s for s in steps if s["urn"].endswith("Stage::st"))


def dep_steps(steps: list[dict]) -> list[dict]:
    return [s for s in steps if s["urn"] == DEPLOYMENT_URN]


def no_stage(steps):
    return [s for s in steps if s is not stage_step(steps)]


def stage_after_delete(steps):
    stage = stage_step(steps)
    rest = [s for s in steps if s is not stage]
    return rest + [stage]


def stage_same_deployment(steps):
    stage_step(steps)["newState"]["inputs"]["deployment"] = "olddep1"
    return steps


def stage_replaced(steps):
    stage_step(steps)["op"] = "replace"
    return steps


def stage_without_diff(steps):
    stage = stage_step(steps)
    stage["diffReasons"] = []
    stage["detailedDiff"] = {}
    return steps


def stage_on_other_deployment(steps):
    stage_step(steps)["oldState"]["inputs"]["deployment"] = "otherdep"
    return steps


def replace_not_marked_for_delete(steps):
    dep_steps(steps)[1]["oldState"].pop("delete")
    return steps


def mismatched_old_ids(steps):
    dep_steps(steps)[2]["oldState"]["id"] = "different"
    return steps


def no_old_id(steps):
    for item in dep_steps(steps):
        item.get("oldState", {}).pop("id", None)
    return steps


def extra_delete(steps):
    return steps + [copy.deepcopy(dep_steps(steps)[2])]


def second_stage_stays(steps):
    """Another stage (shown by --show-sames) stays on the old deployment."""
    stage = copy.deepcopy(stage_step(steps))
    stage["urn"] += "2"
    stage["op"] = "same"
    stage["newState"]["inputs"]["deployment"] = "olddep1"
    return steps + [stage]


@pytest.mark.parametrize(
    "mutate",
    [
        no_stage,
        stage_after_delete,
        stage_same_deployment,
        stage_replaced,
        stage_without_diff,
        stage_on_other_deployment,
        replace_not_marked_for_delete,
        mismatched_old_ids,
        no_old_id,
        extra_delete,
        second_stage_stays,
    ],
)
def test_e_deployment_replace_without_every_condition_fails(mutate) -> None:
    steps = mutate(cbd_steps())
    assert gr.allowed_deployment_replacements(steps) == set()
    assert [s["op"] for s in gr.find_destructive_steps(steps)]


def test_e_stage_moved_through_detailed_diff_only_passes() -> None:
    steps = cbd_steps()
    stage_step(steps)["diffReasons"] = None
    assert gr.allowed_deployment_replacements(steps) == {DEPLOYMENT_URN}


def test_e_allowance_is_only_for_the_deployment_type() -> None:
    """The same create-before-delete shape on a Stage is still blocked."""
    steps = cbd_steps()
    for item in dep_steps(steps):
        for key in ("oldState", "newState"):
            if key in item:
                item[key]["type"] = "aws:apigateway/stage:Stage"
    assert gr.find_destructive_steps(steps)


def test_e_allowance_covers_only_the_moved_deployment() -> None:
    """A second replaced deployment that no stage leaves is still blocked."""
    other = [dict(copy.deepcopy(s), urn=s["urn"] + "2") for s in dep_steps(cbd_steps())]
    for item in other:
        item["oldState"]["id"] = "olddep2"
    steps = cbd_steps() + other
    found = gr.find_destructive_steps(steps)
    assert {s["urn"] for s in found} == {DEPLOYMENT_URN + "2"}


# --- N: IAM gate ----------------------------------------------------------------------


def test_n_real_iam_role_fails_the_iam_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, fixture("iam-role-create"))
    assert gr.cli(["iam-gate", str(path)]) == 1
    assert "IAM resource blocked: create aws:iam/role:Role" in capsys.readouterr().err


@pytest.mark.parametrize("op", ["create", "same", "update", "delete", "replace"])
@pytest.mark.parametrize(
    "type_",
    [
        "aws:iam/role:Role",
        "aws:iam/policy:Policy",
        "aws:iam/rolePolicyAttachment:RolePolicyAttachment",
    ],
)
def test_n_any_iam_resource_in_any_op_fails(op: str, type_: str) -> None:
    assert gr.find_iam_steps([step(op, type_)])


def test_non_iam_types_pass_the_iam_gate() -> None:
    plan = fixture("front-door-create")["steps"]
    assert gr.find_iam_steps(plan) == []
    assert gr.find_iam_steps([step("create", "aws:ssm/parameter:Parameter")]) == []


# --- helpers and CLI ------------------------------------------------------------------


def test_step_resource_type_sources() -> None:
    assert gr.step_resource_type({"oldState": {"type": "aws:kms/key:Key"}}) == (
        "aws:kms/key:Key"
    )
    urn = f"{P}pulumi:pulumi:Stack$aws:iam/role:Role::r"
    assert gr.step_resource_type({"urn": urn}) == "aws:iam/role:Role"
    assert gr.step_resource_type({"urn": "bad"}) == ""
    assert gr.step_resource_type({"newState": "x", "urn": None}) == ""


def test_summarize(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    blocked = {
        "steps": [step("delete", "aws:wafv2/webAcl:WebAcl")] + cbd_steps(),
        "changeSummary": {"delete": 1, "replace": 1},
    }
    paths = [
        write(tmp_path, blocked, "a.json"),
        write(tmp_path, {"steps": []}, "b.json"),
        write(tmp_path, {"steps": []}, "iam-inputs.json"),
    ]
    assert gr.cli(["summarize", *map(str, paths)]) == 0
    out = capsys.readouterr().out
    assert "### Pulumi Preview: a" in out
    assert "| delete | 1 |" in out
    assert "Destructive-step count: `1`" in out
    assert "- `delete` `aws:wafv2/webAcl:WebAcl`" in out
    assert f"- `{DEPLOYMENT_URN}`" in out
    assert "### Pulumi Preview: b" in out and "| none | 0 |" in out
    assert "IAM resource count: `0`" in out
    assert "iam-inputs" not in out
    assert gr.summarize_preview(paths[0], stack="ci").startswith(
        "### Pulumi Preview: ci"
    )


@pytest.mark.parametrize(
    "document",
    [[], {"changeSummary": {}}, {"steps": "x"}, {"steps": [1]}],
)
def test_malformed_previews_fail_closed(document: object, tmp_path: Path) -> None:
    path = write(tmp_path, document)
    for command in ("destructive-gate", "iam-gate", "summarize"):
        assert gr.cli([command, str(path)]) == 1


def test_missing_or_only_generated_files_fail(tmp_path: Path) -> None:
    assert gr.cli(["iam-gate", str(tmp_path / "missing.json")]) == 1
    helper = write(tmp_path, {"steps": []}, "iam-inputs.json")
    assert gr.cli(["destructive-gate", str(helper)]) == 1


def test_main_runs_the_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write(tmp_path, CI_CREATE_ONLY)
    monkeypatch.setattr("sys.argv", ["pulumi_ci_guardrails.py", "iam-gate", str(path)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(gr.__file__, run_name="__main__")
    assert raised.value.code == 0


def test_allowance_helpers_fail_closed_on_odd_states() -> None:
    assert gr._state_value({"oldState": "x"}, "oldState", "inputs") is None
    assert gr._changed_keys({"diffReasons": ["a"], "detailedDiff": None}) == {"a"}
    assert gr._old_deployment_id([{"oldState": {"id": ""}}]) is None
    assert gr._old_deployment_id([{"oldState": {"id": 7}}]) is None
    assert gr._old_deployment_id([]) is None


def test_e_real_replace_with_show_sames_passes(tmp_path: Path) -> None:
    """`--show-sames` (as the Structural Preview runs) lists unchanged
    resources with their inputs; the moved stage still allows the replace."""
    plan = fixture("deployment-replace-cbd-sames")
    sames = [
        s
        for s in plan["steps"]
        if s["op"] == "same" and gr.step_resource_type(s).startswith("aws:")
    ]
    assert sames and all("inputs" in s["newState"] for s in sames)
    assert gr.cli(["destructive-gate", str(write(tmp_path, plan))]) == 0
