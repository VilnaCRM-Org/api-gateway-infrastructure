"""Pulumi graph test: the first phase owns only the TLS prerequisite."""

import asyncio
import unittest

from pulumi.runtime import mocks, settings, stack

from poc_gateway import provision_test_certificate


class GatewayMocks(mocks.Mocks):
    def __init__(self) -> None:
        self.resources = []

    def call(self, args: mocks.MockCallArgs) -> dict:
        if args.token == "aws:index/getCallerIdentity:getCallerIdentity":
            return {"accountId": "891377212104", "id": "891377212104"}
        if args.token == "aws:index/getRegion:getRegion":
            return {"name": "eu-central-1", "id": "eu-central-1"}
        if args.token == "aws:route53/getZone:getZone":
            return {
                "name": "vilnacrmtest.com.",
                "privateZone": False,
                "zoneId": "Z04999481RZ4UQK2NANVH",
                "id": "Z04999481RZ4UQK2NANVH",
            }
        raise AssertionError(f"Unexpected provider invoke: {args.token}")

    def new_resource(self, args: mocks.MockResourceArgs) -> tuple[str, dict]:
        self.resources.append((args.typ, args.name, args.inputs))
        outputs = dict(args.inputs)
        if args.typ == "aws:acm/certificate:Certificate":
            dns_name = "_test.user.vilnacrmtest.com."
            dns_value = "_validation.acm-validations.aws."
            outputs.update(
                {
                    "arn": "arn:aws:acm:eu-central-1:891377212104:"
                    "certificate/00000000-0000-0000-0000-000000000000",
                    "domainValidationOptions": [
                        {
                            "domainName": "user.vilnacrmtest.com",
                            "resourceRecordName": dns_name,
                            "resourceRecordType": "CNAME",
                            "resourceRecordValue": dns_value,
                        }
                    ],
                }
            )
        if args.typ == "aws:route53/record:Record":
            outputs["fqdn"] = "_test.user.vilnacrmtest.com"
        if args.typ == "aws:acm/certificateValidation:CertificateValidation":
            outputs["certificateArn"] = args.inputs["certificateArn"]
        if args.typ == "aws:ssm/parameter:Parameter":
            outputs.update(
                {
                    "arn": "arn:aws:ssm:eu-central-1:891377212104:"
                    "parameter/vilnacrm/test/user-service/"
                    "gateway-certificate-arn",
                    "version": 1,
                }
            )
        return f"{args.name}-id", outputs


class TestGatewayGraph(unittest.TestCase):
    def test_certificate_phase_has_no_public_route_or_example_bucket(
        self,
    ) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        provider = GatewayMocks()
        monitor = mocks.MockMonitor(provider)
        try:
            mocks.set_mocks(
                provider, project="vilnacrm", stack="test", monitor=monitor
            )
            loop.run_until_complete(
                stack.run_pulumi_func(provision_test_certificate)
            )
            types = [item[0] for item in provider.resources]
            self.assertEqual(
                types,
                [
                    "aws:acm/certificate:Certificate",
                    "aws:route53/record:Record",
                    "aws:acm/certificateValidation:CertificateValidation",
                    "aws:ssm/parameter:Parameter",
                ],
            )
            parameter = provider.resources[-1][2]
            self.assertEqual(
                parameter["name"],
                "/vilnacrm/test/user-service/gateway-certificate-arn",
            )
            self.assertEqual(parameter["type"], "String")
        finally:
            settings.reset_options(project=None, stack=None)
            loop.close()
            asyncio.set_event_loop(None)


if __name__ == "__main__":
    unittest.main()
