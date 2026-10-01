---
artifact: architecture
workflow: _bmad/bmm/workflows/3-solutioning/bmad-create-architecture (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 3 (2026-10-01: D-A9 governance owns the gateway's grants and non-role BI resources; D-A10 no ConfigRead roles)
inputDocuments: [research.md, brief.md, prd.md, decisions.md, USI specs/workload-wa-hardening (9d5df4a), USI specs/poc-api-gateway-backend.md]
---

# Architecture: the API gateway Well-Architected track

## 1. Target and engine discovery

| Item | Value |
| --- | --- |
| Repository | `VilnaCRM-Org/api-gateway-infrastructure` (id `887871673`, owner id `114362548`, public) |
| Engine | Pulumi, Python; toolchain moves to uv (PD-2) |
| Stacks | `test` (account `891377212104`), `prod` (account `933245420672`), both `eu-central-1` |
| Backend | `s3://pulumi-api-gateway-infrastructure-{env}-state`, `awskms://alias/pulumi-api-gateway-infrastructure-{env}-secrets?region=eu-central-1` (FR-A03) |
| Provider | `pulumi-aws` 7.23.0 (`integration_target`, `endpoint_access_mode`; research GR-17) |
| Deploy path | PR ChatOps `/pulumi <env> plan|up`, OIDC, saved plans, `@Kravalg`-gated environments (AD-A11) |

## 2. Boundaries and ownership

```
bootstrap-infrastructure (BI; CODEOWNERS @Kravalg; human seed operator XP-A1)
  ├─ independent seed stack (issue-215 CloudFormation; Retain; deny-update), D-A1:
  │    ├─ gateway roles per env, created with disabled trust, then activated:
  │    │    GitHubCi{Preview,Apply,Drift}-api-gateway-infrastructure-{env},
  │    │    PulumiStateRepl-… (PD-12), ApiGatewayCloudWatchLogs-{env};
  │    │    no ConfigRead readers (D-A10)
  │    ├─ their seed-owned boundaries and immutable guards (issue215-seed/{env}/…)
  │    ├─ the D-A9 governance admission: exact gateway ARNs in the governance
  │    │    guard, ceilings and operator bindings, and the operator guards
  │    └─ registration in pulumi/seed/catalogs/{env}.json (G1.1 source, G1.2 install)
  ├─ governance stack, external-identity mode (D-A9, as for USI):
  │    identity grants (G1.3 basic, G1.4a, G1.4b, G1.7, G1.8),
  │    backend: state bucket, replica, Pulumi secrets key (G1.3),
  │    gateway CMK (G1.6, D-A4), AWS::ApiGateway::Account and the
  │    WAF-log resource policy (G1.5, D-A5)
  ├─ operator stack (github-ci-bootstrap): the governance roles' gateway
  │    storage and IAM identity policies (G1.3, D-A9)
  └─ no gateway resource (API, WAF, domain, DNS) is BI's

api-gateway-infrastructure (this repo; no IAM resource, no SSM write)
  ├─ repository controls: main ruleset, CODEOWNERS, environments (G2.2, XP-A3)
  ├─ pipeline: battery, guardrails, ChatOps saved plans, drift + probe (G3.x)
  ├─ certificate + DNS validation per env (G4.1 = PR #34 amended, G4.2)
  ├─ contracts/user-service-backend/{env}.json (pinned USI coordinates, G5.1, G6.1)
  └─ front door per env: VPC link V2, REST API, stage, WAF, custom domain,
       alias records, log groups, topic, alarms (G5.2-G5.5, G6.2)

user-service-infrastructure (USI; external, unchanged by this plan)
  ├─ internal ALB in two app subnets; HTTPS listener on 443 with the gateway
  │    certificate pinned by D-15 (USI XP-10, XP-15)
  ├─ ALB SG: sole ingress TCP 443 from the VPC-link SG
  └─ VPC-link SG (user-service-vpc-link-sg): no ingress, 443 egress to app subnets;
       attached by AGI to its VPC link, never edited by AGI
```

Request path: client → `https://<fqdn>` (Regional custom domain, TLS policy,
`STRICT`) → WAF web ACL on stage `live` → REST API `ANY /{proxy+}` →
`HTTP_PROXY` over VPC link V2 (ENIs in the USI app subnets, VPC-link SG) →
internal ALB HTTPS 443 (certificate name verified against the `uri` host) →
ECS tasks.

## 3. Architecture decisions

- **AD-A1 Gateway BI identities through the seed registration route
  (FR-A01, FR-A02, FR-A04, FR-A05; D-A1, D-A9, D-A10; PD-12, PD-14).**
  The user decided (D-A1) to enrol the gateway the way USI is enrolled. USI
  was enrolled in two steps (research GR-18). First, the governance stack
  created the USI roles, their boundaries and their identity documents.
  Then the independent seed registered the roles as `existing: true`, took
  ownership of their boundaries and attached one immutable seed guard to
  each. The governance step is closed to the gateway: `G-GitHubGovernanceApply`
  denies `iam:CreateRole` on Resource `*` (`dc27f076…`) and every `iam:*`
  action outside the USI ARNs (`8c068aaa…`) (research GR-12). Neither deny
  is loosened. So the gateway roles take the seed's own creation path, the
  one the seed used for the `GitHubOperator*` executors, and are registered
  in the same reviewed seed catalog amendment.

  | Element | USI (as enrolled) | Gateway (this plan) |
  | --- | --- | --- |
  | Who creates the roles | governance stack (`governance.py` lines 478-517) | the seed stack, through a CREATE change set the human seed operator installs (G1.2; XP-A1) |
  | Role set per env | `GitHubCi{Preview,Apply,Drift}-…`, `GitHubCiConfigRead-…` (+ `-test-pr` / `-prod-preview`), `PulumiStateRepl-…` | `GitHubCi{Preview,Apply,Drift}-api-gateway-infrastructure-{env}`, `PulumiStateRepl-api-gateway-infrastructure-{env}` (PD-12), `ApiGatewayCloudWatchLogs-{env}` (AD-A9; USI has no counterpart); no ConfigRead readers (D-A10) |
  | Catalog record | `existing: true`, `owner_project: governance` | a new seed-created service kind (proposed `owner_project: independent_seed_service`; the BI owner may rename it): created with disabled trust, then activated, but not a `GitHubOperator*` executor |
  | Boundary | `GovernanceBoundary-user-service-infrastructure-{env}` (existing, transferred to the seed) and `GovernanceReplicationBoundary-…` | new seed-owned `policy/issue215-seed/{env}/ceiling/GovernanceBoundary-api-gateway-infrastructure-{env}` (the CI roles), `…/GovernanceReplicationBoundary-api-gateway-infrastructure-{env}`, `…/ApiGatewayCloudWatchLogs-{env}` |
  | Guards | one per role under `policy/issue215-seed/{env}/guard/` | the same: `…/guard/GitHubCi{Apply,Preview,Drift}-api-gateway-infrastructure`, `…/guard/PulumiStateRepl-api-gateway-infrastructure`, `…/guard/ApiGatewayCloudWatchLogs` (layer 4 below) |
  | Identity grants, backend, CMK | written by governance | written by governance too (D-A9), in an external-identity mode, after the seed admits the exact gateway ARNs |
  | Trust | Preview and Drift also trust the `main` ref (GR-20) | exactly one environment subject per role (PD-14), no `pull_request` |
  | Protection of the new policies | the shared denies `668edd62…` and `415affc4…` (TEST; `94b8d964…` and `e59053be…` in PROD) | unchanged and sufficient: every new policy sits under `policy/issue215-seed/{env}/*`, which those denies already cover (BI `pulumi/seed/README.md` lines 146-147). The roles, like USI's, are not listed in `668edd62…`. Listing them would rewrite 21 existing guard documents per account, so it is not done. |

  - **Source packet (G1.1).** A new amendment module,
    `pulumi/seed/gateway_enrollment_amendment.py`, is modelled on
    `test_poc_prerequisite_amendment.py`. It pins, per environment:
    - the baseline catalog hash, which is the pin in force at its slot
      (TEST `ef419680…` on origin/main, `ff2eaf29…` once #284's pin PR
      merges, or a later USI result; PROD `d4b56073…`);
    - the digest of the complete installed seed template, as #284 pinned
      `8b86a7ff…` for TEST;
    - the result catalog hash;
    - the exact list of Add rows and of the D-A9 admission Modify rows.

    It fails closed if replayed against the result. The same PR changes
    `pulumi/seed/policy_registry.py`:
    - the closure counts and the policy-kind inventory;
    - the new principal kind in `_verify_role`, and a **mixed-phase
      verifier** (proposed name `verify_gateway_enrollment`) for the window
      between the CREATE and the activation change sets. It applies
      `verify_active_enrollment`'s checks to every pre-existing principal,
      including the three `GitHubOperator*` executors, which are already
      active in TEST (#284 `post-seed-activation.md` lines 231-236). No
      PROD executor activation is evidenced in the BI sources read, so the
      verifier takes each executor's phase (active or disabled) per
      environment from an observed fact recorded at G1.2 step 1 and pinned
      in the evidence, not from an assumption. It
      applies disabled-trust checks to the new gateway principals only.
      Neither existing verifier can pass in that window:
      `verify_enrollment` requires disabled trust for every `existing:
      false` principal, which includes the active executors (lines 441-446
      and 490-502), and `verify_active_enrollment` rejects the still-disabled
      gateway roles;
    - an active-trust check in `verify_active_enrollment` that compares each
      gateway role with its exact AD-A1 trust, instead of
      `_active_executor_trust`, which maps only the `GitHubOperator*` ARNs;
    - `_mutable_attachment_sets`: the gateway Apply role's governance-owned
      managed policies (the fixed ARN set of the D-A9 admission below), as
      for the USI Apply role (`policy_registry.py` lines 532-551); exact
      attachments for every other gateway role;
    - an **inline-policy allowance** for the new kind: exactly the fixed
      governance-owned inline policy names on the Preview, Drift and
      replication roles (see "Fixed policy set" below), and none on the
      Apply or logging role. Today `_verify_role` (line 447) and
      `_verify_active_executor` (line 524) reject any inline grant on an
      `existing: false` principal.

    It also changes `scripts/operator_seed_installation.py`:
    - `_role_resource`, which today creates "only the three bounded
      executors";
    - a gateway enrolment change-set validator that accepts exactly the
      Add rows and the exact Modify rows of the D-A9 governance admission (the governance guard `G-GitHubGovernanceApply`, the ceilings `ceiling/GitHubGovernanceApply`, `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift`, and the five operator executor guards);
    - a gateway activation packet and validator that accept exactly the
      gateway trust Modify rows. Today's activation validator requires
      exactly the three executor trusts (lines 433-462).

    Finally it updates the README counts. CATALOG_HASHES does **not** move
    in this PR (#284 order).
  - **Verifier count changes, per environment.** The baseline is 55
    policies, 24 principals and 21 existing roles (`policy_registry.py`
    lines 347-362).
    - **Principals:** 24 → 29: Preview, Apply, Drift, replication and
      logging (no ConfigRead reader, D-A10).
    - **Existing roles:** stay 21.
    - **Seed-created principals:** 3 → 8. `verify_enrollment` returns a
      fixed 3 (line 502). The mixed-phase verifier reports the 3
      executors in their observed phase and 5 disabled gateway principals.
      After activation, `verify_active_enrollment` reports 8 active
      seed-created principals (if the executors are active).
    - **Policies:** 55 → 64 = 55 + 3 boundaries + 5 guards + 1 identity
      policy (the logging role's fixed grant). Under D-A9 the CI and
      replication roles' identity documents are governance-owned, so they
      are not seed policies and are not counted. The D-A9 admission
      changes existing documents in place and adds no seed policy.
    - These figures (29 principals, 8 seed-created, 64 policies) hold
      under OQ-11 (b) or (c). Under OQ-11 (a), a dedicated governance
      Apply role adds one principal, one ceiling and one guard: 30
      principals, 9 seed-created, 66 policies.
    - The amendment module recomputes and pins these numbers. Every
      principal stays at ≤ 10 attachments.
  - **Installation and activation (G1.2)**, per environment, TEST first, by
    the human seed operator (XP-A1) in a seed slot (XP-A4), inside a
    freeze window. The steps follow #284's procedure (research GR-18).
    1. Authenticate the account, the seed key, and the complete live seed
       template and stack policy, which must equal the packet's baseline.
    2. Check that every new role and policy name is absent from the live
       account (`README.md` lines 94-98).
    3. Create one change set from an S3 `TemplateURL` bound to its digest.
       A stack policy cannot permit or deny an Add: its actions are only
       `Update:Modify`, `Update:Replace`, `Update:Delete` and `Update:*`
       (`operator_seed_installation.py` lines 232, 357, 363, 555, 561). So
       the change-set validator is what blocks any extra row. It accepts
       exactly the expected Add rows, with no Modify, Remove, replacement
       or dynamic row; the exact Modify rows of the D-A9 governance admission (the governance guard `G-GitHubGovernanceApply`, the ceilings `ceiling/GitHubGovernanceApply`, `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift`, and the five operator executor guards) are the only exception. Those Modify
       rows also need a temporary `Update:Modify` stack policy on exactly
       their logical ids, as #284 used.
    4. Execute only that change-set id, and restore the permanent
       deny-update stack policy on success or failure.
    5. Read back every document, version, attachment, boundary and the
       disabled gateway trusts; the mixed-phase verifier passes.
    6. Install the activation change set, under a temporary
       `Update:Modify` stack policy on exactly the gateway role logical ids
       (as `build_activation` does for the executors, lines 350-371): Modify
       rows on exactly the gateway roles' `AssumeRolePolicyDocument`. The values are the
       AD-A1 OIDC trusts; `s3.amazonaws.com` (replication role) and
       `apigateway.amazonaws.com` (logging role), each with
       `aws:SourceAccount`.
    7. Read back again; `operator_seed_observation.py --active` gives a
       `verify_active_enrollment` pass.
    8. A reviewed PR moves `CATALOG_HASHES[env]` to the result, with the
       evidence as a PR comment (#284 NFR8), and the freeze closes.
  - **Change-set evidence.** The full paginated listings of both change
    sets with their ids, the template digests, both readbacks, both
    verifier outputs, the absent-name results and `@Kravalg`'s seed-review
    approval.
  - **Serialization.** Each environment's install, activation and pin is
    one seed operation in the one-open queue shared with the USI plan's
    seed operations (XP-A4; USI architecture §4 C-BI), on its predecessor's
    result catalog. Between install and pin, every operator run fails
    closed at enrollment (#284 `post-seed-activation.md` lines 107-125), so
    the freeze window bounds that gap.
  - **Trust.** The OIDC provider; `aud` `sts.amazonaws.com`; the
    `token.actions.githubusercontent.com:repository_id` (`887871673`) and
    `:repository_owner_id` (`114362548`) claims, as BI pins them for other
    repositories (BI `pulumi/infra/github_identity.py` lines 31-41); the
    `sub` in both the name and the immutable-id format (lines 44-68), for
    exactly one environment per role: `{env}-preview`, `{env}` or
    `{env}-drift` (PD-14). **No `pull_request` or `ref` subject** (research
    GR-11, GR-20: the generic TEST preview trust would add `pull_request`;
    USI had it retired in #276). The replication role trusts only
    `s3.amazonaws.com`, and the logging role only
    `apigateway.amazonaws.com`, each with `aws:SourceAccount`.
  - **ConfigRead roles: none (D-A10).** The pipeline reads role ARNs and
    backend names from protected-environment variables. Adding a reader
    later needs a reviewed seed catalog amendment (a new principal, its
    guard and the count change) and a CI-secret owner; it is not planned.
  - **Governance admission (D-A9), in the same G1.2 change set per
    account.** Governance owns the gateway's grants, backend, CMK and
    account settings, as it does for USI. It runs in a new
    external-identity mode (a reviewed BI code change), in which it reads
    the seed-created gateway roles and creates none. The gateway is added
    to `pulumi/repositories.governance.json`. `dc27f076…` is unchanged, so
    governance still cannot create, delete or re-bound a role. Every
    extension names exact ARNs only, following the #284 FR6 precedent,
    under the BI owner's review and `@Kravalg`'s approval:
    - **Guard lists:** the exact gateway role ARNs and governance-owned
      gateway policy ARNs are added to the two `NotResource` lists of
      `G-GitHubGovernanceApply`. The statement ids follow the baseline:
      TEST `8c068aaa…`/`5366ec11…` at `ef419680…`,
      `21195ff8…`/`bb116727…` at #284's `ff2eaf29…`; PROD
      `9fb811f6…`/`06267ab9…`. This narrows two deny lists; the
      recorded exception is D-A9 (brief constraints; readiness).
    - **Governance ceilings:** `ceiling/GitHubGovernanceApply` gains the
      exact gateway bucket names in its S3 create and delete statement
      (`7a36d2ff…`). It gains `kms:CreateKey` with
      `aws:RequestTag/Repository = api-gateway-infrastructure`
      (`a392c269…` shape, with a second `aws:RequestTag/Purpose` value for
      the gateway logs CMK). It gains the gateway entries of the KMS
      management statements, which today admit only the USI key and alias:
      `81c3805b…` (key policy, rotation, alias, describe; conditioned on
      the USI tags), `6f28ae7e…` (`kms:TagResource`) and `37942811…`
      (aliases: only `alias/pulumi-user-service-infrastructure-{env}-secrets`);
      PROD `c453626c…`, `8fa820e5…`, `baf46019…`. Both gateway key aliases
      (`pulumi-api-gateway-infrastructure-{env}-secrets` and
      `api-gateway-infrastructure-{env}-logs`) are added. It gains
      role-policy attach and put on the exact
      gateway roles with the gateway boundary (`00257170…`, `d35c02e1…`
      shape), and `iam:PassRole` of the gateway replication role to S3
      (`abfe3f39…` shape). For G1.5 it gains `apigateway:PATCH` on
      `/account`, `iam:PassRole` of `ApiGatewayCloudWatchLogs-{env}` to
      `apigateway.amazonaws.com`, and `logs:PutResourcePolicy` /
      `DescribeResourcePolicies` for the gateway WAF-log policy (D-A5 keeps
      that action off every gateway role). `C-GitHubGovernancePreview` and
      `C-GitHubGovernanceDrift` gain the matching exact reads (for
      example `6b2d4e23…`, `0d44e2be…`, `011f1685…`).
    - **Size blocker (V-A12; OQ-11, open).** A managed policy is limited
      to 6144 characters, and a role has exactly one permissions
      boundary, so `ceiling/GitHubGovernanceApply` cannot be split. Its
      canonical JSON is already 5752 characters in TEST and 5762 in PROD
      (read-only Python with `policy_registry.canonical_json`), leaving
      about 390. The revision-3 audit rendered the exact-ARN additions
      above: 7924 / 7934 characters as new statements, 7187 / 7197 merged
      into the existing statements, about 8729 with the KMS management
      entries. **The admission into the Apply ceiling therefore cannot be
      built with exact ARNs only.** The Preview and Drift ceilings (3789 /
      3799) have room. G1.1 checks every candidate ceiling at ≤ 6144 and
      STOPs otherwise. How to restructure is OQ-11 (`decisions.md` §3);
      this plan does not choose.
    - **Operator bindings and operator guards:** the governance roles' own
      gateway identity policies (for example
      `GitHubGovernanceApply-{env}-api-gateway-infrastructure-storage` and
      `-iam`, written by the operator stack) are added to the catalog's
      `operator_bindings` (`policy_write`, `policy_read`, and
      `policy_read_resources`, which equals the `NotResource` list of
      `408cdbf9…`/`7a337042…` and must change with it). The bindings are
      catalog metadata, not template rows: they change in the result
      catalog and the pin PR, not in the change set. The five
      `GitHubOperator*` guards that close those names to the USI ones are
      amended by the same exact ARNs: TEST `0c5eed92…`
      (`GitHubOperatorApply-iam-write`), `c18540fb…`
      (`GitHubOperatorApply-attachments`), `408cdbf9…` (the three
      `-iam-read` guards); PROD `de33acbe…`, `0142330f…`, `7a337042…`.
      `c18540fb…` and `0142330f…` are `Deny` statements on Resource `*`
      with an `ArnNotEquals iam:PolicyARN` condition, so adding gateway
      ARNs narrows a Resource-`*` deny. They are named in the recorded D-A9
      exception. `dc27f076…` stays the protected, unchanged Resource-`*`
      deny.
    - **Fixed policy set.** G1.1 fixes, per environment, the full ARN set
      of governance-owned gateway **managed** policies on the Apply role
      (for example
      `GitHubCiApply-api-gateway-infrastructure-{env}-pulumi-backend`,
      `-secret-read-deny`, `-certificate`, `-front-door`), and the names of
      the governance-owned **inline** policies on the Preview, Drift and
      replication roles. Governance writes those inline, as it does for USI
      (BI `ci_bootstrap.py` lines 813-853, managed only for `apply`;
      `pulumi_state.py` line 613); `8c068aaa…` admits them through the role
      ARN. The new seed-created service kind therefore allows exactly those
      inline names on those three roles. Today `_verify_role` (line 447)
      and `_verify_active_executor` (line 524) reject any inline grant on
      an `existing: false` principal. Later grant stories (G1.4a,
      G1.4b, G1.7, G1.8) then change only those documents, through
      governance PRs. A grant that needs a new ARN is a new seed
      admission in its own slot.
  - **Layer 3, boundary as a service-family ceiling.** The CI boundary
    allows `sts:GetCallerIdentity`, the state bucket and secrets key, and
    the gateway service families (`apigateway`, `wafv2`, `acm`, `route53`
    on the gateway zones, `logs` on the gateway log groups plus the
    log-delivery and Logs Insights actions, `cloudwatch` alarms and the
    probe metric namespace, `sns` on the gateway topic, `kms` on the
    gateway CMK, and the read-only `elasticloadbalancing` and `ec2`
    describes of AD-A7). Exact resources stay in the identity allows. A
    ceiling sized up front means later grant changes are identity changes
    only, never a boundary amendment (the USI plan's fallback form, USI
    `epics-stories.md` Epic 5 preamble). The rendered size is checked
    against 6144 characters in G1.1.
  - **Layer 4, guards.** These reuse the USI guard statements verbatim.
    Shared statements are indexed by their hash, so a reused statement
    adds no statement to the catalog. The ids below are the TEST ones at
    origin/main. PROD uses the PROD statements of the same shape:
    `dc27f076…` and `05f77e26…` are identical, and `e59053be…`,
    `94b8d964…`, `0c46dd13…` and `aec83856…` stand for `415affc4…`,
    `668edd62…`, `6bd9deea…` and `d413d73a…`.
    - The **Apply** guard: `dc27f076…` (role creation and deletion,
      boundary changes, STS session issuance), `415affc4…`, `668edd62…`,
      `6bd9deea…`, `05f77e26…` and `d413d73a…`, plus one new statement. The
      new statement has the shape of `9f269660…` (secret, parameter, ECR
      token and `lambda:GetFunction` reads), with Resource `*` and no CI-secret
      exception, because the gateway has no CI secrets (D-A10).
    - The **Preview** and **Drift** guards: `ae950d73…` and the same five
      shared statements, plus one new statement. The new statement has the
      shape of `119623e2…`: state writes are allowed only under
      `pulumi-api-gateway-infrastructure-{env}-state/.pulumi/locks/*`.
    - The **replication** and **logging** guards: `dc27f076…` and the five
      shared statements, as USI's `PulumiStateRepl-` guard.

    No existing seed statement or ceiling changes except the D-A9
    governance admission above.
  - **Layer 5, attachment constraint.** `verify_active_enrollment` and
    `_mutable_attachment_sets` gain entries for the gateway roles only.
    The gateway Apply role's governance-owned policies are listed, as
    USI's are (`policy_registry.py` lines 532-551); every other gateway
    role's attachment set is exact.
  - **Layers 1-2, identity allows and denies.** AD-A7. Governance writes
    them (D-A9) through reviewed governance PRs, inside the fixed policy
    set the seed admitted.
  - **What does not follow the USI pattern, and why.**
    1. **Role creation** moves from governance to the seed, because
       `dc27f076…` blocks governance and may not be narrowed. D-A1 decides
       this.
    2. **The writer of grants and non-role resources** stays governance,
       as for USI, but governance is blocked by its guard (`8c068aaa…`,
       `5366ec11…`), its USI-scoped ceilings and the operator guards until
       the D-A9 admission. D-A9 decides this.
    3. **ConfigRead:** none (D-A10). USI's readers carry `pull_request`
       and `ref` trust, and their CI secrets would need an owner.
    4. **The trust subject list** is stricter (PD-14).

    V-A10 is the BI owner's confirmation that the inventory extension is
    acceptable. #285 avoided such an extension for its runtime roles
    (research GR-19, K-16).
- **AD-A2 PR #34: adopt and amend (FR-A14, FR-A24; PD-9).**
  - **Kept:** `assert_test_target`, `only_validation_option`, the stack
    check, the certificate, the validation record with
    `allow_overwrite=False`, `CertificateValidation`, the tests.
  - **Dropped:** the `aws.ssm.Parameter` and the two parameter exports.
    Under D-15 no role reads it, and keeping it would need an
    `ssm:PutParameter` grant for an unused value.
  - **Dropped:** the `my-bucket` preservation. The governed backend is new
    and empty, so the program never owned that bucket there; any legacy
    bucket outside it is retired after an emptiness check (D-A6).
  - **Changed:** the account, region, zone and FQDN move from Python
    constants into stack config (FR-A09); both resources get `protect` and
    `retainOnDelete`; the module moves to `pulumi/app/certificate.py`
    behind the `features.certificate` flag (AD-A15); the tests move to
    pytest with 100% branch coverage.
  - **Sequence:** rebased after the pipeline (G3.4), so its first apply is
    a saved plan. The author's commits stay; a maintainer may push the
    amendment commits if the author agrees, otherwise a successor PR
    cherry-picks them with `Co-authored-by` credit.
  - **Why not adopt as is:** it merges an SSM publication D-15 retired and a
    resource kept for a backend this pipeline does not use. **Why not
    supersede:** its fail-closed logic and tests are correct and reviewed.
- **AD-A3 The cross-repository contract (FR-A14, FR-A15, FR-A16, FR-A25;
  D-A8, D-A2).** Two pins, one in each direction, both reviewed PRs,
  neither a broad read:
  - **Gateway → USI (D-15):** the gateway owner hands the issued
    certificate ARN to the USI owner (XP-A8); a USI contract PR pins it
    (USI XP-10, XP-15). Nothing is published in SSM.
  - **USI → gateway:** the USI owner hands over the
    `poc-api-gateway-backend/v1` field values (XP-A7); a gateway PR pins
    them in `contracts/user-service-backend/{env}.json` with their source
    (the USI apply run URL and commit, and the sha256 of the canonical
    JSON). A Pulumi `StackReference` would need a read on the USI state
    bucket and its key; it is rejected.
  - **Provenance (D-A8).** The USI spec's authenticated publication does
    not exist (USI `specs/poc-api-gateway-backend.md` lines 10-15). By D-A8
    the authority is the gateway's own live re-verification below; the strongest binding is the listener's
    certificate, which must be this repository's certificate.
  - **What the gateway uses:** `listener_arn`, the load balancer ARN
    derived from it (`…:listener/app/<name>/<id>/<l>` →
    `…:loadbalancer/app/<name>/<id>`), `subnet_ids`,
    `vpc_link_security_group_id`, `alb_security_group_id`, `vpc_id`,
    `tls_server_name` and `certificate_arn`. `integration_type` and
    `connection_type` are checked equal to `HTTP_PROXY` and `VPC_LINK`.
    `request_parameters` is checked equal to the v1 constant and not used:
    the REST API maps the path itself (AD-A4; K-9; USI-F1).
  - **Live verification on every preview and drift**, by Pulumi data-source
    invokes in the program (so a mismatch fails the plan): the listener
    (HTTPS, 443, that load balancer, that certificate), the load balancer
    (internal, `application`, those subnets, only the ALB group), the ALB
    group (its only ingress is TCP 443 from the VPC-link group), the
    VPC-link group (no ingress), the subnets (in `vpc_id`).
  - **The USI abandon rehearsal (D-A2).** USI S4.6 step 18 requires no
    foreign ENI in the application subnets, step 19 deletes them with the
    security groups, and step 20 rebuilds them with new ids. A VPC link
    holds ENIs in those subnets and pins their ids (VPC link V2 is
    immutable, GA-2). By D-A2 the gateway's TEST rows (19-25) run once,
    after step 20, against the rebuilt workload. The TEST contract cites
    the step-20 run (FR-A25), and USI runs step 17 after step 20, held for
    gate A-T step 10 (CR-A1). No gateway teardown, recovery role or
    rebuild exists.
  - **Replacement windows (operating residual, not a risk acceptance).**
    If USI replaces its ALB, listener or a group outside the rehearsal,
    gateway previews and drift fail closed until a gateway PR pins the
    new descriptor; a changed subnet or VPC-link group needs a new VPC
    link, which in PROD is a reviewed recovery outside routine apply (no
    PROD delete grant exists). If the gateway replaces its certificate, the
    USI side has the D-15 residual of USI `prd.md` §7 XP-10.
  - **Invariant the USI side keeps** (AS-2): the ALB SG's sole ingress
    from the VPC-link SG; the VPC-link SG with no ingress. The gateway
    never adds a rule to either group.
- **AD-A4 Front-door topology (FR-A17; D-3; V-A1, V-A2, V-A4).**
  - `aws.apigatewayv2.VpcLink` on the two pinned subnets with only the
    pinned VPC-link group.
  - `aws.apigateway.RestApi` (`endpoint_configuration REGIONAL`,
    `disable_execute_api_endpoint True`, no API keys, no authorizer: the
    application authenticates), resources `/` and `/{proxy+}`, method
    `ANY`, `authorization NONE`.
  - `aws.apigateway.Integration`: `type HTTP_PROXY`,
    `connection_type VPC_LINK`, `connection_id` the VPC link id,
    `integration_target` the derived load balancer ARN (GA-1, GR-17),
    `integration_http_method ANY`, `uri https://<fqdn>/{proxy}` (root:
    `https://<fqdn>/`), `request_parameters
    {"integration.request.path.proxy": "method.request.path.proxy"}`,
    `tls_config.insecure_skip_verification False`, timeout 29,000 ms.
  - `aws.apigateway.Deployment` with `triggers` on a hash of the API
    definition, and `aws.apigateway.Stage` `live`.
  - **NLB fallback (V-A1):** only if V-A1 fails in TEST. A reviewed
    variant puts an internal NLB (TCP 443, ALB-type target group) in front
    of the ALB; it needs a USI change (the NLB's group in the ALB's
    ingress) and a new contract field, so it is a new plan revision, never
    a silent switch.
- **AD-A5 Stage logging and throttling (FR-A18; PD-3, PD-5).**
  - Access log group `/aws/apigateway/api-gateway-infrastructure-{env}/access`,
    the gateway CMK (D-A4), retention PD-5. JSON format:
    `{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","path":"$context.path","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","responseLatency":"$context.responseLatency","integrationLatency":"$context.integration.latency","integrationStatus":"$context.integration.status","wafResponseCode":"$context.wafResponseCode","tlsVersion":"$context.tlsVersion","cipherSuite":"$context.cipherSuite","userAgent":"$context.identity.userAgent","domainName":"$context.domainName"}`.
  - `aws.apigateway.MethodSettings` on `*/*`: `metrics_enabled true`,
    `logging_level OFF`, `data_trace_enabled false`,
    `throttling_rate_limit` and `throttling_burst_limit` per PD-3 (TEST) or
    D-A7 (PROD),
    `caching_enabled false`.
  - The account's `cloudWatchRoleArn` is BI's (AD-A9); this repository
    never manages `aws.apigateway.Account`.
- **AD-A6 WAF (FR-A19; PD-4, PD-8).**
  - `aws.wafv2.WebAcl` `api-gateway-infrastructure-{env}`, scope `REGIONAL`,
    default action Allow, `visibility_config` with metrics and sampled
    requests on the ACL and every rule.
  - Rules, in priority order: 0 `AWSManagedRulesAmazonIpReputationList`
    (block); 1 `AWSManagedRulesKnownBadInputsRuleSet` (block); 2
    `AWSManagedRulesCommonRuleSet` (TEST: `override_action count` until
    gate A-T step 11 switches it; PROD: block, with any rule overrides the
    TEST evidence justified); 3 `AWSManagedRulesAnonymousIpList` (count);
    10 rate rule on the token path (scope-down: URI path starts with the
    token path that G5.4 reads from the user-service routes, limit PD-4,
    window 300 s, aggregate `IP`, block); 11 global rate rule (limit
    PD-4, window 300 s, aggregate `IP`, block).
  - The aggregation key is the source IP that WAF sees on a Regional REST
    API stage, which is the client's address; no forwarded-IP header is
    trusted.
  - WCU is computed in a unit test from the published capacities and
    must stay ≤ 1,500.
  - `aws.wafv2.WebAclAssociation` to the stage ARN (needs both
    `wafv2:AssociateWebACL` and `apigateway:SetWebACL`, AD-A7);
    `aws.wafv2.WebAclLoggingConfiguration` to
    `aws-waf-logs-api-gateway-infrastructure-{env}` (the gateway CMK, D-A4,
    retention PD-5), `redacted_fields` single header `authorization` and
    `cookie`; log filter: keep all.
- **AD-A7 Identity allows and denies (FR-A04; NFR-A02; V-A3, V-A7, V-A8).**
  `{a}` is the account, `{fqdn}` the stack FQDN, `{zone}` the zone id,
  `P` = `api-gateway-infrastructure-{env}`, `G` the gateway CMK. All
  Regional ARNs are `eu-central-1`. Rows marked **cert** are granted by
  G1.4a (TEST) and G1.7 (PROD); all other rows by G1.4b (TEST) and G1.8
  (PROD).

  | Role | Allow | Resources and conditions | Grant |
  | --- | --- | --- | --- |
  | Preview, Drift, Apply | state and secrets key (BI backend pattern: `pulumi-backend`, and `secret-read-deny` or `read-only`, governance.py lines 414-476) | the FR-A03 bucket and key | G1.3 (governance, D-A9) |
  | Preview, Drift, Apply | `acm:DescribeCertificate`, `ListTagsForCertificate` | `certificate/*` with `aws:ResourceTag/Owner = api-gateway-infrastructure` (GA-16; V-A7) | cert |
  | Preview, Drift, Apply | `route53:GetHostedZone`, `ListResourceRecordSets`, `ListTagsForResource`; `route53:GetChange` | `hostedzone/{zone}`; `change/*` | cert |
  | Apply | `acm:RequestCertificate`, `AddTagsToCertificate` | `acm:DomainNames` = [`{fqdn}`], `acm:ValidationMethod` = `DNS`, `aws:RequestTag/Owner = api-gateway-infrastructure` on request; `aws:ResourceTag/Owner` on tagging (GA-16) | cert |
  | Apply | `route53:ChangeResourceRecordSets` (validation) | `hostedzone/{zone}`; names `_*.{fqdn}`, type `CNAME`, action `CREATE`; `Null` guards on the three keys (the BI DKIM precedent, GR-14) | cert |
  | Preview, Drift, Apply | `apigateway:GET` | `arn:aws:apigateway:eu-central-1::/restapis`, `/restapis/*`, `/vpclinks`, `/vpclinks/*`, `/domainnames`, `/domainnames/{fqdn}`, `/domainnames/{fqdn}/*`, `/tags/*`, `/account` | |
  | Preview, Drift, Apply | `wafv2:GetWebACL`, `GetLoggingConfiguration`, `GetWebACLForResource`, `ListTagsForResource`, `ListResourcesForWebACL`; `wafv2:DescribeManagedRuleGroup`, `ListAvailableManagedRuleGroups`, `CheckCapacity` | `regional/webacl/P/*` (for a REST stage, `GetWebACLForResource` and `ListResourcesForWebACL` are authorized on the web ACL, GA-17); the managed-rule and capacity actions on `*` only if V-A8 shows no resource-level support | |
  | Preview, Drift, Apply | `logs:DescribeLogGroups`; `logs:ListTagsForResource` | `log-group:*` (V-A8); the two gateway log groups | |
  | Preview, Drift, Apply | `cloudwatch:DescribeAlarms`, `ListTagsForResource`; `sns:GetTopicAttributes`, `ListTagsForResource`, `ListSubscriptionsByTopic`; `kms:DescribeKey` | `alarm:P-*`; `…:sns:…:P-alarms`; `G` | |
  | Preview, Drift, Apply | `elasticloadbalancing:DescribeListeners`, `DescribeLoadBalancers`, `DescribeTags`; `ec2:DescribeSecurityGroups`, `DescribeSecurityGroupRules`, `DescribeSubnets`, `DescribeVpcs` | `*`, the read-only exceptions without resource-level support (V-A8 confirms each from the Service Authorization Reference) | |
  | Drift | evidence reads: `logs:StartQuery`, `GetQueryResults`, `FilterLogEvents`; `wafv2:GetSampledRequests` | the two gateway log groups (`GetQueryResults` on `*` if V-A8 says so); `regional/webacl/P/*` | |
  | Drift | `cloudwatch:PutMetricData` | `cloudwatch:namespace` = `ApiGatewayInfrastructure/{env}` (the probe metric) | |
  | Apply | `apigateway:POST`, `PUT`, `PATCH` | `/restapis`, `/restapis/*`, `/vpclinks`, `/vpclinks/*`, `/domainnames`, `/domainnames/{fqdn}`, `/domainnames/{fqdn}/*`, `/tags/*`; creates and updates of `/restapis` require `apigateway:Request/DisableExecuteApiEndpoint` true (GA-7, V-A11) | |
  | Apply | `apigateway:SetWebACL` | `/restapis/*/stages/*` (required with `wafv2:AssociateWebACL` for REST stages; GA-17) | |
  | Apply | `apigateway:DELETE` | only `/restapis/*/deployments/*` (AD-A10 allowance) | |
  | Apply | `wafv2:CreateWebACL`, `UpdateWebACL`, `AssociateWebACL`, `PutLoggingConfiguration`, `DeleteLoggingConfiguration`, `TagResource` | `regional/webacl/P/*`, the stage ARN, the managed rule groups (`regional/managedruleset/*/*`) | |
  | Apply | `route53:ChangeResourceRecordSets` (alias) | `hostedzone/{zone}`; names `{fqdn}`, types `A`, `AAAA`, actions `CREATE`, `UPSERT`, `DELETE` (an in-place change may be sent as a delete-and-create batch; a lone delete is still stopped by the destructive gate); `Null` guards | |
  | Apply | `logs:CreateLogGroup`, `PutRetentionPolicy`, `AssociateKmsKey`, `TagResource`; `logs:CreateLogDelivery`, `DeleteLogDelivery`, `DescribeResourcePolicies` | the two gateway log groups; the log-delivery actions on `*` (GA-9) | |
  | Apply | `kms:DescribeKey`, `kms:CreateGrant` | `G`, `kms:ViaService = logs.eu-central-1.amazonaws.com` (USI research A-28) | |
  | Apply | `cloudwatch:PutMetricAlarm`, `TagResource`, `SetAlarmState` | `alarm:P-*` (`SetAlarmState` for gate A-T step 9) | |
  | Apply | `sns:CreateTopic`, `SetTopicAttributes`, `TagResource`, `Subscribe` | `…:sns:eu-central-1:{a}:P-alarms` | |

  **Denies on the three CI roles (layer 2):** `iam:*`; `ssm:*`;
  `secretsmanager:GetSecretValue` and `BatchGetSecretValue`;
  `lambda:GetFunction`; `apigateway:PATCH`, `PUT`, `POST` and `DELETE` on
  `/account`; `logs:PutResourcePolicy` and `DeleteResourcePolicy`;
  `route53:ChangeResourceRecordSets` for names `*._domainkey.*` (AD-A8);
  every `Delete*` of `wafv2`, `acm`, `logs`, `sns`, `cloudwatch` and
  `apigateway`, **except** `apigateway:DELETE` on
  `/restapis/*/deployments/*`, `wafv2:DeleteLoggingConfiguration` and
  `logs:DeleteLogDelivery` (the deny uses `NotAction`/`NotResource` for
  these three); `sts:AssumeRole`. Preview and Drift have no write except
  Drift's `PutMetricData`. If V-A7 shows that a certificate read does not
  support the tag condition, the fallback (account-wide `certificate/*`
  metadata reads) is a user decision, as D-15's option (c) is for USI; it
  is not defaulted.

  **No recovery role exists** (D-A2): the TEST front door is built once,
  after USI S4.6 step 20, so no teardown grant is needed in either
  environment.
- **AD-A8 DNS and the shared TEST zone (FR-A14, FR-A20; XP-A6).** The TEST
  zone already holds USI's DKIM CNAMEs (`<token>._domainkey.user.vilnacrmtest.com`,
  GR-14). The gateway owns only `user.vilnacrmtest.com` (alias A and AAAA)
  and the ACM validation CNAME `_<token>.user.vilnacrmtest.com`. The
  `_*.{fqdn}` pattern does not match the DKIM names (their first label
  does not start with `_`); the explicit deny on `*._domainkey.*` is
  defence in depth, so no future pattern of this repository can reach
  USI's records. In PROD the gateway owns `user.vilnacrm.com` (alias A
  and AAAA) and its validation CNAME in the public zone of account
  `933245420672` (D-A3; zone id from XP-A11), under the same rules. All gateway records are `protect`ed and
  `retainOnDelete`; the validation CNAME must stay for managed renewal
  (GA-15); `aws:route53/` is a critical type in the destructive gate.
- **AD-A9 Account-level logging role and WAF log policy (FR-A05; D-A5;
  D-A9; K-6, K-7).** Per account, the role comes from the D-A1 seed
  amendment (AD-A1) and the other two resources from governance (D-A9):
  - `ApiGatewayCloudWatchLogs-{env}`, trusted by `apigateway.amazonaws.com`
    with `aws:SourceAccount` = the account, with a seed-owned identity
    policy of
    `logs:CreateLogStream`, `PutLogEvents`, `DescribeLogStreams` on the
    access-log group ARN and `logs:DescribeLogGroups` on `log-group:*`
    (the same V-A8 scope as AD-A7), instead of the AWS managed policy on
    `*` (GA-4; V-A9);
  - `AWS::ApiGateway::Account` with that role's ARN (after XP-A12);
  - (D-A5) an `AWS::Logs::ResourcePolicy` allowing
    `delivery.logs.amazonaws.com` to write to
    `aws-waf-logs-api-gateway-infrastructure-*` with `aws:SourceAccount`
    and `aws:SourceArn` conditions (V-A6).

  Execution logging stays off (AD-A5), so the role needs no
  `API-Gateway-Execution-Logs_*` group.
- **AD-A10 Guardrails and the policy pack (FR-A11).**
  - **Destructive gate:** the ported `scripts/pulumi_ci_guardrails.py`
    with `CRITICAL_TYPE_PATTERNS` extended by `aws:apigateway/`,
    `aws:apigatewayv2/`, `aws:wafv2/`, `aws:acm/`, `aws:cloudwatch/logGroup`
    (`aws:route53/` and `aws:kms/` are already there). One allowance,
    pinned by a test: `aws:apigateway/deployment:Deployment` may be
    replaced when the plan is create-before-delete and the stage moves to
    the new deployment in the same plan. Nothing else, no label override.
  - **IAM gate:** any `aws:iam/*` resource in the plan fails.
  - **Policy pack (CrossGuard, mandatory):** every REST API has
    `disable_execute_api_endpoint`; every stage has an access-log
    destination in a gateway log group, `logging_level OFF` and
    throttling on `*/*`; **every stage that a base path mapping
    references** has exactly one web ACL association (a stage without a
    mapping is unreachable, because the default endpoint is disabled, so
    G5.3 can create the stage before G5.4 adds the ACL); every domain uses
    the AD-A4 TLS policy and `STRICT` (or the V-A5 fallback with a
    recorded reason); every log group has a KMS key and a retention;
    every integration with `connection_type VPC_LINK` has
    `insecure_skip_verification False`; every alarm carries a `runbook`
    tag; no `aws:ssm/*` resource.
- **AD-A11 Pipeline and repository controls (FR-A07, FR-A08, FR-A10,
  FR-A12, FR-A13).** Port the generic USI parts (research GR-8): the PR
  battery workflows, `pulumi-pr-guardrails.yml`, `pulumi-pr-commands.yml`,
  `codeql.yml`, `security-scans.yml`, `scheduled-drift.yml`,
  `initialize-stack.yml`, and `scripts/pulumi_ci_guardrails.py`,
  `pulumi_pr_comment.py`, `pulumi_command_preflight.py`,
  `run_pulumi_command.py`, `_pulumi_command_support.py`,
  `configure_github_repository_controls.py`,
  `_github_repository_controls.py`, `_github_environment_controls.py`.
  Not ported: `scripts/poc_*`, `scripts/service_execution_*`, the
  registry and workload stages of `self-deploy.yml`. The deploy workflow
  `deploy.yml` (on `repository_dispatch` `pulumi-pr-command`) has jobs
  `preflight` → `{env}_preview` (Preview role, `{env}-preview`, saved
  plan + sha256 artifact) → `{env}_destructive_diff` → `{env}_iam_gate` →
  `{env}_apply` (`{env}` environment, Apply role, sha256 re-checked, `pulumi
  up --plan`) → `comment_result`; `role-session-name`
  `gha-agi-{env}-{purpose}-${{ github.run_id }}`; no
  `role-duration-seconds` above 3600. PROD preflight requires a
  successful TEST apply of the same head SHA. Drift runs `pulumi preview
  --refresh --expect-no-changes` (USI `scripts/_pulumi_command_support.py`
  line 68). `autorelease.yml` follows PD-11.

  **Required checks (the ruleset):** `Ruff`, `Types`, `Maintainability`,
  `Coverage`, `Bandit`, `Dependency Audit`, `Secrets Scan`, `Actionlint`,
  `Zizmor`, `Yamllint`, `Hadolint`, `Dependency Review`, `CodeQL (python)`,
  `CodeQL (actions)`, `Structural Preview`, `Destructive Diff Gate`,
  `IAM Gate`, `Policy`, `Contract Schema`. Each name equals a job that
  exists by G3.3 (`Contract Schema` validates `contracts/schema/` and
  every file under `contracts/`, and passes with only the schema
  present), and a unit test in G2.2 pins the list against the workflows.
- **AD-A12 Gate model and order against the USI gates (FR-A22, FR-A23,
  FR-A25; D-6; D-A2; CR-A1).** Three gateway gates:
  - **Gate A-0 (pipeline ready):** rows 1-13 done; `/pulumi test plan` on
    an empty-diff head succeeds; ruleset and environments read back.
  - **Gate A-T (TEST front door):** rows 20-24 applied; the campaign, run
    inside the USI TEST daytime window (PD-13); probes are
    unauthenticated HTTPS and TLS from the runner; evidence reads run
    under the Drift role in `test-drift`; only step 9 uses the Apply role:
    1. preview contract checks pass (AD-A3);
    2. `GET https://user.vilnacrmtest.com/<health path>` returns the
       service's response, and the request id is found in the access log
       (Logs Insights, Drift role);
    3. the default `execute-api` URL returns 403;
    4. the ALB DNS name resolves only to private addresses, and a TCP
       connect from the runner to port 443 fails;
    5. TLS: 1.3 and 1.2 (ECDHE GCM) succeed; 1.1 and a 1.2 CBC suite fail;
       an SNI/Host mismatch is rejected (`STRICT`);
    6. WAF: a known-bad-input probe is blocked, with the terminating rule
       in the WAF log; `GetSampledRequests` shows samples for each rule
       that matched; the `authorization` header is redacted;
    7. rate: a burst above PD-3 gets 429; the token-path rate rule blocks
       after its limit inside one window;
    8. access-log lines carry every AD-A5 field and no header or body;
    9. `SetAlarmState` on each alarm reaches the topic;
    10. two consecutive scheduled drift runs (weekday daytime) are clean
        and their probes succeed;
    11. after at least seven days of WAF logs, a reviewed PR switches
        `AWSManagedRulesCommonRuleSet` to block, with any rule override
        justified from the logs (PD-8);
    12. the evidence bundle (run URLs, artifact sha256s) of steps 1-10 is
        attached to the G5.6 PR and handed to the USI owner for USI S4.6
        step 17 as soon as step 10 passes. Step 11 is **not** part of the
        step-17 bundle, so it never holds the USI campaign; it must pass
        before gate A-P. Step 10 holds step 17 for two weekday drift runs (CR-A1).
  - **Gate A-P (PROD front door):** gate A-T passed; USI gate 2 passed and
    the USI PROD workload applied (USI row 52); the PROD certificate
    for `user.vilnacrm.com` issued (G4.2, D-A3); the PROD contract pinned
    (G6.1); the D-A7 PROD values confirmed by the user in the G6.2 PR;
    then the same campaign in PROD (daily schedule), with step 11 already
    done.

  **Order against the USI ordered list (USI `epics-stories.md`):**

  | Gateway row | Must happen | USI row or step |
  | --- | --- | --- |
  | 15 (G4.1 TEST certificate) applied and handed over | before | row 42 (XP-11 needs the XP-10 ARN), hence before row 43 (gate 1) |
  | 19 (XP-A7 TEST descriptor) | after | row 43, S4.6 step 20 (D-A2) |
  | 20-25 (TEST front door, gate A-T steps 1-10 and 12) | before | S4.6 step 17, which USI runs after step 20 and holds for gate A-T step 10, two weekday drift runs (CR-A1) |
  | 27 (G4.2 PROD certificate) applied and handed over | before | row 49 (XP-15), hence before row 52 (gate 2a) |
  | 28 (XP-A7 PROD descriptor), 30-32 (gate A-P) | after | row 52 (gate 2b and the PROD apply) |

  USI S4.6 step 17's "S5.16 has merged" means gateway row 24 applied and
  row 25's evidence published. USI gate 2's "S5.16 with S4.6 step 17
  evidence if PROD is publicly exposed" is met by row 25.
- **AD-A13 Dependabot PRs (FR-A24; PD-10).**
  - **#33** (super-linter 7.1.0 → 8.3.1): **close.** G2.1 removes the
    super-linter workflow, which never fails a PR (`continue-on-error`)
    and pushes with an App token on PR events; its checks fail anyway
    (GR-5).
  - **#32** (virtualenv in `poetry.lock`): **close.** G3.1 replaces Poetry
    with a uv lockfile (PD-2); pip-audit in G3.2 gates every resolved
    version, including any virtualenv advisory.
  - **#26** (all-deps group, `pulumi-aws` 6.62.2): **close.** It stays on
    the 6.x line; G3.1 pins `pulumi-aws` 7.23.0, the version this plan
    verified for `integration_target`. No checks ran on its head.
  - Rebasing any of them would produce a change G2.1 or G3.1 deletes.
    Each is closed with a comment that names the superseding story.
- **AD-A14 KMS (FR-A06; D-A4; D-A9).** By D-A4, one BI-owned symmetric CMK
  per environment for the two log groups and the topic, created by the
  governance stack (D-A9). Key policy
  statements: the account root (administration through BI only);
  `logs.eu-central-1.amazonaws.com` with `kms:Encrypt*`, `Decrypt*`,
  `ReEncrypt*`, `GenerateDataKey*`, `Describe*`, conditioned on
  `kms:EncryptionContext:aws:logs:arn` equal to the two log-group ARNs;
  `cloudwatch.amazonaws.com` and `sns.amazonaws.com` for the topic
  (`kms:Decrypt`, `GenerateDataKey*`) with `aws:SourceAccount`; the
  gateway Apply role's `kms:DescribeKey` and `kms:CreateGrant` via `logs`.
  Rotation on. The D-4 runtime CMK is not used for the gateway.
- **AD-A15 Program structure and feature flags (FR-A09).**
  `pulumi/__main__.py` loads `app/config.py` (stack config, typed, closed)
  and builds, in order: `app/certificate.py` (AD-A2),
  `app/backend_contract.py` (AD-A3: load, offline checks, live invokes),
  `app/observability.py` (log groups, topic, alarms), `app/front_door.py`
  (VPC link, REST API, deployment, stage, method settings), `app/waf.py`,
  `app/domain.py` (domain, mapping, alias records). Two stack-config
  flags gate them: `features.certificate` (the certificate module) and
  `features.front_door` (every module after it; in TEST it may turn on
  only with a contract that cites the USI step-20 run, FR-A25). Both start `false` in
  both stacks; the TEST flags turn on in G4.1 and G5.1, the PROD flags in
  G4.2 and G6.1. So a PROD drift run before row 27 previews an empty
  program and needs no PROD grant beyond the backend, and a PROD stack
  never shows pending creates from TEST work. Each module exposes a pure
  builder tested with Pulumi mocks. `contracts/` holds the JSON schema
  and the per-stack contracts; `policy/` the CrossGuard pack;
  `docs/runbooks/` the runbooks.

## 4. IAM and state boundary; single-writer chains

- **No IAM in this repository.** The program declares no `aws:iam/*`
  resource, no `aws.apigateway.Account` and no `aws:ssm/*`.
- **State.** One stack per environment in the FR-A03 backend; no stack
  reads another stack's state.
- **Chains (one writer at a time):**

  | Chain | Files or objects | Order |
  | --- | --- | --- |
  | C-BI-A (seed operations shared with the USI C-BI queue, XP-A4; then governance and operator changes) | BI seed catalogs, `pulumi/seed/policy_registry.py`, `pulumi/seed/gateway_enrollment_amendment.py`, `scripts/operator_seed_installation.py`, the installed seed stack; `pulumi/repositories.governance.json`, `pulumi/infra/governance.py` (external-identity mode), the operator's governance identity policies | G1.1 → G1.2 → G1.3 → G1.4a → G1.5 → G1.6 → G1.4b → G1.7 → G1.8 (TEST before PROD inside each) |
  | C-controls | `scripts/configure_github_repository_controls.py`, `_github_*`, CODEOWNERS | G2.1 → G2.2 → XP-A3 |
  | C-pipeline | `.github/workflows/`, `scripts/pulumi_*`, `run_pulumi_command.py`, `Makefile` | G2.1 → G3.1 → G3.2 → G3.3 → G3.4 → G3.5 |
  | C-policy | `policy/` | G3.3 (later rule changes only with the story that needs them, in C-program order) |
  | C-program | `pulumi/__main__.py`, `pulumi/app/*`, stack config | G3.1 → G4.1 → G5.1 → G5.2 → G5.3 → G5.4 → G5.5 → G5.6 (step-11 rule switch) → G4.2 → G6.1 → G6.2 |
  | C-contract | `contracts/` | G3.3 (schema) → G5.1 → G6.1 |

## 5. Validation

| ID | What is verified | Method | Story | Fallback |
| --- | --- | --- | --- | --- |
| V-A1 | REST API → VPC link V2 → internal ALB works in `eu-central-1` | docs (GA-1, GA-2) + live TEST (gate A-T step 2) | G5.3, G5.6 | NLB variant (AD-A4), new plan revision |
| V-A2 | `integration_target` takes the load balancer ARN (not the listener ARN the CloudFormation reference names) | provider source (GR-17) + docs (GA-1) + TEST preview and apply | G5.3 | the listener ARN, if the service rejects the load balancer ARN; recorded |
| V-A3 | The exact caller permissions of `CreateVpcLink` (V2) | simulator matrix in G1.4b + the first TEST apply; CloudTrail read-back by the BI owner | G1.4b, G5.3 | add only the denied action, by a governance grant change inside the admitted policy set |
| V-A4 | API Gateway verifies the ALB certificate against the `uri` host | TEST (gate A-T step 2) | G5.6 | — (a failure is a STOP) |
| V-A5 | `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` with `STRICT` on a Regional custom domain through `pulumi-aws` 7.23.0 | provider source (GR-17) + TEST apply | G5.5 | `TLS_1_2`, recorded |
| V-A6 | WAF logging succeeds with the BI pre-created resource policy and no `logs:PutResourcePolicy` | TEST apply | G5.4 | STOP; a new user decision (for example WAF logs to an S3 bucket); `logs:PutResourcePolicy` on `*` is excluded by D-A5 |
| V-A7 | Which ACM actions support `aws:ResourceTag`, `acm:DomainNames` and `acm:ValidationMethod` (GA-16) | Service Authorization Reference (ACM), per action | G1.4a | user decision (AD-A7), not defaulted |
| V-A8 | Which read actions lack resource-level support (`elasticloadbalancing:Describe*`, `ec2:Describe*`, `logs:DescribeLogGroups`, `logs:GetQueryResults`, `wafv2` list and capacity, `logs:CreateLogDelivery`) | Service Authorization Reference JSON (as the USI plan fetched it, revision 12) | G1.4a, G1.4b | none: an action with resource-level support gets exact resources |
| V-A9 | Access logging works with the scoped CloudWatch role and a KMS log group | TEST (gate A-T step 8) | G1.5, G5.6 | the AWS managed policy, only by user decision |
| V-A10 | The BI owner accepts the seed inventory extension of D-A1: the new seed-created service principal kind, the count and kind changes in `policy_registry.py`, and the Add-row and activation validators in `operator_seed_installation.py`. #285 avoided such an extension (GR-19). | BI owner, G1.1 review | G1.1 | STOP; escalate to the user. There is no silent fallback to an independent stack. |
| V-A12 | Every governance ceiling, after the D-A9 admission, renders at ≤ 6144 characters in canonical JSON | G1.1 render test (`policy_registry` `canonical_json`, the registry's 6144 check) | G1.1 | STOP; OQ-11. Today the Apply ceiling fails: 5752/5762 + the additions |
| V-A11 | The API Gateway condition key `apigateway:Request/DisableExecuteApiEndpoint` on `/restapis` creates | docs (GA-7) + simulator | G1.4b | the policy pack alone enforces it |

## 6. Well-Architected mapping

| Pillar | Where |
| --- | --- |
| Security | AD-A1 (OIDC trust, no `pull_request`, seed-owned guards created with each role), AD-A6 (WAF), AD-A4/AD-A5 (TLS, no execute-api, no data trace), AD-A7 (least privilege, denies), AD-A9 (scoped logging role), AD-A14 (KMS), FR-A08 and PD-11 (no PAT, no App private key, SHA pins). Secret rotation: the plan creates no secret; the only long-lived secret the repository used (the App private key) is dropped (PD-11). |
| Reliability | two AZs (USI subnets), VPC-link probe (FR-A13), RTO PD-6, retained certificate and DNS, replicated state (PD-12) |
| Operational excellence | saved plans, drift, alarms with runbooks, gate campaigns, feature flags (AD-A15) |
| Performance efficiency | Regional endpoint, no cache, latency alarm, NFR-A06 |
| Cost optimization | one web ACL, ≤ 1,500 WCU, no paid groups, PD-5 retention |
| Sustainability | no idle compute added; the gateway is serverless |
