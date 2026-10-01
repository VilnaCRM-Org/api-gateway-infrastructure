"""The CrossGuard policy pack of the API gateway (AD-A10, FR-A11).

Every rule in `policy/guardrails.py` becomes a mandatory policy. This module
only adapts CrossGuard's arguments: it copies the properties with every
value the preview cannot know replaced by `guardrails.UNKNOWN`, so a rule
never meets CrossGuard's unknown-value error (which would turn the rule into
an advisory skip during preview).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pulumi_policy import (
    EnforcementLevel,
    Policy,
    PolicyPack,
    ReportViolation,
    ResourceValidationArgs,
    ResourceValidationPolicy,
    StackValidationArgs,
    StackValidationPolicy,
)
from pulumi_policy.proxy import UnknownValueError

from policy import guardrails
from policy.guardrails import Finding, Resource

POLICY_PACK_NAME = "api-gateway-guardrails"


def plain(value: Any) -> Any:
    """A plain copy of CrossGuard properties, unknowns as `UNKNOWN`."""
    if isinstance(value, Mapping):
        copied = {}
        for key in value:
            try:
                copied[key] = plain(value[key])
            except UnknownValueError:
                copied[key] = guardrails.UNKNOWN
        return copied
    if isinstance(value, Sequence) and not isinstance(value, str):
        items = []
        for index in range(len(value)):
            try:
                items.append(plain(value[index]))
            except UnknownValueError:
                items.append(guardrails.UNKNOWN)
        return items
    return value


def stack_resource(item: Any) -> Resource:
    """A `Resource` from a CrossGuard `PolicyResource`."""
    return Resource(
        urn=item.urn,
        type=item.resource_type,
        props=plain(item.props),
        deps={
            name: frozenset(dep.urn for dep in deps)
            for name, deps in item.property_dependencies.items()
        },
    )


def resource_policy(
    rule: Callable[[Resource], list[str]],
) -> Callable[[ResourceValidationArgs, ReportViolation], None]:
    """Wrap a resource rule as a CrossGuard resource validation."""

    def validate(args: ResourceValidationArgs, report: ReportViolation) -> None:
        resource = Resource(args.urn, args.resource_type, plain(args.props))
        for message in rule(resource):
            report(message, None)

    return validate


def stack_policy(
    rule: Callable[[Sequence[Resource]], list[Finding]],
) -> Callable[[StackValidationArgs, ReportViolation], None]:
    """Wrap a stack rule as a CrossGuard stack validation."""

    def validate(args: StackValidationArgs, report: ReportViolation) -> None:
        resources = [stack_resource(item) for item in args.resources]
        for urn, message in rule(resources):
            report(message, urn)

    return validate


def build_policies() -> list[Policy]:
    """Every AD-A10 rule as a mandatory CrossGuard policy."""
    policies: list[Policy] = [
        ResourceValidationPolicy(
            name=name,
            description=description,
            validate=resource_policy(rule),
            enforcement_level=EnforcementLevel.MANDATORY,
        )
        for name, description, rule in guardrails.RESOURCE_RULES
    ]
    policies += [
        StackValidationPolicy(
            name=name,
            description=description,
            validate=stack_policy(rule),
            enforcement_level=EnforcementLevel.MANDATORY,
        )
        for name, description, rule in guardrails.STACK_RULES
    ]
    return policies


def serve() -> None:
    """Start the policy pack; the Pulumi engine calls `policy/__main__.py`."""
    PolicyPack(
        name=POLICY_PACK_NAME,
        policies=build_policies(),
        enforcement_level=EnforcementLevel.MANDATORY,
    )
