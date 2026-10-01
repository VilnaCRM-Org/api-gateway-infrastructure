"""The AD-A10 CrossGuard pack (G3.3, FR-A11): rules over fixture graphs.

P: a compliant front door passes every rule. N: a stage without access
logs, an API without `disable_execute_api_endpoint`, a log group without a
key, a stage that a base path mapping references but no web ACL protects,
an `aws:ssm/*` resource, and each other AD-A10 rule broken once, fail.
E: a stage that no mapping references passes without a web ACL.

The graphs mirror what CrossGuard hands the pack during a real offline
preview (property names, float numbers, unknown outputs and property
dependencies as pulumi 3.223.0 / pulumi-aws 7.23.0 report them; G3.3
evidence `exp/out-text.txt`).
"""

from __future__ import annotations

import copy
from collections.abc import Callable

import pytest

from policy import guardrails as g
from policy.guardrails import UNKNOWN, Resource

P = "urn:pulumi:ci::api-gateway-infrastructure::"
API = P + "aws:apigateway/restApi:RestApi::api"
STAGE = P + "aws:apigateway/stage:Stage::live"
ACCESS = P + "aws:cloudwatch/logGroup:LogGroup::access"
WAF_LOGS = P + "aws:cloudwatch/logGroup:LogGroup::waf"
SETTINGS = P + "aws:apigateway/methodSettings:MethodSettings::all"
DOMAIN = P + "aws:apigateway/domainName:DomainName::domain"
MAPPING = P + "aws:apigateway/basePathMapping:BasePathMapping::root"
ACL = P + "aws:wafv2/webAcl:WebAcl::acl"
ASSOC = P + "aws:wafv2/webAclAssociation:WebAclAssociation::stage"
INTEGRATION = P + "aws:apigateway/integration:Integration::proxy"
LINK = P + "aws:apigatewayv2/vpcLink:VpcLink::link"
ALARM = P + "aws:cloudwatch/metricAlarm:MetricAlarm::5xx"
KEY = "arn:aws:kms:eu-central-1:111111111111:key/00000000-0000-0000-0000-000000000000"
ACCESS_NAME = "/aws/apigateway/api-gateway-infrastructure-ci/access"


def front_door() -> dict[str, Resource]:
    """A compliant front door, as a preview of its creation reports it."""
    items = [
        Resource(
            API,
            g.REST_API,
            {"disableExecuteApiEndpoint": True, "id": UNKNOWN},
        ),
        Resource(
            ACCESS,
            g.LOG_GROUP,
            {"name": ACCESS_NAME, "kmsKeyId": KEY, "retentionInDays": 30.0},
        ),
        Resource(
            WAF_LOGS,
            g.LOG_GROUP,
            {
                "name": "aws-waf-logs-api-gateway-infrastructure-ci",
                "kmsKeyId": KEY,
                "retentionInDays": 30.0,
            },
        ),
        Resource(
            STAGE,
            g.STAGE,
            {
                "stageName": "live",
                "restApi": UNKNOWN,
                "arn": UNKNOWN,
                "accessLogSettings": {"destinationArn": UNKNOWN, "format": "{}"},
            },
            {
                "restApi": frozenset({API}),
                "accessLogSettings": frozenset({ACCESS}),
            },
        ),
        Resource(
            SETTINGS,
            g.METHOD_SETTINGS,
            {
                "methodPath": "*/*",
                "stageName": "live",
                "restApi": UNKNOWN,
                "settings": {
                    "loggingLevel": "OFF",
                    "throttlingRateLimit": 50.0,
                    "throttlingBurstLimit": 100.0,
                    "dataTraceEnabled": UNKNOWN,
                },
            },
            {"stageName": frozenset({STAGE}), "restApi": frozenset({API})},
        ),
        Resource(
            DOMAIN,
            g.DOMAIN_NAME,
            {
                "securityPolicy": g.TLS_SECURITY_POLICY,
                "endpointAccessMode": "STRICT",
            },
        ),
        Resource(
            MAPPING,
            g.BASE_PATH_MAPPING,
            {"stageName": "live", "restApi": UNKNOWN, "basePath": None},
            {"stageName": frozenset({STAGE}), "restApi": frozenset({API})},
        ),
        Resource(ACL, "aws:wafv2/webAcl:WebAcl", {"scope": "REGIONAL"}),
        Resource(
            ASSOC,
            g.WEB_ACL_ASSOCIATION,
            {"resourceArn": UNKNOWN, "webAclArn": UNKNOWN},
            {"resourceArn": frozenset({STAGE}), "webAclArn": frozenset({ACL})},
        ),
        Resource(
            INTEGRATION,
            g.INTEGRATION,
            {
                "connectionType": "VPC_LINK",
                "connectionId": UNKNOWN,
                "tlsConfig": {"insecureSkipVerification": False},
            },
            {"connectionId": frozenset({LINK})},
        ),
        Resource(
            ALARM,
            "aws:cloudwatch/metricAlarm:MetricAlarm",
            {"tags": {"runbook": "docs/runbooks/5xx.md"}},
        ),
    ]
    return {item.urn: item for item in items}


def evaluate(graph: dict[str, Resource]) -> list[tuple[str, str, str]]:
    """Every (policy, urn, message) the pack's rules report for `graph`."""
    resources = list(graph.values())
    found = [
        (name, item.urn, message)
        for name, _, rule in g.RESOURCE_RULES
        for item in resources
        for message in rule(item)
    ]
    found += [
        (name, urn, message)
        for name, _, rule in g.STACK_RULES
        for urn, message in rule(resources)
    ]
    return found


def with_props(graph, urn, **props):
    item = graph[urn]
    merged = dict(copy.deepcopy(dict(item.props)), **props)
    graph[urn] = Resource(item.urn, item.type, merged, item.deps)
    return graph


def with_deps(graph, urn, **deps):
    item = graph[urn]
    merged = dict(item.deps, **{k: frozenset(v) for k, v in deps.items()})
    graph[urn] = Resource(item.urn, item.type, item.props, merged)
    return graph


def without(graph, *urns):
    for urn in urns:
        del graph[urn]
    return graph


def policies(found):
    return sorted({name for name, _, _ in found})


# --- P and E ----------------------------------------------------------------------


def test_p_compliant_front_door_passes() -> None:
    assert evaluate(front_door()) == []


def test_e_unmapped_stage_passes_without_a_web_acl() -> None:
    graph = without(front_door(), MAPPING, ASSOC, ACL, DOMAIN)
    assert evaluate(graph) == []


def test_e_unmapped_stage_with_an_acl_still_passes() -> None:
    assert evaluate(without(front_door(), MAPPING)) == []


def test_empty_program_passes() -> None:
    assert evaluate({}) == []


# --- N: one broken rule each ------------------------------------------------------

Mutation = Callable[[dict[str, Resource]], dict[str, Resource]]
N_CASES: list[tuple[str, Mutation, str]] = [
    # A stage without access logs.
    (
        "stage-no-access-log-settings",
        lambda gr: with_props(gr, STAGE, accessLogSettings=None),
        "stage-access-logs",
    ),
    (
        "stage-empty-access-log-destination",
        lambda gr: with_props(gr, STAGE, accessLogSettings={"destinationArn": ""}),
        "stage-access-logs",
    ),
    (
        "stage-logs-to-the-waf-log-group",
        lambda gr: with_deps(gr, STAGE, accessLogSettings={WAF_LOGS}),
        "stage-access-logs",
    ),
    (
        "stage-logs-to-a-group-outside-the-stack",
        lambda gr: with_deps(
            with_props(
                gr,
                STAGE,
                accessLogSettings={
                    "destinationArn": "arn:aws:logs:eu-central-1:111111111111:"
                    "log-group:/elsewhere"
                },
            ),
            STAGE,
            accessLogSettings=set(),
        ),
        "stage-access-logs",
    ),
    # An API without disable_execute_api_endpoint.
    (
        "api-execute-endpoint-on",
        lambda gr: with_props(gr, API, disableExecuteApiEndpoint=False),
        "rest-api-disables-execute-api-endpoint",
    ),
    (
        "api-execute-endpoint-unset",
        lambda gr: with_props(gr, API, disableExecuteApiEndpoint=None),
        "rest-api-disables-execute-api-endpoint",
    ),
    (
        "api-execute-endpoint-unknown",
        lambda gr: with_props(gr, API, disableExecuteApiEndpoint=UNKNOWN),
        "rest-api-disables-execute-api-endpoint",
    ),
    # A log group without a key (and without a retention).
    (
        "log-group-no-key",
        lambda gr: with_props(gr, ACCESS, kmsKeyId=None),
        "log-group-kms-and-retention",
    ),
    (
        "log-group-empty-key",
        lambda gr: with_props(gr, WAF_LOGS, kmsKeyId=""),
        "log-group-kms-and-retention",
    ),
    (
        "log-group-no-retention",
        lambda gr: with_props(gr, ACCESS, retentionInDays=None),
        "log-group-kms-and-retention",
    ),
    (
        "log-group-never-expires",
        lambda gr: with_props(gr, ACCESS, retentionInDays=0.0),
        "log-group-kms-and-retention",
    ),
    # A stage that a base path mapping references but no web ACL protects.
    (
        "mapped-stage-no-web-acl",
        lambda gr: without(gr, ASSOC),
        "mapped-stage-has-one-web-acl",
    ),
    (
        "mapped-stage-two-web-acls",
        lambda gr: (
            gr
            | {
                ASSOC + "2": Resource(
                    ASSOC + "2",
                    g.WEB_ACL_ASSOCIATION,
                    {"resourceArn": UNKNOWN},
                    {"resourceArn": frozenset({STAGE})},
                )
            }
        ),
        "mapped-stage-has-one-web-acl",
    ),
    (
        "mapping-without-stage-name-exposes-the-unprotected-stage",
        lambda gr: without(with_props(gr, MAPPING, stageName=None), ASSOC),
        "mapped-stage-has-one-web-acl",
    ),
    (
        "mapping-to-no-stage-of-this-stack",
        lambda gr: with_deps(
            with_props(gr, MAPPING, stageName=UNKNOWN), MAPPING, stageName=set()
        ),
        "mapped-stage-has-one-web-acl",
    ),
    # An aws:ssm/* resource.
    (
        "ssm-parameter",
        lambda gr: (
            gr
            | {
                "ssm": Resource(
                    P + "aws:ssm/parameter:Parameter::cert",
                    "aws:ssm/parameter:Parameter",
                    {"type": "String"},
                )
            }
        ),
        "no-ssm-resources",
    ),
    # The other AD-A10 rules.
    (
        "settings-logging-info",
        lambda gr: with_props(
            gr,
            SETTINGS,
            settings={
                "loggingLevel": "INFO",
                "throttlingRateLimit": 50.0,
                "throttlingBurstLimit": 100.0,
            },
        ),
        "stage-logging-off-and-throttled",
    ),
    (
        "settings-logging-unknown",
        lambda gr: with_props(
            gr,
            SETTINGS,
            settings={
                "loggingLevel": UNKNOWN,
                "throttlingRateLimit": 50.0,
                "throttlingBurstLimit": 100.0,
            },
        ),
        "stage-logging-off-and-throttled",
    ),
    (
        "settings-no-throttling",
        lambda gr: with_props(gr, SETTINGS, settings={"loggingLevel": "OFF"}),
        "stage-logging-off-and-throttled",
    ),
    (
        "settings-throttling-disabled",
        lambda gr: with_props(
            gr,
            SETTINGS,
            settings={
                "loggingLevel": "OFF",
                "throttlingRateLimit": -1.0,
                "throttlingBurstLimit": -1.0,
            },
        ),
        "stage-logging-off-and-throttled",
    ),
    (
        "settings-throttling-boolean",
        lambda gr: with_props(
            gr,
            SETTINGS,
            settings={
                "loggingLevel": "OFF",
                "throttlingRateLimit": True,
                "throttlingBurstLimit": 1.0,
            },
        ),
        "stage-logging-off-and-throttled",
    ),
    (
        "stage-without-method-settings",
        lambda gr: without(gr, SETTINGS),
        "stage-logging-off-and-throttled",
    ),
    (
        "method-level-override-logs",
        lambda gr: (
            gr
            | {
                "m": Resource(
                    P + "aws:apigateway/methodSettings:MethodSettings::get",
                    g.METHOD_SETTINGS,
                    {"methodPath": "/GET", "settings": {"loggingLevel": "ERROR"}},
                )
            }
        ),
        "stage-logging-off-and-throttled",
    ),
    (
        "domain-tls-1-2",
        lambda gr: with_props(gr, DOMAIN, securityPolicy="TLS_1_2"),
        "domain-tls-policy-strict",
    ),
    (
        "domain-basic",
        lambda gr: with_props(gr, DOMAIN, endpointAccessMode="BASIC"),
        "domain-tls-policy-strict",
    ),
    (
        "integration-skips-verification",
        lambda gr: with_props(
            gr, INTEGRATION, tlsConfig={"insecureSkipVerification": True}
        ),
        "vpc-link-integration-verifies-tls",
    ),
    (
        "integration-no-tls-config",
        lambda gr: with_props(gr, INTEGRATION, tlsConfig=None),
        "vpc-link-integration-verifies-tls",
    ),
    (
        "integration-unknown-connection-type",
        lambda gr: with_props(gr, INTEGRATION, connectionType=UNKNOWN, tlsConfig=None),
        "vpc-link-integration-verifies-tls",
    ),
    (
        "alarm-no-runbook",
        lambda gr: with_props(gr, ALARM, tags={"Owner": "x"}),
        "alarm-runbook-tag",
    ),
    (
        "alarm-empty-runbook",
        lambda gr: with_props(gr, ALARM, tags={"runbook": " "}),
        "alarm-runbook-tag",
    ),
    (
        "alarm-unknown-tags",
        lambda gr: with_props(gr, ALARM, tags=UNKNOWN),
        "alarm-runbook-tag",
    ),
    (
        "composite-alarm-no-runbook",
        lambda gr: (
            gr
            | {
                "c": Resource(
                    P + "aws:cloudwatch/compositeAlarm:CompositeAlarm::c",
                    "aws:cloudwatch/compositeAlarm:CompositeAlarm",
                    {"tags": None},
                )
            }
        ),
        "alarm-runbook-tag",
    ),
]


@pytest.mark.parametrize(
    ("mutate", "policy"),
    [(m, p) for _, m, p in N_CASES],
    ids=[case for case, _, _ in N_CASES],
)
def test_n_each_broken_rule_fails(mutate: Mutation, policy: str) -> None:
    found = evaluate(mutate(front_door()))
    assert policies(found) == [policy], found


# --- edges of the rules -----------------------------------------------------------


def test_unknown_values_that_are_only_required_to_be_set_pass() -> None:
    graph = with_props(front_door(), ACCESS, kmsKeyId=UNKNOWN, retentionInDays=UNKNOWN)
    graph = with_props(graph, ALARM, tags={"runbook": UNKNOWN})
    assert evaluate(graph) == []


def test_links_by_known_values_without_dependencies() -> None:
    """A stage, mapping, association and settings linked by literal values."""
    arn = "arn:aws:apigateway:eu-central-1::/restapis/abc123/stages/live"
    log_arn = "arn:aws:logs:eu-central-1:111111111111:log-group:" + ACCESS_NAME
    graph = with_deps(
        with_props(
            front_door(),
            STAGE,
            restApi="abc123",
            arn=arn,
            accessLogSettings={"destinationArn": log_arn},
        ),
        STAGE,
        restApi=set(),
        accessLogSettings=set(),
    )
    graph = with_deps(
        with_props(graph, MAPPING, restApi="abc123"),
        MAPPING,
        stageName=set(),
        restApi=set(),
    )
    graph = with_deps(
        with_props(graph, SETTINGS, restApi="abc123"),
        SETTINGS,
        stageName=set(),
        restApi=set(),
    )
    graph = with_deps(
        with_props(graph, ASSOC, resourceArn=arn), ASSOC, resourceArn=set()
    )
    assert evaluate(graph) == []
    # The same graph with the association pointing elsewhere fails.
    other = with_props(graph, ASSOC, resourceArn=arn + "x")
    assert policies(evaluate(other)) == ["mapped-stage-has-one-web-acl"]


def test_access_log_destination_by_log_group_arn() -> None:
    log_arn = "arn:aws:logs:eu-central-1:111111111111:log-group:" + ACCESS_NAME
    graph = with_props(front_door(), ACCESS, arn=log_arn)
    graph = with_deps(
        with_props(graph, STAGE, accessLogSettings={"destinationArn": log_arn}),
        STAGE,
        accessLogSettings=set(),
    )
    assert evaluate(graph) == []


def test_stage_name_alone_does_not_link_another_api() -> None:
    """Same stage name, different API: the mapping exposes no stage here."""
    graph = with_deps(
        with_props(front_door(), MAPPING, restApi="other"), MAPPING, stageName=set()
    )
    graph = with_deps(graph, MAPPING, restApi=set())
    assert policies(evaluate(graph)) == ["mapped-stage-has-one-web-acl"]


def test_mapping_without_stage_name_covers_every_stage_of_its_api() -> None:
    graph = with_props(front_door(), MAPPING, stageName=None)
    assert evaluate(graph) == []
    stages = [r for r in front_door().values() if r.type == g.STAGE]
    exposed = g.mapped_stages(graph[MAPPING], stages)
    assert [s.urn for s in exposed] == [STAGE]


def test_non_vpc_link_integration_needs_no_tls_config() -> None:
    graph = with_props(
        front_door(), INTEGRATION, connectionType="INTERNET", tlsConfig=None
    )
    assert evaluate(graph) == []


def test_method_override_without_logging_level_passes() -> None:
    extra = Resource(
        P + "aws:apigateway/methodSettings:MethodSettings::get",
        g.METHOD_SETTINGS,
        {"methodPath": "/GET", "settings": {"metricsEnabled": True}},
    )
    assert evaluate(front_door() | {"m": extra}) == []


def test_unknown_marker_and_known() -> None:
    assert repr(UNKNOWN) == "UNKNOWN"
    assert not g.known(UNKNOWN)
    assert not g.known(None)
    assert g.known("")


def test_every_ad_a10_rule_is_a_policy() -> None:
    names = [name for name, _, _ in g.RESOURCE_RULES + g.STACK_RULES]
    assert names == [
        "rest-api-disables-execute-api-endpoint",
        "domain-tls-policy-strict",
        "log-group-kms-and-retention",
        "vpc-link-integration-verifies-tls",
        "alarm-runbook-tag",
        "no-ssm-resources",
        "stage-access-logs",
        "stage-logging-off-and-throttled",
        "mapped-stage-has-one-web-acl",
    ]
    assert len(set(names)) == len(names)


def test_v_a5_fallback_is_not_accepted_without_a_reviewed_rule() -> None:
    """`TLS_1_2` needs a recorded reason the plan does not locate (G5.5)."""
    graph = with_props(front_door(), DOMAIN, securityPolicy="TLS_1_2")
    assert policies(evaluate(graph)) == ["domain-tls-policy-strict"]


# --- G3.3 audit: v2 mappings and domains, the stack's own group, known values -------

V2_MAPPING = P + "aws:apigatewayv2/apiMapping:ApiMapping::root"


def v2_mapping(**deps) -> Resource:
    return Resource(
        V2_MAPPING,
        g.API_MAPPING,
        {"stage": "live", "apiId": UNKNOWN, "domainName": "user.example.com"},
        {
            "stage": frozenset({STAGE}),
            "apiId": frozenset({API}),
            **{k: frozenset(v) for k, v in deps.items()},
        },
    )


def test_e_v2_api_mapping_to_a_protected_stage_passes() -> None:
    assert evaluate(without(front_door(), MAPPING) | {V2_MAPPING: v2_mapping()}) == []


def test_n_v2_api_mapping_to_an_unprotected_stage_fails() -> None:
    graph = without(front_door(), MAPPING, ASSOC) | {V2_MAPPING: v2_mapping()}
    assert policies(evaluate(graph)) == ["mapped-stage-has-one-web-acl"]


@pytest.mark.parametrize(
    "configuration",
    [
        {"securityPolicy": "TLS_1_2", "endpointType": "REGIONAL"},
        {"securityPolicy": g.TLS_SECURITY_POLICY},
        None,
    ],
)
def test_n_v2_domain_fails(configuration) -> None:
    domain = Resource(
        P + "aws:apigatewayv2/domainName:DomainName::v2",
        g.DOMAIN_NAME_V2,
        {"domainNameConfiguration": configuration},
    )
    assert g.domain_violations(domain)
    graph = front_door() | {domain.urn: domain}
    assert policies(evaluate(graph)) == ["domain-tls-policy-strict"]


def restacked(graph: dict[str, Resource], stack: str) -> dict[str, Resource]:
    """The graph with every URN moved to `stack` (log group names unchanged)."""

    def move(urn: str) -> str:
        return urn.replace("urn:pulumi:ci::", f"urn:pulumi:{stack}::")

    return {
        move(urn): Resource(
            move(r.urn),
            r.type,
            r.props,
            {k: frozenset(map(move, v)) for k, v in r.deps.items()},
        )
        for urn, r in graph.items()
    }


@pytest.mark.parametrize("stack", ["test", "prod", "other"])
def test_n_stage_logging_to_another_stacks_group_fails(stack: str) -> None:
    found = evaluate(restacked(front_door(), stack))
    assert policies(found) == ["stage-access-logs"]


def test_access_log_group_name_comes_from_the_urn() -> None:
    assert g.access_log_group_name(STAGE) == ACCESS_NAME
    assert g.access_log_group_name("not-a-urn") is None


def test_n_known_foreign_destination_beats_a_dependency() -> None:
    graph = with_props(
        front_door(),
        STAGE,
        accessLogSettings={
            "destinationArn": "arn:aws:logs:eu-central-1:111111111111:log-group:x",
            "format": "{}",
        },
    )
    assert policies(evaluate(graph)) == ["stage-access-logs"]


def test_n_known_foreign_association_arn_beats_a_dependency() -> None:
    graph = with_props(
        front_door(), ASSOC, resourceArn="arn:aws:apigateway:eu-central-1::/x"
    )
    assert policies(evaluate(graph)) == ["mapped-stage-has-one-web-acl"]


def test_n_known_foreign_stage_name_beats_a_dependency() -> None:
    graph = with_props(front_door(), MAPPING, stageName="other")
    assert policies(evaluate(graph)) == ["mapped-stage-has-one-web-acl"]
