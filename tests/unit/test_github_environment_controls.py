"""The branch-policy and self-review readers the controls share (G2.2)."""

from __future__ import annotations

import pytest

import _github_environment_controls as ec

MAIN = {"id": 1, "name": "main", "type": "branch"}
CUSTOM = {"protected_branches": False, "custom_branch_policies": True}


def test_complete_branch_policies_requires_a_whole_listing() -> None:
    assert ec.complete_branch_policies(
        {"branch_policies": [MAIN], "total_count": 1}
    ) == [MAIN]
    for response in (
        [],
        {"branch_policies": "x", "total_count": 1},
        {"branch_policies": [MAIN], "total_count": 2},
        {"branch_policies": [MAIN], "total_count": True},
    ):
        assert ec.complete_branch_policies(response) is None


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        (
            {"deployment_branch_policy": CUSTOM, "deployment_branch_policies": [MAIN]},
            True,
        ),
        (
            {"deployment_branch_policy": CUSTOM, "deployment_branch_policies": None},
            False,
        ),
        ({"deployment_branch_policy": CUSTOM, "deployment_branch_policies": []}, False),
        (
            {"deployment_branch_policy": CUSTOM, "deployment_branch_policies": ["x"]},
            False,
        ),
        (
            {
                "deployment_branch_policy": CUSTOM,
                "deployment_branch_policies": [{**MAIN, "name": "main*"}],
            },
            False,
        ),
        (
            {
                "deployment_branch_policy": CUSTOM,
                "deployment_branch_policies": [{**MAIN, "type": "tag"}],
            },
            False,
        ),
        (
            {"deployment_branch_policy": None, "deployment_branch_policies": [MAIN]},
            False,
        ),
    ],
)
def test_main_only(environment: dict, expected: bool) -> None:
    assert ec.environment_is_main_only(environment) is expected


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({"prevent_self_review": True}, True),
        ({}, False),
        ({"protection_rules": "x"}, False),
        ({"protection_rules": ["x", {"type": "required_reviewers"}]}, False),
        (
            {
                "protection_rules": [
                    {"type": "required_reviewers", "prevent_self_review": True}
                ]
            },
            True,
        ),
    ],
)
def test_self_review(environment: dict, expected: bool) -> None:
    assert ec.environment_prevents_self_review(environment) is expected
