"""The AD-A10 front-door rules, as pure functions over a resource model.

`policy/pack.py` turns CrossGuard arguments into `Resource` values and calls
these functions; tests call them directly with fixture graphs. A value that
`pulumi preview` cannot know yet (an output of a resource still to be
created) is `UNKNOWN`. Rules read it as follows:

- a rule that needs a literal (`disable_execute_api_endpoint` true,
  `logging_level` `OFF`, the TLS policy, `STRICT`, a throttle above zero,
  `insecure_skip_verification` false) fails on `UNKNOWN`: the program sets
  those values as literals, so an unknown one cannot be checked;
- a rule that needs a value to be present (a log group's KMS key and
  retention, an alarm's `runbook` tag value) accepts `UNKNOWN`: the value is
  set, from another resource's output;
- links between resources (stage to log group, mapping to stage,
  association to stage, method settings to stage) use the engine's property
  dependencies, which are always known, and otherwise equal known values.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

REST_API = "aws:apigateway/restApi:RestApi"
STAGE = "aws:apigateway/stage:Stage"
METHOD_SETTINGS = "aws:apigateway/methodSettings:MethodSettings"
BASE_PATH_MAPPING = "aws:apigateway/basePathMapping:BasePathMapping"
DOMAIN_NAME = "aws:apigateway/domainName:DomainName"
INTEGRATION = "aws:apigateway/integration:Integration"
WEB_ACL_ASSOCIATION = "aws:wafv2/webAclAssociation:WebAclAssociation"
LOG_GROUP = "aws:cloudwatch/logGroup:LogGroup"
ALARM_TYPES = (
    "aws:cloudwatch/metricAlarm:MetricAlarm",
    "aws:cloudwatch/compositeAlarm:CompositeAlarm",
)
SSM_PREFIX = "aws:ssm/"

# AD-A4 / FR-A20. The V-A5 fallback (`TLS_1_2` "with a recorded reason") is
# not accepted here: the plan does not say where the reason is recorded, so
# the fallback needs its own reviewed rule change (C-policy) in G5.5.
TLS_SECURITY_POLICY = "SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09"
ENDPOINT_ACCESS_MODE = "STRICT"
# AD-A5: `/aws/apigateway/api-gateway-infrastructure-{env}/access`, for the
# three stacks of AD-A15.
ACCESS_LOG_GROUP = re.compile(
    r"/aws/apigateway/api-gateway-infrastructure-(?:ci|test|prod)/access"
)
ALL_METHODS = "*/*"
LOGGING_OFF = "OFF"
RUNBOOK_TAG = "runbook"
VPC_LINK = "VPC_LINK"


class _Unknown:
    """A value `pulumi preview` cannot know yet."""

    def __repr__(self) -> str:
        return "UNKNOWN"


UNKNOWN: Any = _Unknown()


@dataclass(frozen=True)
class Resource:
    """One resource: its URN, type, properties and property dependencies."""

    urn: str
    type: str
    props: Mapping[str, Any]
    deps: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        """The property `name`, or None when it is not set."""
        return self.props.get(name)

    def refers(self, name: str, target: Resource) -> bool:
        """True when property `name` depends on `target`."""
        return target.urn in self.deps.get(name, frozenset())


Finding = tuple[str, str]  # (urn, message)


def known(value: object) -> bool:
    """True for a set value that the preview knows."""
    return value is not None and value is not UNKNOWN


def _positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


# --- resource rules -----------------------------------------------------------


def rest_api_violations(resource: Resource) -> list[str]:
    """Every REST API has `disable_execute_api_endpoint` true (AD-A4)."""
    if resource.type != REST_API:
        return []
    if resource.get("disableExecuteApiEndpoint") is True:
        return []
    return ["A REST API must set disable_execute_api_endpoint to true."]


def domain_violations(resource: Resource) -> list[str]:
    """Every domain uses the AD-A4 TLS policy and `STRICT`."""
    if resource.type != DOMAIN_NAME:
        return []
    found = []
    if resource.get("securityPolicy") != TLS_SECURITY_POLICY:
        found.append(f"A custom domain must use security_policy {TLS_SECURITY_POLICY}.")
    if resource.get("endpointAccessMode") != ENDPOINT_ACCESS_MODE:
        found.append(
            f"A custom domain must use endpoint_access_mode {ENDPOINT_ACCESS_MODE}."
        )
    return found


def log_group_violations(resource: Resource) -> list[str]:
    """Every log group has a KMS key and a retention."""
    if resource.type != LOG_GROUP:
        return []
    found = []
    key = resource.get("kmsKeyId")
    if not (key is UNKNOWN or (isinstance(key, str) and key)):
        found.append("A log group must be encrypted with a KMS key (kms_key_id).")
    retention = resource.get("retentionInDays")
    if not (retention is UNKNOWN or _positive_number(retention)):
        found.append("A log group must set a retention (retention_in_days > 0).")
    return found


def integration_violations(resource: Resource) -> list[str]:
    """Every VPC_LINK integration has `insecure_skip_verification` false."""
    if resource.type != INTEGRATION:
        return []
    connection = resource.get("connectionType")
    if connection is not UNKNOWN and connection != VPC_LINK:
        return []
    tls = resource.get("tlsConfig")
    if isinstance(tls, Mapping) and tls.get("insecureSkipVerification") is False:
        return []
    return [
        "A VPC_LINK integration must set tls_config.insecure_skip_verification "
        "to false."
    ]


def alarm_violations(resource: Resource) -> list[str]:
    """Every alarm carries a `runbook` tag."""
    if resource.type not in ALARM_TYPES:
        return []
    tags = resource.get("tags")
    if isinstance(tags, Mapping) and RUNBOOK_TAG in tags:
        value = tags[RUNBOOK_TAG]
        if value is UNKNOWN or (isinstance(value, str) and value.strip()):
            return []
    return [f"An alarm must carry a non-empty '{RUNBOOK_TAG}' tag."]


def ssm_violations(resource: Resource) -> list[str]:
    """No `aws:ssm/*` resource (D-15)."""
    if resource.type.startswith(SSM_PREFIX):
        return [
            f"{resource.type} is not allowed: this program publishes nothing in SSM."
        ]
    return []


RESOURCE_RULES: tuple[tuple[str, str, Callable[[Resource], list[str]]], ...] = (
    (
        "rest-api-disables-execute-api-endpoint",
        "Every REST API sets disable_execute_api_endpoint (AD-A4, AD-A10).",
        rest_api_violations,
    ),
    (
        "domain-tls-policy-strict",
        "Every custom domain uses the AD-A4 TLS policy and STRICT (AD-A10).",
        domain_violations,
    ),
    (
        "log-group-kms-and-retention",
        "Every log group has a KMS key and a retention (AD-A10).",
        log_group_violations,
    ),
    (
        "vpc-link-integration-verifies-tls",
        "Every VPC_LINK integration verifies the backend certificate (AD-A10).",
        integration_violations,
    ),
    (
        "alarm-runbook-tag",
        "Every alarm carries a runbook tag (AD-A10, FR-A21).",
        alarm_violations,
    ),
    (
        "no-ssm-resources",
        "No aws:ssm/* resource (AD-A10, D-15).",
        ssm_violations,
    ),
)


# --- links between resources --------------------------------------------------


def _same_reference(left: Resource, right: Resource, name: str) -> bool:
    """True when both resources' property `name` names the same thing."""
    value = left.get(name)
    if known(value) and value == right.get(name):
        return True
    return bool(left.deps.get(name, frozenset()) & right.deps.get(name, frozenset()))


def _names_stage(resource: Resource, stage: Resource) -> bool:
    """True when `resource.stageName` (with its `restApi`) is `stage`."""
    if resource.refers("stageName", stage):
        return True
    name = resource.get("stageName")
    return (
        known(name)
        and name == stage.get("stageName")
        and _same_reference(resource, stage, "restApi")
    )


def mapped_stages(mapping: Resource, stages: Sequence[Resource]) -> list[Resource]:
    """The stages a base path mapping exposes.

    A mapping without a stage name exposes every stage of its API (callers
    pick the stage in the path), so it references all of them.
    """
    if mapping.get("stageName") is None:
        return [s for s in stages if _same_reference(mapping, s, "restApi")]
    return [s for s in stages if _names_stage(mapping, s)]


def associated(association: Resource, stage: Resource) -> bool:
    """True when a web ACL association targets `stage`."""
    if association.refers("resourceArn", stage):
        return True
    arn = association.get("resourceArn")
    return known(arn) and arn == stage.get("arn")


def _access_log_groups(stage: Resource, groups: Sequence[Resource]) -> list[Resource]:
    settings = stage.get("accessLogSettings")
    destination = (
        settings.get("destinationArn") if isinstance(settings, Mapping) else None
    )
    linked = []
    for group in groups:
        name = group.get("name")
        if (
            stage.refers("accessLogSettings", group)
            or (known(destination) and destination == group.get("arn"))
            or (
                known(destination)
                and known(name)
                and str(destination).endswith(f":log-group:{name}")
            )
        ):
            linked.append(group)
    return linked


# --- stack rules --------------------------------------------------------------


def _by_type(resources: Iterable[Resource], *types: str) -> list[Resource]:
    return [r for r in resources if r.type in types]


def stage_access_log_findings(resources: Sequence[Resource]) -> list[Finding]:
    """Every stage logs access to the gateway access log group (AD-A5)."""
    groups = _by_type(resources, LOG_GROUP)
    found = []
    for stage in _by_type(resources, STAGE):
        settings = stage.get("accessLogSettings")
        destination = (
            settings.get("destinationArn") if isinstance(settings, Mapping) else None
        )
        if destination is None or destination == "":
            found.append((stage.urn, "A stage must set an access-log destination."))
            continue
        names = [g.get("name") for g in _access_log_groups(stage, groups)]
        if not any(known(n) and ACCESS_LOG_GROUP.fullmatch(str(n)) for n in names):
            found.append(
                (
                    stage.urn,
                    "A stage's access-log destination must be the gateway access "
                    "log group /aws/apigateway/api-gateway-infrastructure-{env}/access "
                    "of this stack.",
                )
            )
    return found


def _method_settings_problems(settings: object, all_methods: bool) -> list[str]:
    values = settings if isinstance(settings, Mapping) else {}
    level = values.get("loggingLevel")
    problems = []
    if (all_methods or level is not None) and level != LOGGING_OFF:
        problems.append(f"logging_level must be {LOGGING_OFF}")
    if all_methods and not (
        _positive_number(values.get("throttlingRateLimit"))
        and _positive_number(values.get("throttlingBurstLimit"))
    ):
        problems.append("throttling_rate_limit and throttling_burst_limit must be > 0")
    return problems


def stage_method_settings_findings(resources: Sequence[Resource]) -> list[Finding]:
    """Every stage has `logging_level OFF` and throttling on `*/*` (AD-A5).

    Execution logging stays off everywhere: a method-level override that
    sets a logging level other than `OFF` also fails.
    """
    method_settings = _by_type(resources, METHOD_SETTINGS)
    found = []
    for item in method_settings:
        all_methods = item.get("methodPath") == ALL_METHODS
        for problem in _method_settings_problems(item.get("settings"), all_methods):
            found.append((item.urn, f"Method settings: {problem}."))
    for stage in _by_type(resources, STAGE):
        if not any(
            m.get("methodPath") == ALL_METHODS and _names_stage(m, stage)
            for m in method_settings
        ):
            found.append(
                (
                    stage.urn,
                    "A stage needs method settings on */* with logging_level OFF "
                    "and throttling.",
                )
            )
    return found


def mapped_stage_web_acl_findings(resources: Sequence[Resource]) -> list[Finding]:
    """Every stage a base path mapping references has exactly one web ACL.

    A stage that no mapping references is unreachable (the default endpoint
    is disabled), so it may exist without a web ACL (G5.3 before G5.4).
    """
    stages = _by_type(resources, STAGE)
    associations = _by_type(resources, WEB_ACL_ASSOCIATION)
    found: list[Finding] = []
    mapped: dict[str, Resource] = {}
    for mapping in _by_type(resources, BASE_PATH_MAPPING):
        targets = mapped_stages(mapping, stages)
        if not targets:
            found.append(
                (
                    mapping.urn,
                    "A base path mapping must reference a stage of this stack.",
                )
            )
        mapped.update((stage.urn, stage) for stage in targets)
    for urn, stage in mapped.items():
        count = sum(associated(a, stage) for a in associations)
        if count != 1:
            found.append(
                (
                    urn,
                    "A stage that a base path mapping references needs exactly one "
                    f"web ACL association; found {count}.",
                )
            )
    return found


STACK_RULES: tuple[
    tuple[str, str, Callable[[Sequence[Resource]], list[Finding]]], ...
] = (
    (
        "stage-access-logs",
        "Every stage logs access to the gateway access log group (AD-A5, AD-A10).",
        stage_access_log_findings,
    ),
    (
        "stage-logging-off-and-throttled",
        "Every stage has logging_level OFF and throttling on */* (AD-A5, AD-A10).",
        stage_method_settings_findings,
    ),
    (
        "mapped-stage-has-one-web-acl",
        "Every stage a base path mapping references has exactly one web ACL "
        "association (AD-A6, AD-A10).",
        mapped_stage_web_acl_findings,
    ),
)
