"""Render the D-A11 governance policies and measure them (planning evidence).

Read-only. Run from a bootstrap-infrastructure checkout's `pulumi/` directory:

    python3 <path>/render_governance_sizes.py

It loads the public seed catalogs and `seed.policy_registry.canonical_json`,
builds the planning render of the dedicated gateway governance Apply ceiling
(its identity has the same statements) and the in-place-merged shared
governance Preview/Drift ceilings, and prints canonical JSON lengths against
the 6144-character managed-policy limit. Names marked "planning" and the
replica bucket placeholder are fixed exactly in G1.1. No AWS call is made.
"""

from __future__ import annotations

import copy
import json
import sys

sys.path.insert(0, ".")
from seed.policy_registry import canonical_json  # noqa: E402

ACCOUNTS = {"test": "891377212104", "prod": "933245420672"}
P = "api-gateway-infrastructure"
PURPOSES = ["pulumi-secrets", "gateway-logs"]
REPLICA = "arn:aws:s3:::pulumi-api-gateway-infrastruc-XXXXXXXX-eu-west-1-replication"
FIRST_ACTION = {
    "generic": "access-analyzer:ValidatePolicy",
    "s3": "s3:CreateBucket",
    "kms_mgmt": "kms:CancelKeyDeletion",
    "tag": "kms:TagResource",
    "list": "s3:ListBucket",
    "loc": "s3:GetBucketLocation",
    "gkey": "kms:Decrypt",
}


def _first(statement: dict) -> str:
    action = statement["Action"]
    return action if isinstance(action, str) else action[0]


def _policy(catalog: dict, suffix: str) -> list[str]:
    return [v for k, v in catalog["policies"].items() if k.endswith(suffix)][0][
        "statement_ids"
    ]


def dedicated_apply_ceiling(env: str, catalog: dict) -> dict:
    acct = ACCOUNTS[env]
    st = catalog["statements"]
    usi = {_first(st[k]): st[k] for k in _policy(catalog, "ceiling/GitHubGovernanceApply")}
    iam = f"arn:aws:iam::{acct}:"
    base = f"arn:aws:s3:::pulumi-bootstrap-infrastructure-{env}-state/governance/.pulumi"
    stack = f"{env}-{P}"
    s3 = copy.deepcopy(usi[FIRST_ACTION["s3"]])
    s3["Resource"] = [REPLICA, f"arn:aws:s3:::pulumi-{P}-{env}-state"]
    kms = copy.deepcopy(usi[FIRST_ACTION["kms_mgmt"]])
    kms["Condition"] = {
        "StringEquals": {
            "aws:ResourceTag/Environment": env,
            "aws:ResourceTag/Purpose": PURPOSES,
            "aws:ResourceTag/Repository": P,
        }
    }
    tag = copy.deepcopy(usi[FIRST_ACTION["tag"]])
    tag["Condition"] = {
        "StringEquals": {
            "aws:RequestTag/Repository": P,
            "aws:ResourceTag/Environment": env,
            "aws:ResourceTag/Purpose": PURPOSES,
            "aws:ResourceTag/Repository": P,
        },
        "StringEqualsIfExists": {
            "aws:RequestTag/Environment": env,
            "aws:RequestTag/Purpose": PURPOSES,
        },
    }
    statements = [
        copy.deepcopy(usi[FIRST_ACTION["generic"]]),
        s3,
        kms,
        {
            "Action": "kms:CreateKey",
            "Condition": {
                "StringEquals": {
                    "aws:RequestTag/Environment": env,
                    "aws:RequestTag/Purpose": PURPOSES,
                    "aws:RequestTag/Repository": P,
                }
            },
            "Effect": "Allow",
            "Resource": "*",
        },
        tag,
        {
            "Action": ["kms:CreateAlias", "kms:DeleteAlias", "kms:UpdateAlias"],
            "Effect": "Allow",
            "Resource": [
                f"arn:aws:kms:eu-central-1:{acct}:alias/pulumi-{P}-{env}-secrets",
                f"arn:aws:kms:eu-central-1:{acct}:alias/{P}-{env}-logs",
            ],
        },
        {
            "Action": ["iam:AttachRolePolicy", "iam:DeleteRolePolicy", "iam:DetachRolePolicy", "iam:PutRolePolicy"],
            "Condition": {"StringEquals": {"iam:PermissionsBoundary": f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceBoundary-{P}-{env}"}},
            "Effect": "Allow",
            "Resource": [f"{iam}role/GitHubCi{x}-{P}-{env}" for x in ("Apply", "Drift", "Preview")],
        },
        {
            "Action": ["iam:DeleteRolePolicy", "iam:PutRolePolicy"],
            "Condition": {"StringEquals": {"iam:PermissionsBoundary": f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceReplicationBoundary-{P}-{env}"}},
            "Effect": "Allow",
            "Resource": f"{iam}role/PulumiStateRepl-{P}-{env}",
        },
        {"Action": "iam:PassRole", "Condition": {"StringEquals": {"iam:PassedToService": "s3.amazonaws.com"}}, "Effect": "Allow", "Resource": f"{iam}role/PulumiStateRepl-{P}-{env}"},
        {"Action": "iam:PassRole", "Condition": {"StringEquals": {"iam:PassedToService": "apigateway.amazonaws.com"}}, "Effect": "Allow", "Resource": f"{iam}role/ApiGatewayCloudWatchLogs-{env}"},
        {"Action": ["apigateway:GET", "apigateway:PATCH"], "Effect": "Allow", "Resource": "arn:aws:apigateway:eu-central-1::/account"},
        {"Action": ["logs:DeleteResourcePolicy", "logs:DescribeResourcePolicies", "logs:PutResourcePolicy"], "Effect": "Allow", "Resource": "*"},
        copy.deepcopy(usi[FIRST_ACTION["loc"]]),
        copy.deepcopy(usi[FIRST_ACTION["list"]]),
        {
            "Action": ["s3:DeleteObject", "s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"],
            "Effect": "Allow",
            "Resource": [f"{base}/*/governance/{stack}*", f"{base}/locks/organization/governance/{stack}/*"],
        },
        {"Action": "s3:GetObject", "Effect": "Allow", "Resource": f"{base}/meta.yaml"},
        copy.deepcopy(usi[FIRST_ACTION["gkey"]]),
    ]
    return {"Version": "2012-10-17", "Statement": statements}


def merged_shared_ceiling(env: str, catalog: dict, name: str) -> tuple[dict, list[str]]:
    acct = ACCOUNTS[env]
    st = catalog["statements"]
    iam = f"arn:aws:iam::{acct}:"
    usi_apply = set(_policy(catalog, "ceiling/GitHubGovernanceApply"))
    out, touched = [], []
    for k in _policy(catalog, f"ceiling/{name}"):
        s = copy.deepcopy(st[k])
        first = _first(s)
        if k not in usi_apply:
            r = s.get("Resource")
            if first == "iam:GetRole":
                s["Resource"] = r + [f"{iam}role/GitHubCi{x}-{P}-{env}" for x in ("Apply", "Drift", "Preview")] + [f"{iam}role/PulumiStateRepl-{P}-{env}", f"{iam}role/ApiGatewayCloudWatchLogs-{env}"]
            elif first == "iam:GetPolicy":
                s["Resource"] = r + [f"{iam}policy/GitHubCiApply-{P}-{env}-{x}" for x in ("pulumi-backend", "secret-read-deny", "certificate", "front-door")] + [f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceBoundary-{P}-{env}", f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceReplicationBoundary-{P}-{env}"]
            elif first == "s3:GetAccelerateConfiguration":
                s["Resource"] = r + [REPLICA, f"arn:aws:s3:::pulumi-{P}-{env}-state"]
            elif first == "kms:DescribeKey" and "Condition" in s:
                eq = s["Condition"]["StringEquals"]
                eq["aws:ResourceTag/Repository"] = [eq["aws:ResourceTag/Repository"], P]
                eq["aws:ResourceTag/Purpose"] = PURPOSES
            elif first == "access-analyzer:ValidatePolicy":
                s["Action"] = sorted(s["Action"] + ["logs:DescribeResourcePolicies"])
            else:
                out.append(s)
                continue
            touched.append(k[:8])
        out.append(s)
    out.append({"Action": "apigateway:GET", "Effect": "Allow", "Resource": "arn:aws:apigateway:eu-central-1::/account"})
    return {"Version": "2012-10-17", "Statement": out}, touched


def main() -> None:
    for env in ("test", "prod"):
        catalog = json.load(open(f"seed/catalogs/{env}.json", encoding="utf-8"))
        ceiling = dedicated_apply_ceiling(env, catalog)
        print(env, "dedicated-apply-ceiling", len(canonical_json(ceiling)))
        for name in ("C-GitHubGovernancePreview", "C-GitHubGovernanceDrift"):
            before = {"Version": "2012-10-17", "Statement": [catalog["statements"][k] for k in _policy(catalog, f"ceiling/{name}")]}
            after, touched = merged_shared_ceiling(env, catalog, name)
            print(env, name, len(canonical_json(before)), "->", len(canonical_json(after)), "in-place:", ",".join(touched))


if __name__ == "__main__":
    main()
