"""Safety checks for the TEST certificate prerequisite."""

import unittest
from types import SimpleNamespace

from poc_gateway import assert_test_target, only_validation_option


class TestGatewayCertificateTarget(unittest.TestCase):
    def test_pinned_public_test_zone(self) -> None:
        assert_test_target(
            account_id="891377212104",
            region="eu-central-1",
            zone_name="vilnacrmtest.com.",
            private_zone=False,
        )

    def test_wrong_account_region_or_zone_is_rejected(self) -> None:
        good = {
            "account_id": "891377212104",
            "region": "eu-central-1",
            "zone_name": "vilnacrmtest.com.",
            "private_zone": False,
        }
        for field, bad in (
            ("account_id", "123456789012"),
            ("region", "us-east-1"),
            ("zone_name", "vilnacrm.com."),
            ("private_zone", True),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                assert_test_target(**{**good, field: bad})

    def test_only_exact_domain_cname_is_accepted(self) -> None:
        good = SimpleNamespace(
            domain_name="user.vilnacrmtest.com",
            resource_record_type="CNAME",
        )
        self.assertIs(only_validation_option([good]), good)
        for bad in (
            [],
            [good, good],
            [
                SimpleNamespace(
                    domain_name="user.vilnacrm.com",
                    resource_record_type="CNAME",
                )
            ],
            [
                SimpleNamespace(
                    domain_name="user.vilnacrmtest.com",
                    resource_record_type="TXT",
                )
            ],
        ):
            with self.subTest(options=bad), self.assertRaises(ValueError):
                only_validation_option(bad)


if __name__ == "__main__":
    unittest.main()
