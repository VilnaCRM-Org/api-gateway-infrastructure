"""Render the D-A11 governance policies and measure them (planning evidence).

Read-only. Run from a bootstrap-infrastructure checkout's `pulumi/` directory:

    python3 <path>/render_governance_sizes.py

It loads the public seed catalogs and `seed.policy_registry.canonical_json`,
then renders the dedicated gateway governance Apply role's ceiling, identity
and guard (the guard with `SeedKmsKeyArn` bound to a key ARN of the real
length), plus the amended shared governance Preview/Drift ceilings. It prints
canonical JSON lengths against the 6144-character managed-policy limit. The
replica bucket names are the deterministic names of BI
`pulumi/infra/pulumi_state.py` `_replica_bucket_name` (lines 267-275).
Names marked "planning" are fixed exactly in G1.1. No AWS call is made.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys

sys.path.insert(0, ".")
from seed.policy_registry import canonical_json  # noqa: E402

ACCOUNTS = {"test": "891377212104", "prod": "933245420672"}
P = "api-gateway-infrastructure"
PURPOSES = ["pulumi-secrets", "gateway-logs"]
REPLICATION_REGION = "eu-west-1"
# Role-level writes the dedicated role must never have (readiness F2).
ROLE_WRITES = {
    "iam:UpdateAssumeRolePolicy",
    "iam:UpdateRole",
    "iam:UpdateRoleDescription",
    "iam:TagRole",
    "iam:UntagRole",
}


def replica_bucket(bucket: str) -> str:
    """Mirror BI `_replica_bucket_name` exactly."""
    suffix = f"-{REPLICATION_REGION}-replication"
    max_prefix = 63 - len(suffix)
    if len(bucket) <= max_prefix:
        return f"{bucket}{suffix}"
    digest = hashlib.sha256(bucket.encode("utf-8")).hexdigest()[:8]
    return f"{bucket[: max(max_prefix - len(digest) - 1, 1)]}-{digest}{suffix}"


def _first(statement: dict) -> str:
    action = statement["Action"]
    return action if isinstance(action, str) else action[0]


def _policy_ids(catalog: dict, suffix: str) -> list[str]:
    return [v for k, v in catalog["policies"].items() if k.endswith(suffix)][0][
        "statement_ids"
    ]


def _names(env: str) -> dict:
    acct = ACCOUNTS[env]
    iam = f"arn:aws:iam::{acct}:"
    state = f"pulumi-{P}-{env}-state"
    return {
        "iam": iam,
        "state": f"arn:aws:s3:::{state}",
        "replica": f"arn:aws:s3:::{replica_bucket(state)}",
        "ci_roles": [f"{iam}role/GitHubCi{x}-{P}-{env}" for x in ("Apply", "Drift", "Preview")],
        "repl_role": f"{iam}role/PulumiStateRepl-{P}-{env}",
        "log_role": f"{iam}role/ApiGatewayCloudWatchLogs-{env}",
        "apply_policies": [
            f"{iam}policy/GitHubCiApply-{P}-{env}-{x}"
            for x in ("pulumi-backend", "secret-read-deny", "certificate", "front-door")
        ],
        "boundaries": [
            f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceBoundary-{P}-{env}",
            f"{iam}policy/issue215-seed/{env}/ceiling/GovernanceReplicationBoundary-{P}-{env}",
        ],
    }


def dedicated_apply_statements(env: str, catalog: dict) -> list[dict]:
    """Ceiling and identity share these statements."""
    acct = ACCOUNTS[env]
    st = catalog["statements"]
    usi = {_first(st[k]): st[k] for k in _policy_ids(catalog, "ceiling/GitHubGovernanceApply")}
    n = _names(env)
    base = f"arn:aws:s3:::pulumi-bootstrap-infrastructure-{env}-state/governance/.pulumi"
    stack = f"{env}-{P}"
    generic = copy.deepcopy(usi["access-analyzer:ValidatePolicy"])
    generic["Action"] = [a for a in generic["Action"] if a not in ROLE_WRITES]
    s3 = copy.deepcopy(usi["s3:CreateBucket"])
    s3["Resource"] = [n["replica"], n["state"]]
    kms = copy.deepcopy(usi["kms:CancelKeyDeletion"])
    kms["Condition"] = {
        "StringEquals": {
            "aws:ResourceTag/Environment": env,
            "aws:ResourceTag/Purpose": PURPOSES,
            "aws:ResourceTag/Repository": P,
        }
    }
    tag = copy.deepcopy(usi["kms:TagResource"])
    # RequestTag/Repository and ResourceTag/Repository are distinct keys.
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
    return [
        generic,
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
            "Condition": {"StringEquals": {"iam:PermissionsBoundary": n["boundaries"][0]}},
            "Effect": "Allow",
            "Resource": n["ci_roles"],
        },
        {
            "Action": ["iam:DeleteRolePolicy", "iam:PutRolePolicy"],
            "Condition": {"StringEquals": {"iam:PermissionsBoundary": n["boundaries"][1]}},
            "Effect": "Allow",
            "Resource": n["repl_role"],
        },
        {"Action": "iam:PassRole", "Condition": {"StringEquals": {"iam:PassedToService": "s3.amazonaws.com"}}, "Effect": "Allow", "Resource": n["repl_role"]},
        {"Action": "iam:PassRole", "Condition": {"StringEquals": {"iam:PassedToService": "apigateway.amazonaws.com"}}, "Effect": "Allow", "Resource": n["log_role"]},
        {"Action": ["apigateway:GET", "apigateway:PATCH"], "Effect": "Allow", "Resource": "arn:aws:apigateway:eu-central-1::/account"},
        # No DeleteResourcePolicy (readiness F6). Resource "*" pending V-A8.
        {"Action": ["logs:DescribeResourcePolicies", "logs:PutResourcePolicy"], "Effect": "Allow", "Resource": "*"},
        copy.deepcopy(usi["s3:GetBucketLocation"]),
        copy.deepcopy(usi["s3:ListBucket"]),
        {
            "Action": ["s3:DeleteObject", "s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"],
            "Effect": "Allow",
            "Resource": [f"{base}/*/governance/{stack}*", f"{base}/locks/organization/governance/{stack}/*"],
        },
        {"Action": "s3:GetObject", "Effect": "Allow", "Resource": f"{base}/meta.yaml"},
        copy.deepcopy(usi["kms:Decrypt"]),
    ]


def _bind_seed_key(value, key_arn: str):
    if isinstance(value, dict):
        if value == {"Ref": "SeedKmsKeyArn"}:
            return key_arn
        return {k: _bind_seed_key(v, key_arn) for k, v in value.items()}
    if isinstance(value, list):
        return [_bind_seed_key(v, key_arn) for v in value]
    return value


def dedicated_guard(env: str, catalog: dict) -> dict:
    """Six shared USI guard statements plus gateway-only denies."""
    st = catalog["statements"]
    n = _names(env)
    shared = [st[k] for k in _policy_ids(catalog, "guard/G-GitHubGovernanceApply")[:6]]
    roles = n["ci_roles"] + [n["repl_role"], n["log_role"]]
    key_arn = f"arn:aws:kms:eu-central-1:{ACCOUNTS[env]}:key/00000000-0000-0000-0000-000000000000"
    statements = _bind_seed_key(copy.deepcopy(shared), key_arn) + [
        {
            "Action": "iam:*",
            "Effect": "Deny",
            "NotResource": sorted(
                [f"{n['iam']}oidc-provider/token.actions.githubusercontent.com"]
                + n["apply_policies"] + n["boundaries"] + roles
            ),
        },
        {
            "Action": ["iam:CreatePolicy", "iam:CreatePolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:TagPolicy", "iam:UntagPolicy"],
            "Effect": "Deny",
            "NotResource": n["apply_policies"],
        },
        # Trust, role and tag updates on the five gateway roles (455fe8d0 pattern).
        {"Action": sorted(ROLE_WRITES), "Effect": "Deny", "Resource": roles},
        # Attach/detach only the four fixed Apply-role policies.
        {
            "Action": ["iam:AttachRolePolicy", "iam:DetachRolePolicy"],
            "Condition": {"ArnNotEquals": {"iam:PolicyARN": n["apply_policies"]}},
            "Effect": "Deny",
            "Resource": "*",
        },
        # No inline policy on the CI Apply role or the logging role.
        {"Action": ["iam:DeleteRolePolicy", "iam:PutRolePolicy"], "Effect": "Deny", "Resource": [n["ci_roles"][0], n["log_role"]]},
    ]
    return {"Version": "2012-10-17", "Statement": statements}


def merged_shared_ceiling(env: str, catalog: dict, name: str) -> tuple[dict, list[str]]:
    """In-place merge into Preview/Drift-only statements; KMS read separate."""
    st = catalog["statements"]
    n = _names(env)
    usi_apply = set(_policy_ids(catalog, "ceiling/GitHubGovernanceApply"))
    out, touched = [], []
    for k in _policy_ids(catalog, f"ceiling/{name}"):
        s = copy.deepcopy(st[k])
        first = _first(s)
        if k not in usi_apply:
            r = s.get("Resource")
            if first == "iam:GetRole":
                s["Resource"] = r + n["ci_roles"] + [n["repl_role"], n["log_role"]]
            elif first == "iam:GetPolicy":
                s["Resource"] = r + n["apply_policies"] + n["boundaries"]
            elif first == "s3:GetAccelerateConfiguration":
                s["Resource"] = r + [n["replica"], n["state"]]
            elif first == "access-analyzer:ValidatePolicy":
                s["Action"] = sorted(s["Action"] + ["logs:DescribeResourcePolicies"])
            else:
                out.append(s)
                continue
            touched.append(k[:8])
        out.append(s)
    out.append({
        "Action": ["kms:DescribeKey", "kms:GetKeyPolicy", "kms:GetKeyRotationStatus", "kms:ListResourceTags"],
        "Condition": {"StringEquals": {"aws:ResourceTag/Environment": env, "aws:ResourceTag/Purpose": PURPOSES, "aws:ResourceTag/Repository": P}},
        "Effect": "Allow",
        "Resource": f"arn:aws:kms:eu-central-1:{ACCOUNTS[env]}:key/*",
    })
    out.append({"Action": "apigateway:GET", "Effect": "Allow", "Resource": "arn:aws:apigateway:eu-central-1::/account"})
    return {"Version": "2012-10-17", "Statement": out}, touched


def main() -> None:
    for env in ("test", "prod"):
        catalog = json.load(open(f"seed/catalogs/{env}.json", encoding="utf-8"))
        statements = dedicated_apply_statements(env, catalog)
        doc = {"Version": "2012-10-17", "Statement": statements}
        print(env, "replica", replica_bucket(f"pulumi-{P}-{env}-state"))
        print(env, "dedicated-apply-ceiling", len(canonical_json(doc)))
        print(env, "dedicated-apply-identity", len(canonical_json(copy.deepcopy(doc))))
        print(env, "dedicated-apply-guard", len(canonical_json(dedicated_guard(env, catalog))))
        for name in ("C-GitHubGovernancePreview", "C-GitHubGovernanceDrift"):
            before = {"Version": "2012-10-17", "Statement": [catalog["statements"][k] for k in _policy_ids(catalog, f"ceiling/{name}")]}
            after, touched = merged_shared_ceiling(env, catalog, name)
            print(env, name, len(canonical_json(before)), "->", len(canonical_json(after)), "in-place:", ",".join(touched))


if __name__ == "__main__":
    main()
