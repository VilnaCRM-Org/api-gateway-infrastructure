"""Fail-closed TEST certificate prerequisite for the user-service gateway."""

from collections.abc import Sequence
from typing import Any

import pulumi
import pulumi_aws as aws

TEST_ACCOUNT_ID = "891377212104"
TEST_REGION = "eu-central-1"
TEST_ZONE_ID = "Z04999481RZ4UQK2NANVH"
TEST_ZONE_NAME = "vilnacrmtest.com"
TEST_DOMAIN = "user.vilnacrmtest.com"
CERTIFICATE_PARAMETER = "/vilnacrm/test/user-service/gateway-certificate-arn"


def assert_test_target(
    *, account_id: str, region: str, zone_name: str, private_zone: bool
) -> None:
    """Stop before registration when account, region, or DNS zone changed."""
    if account_id != TEST_ACCOUNT_ID or region != TEST_REGION:
        raise ValueError(
            "API Gateway PoC may run only in the pinned TEST account/region."
        )
    if zone_name.rstrip(".") != TEST_ZONE_NAME or private_zone:
        raise ValueError("Pinned public TEST DNS zone required.")


def only_validation_option(options: Sequence[Any]) -> Any:
    """Require one exact-name DNS validation token without wildcard SANs."""
    if len(options) != 1:
        raise ValueError("Expected exactly one ACM DNS validation option.")
    option = options[0]
    if option.domain_name != TEST_DOMAIN:
        raise ValueError("ACM validation option has an unexpected domain.")
    if option.resource_record_type != "CNAME":
        raise ValueError("ACM validation must use a DNS CNAME record.")
    return option


def provision_test_certificate() -> None:
    """Own the TLS prerequisite and publish its ARN for trusted service IaC."""
    if pulumi.get_stack() != "test":
        raise ValueError("TEST gateway certificate requires stack 'test'.")

    caller = aws.get_caller_identity()
    region = aws.get_region()
    zone = aws.route53.get_zone(zone_id=TEST_ZONE_ID)
    assert_test_target(
        account_id=caller.account_id,
        region=region.name,
        zone_name=zone.name,
        private_zone=zone.private_zone,
    )

    certificate = aws.acm.Certificate(
        "user-service-test-public-certificate",
        domain_name=TEST_DOMAIN,
        validation_method="DNS",
        tags={"Environment": "test", "Owner": "api-gateway-infrastructure"},
    )
    options = certificate.domain_validation_options
    option = options.apply(only_validation_option)
    validation_record = aws.route53.Record(
        "user-service-test-certificate-validation",
        zone_id=TEST_ZONE_ID,
        name=option.apply(lambda value: value.resource_record_name),
        type=option.apply(lambda value: value.resource_record_type),
        records=[option.apply(lambda value: value.resource_record_value)],
        ttl=300,
        allow_overwrite=False,
    )
    validated = aws.acm.CertificateValidation(
        "user-service-test-public-certificate-ready",
        certificate_arn=certificate.arn,
        validation_record_fqdns=[validation_record.fqdn],
    )
    parameter = aws.ssm.Parameter(
        "user-service-test-gateway-certificate-arn",
        name=CERTIFICATE_PARAMETER,
        type="String",
        value=validated.certificate_arn,
        tags={"Environment": "test", "Owner": "api-gateway-infrastructure"},
    )

    pulumi.export("certificate_arn", validated.certificate_arn)
    pulumi.export("certificate_parameter_arn", parameter.arn)
    pulumi.export("certificate_parameter_version", parameter.version)
