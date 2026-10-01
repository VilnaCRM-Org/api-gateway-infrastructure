"""The CrossGuard adapter of the pack (`policy/pack.py`, `policy/__main__.py`).

It hands the AD-A10 rules plain properties, with every value the preview
cannot know as `UNKNOWN`, so CrossGuard's unknown-value error can never turn
a mandatory rule into an advisory skip; and it registers every rule as a
mandatory policy of the `api-gateway-guardrails` pack.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest
from pulumi_policy import (
    EnforcementLevel,
    PolicyCustomTimeouts,
    PolicyResource,
    PolicyResourceOptions,
    ResourceValidationArgs,
    ResourceValidationPolicy,
    StackValidationArgs,
    StackValidationPolicy,
)
from pulumi_policy.proxy import (
    UNKNOWN_BOOLEAN_VALUE,
    UNKNOWN_NUMBER_VALUE,
    UNKNOWN_STRING_VALUE,
    unknown_checking_proxy,
)

from policy import guardrails, pack

ROOT = Path(__file__).resolve().parents[2]
URN = "urn:pulumi:ci::api-gateway-infrastructure::aws:apigateway/restApi:RestApi::api"


def options() -> PolicyResourceOptions:
    return PolicyResourceOptions(
        False, [], None, [], PolicyCustomTimeouts(0, 0, 0), [], None
    )


def policy_resource(urn, type_, props, deps=None) -> PolicyResource:
    return PolicyResource(
        type_,
        unknown_checking_proxy(props),
        urn,
        urn.rsplit("::", 1)[-1],
        options(),
        None,
        None,
        [],
        deps or {},
    )


def test_plain_replaces_unknowns_at_every_depth() -> None:
    proxied = unknown_checking_proxy(
        {
            "a": UNKNOWN_STRING_VALUE,
            "b": {"c": [1.0, UNKNOWN_NUMBER_VALUE], "d": UNKNOWN_BOOLEAN_VALUE},
            "s": "text",
            "n": None,
        }
    )
    assert pack.plain(proxied) == {
        "a": guardrails.UNKNOWN,
        "b": {"c": [1.0, guardrails.UNKNOWN], "d": guardrails.UNKNOWN},
        "s": "text",
        "n": None,
    }


def test_resource_policy_reports_on_unknown_literal() -> None:
    """An unknown `disableExecuteApiEndpoint` is a violation, not a skip."""
    reports = []
    validate = pack.resource_policy(guardrails.rest_api_violations)
    args = ResourceValidationArgs(
        guardrails.REST_API,
        unknown_checking_proxy({"disableExecuteApiEndpoint": UNKNOWN_BOOLEAN_VALUE}),
        URN,
        "api",
        options(),
        None,
    )
    validate(args, lambda message, urn=None: reports.append((message, urn)))
    assert reports == [
        ("A REST API must set disable_execute_api_endpoint to true.", None)
    ]


def test_resource_policy_is_silent_when_compliant() -> None:
    reports = []
    args = ResourceValidationArgs(
        guardrails.REST_API,
        unknown_checking_proxy({"disableExecuteApiEndpoint": True}),
        URN,
        "api",
        options(),
        None,
    )
    pack.resource_policy(guardrails.rest_api_violations)(
        args, lambda message, urn=None: reports.append(message)
    )
    assert reports == []


def test_stack_policy_reports_at_the_resource_urn() -> None:
    stage_urn = URN.replace("restApi:RestApi::api", "stage:Stage::live")
    stage = policy_resource(
        stage_urn,
        guardrails.STAGE,
        {"stageName": "live", "accessLogSettings": {"destinationArn": ""}},
    )
    reports = []
    validate = pack.stack_policy(guardrails.stage_access_log_findings)
    validate(
        StackValidationArgs([stage]),
        lambda message, urn=None: reports.append((message, urn)),
    )
    assert reports == [("A stage must set an access-log destination.", stage_urn)]


def test_stack_resource_keeps_property_dependencies() -> None:
    api = policy_resource(URN, guardrails.REST_API, {"id": UNKNOWN_STRING_VALUE})
    stage_urn = URN.replace("restApi:RestApi::api", "stage:Stage::live")
    stage = policy_resource(
        stage_urn,
        guardrails.STAGE,
        {"restApi": UNKNOWN_STRING_VALUE},
        {"restApi": [api]},
    )
    converted = pack.stack_resource(stage)
    assert converted == guardrails.Resource(
        stage_urn,
        guardrails.STAGE,
        {"restApi": guardrails.UNKNOWN},
        {"restApi": frozenset({URN})},
    )


def test_every_rule_is_a_mandatory_policy() -> None:
    built = pack.build_policies()
    resource_rules = [p for p in built if isinstance(p, ResourceValidationPolicy)]
    stack_rules = [p for p in built if isinstance(p, StackValidationPolicy)]
    assert [p.name for p in resource_rules] == [
        name for name, _, _ in guardrails.RESOURCE_RULES
    ]
    assert [p.name for p in stack_rules] == [
        name for name, _, _ in guardrails.STACK_RULES
    ]
    assert {p.enforcement_level for p in built} == {EnforcementLevel.MANDATORY}


class Recorder:
    calls: list[dict] = []

    def __init__(self, **kwargs) -> None:
        Recorder.calls.append(kwargs)


def test_serve_starts_the_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    Recorder.calls = []
    monkeypatch.setattr(pack, "PolicyPack", Recorder)
    pack.serve()
    (call,) = Recorder.calls
    assert call["name"] == pack.POLICY_PACK_NAME == "api-gateway-guardrails"
    assert call["enforcement_level"] == EnforcementLevel.MANDATORY
    assert len(call["policies"]) == len(guardrails.RESOURCE_RULES) + len(
        guardrails.STACK_RULES
    )


def test_engine_entry_point_serves_the_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    """`policy/__main__.py` puts the repository root on sys.path and serves."""
    Recorder.calls = []
    monkeypatch.setattr(pack, "PolicyPack", Recorder)
    monkeypatch.setattr("sys.path", list(__import__("sys").path))
    runpy.run_path(str(ROOT / "policy" / "__main__.py"), run_name="__main__")
    assert len(Recorder.calls) == 1
    assert __import__("sys").path[0] == str(ROOT)


def test_pack_manifest_runs_on_the_image_python() -> None:
    manifest = (ROOT / "policy" / "PulumiPolicy.yaml").read_text(encoding="utf-8")
    assert "runtime: python" in manifest
    assert "virtualenv" not in manifest
