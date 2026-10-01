---
artifact: architecture
workflow: _bmad/bmm/workflows/3-solutioning/bmad-create-architecture (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 7 (2026-10-01: readiness round 3 R3-1…R3-6 and nits resolved)
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
  │    ├─ the dedicated governance Apply role (D-A11): GitHubGovernanceApply-
  │    │    api-gateway-infrastructure-{env}, its ceiling, guard and identity
  │    ├─ the D-A9 admission, re-scoped by D-A11: exact gateway entries in the
  │    │    shared Preview/Drift ceilings, the operator bindings and guards
  │    └─ registration in pulumi/seed/catalogs/{env}.json (G1.1 source, G1.2 install)
  ├─ governance stack, external-identity mode, gateway target under the
  │    dedicated Apply role (D-A9, D-A11):
  │    identity grants (G1.3 basic, G1.4a, G1.4b, G1.7, G1.8),
  │    backend: state bucket, replica, Pulumi secrets key (G1.3),
  │    gateway CMK (G1.6, D-A4), AWS::ApiGateway::Account (G1.5), and,
  │    under D-A12 branch B only, the resource-scoped WAF-log resource
  │    policy (G1.5b, rows 21a and 31b); under branch A the human seed
  │    operator writes it once (account-scoped; row-16 slot)
  ├─ operator stack (github-ci-bootstrap): the shared governance Preview/Drift roles' gateway
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
  | Identity grants, backend, CMK | written by governance under `GitHubGovernanceApply-{env}` | written by governance too (D-A9), in an external-identity mode, under the dedicated `GitHubGovernanceApply-api-gateway-infrastructure-{env}` (D-A11) |
  | Trust | Preview and Drift also trust the `main` ref (GR-20) | exactly one environment subject per role (PD-14), no `pull_request` |
  | Protection of the new policies | the shared denies `668edd62…` and `415affc4…` (TEST; `94b8d964…` and `e59053be…` in PROD) | unchanged and sufficient: every new policy sits under `policy/issue215-seed/{env}/*`, which those denies already cover (BI `pulumi/seed/README.md` lines 146-147). The roles, like USI's, are not listed in `668edd62…`. Listing them would rewrite 21 existing guard documents per account, so it is not done. |

  - **Source packet (G1.1).** A new amendment module,
    `pulumi/seed/gateway_enrollment_amendment.py`, is modelled on
    `test_poc_prerequisite_amendment.py`. It pins, per environment:
    - the baseline catalog hash. This is the result catalog of the seed
      operation just before the gateway's slot in the shared queue
      (CR-A2: after USI row 34 S5.7 and before USI row 42 S5.18a/XP-11).
      It is downstream of #284's `ff2eaf29…` (TEST). The origin/main pin
      `ef419680…` is **never** a valid baseline: installing on it would
      precede #284 and invalidate #284's pinned template `8b86a7ff…`.
      PROD's baseline is likewise the result catalog in force at the PROD
      slot (`d4b56073…` unless an earlier operation changed PROD);
    - the digest of the complete installed seed template at that slot, as
      #284 pinned `8b86a7ff…` for its own TEST baseline;
    - the result catalog hash;
    - the exact list of Add rows and of the D-A9/D-A11 admission Modify rows.

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
      Add rows and the exact in-place Modify rows of the shared Preview/Drift ceilings (`C-GitHubGovernancePreview`, `C-GitHubGovernanceDrift`) and the five operator executor guards;
    - a gateway activation packet and validator that accept exactly the
      gateway trust Modify rows. Today's activation validator requires
      exactly the three executor trusts (lines 433-462).

    Finally it updates the README counts. CATALOG_HASHES does **not** move
    in this PR (#284 order).
  - **Verifier count changes, per environment.** The baseline is 55
    policies, 24 principals and 21 existing roles (`policy_registry.py`
    lines 347-362).
    - **Principals:** 24 → 30: Preview, Apply, Drift, replication,
      logging, and the dedicated governance Apply role (D-A11); no
      ConfigRead reader (D-A10).
    - **Existing roles:** stay 21.
    - **Seed-created principals:** 3 → 9. `verify_enrollment` returns a
      fixed 3 (line 502). The mixed-phase verifier reports the 3
      executors in their observed phase and 6 disabled gateway principals.
      After activation, `verify_active_enrollment` reports 9 active
      seed-created principals (if the executors are active).
    - **Policies:** 55 → **67**, not the 66 first estimated for OQ-11 (a):
      - 55, the baseline;
      - + 4 ceilings/boundaries: CI, replication, logging, and the
        dedicated governance Apply ceiling;
      - + 6 guards: CI Apply, Preview, Drift, replication, logging, and
        the dedicated governance guard;
      - + 2 identity policies: the logging role's, and the dedicated
        role's seed-owned identity.

      The 66 estimate counted one ceiling and one guard for the new role
      but no identity. Its identity is seed-owned (see "Governance
      admission"), so it is a seed policy. An operator-written identity
      would give 66, but it would need the operator's role lists amended
      too. The CI and replication roles' identity documents are
      governance-owned, so they are not seed policies. The shared-ceiling
      and operator-guard amendments change existing documents in place and
      add no policy.
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
       or dynamic row; the exact in-place Modify rows of the shared Preview/Drift ceilings (`C-GitHubGovernancePreview`, `C-GitHubGovernanceDrift`) and the five operator executor guards are the only exception. Those Modify
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
       `aws:SourceAccount`. The replication role also carries
       `aws:SourceArn` = `arn:aws:s3:::pulumi-api-gateway-infrastructure-{env}-state`,
       as BI's `_replication_assume_role_policy` does (`pulumi_state.py`
       lines 123-142); the activation validator asserts both conditions.
       For the dedicated governance Apply role,
       the BI governance trust of D-A11 (environment
       `{env}-governance-api-gateway-infrastructure`).
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
    `s3.amazonaws.com` with `aws:SourceAccount` and `aws:SourceArn` = the
    gateway state bucket ARN (BI `pulumi_state.py` lines 123-142); the
    logging role trusts only `apigateway.amazonaws.com` with
    `aws:SourceAccount` (V-A9).
  - **ConfigRead roles: none (D-A10).** The pipeline reads role ARNs and
    backend names from protected-environment variables. Adding a reader
    later needs a reviewed seed catalog amendment (a new principal, its
    guard and the count change) and a CI-secret owner; it is not planned.
  - **Governance admission (D-A9, D-A11), in the same G1.2 change set
    per account.** Governance owns the gateway's grants, backend, CMK and
    account settings, as it does for USI (D-A9). It runs in a new
    external-identity mode (a reviewed BI code change), in which it reads
    the seed-created gateway roles and creates none. It also creates no
    `CiConfiguration`: no CI secrets and no ConfigRead roles (D-A10;
    today `RepoGovernance` creates them for every catalog repository,
    `governance.py` lines 657 and 765-778). Every extension names exact
    ARNs (the #284 FR6 precedent), except the four forms the user accepted
    in D-A14, listed below, under the BI owner's review
    and `@Kravalg`'s approval. By D-A11 the gateway's governance **apply**
    runs under a dedicated role. USI's `ceiling/GitHubGovernanceApply` and
    `G-GitHubGovernanceApply` (including `8c068aaa…`, `5366ec11…` and
    `dc27f076…`) are **not changed**.
    - **Dedicated governance Apply role (D-A11).**
      `GitHubGovernanceApply-api-gateway-infrastructure-{env}`. It follows
      the BI pattern `GitHubGovernance{Purpose}-{env}` of
      `governance_automation.py` line 694, with the target repository
      inserted; it is ≤ 64 characters, and the BI owner may shorten it.
      It is a seed-created principal of the new service kind: created with
      disabled trust, then activated (AD-A1 steps 3-6).
      - **Trust**, mirroring `governance_trust_policy`
        (`governance_automation.py` lines 343-395): the BI repository
        `VilnaCRM-Org/bootstrap-infrastructure` with its immutable ids,
        `aud` `sts.amazonaws.com`, `workflow` "Pulumi PR Command Runner",
        `ref` `refs/heads/main`, and `job_workflow_ref` set to
        `pulumi-governance-account.yml@refs/heads/main`. The one difference
        is the environment: `{env}-governance-api-gateway-infrastructure`
        (`sub` and `environment` claims), instead of the USI apply's
        `{env}-governance`. So a USI governance job cannot assume the
        gateway role, and the gateway job cannot assume the USI role.
      - **Ceiling**
        `policy/issue215-seed/{env}/ceiling/GitHubGovernanceApply-api-gateway-infrastructure`
        (planning name). Its statements have the shape of the USI ceiling,
        with gateway resources only:
        - the generic IAM and STS statement on `*`, of `e1ba4aab…`'s
          shape **without** `iam:UpdateAssumeRolePolicy`, `UpdateRole`,
          `UpdateRoleDescription`, `TagRole` and `UntagRole`. The dedicated
          role may not change any role's trust or tags (readiness F2). The
          remaining policy and role reads and policy writes are confined by
          its guard;
        - S3 on the exact gateway state and replica buckets;
        - KMS management, `CreateKey` and `TagResource`, conditioned on
          `Repository = api-gateway-infrastructure`, the environment and
          `Purpose` ∈ {`pulumi-secrets`, `gateway-logs`};
        - both exact key aliases;
        - role-policy attach and put on the three gateway CI roles with
          the gateway boundary, and put on the replication role with the
          replication boundary;
        - `iam:PassRole` of the replication role to S3, and of
          `ApiGatewayCloudWatchLogs-{env}` to `apigateway.amazonaws.com`;
        - `apigateway:GET`/`PATCH` on `/account`;
        - for the WAF-log resource policy, **no `logs:PutResourcePolicy`
          on `*`** for this or any CI or governance role (D-A12). V-A8
          decides the branch in G1.1 (row 8). The scoped form is a
          **resource-scoped** CloudWatch Logs resource policy on the exact
          log-group ARN: pinned `pulumi_aws` 7.23.0
          `cloudwatch/log_resource_policy.py` lines 33-35, 85 and 108-111
          take exactly one of `policy_name` or `resource_arn`, "attached per
          log group resource ARN".
          - **(A)** no scoped form, or V-A6 shows WAF logging rejects a
            resource-scoped policy. The reviewed non-root human seed
            operator writes an account-scoped policy for
            `aws-waf-logs-api-gateway-infrastructure-*` once, outside CI,
            as the service-linked roles are handled. It takes its own
            XP-A4 slot before row 16, with the BI owner as owner and
            evidence (the written document, a `DescribeResourcePolicies`
            readback, `@Kravalg` approval). This ceiling and identity
            carry **no** `logs:` statement under branch A.
          - **(B)** a scoped form exists. This ceiling and identity gain
            `logs:PutResourcePolicy` on exactly the
            `aws-waf-logs-api-gateway-infrastructure-{env}` log-group ARN,
            and `logs:DescribeResourcePolicies` (form 1 of D-A14) for the
            governance refresh. Because a resource-scoped policy needs the
            log group, which the CI Apply role creates in G5.2 (TEST) and
            G6.2a (PROD), governance writes it in its own rows, G1.5b:
            row 21a (TEST, after row 21, before row 23) and row 31b
            (PROD, between G6.2a and G6.2). Governance never creates the
            log group;
        - the governance backend: the shared `governance/` prefix
          statements (`69f23143…`, `d4192129…` reused); object read and
          write only on the gateway stack's **exact** paths (form 3 of
          D-A14), following the layout of the BI operator bindings
          (`read_objects`, `write_checkpoints`):
          `governance/.pulumi/stacks/governance/{stack}.*` (`.json`, `.json.bak`
          and `.pulumi-tags`, as BI's operator `read_objects` list them),
          `governance/.pulumi/history/governance/{stack}/*`,
          `governance/.pulumi/backups/governance/{stack}/*`, and
          `governance/.pulumi/locks/organization/governance/{stack}/*`,
          where `{stack}` = `{env}-api-gateway-infrastructure`; a read of
          `governance/.pulumi/meta.yaml`; and the governance secrets key
          by its **exact key ARN**, which G1.1 pins from an authenticated
          `kms:DescribeKey` of `alias/pulumi-platform-bootstrap-{env}`,
          instead of reusing `94a9f77e…` (`key/*` with
          `kms:ResourceAliases`, which is not a D-A14 form).

        It has no Secrets Manager statement (D-A10).

        The replica bucket names are the deterministic names of BI
        `pulumi_state.py` `_replica_bucket_name` (lines 267-275):
        `pulumi-api-gateway-infrastructur-3ca14569-eu-west-1-replication`
        (TEST) and `pulumi-api-gateway-infrastructur-8e7bb9a0-eu-west-1-replication`
        (PROD), 63 characters each.

        **Measured (revision 7): 5830 characters** in TEST and in PROD
        under branch A, and **6065 under branch B**. This is canonical JSON
        with `policy_registry.canonical_json`, rendered by
        `evidence/render_governance_sizes.py`. Headroom is 314 (A) and 79
        (B) characters. The dedicated ceiling and identity contain **none**
        of the four Apply-policy planning names; those appear only in the
        guard and the shared ceilings. Their remaining planning lengths are
        the gateway boundary paths in the attach/put conditions. The key
        id, the log-group ARN and the replica names are rendered at their
        real lengths. **The copied USI action lists are pinned:** the
        rendered documents are committed as
        `evidence/dedicated-apply-ceiling-{A,B}-{test,prod}.json` and
        `evidence/dedicated-apply-guard-{test,prod}.json`. These cover the
        generic IAM/STS list of `e1ba4aab…` minus the five role writes, the
        S3 list of `7a36d2ff…`, the KMS management list of `81c3805b…`,
        and the `6f28ae7e…`, `69f23143…` and `d4192129…` shapes. G1.1
        builds from these pinned documents, not from a live re-derivation
        of USI's ceiling. **Pre-named escalation:** if a G1.1 render with
        the final names exceeds 6144, G1.1 STOPs and the user decides; no
        compaction or form change is made silently. Revision 6's 5905,
        revision 5's 5737 and revision 4's 5866 are superseded.
      - **Guard**
        `policy/issue215-seed/{env}/guard/G-GitHubGovernanceApply-api-gateway-infrastructure`.
        It holds the six shared statements of USI's
        `G-GitHubGovernanceApply`, reused verbatim (TEST `dc27f076…`,
        `415affc4…`, `668edd62…`, `6bd9deea…`, `05f77e26…`, `d413d73a…`;
        PROD `dc27f076…`, `e59053be…`, `94b8d964…`, `0c46dd13…`,
        `05f77e26…`, `aec83856…`). It adds six new statements, gateway
        ARNs only. The first two have the `8c068aaa…`/`5366ec11…` shape:
        - `iam:*` denied outside the OIDC provider, the four Apply-role
          managed policies, the two gateway boundaries, and the five
          gateway roles;
        - policy writes denied outside those four policies;
        - `iam:UpdateAssumeRolePolicy`, `UpdateRole`,
          `UpdateRoleDescription`, `TagRole` and `UntagRole` denied on the
          five gateway roles (the pattern of BI operator guard
          `455fe8d0…`); `PutRolePermissionsBoundary` and
          `DeleteRolePermissionsBoundary` are already denied by
          `dc27f076…`;
        - `iam:AttachRolePolicy` and `DetachRolePolicy` denied on
          Resource `*` unless `iam:PolicyARN` is one of the four fixed
          Apply-role policies (`ArnNotEquals`);
        - `iam:AttachRolePolicy` denied on every gateway role except the
          CI Apply role, so the Apply-role policies cannot be attached to
          Preview, Drift, replication or logging (round-2 L4);
        - `iam:PutRolePolicy` and `DeleteRolePolicy` denied on the CI Apply
          role and the logging role. Inline names on Preview, Drift and
          replication cannot be constrained by an IAM condition key, so
          their fixed names are enforced by the registry's inline
          allowance (detective, at every `verify_active_enrollment`).

        **Measured (revision 6): 5565 characters** (TEST and PROD), with
        `SeedKmsKeyArn` in `d413d73a…`/`aec83856…` bound to a key ARN of
        the real length (`render_governance_sizes.py`). Revision 5's 5198
        did not have the attach deny of round-2 L4.
      - **Identity**
        `policy/issue215-seed/{env}/identity/I-GitHubGovernanceApply-api-gateway-infrastructure`.
        It is seed-owned and grants the same statements as the ceiling.
        **Measured (revision 7): 5830 (A) / 6065 (B) characters**, the
        same statements as the ceiling. It is seed-owned rather than
        written by the operator stack, as USI's governance identity is.
        Today's operator guards close the operator's role writes and role
        reads to a fixed role list (`455fe8d0…`, `fabd8598…` in TEST), so
        an operator-written identity would need those two lists, the
        operator's policy lists and the bindings' `role_write`/`role_read`
        amended. A change to this identity is a seed amendment in its own
        slot.
    - **Selection: one governance target per job and stack.** The
      reusable governance workflow (`pulumi-governance-account.yml`) runs
      the gateway as its own target:
      - a separate stack, `{env}-api-gateway-infrastructure`, of the same
        `governance` project, in the same backend
        `s3://pulumi-bootstrap-infrastructure-{env}-state/governance`. This
        is chosen so that `_validate_backend` (`governance_automation.py`
        line 270, which requires `/governance`) holds, and the shared
        Preview/Drift guards' lock deny (`167f653d…` TEST, `e90f172a…`
        PROD: puts and deletes allowed only under
        `governance/.pulumi/locks/*`) needs no amendment. Residual: USI's
        governance Apply role can still write anything under
        `governance/*` (`beb2b34d…`), including the gateway stack's state.
        Both run under the same BI owners and reviewers, and preview and
        drift detect tampering. The dedicated role is confined to its own
        stack paths;
      - apply in the protected environment
        `{env}-governance-api-gateway-infrastructure`, with `@Kravalg` as
        required reviewer, under the dedicated role;
      - preview and drift in the existing
        `{env}-governance-preview`/`-drift` environments, under the shared
        `GitHubGovernancePreview-{env}`/`GitHubGovernanceDrift-{env}`
        roles.

      **Workflow wiring (G1.3 step 2).** In `pulumi-governance-account.yml`
      the `resolve` job, which declares no environment, reads
      `vars.AWS_GOVERNANCE_{ENV}_APPLY_ROLE_ARN` (lines 128-137). The apply
      job assumes `needs.resolve.outputs.apply_role` (line 493) in the
      hard-coded `environment: {0}-governance` (line 433). The stack checks
      `test "${PULUMI_STACK}" = "${ACCOUNT}"` (lines 249-251, 392-394, 483-485, 621-623)
      allow only the account-named stack. An environment-scoped variable
      could not override the role, because `resolve` never sees it. The
      workflow change therefore resolves everything per target:
      - a new repository variable, `AWS_GOVERNANCE_{ENV}_APPLY_GATEWAY_ROLE_ARN`
        (proposed name), holding the dedicated ARN from the G1.2 readback;
      - `resolve` selects that variable for the gateway target, and
        `AWS_GOVERNANCE_{ENV}_APPLY_ROLE_ARN` for USI;
      - the apply job's environment is
        `{env}-governance-api-gateway-infrastructure` for the gateway
        target and stays `{env}-governance` for USI;
      - `PULUMI_STACK` is `{env}-api-gateway-infrastructure` for the
        gateway, and the four stack checks accept exactly that name for
        that target.

      A workflow fixture test shows that the gateway target's
      `role-to-assume` equals the dedicated ARN and the USI target's is
      unchanged. The USI target, its stack, environments and roles are
      unchanged. The BI repository admin creates the new environments and
      the new variable (G1.3).

      **Stack config and initialization (round-2 N6).**
      - New files `pulumi/governance/Pulumi.test-api-gateway-infrastructure.yaml`
        and `Pulumi.prod-api-gateway-infrastructure.yaml`, modelled on the
        existing `Pulumi.{test,prod}.yaml`, carry the target filter (the
        gateway only), the `secretsprovider`
        `awskms://alias/pulumi-platform-bootstrap-{env}?region=eu-central-1`,
        and the external-identity mode.
      - BI's stack-config preparation requires an existing versioned
        checkpoint (`scripts/_pulumi_stack_config.py` lines 147-152 and
        286-308). The governance workflow has no stack-init path, and the
        dedicated role trusts only GitHub OIDC from that workflow, so no
        human can assume it. A **live `pulumi stack init`** of each gateway
        governance stack therefore runs as follows:
        - **who:** the reviewed non-root human operator of XP-A1 (the seed
          operator class), authenticated by MFA outside GitHub CI;
        - **principal and enforcement:** the operator's own non-root role,
          a placeholder `<XP-A1-operator-role-arn>` that the operator fills
          in at run time. Its trust must allow the role to assume itself
          (self-assume), so that the narrowed session can be created. The
          role is assumed with a **session policy** passed on `AssumeRole`,
          so the effective permission is the role intersected with the
          session policy. The session policy is rendered and committed in
          G1.3 as `pulumi/governance/stack-init-session-policy-{env}.json`.
        - **call set**, derived from the pinned Pulumi CLI's DIY-backend
          `stack init`, existence check and checkpoint write:
          - `s3:GetBucketLocation` on the governance state bucket;
          - `s3:ListBucket` with `s3:prefix` `StringLike`
            `governance/.pulumi/stacks/governance/{stack}.*`, the pattern
            of BI `governance_automation.py` lines 291-296, so a missing
            `{stack}.json` answers 404, not 403;
          - `s3:GetObject`, `GetObjectVersion` and `PutObject` on
            `governance/.pulumi/stacks/governance/{stack}.*`;
          - `s3:GetObject` on `governance/.pulumi/meta.yaml`;
          - only if the pinned CLI takes a lock during init,
            `s3:PutObject` and `DeleteObject` on
            `governance/.pulumi/locks/organization/governance/{stack}/*`;
          - the governance secrets key, by exact ARN, for `kms:Encrypt`,
            `Decrypt`, `GenerateDataKey` and `DescribeKey`.

          A simulator run shows: `HeadObject` on a missing `{stack}.json`
          is allowed (404 path); `PutObject` on `{stack}.json` and
          `GetObject` on `meta.yaml` are allowed; `PutObject` on USI's
          `{env}.json` is denied.
        - **absence proof:** a prefix-restricted listing of
          `governance/.pulumi/stacks/governance/{stack}.` that returns 0
          keys, under the same session. This replaces the
          `pulumi stack ls --json --project governance` step of BI
          `docs/governance-stack.md` lines 240-247, which the narrowed
          session cannot run. Updating that BI document for the gateway
          target is an item the BI owner owns (G1.3).
        - **when:** TEST, then PROD, after G1.3 steps 2-3 and before
          step 4, each with its own per-action authorization and
          `@Kravalg`'s approval;
        - **evidence that the narrowed session was used:**
          - the session ARN from `aws sts get-caller-identity`;
          - the CloudTrail `AssumeRole` event id that carries the session
            policy;
          - a same-session probe: `head-object` on USI's
            `governance/.pulumi/stacks/governance/{env}.json` returns 403;
          - the readback of the new checkpoint object's `VersionId` and
            `ETag`.

          All of it is recorded in the G1.3 PR.
        - **secrets:** `stack init` writes an `encryptedkey` into the
          local stack config. It is never committed (BI
          `docs/governance-stack.md` lines 258-260). The committed
          `Pulumi.{env}-api-gateway-infrastructure.yaml` carries only the
          `secretsprovider` and the config keys.

        It changes no catalog and takes no seed slot.
      - The workflow's per-target change also covers the
        `PULUMI_PREVIEW_STACKS` and `PULUMI_DRIFT_STACKS` checks
        (`pulumi-governance-account.yml` lines 250-251, 393-394, 484-485, 622-623) and the admission
        call `deployment_worker_runtime.py --scope governance --environment`
        (lines 114-119; the other calls at 226-231, 369, 460, 521 and 598), which gains the target, and the receipt call `deployment_worker_receipt.py --scope governance --environment` (lines 680-689), which selects contract steps by scope and environment only and so gains the target too. The fixture test covers
        both targets.
    - **Shared Preview and Drift ceilings (still amended, in-place
      merge).** `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift`
      gain exact gateway reads by merging gateway entries into the
      statements they share only with each other:
      - TEST `6b2d4e23…` (role reads: five gateway roles);
      - `339af045…` (policy reads: four Apply-role policies and the two
        gateway boundaries; `f16f9131…` at `ff2eaf29…`);
      - `0d44e2be…` (bucket reads: two gateway buckets);
      - `2be63eb2…` (branch B only: `logs:DescribeResourcePolicies` added to
        the Resource-`*` read statement, for the governance refresh of the
        resource-scoped policy; an allowed non-exact form, because that
        action has no resource-level support, which V-A8 confirms; under
        branch A it is not added and `2be63eb2…` is untouched);
      - PROD: `ec801503…` (role reads), `6227eeae…` (policy reads),
        `3899b5e7…` (bucket reads), `2be63eb2…`.

      Two new statements are added: `apigateway:GET` on `/account`, and
      the gateway KMS read in **its own statement**. That statement is
      `kms:DescribeKey`, `GetKeyPolicy`, `GetKeyRotationStatus` and
      `ListResourceTags` on `key/*`, conditioned on
      `Repository = api-gateway-infrastructure`, the environment and
      `Purpose` ∈ {`pulumi-secrets`, `gateway-logs`}. USI's `011f1685…`
      is not merged, so there are no cross-combined tag lists
      (readiness F6). No
      backend statement changes, because the gateway stack stays under
      `governance/`. The statements shared with USI's Apply ceiling (TEST
      `69f23143…`, `d4192129…`, `94a9f77e…`; PROD `7741f40a…`,
      `8cc37f1f…`, `c911c28b…`) are not edited, so USI's Apply ceiling
      stays byte-identical. **Shared headroom (V-A13):** USI's own plan
      also adds each new USI managed-policy ARN to the same policy-read
      statement of both shared ceilings (USI `architecture.md` lines
      1947-1968; `epics-stories.md` lines 3598-3610). These additions come
      from S5.2, before the gateway slot, and after it from XP-11 (TEST)
      and S5.24a/b (PROD only). On TEST after #284, 2255 characters are
      free; the gateway takes 1598 under branch A or 1630 under branch B,
      leaving 657 (A) or 625 (B) for USI's TEST additions (S5.2 TEST and
      XP-11). On PROD, 2345 are free, and the gateway takes 1598 (A) or
      1630 (B), leaving 747 (A) or 715 (B) for USI's PROD additions (S5.2
      PROD and S5.24a/b, which are PROD only). G1.1 renders
      against the actual result catalog of the slot's predecessor (USI
      row 34), and CR-A2 gives the USI owner the remaining budget. A
      rebased USI operation that would push either shared ceiling above
      6144 is a STOP for both owners, and restructuring the ceiling is a
      user decision. **Measured (revision 7):**
      - branch A: 3789 → 5387 (TEST) and 3799 → 5397 (PROD); 3889 → 5487
        at #284's `ff2eaf29…`;
      - branch B: 3789 → 5419 (TEST) and 3799 → 5429 (PROD); 3889 → 5519
        at #284's `ff2eaf29…`.
       These
      come from `evidence/render_governance_sizes.py`, and all are under
      6144 (V-A12). Separate new statements for every read would not fit:
      the revision-4 audit measured 6648 / 6658 for that construction.
    - **Allowed non-exact forms: user-accepted, D-A14 (the complete list;
      anything else is a G1.1 STOP).**
      1. Actions without resource-level support on Resource `*`, each
         confirmed by V-A8: `sts:GetCallerIdentity`, `kms:ListAliases`,
         `access-analyzer:ValidatePolicy`, `logs:DescribeResourcePolicies`
         (branch B only),
         and `kms:CreateKey` (tag-conditioned). `logs:PutResourcePolicy`
         is never one of them (D-A12).
      2. KMS `key/*` with exact tag conditions (`Repository`,
         `Environment`, `Purpose`), because key ids are generated. The
         governance secrets key is named by its exact ARN instead.
      3. Governance state paths: the exact stack paths of the gateway
         governance stack.
      4. The `e1ba4aab…`-derived IAM reads and policy writes on `*` that
         the dedicated guard confines to exact ARNs.
    - **Operator bindings and operator guards (still amended).** The
      shared Preview and Drift roles read the gateway through
      operator-written identity policies, as for USI:
      `GitHubGovernancePreview-{env}-api-gateway-infrastructure-{iam,storage}`
      and `GitHubGovernanceDrift-{env}-api-gateway-infrastructure-{iam,storage}`.
      Their existing `-backend` documents are unchanged (same
      `governance/` prefix). These four policies are created only for the
      Preview and Drift purposes. Today `GovernanceAutomation` creates
      `{role}-{repo}-iam`/`-storage` for every purpose and every catalog
      repository (`governance_automation.py` lines 652, 739-764), which
      would attach `GitHubGovernanceApply-{env}-api-gateway-infrastructure-*`
      to USI's Apply role. G1.3's operator code change restricts a
      dedicated-target repository to the Preview/Drift purposes and gives
      it gateway-specific documents. These include the five gateway roles,
      including the logging role, and exclude ConfigRead roles; the four
      Apply-role managed policies and two boundaries; and no CI secrets.
      The four new policy ARNs are added to:
      - the catalog's `operator_bindings`: `policy_write`, `policy_read`,
        and `policy_read_resources`, which equals the `NotResource` list of
        `408cdbf9…`/`7a337042…`. The bindings are catalog metadata, not
        template rows;
      - the operator executor guards: TEST `0c5eed92…` (iam-write),
        `c18540fb…` (attachments), `408cdbf9…` (three iam-read guards);
        PROD `de33acbe…`, `0142330f…`, `7a337042…`.

      `c18540fb…` and `0142330f…` are Resource-`*` denies with an
      `ArnNotEquals iam:PolicyARN` condition; they are named in the
      recorded exception. The operator's role lists (`455fe8d0…`,
      `fabd8598…`) are unchanged.

      **Identity grants matching the ceiling admissions (round-2 N4).** A
      ceiling grants nothing by itself, and every governance `up` also
      assumes the drift role (`pulumi-governance-account.yml` lines 170-172).
      So the gateway operator documents
      `GitHubGovernance{Preview,Drift}-{env}-api-gateway-infrastructure-{iam,storage}`
      enumerate every read the shared ceilings admit for the gateway:
      - IAM reads on the five roles, four Apply-role policies and two
        boundaries;
      - bucket reads on the state and replica buckets;
      - the KMS read with `Purpose` ∈ {`pulumi-secrets`, `gateway-logs`};
        today's `governance_repo_storage_policy` covers only
        `pulumi-secrets` (`governance_automation.py` lines 551-567);
      - `apigateway:GET` on `/account`;
      - branch B only: `logs:DescribeResourcePolicies`. Today's metadata
        document covers only `sts`, `kms:ListAliases` and
        `ValidatePolicy` (lines 714-736). Under branch A no governance role
        refreshes a WAF-log policy, so no `logs:` read is admitted or
        granted (round-3 nit 5).

      G1.3's operator PR owns them. It lands and is applied before G1.5
      and G1.6. A test fails if any gateway admission in either shared
      ceiling has no matching grant in these documents.
    - **Fixed policy set.** G1.1 fixes, per environment:
      - the governance-owned gateway **managed** policies on the CI Apply
        role (`GitHubCiApply-api-gateway-infrastructure-{env}-pulumi-backend`,
        `-secret-read-deny`, `-certificate`, `-front-door`);
      - the names of the governance-owned **inline** policies on the CI
        Preview, Drift and replication roles. Governance writes those
        inline, as for USI (BI `ci_bootstrap.py` lines 813-853;
        `pulumi_state.py` line 613). The dedicated role's guard admits
        them through the role ARN, and the new seed-created kind allows
        exactly those inline names (`_verify_role` line 447 and
        `_verify_active_executor` line 524 reject inline grants today).

      Later grant stories (G1.4a, G1.4b, G1.7, G1.8) change only those
      documents, through governance PRs under the dedicated role. A grant
      that needs a new ARN is a new seed admission in its own slot.
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
       as for USI (D-A9). USI's governance Apply role is closed to the
       gateway by its guard (`8c068aaa…`, `5366ec11…`) and by its ceiling,
       which has no room (5752/5762 of 6144). So the gateway's governance
       apply runs under a dedicated seed-created role (D-A11), and only the
       shared Preview/Drift ceilings and the operator guards and bindings
       are amended.
    3. **ConfigRead:** none (D-A10). USI's readers carry `pull_request`
       and `ref` trust, and their CI secrets would need an owner.
    4. **The trust subject list** is stricter (PD-14).

    V-A10 asks the BI owner to **reverse a documented origin/main rule**,
    and to accept that before any G1.1 code is written. Origin/main
    enforces the opposite of the extension today:
    - `tests/unit/test_poc_installation_boundary.py` lines 63-79 pin 55
      policies, 24 principals and a 58-resource seed graph;
    - `specs/219-test-workload-capability/installability-stop.md` lines
      33-39 say to keep "the original catalog and activation protocol
      intact";
    - `scripts/operator_seed_installation.py` hard-codes the counts at
      lines 165, 204, 209, 462, 517 and 542.

    V-A10 stays a STOP (research GR-19, K-16).
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
  | Preview, Drift, Apply | `cloudwatch:DescribeAlarms`, `ListTagsForResource`; `sns:GetTopicAttributes`, `ListTagsForResource`, `ListSubscriptionsByTopic`, `GetSubscriptionAttributes`; `kms:DescribeKey` | `alarm:P-*`; `…:sns:…:P-alarms`; `G` | |
  | Preview, Drift, Apply | `elasticloadbalancing:DescribeListeners`, `DescribeLoadBalancers`, `DescribeTags`; `ec2:DescribeSecurityGroups`, `DescribeSecurityGroupRules`, `DescribeSubnets`, `DescribeVpcs` | `*`, the read-only exceptions without resource-level support (V-A8 confirms each from the Service Authorization Reference) | |
  | Drift | evidence reads: `logs:StartQuery`, `GetQueryResults`, `FilterLogEvents`; `wafv2:GetSampledRequests`; `ec2:DescribeNetworkInterfaces` (gate A-T step 8b; on `*`, a V-A8 read-only exception) | the two gateway log groups (`GetQueryResults` on `*` if V-A8 says so); `regional/webacl/P/*` | |
  | Drift | `cloudwatch:PutMetricData` | `cloudwatch:namespace` = `ApiGatewayInfrastructure/{env}` (the probe metric) | |
  | Apply | `apigateway:POST`, `PUT`, `PATCH` | `/restapis`, `/restapis/*`, `/vpclinks`, `/vpclinks/*`, `/domainnames`, `/domainnames/{fqdn}`, `/domainnames/{fqdn}/*`, `/tags/*`; creates and updates of `/restapis` require `apigateway:Request/DisableExecuteApiEndpoint` true (GA-7, V-A11). Writes on `/restapis/*` and `/vpclinks/*` carry `aws:ResourceTag/Owner = api-gateway-infrastructure` (and `aws:RequestTag/Owner` on create) where API Gateway supports the tag keys (V-A11). Where it does not, they are **accepted prefixes under NFR-A02**, because API Gateway generates the ids; this is recorded, not silent | |
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
  - the CloudWatch Logs resource policy allowing
    `delivery.logs.amazonaws.com` to write WAF logs, with
    `aws:SourceAccount` and `aws:SourceArn` conditions (V-A6). D-A5 is
    re-scoped by D-A12, per branch:
    - **branch A:** an account-scoped policy for the name pattern
      `aws-waf-logs-api-gateway-infrastructure-*`, written once by the
      human seed operator in its own XP-A4 slot before row 16;
    - **branch B:** a resource-scoped policy on the exact
      `aws-waf-logs-api-gateway-infrastructure-{env}` log-group ARN,
      written by governance in G1.5b (row 21a TEST, row 31b PROD), after
      the CI Apply role has created the log group.

    No CI or governance role ever holds `logs:PutResourcePolicy` on `*`.

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
    8a. latency (NFR-A06): at least 5 minutes after step 7's bursts end
        (one full WAF rate window), from one source IP at **≤ 5 requests/s** for
        at least 10 minutes. That is below the stage throttle (PD-3, 50/s)
        and below the WAF global rate rule (PD-4, 2,000 per 5 minutes, about
        6.7/s). Any 429 or 403 in the window fails the step. The latency
        is computed over the 2xx responses. The p99 of (`responseLatency` − `integrationLatency`) from
        the access log (Logs Insights, Drift role) is ≤ 100 ms;
    8b. availability (NFR-A05): a read-only describe shows the VPC link
        `AVAILABLE` and its ENIs (`ec2:DescribeNetworkInterfaces`, filtered
        to the link's requester; granted to the Drift role in G1.4b)
        spread over the two USI subnets in two Availability Zones. The
        **rebuild dry run** is defined as a `pulumi preview` of the TEST
        stack against a fresh local file backend (an empty state), under
        the Preview role. It shows that the program would recreate every
        resource from IaC, with no import and no manual input. Its
        duration is recorded against PD-6. No live delete takes place;
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
  | 8 (G1.1 source packet, rendered against the seed baseline) | after | USI row 34's result catalog exists (V-A13; CR-A2) |
  | 9 (G1.2 seed install, admission, activation and pin; TEST then PROD) | between | USI row 34 (S5.7) and USI row 42 (S5.18a, then XP-11), in the shared seed queue, after #284 (CR-A2; every later USI seed module rebases on the gateway result catalog) |
  | 15 (G4.1 TEST certificate) applied and handed over | before | row 42 (XP-11 needs the XP-10 ARN), hence before row 43 (gate 1) |
  | 19 (XP-A7 TEST descriptor) | after | row 43, S4.6 step 20 (D-A2) |
  | 20-25 (TEST front door, gate A-T steps 1-10 and 12) | before | S4.6 step 17, which USI runs after step 20 and holds for gate A-T step 10, two weekday drift runs (CR-A1) |
  | 27 (G4.2 PROD certificate) applied and handed over | before | row 49 (XP-15), hence before row 52 (gate 2a). G4.2 follows G5.6's step-11 PR in C-program, at least 7 days of WAF logs after row 23, so USI row 49 waits on that too (G4.2 Needs) |
  | 28 (XP-A7 PROD descriptor), 30, 31a-31c, 32 (gate A-P) | after | row 52 (gate 2b and the PROD apply) |

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
  only with a contract that cites the USI step-20 run, FR-A25). For PROD,
  `features.front_door` also takes the value `observability`, which builds
  only the contract checks and `app/observability.py` (log groups, topic,
  alarms). G6.2a applies that value first, so that under D-A12 branch B
  the WAF log group exists before governance writes its resource-scoped
  policy (row 31b), and G6.2 then sets `true`. Both start `false` in
  both stacks; the TEST flags turn on in G4.1 and G5.1, the PROD flags in
  G4.2, G6.2a (`observability`) and G6.2. So a PROD drift run before row 27 previews an empty
  program and needs no PROD grant beyond the backend, and a PROD stack
  never shows pending creates from TEST work. Each module exposes a pure
  builder tested with Pulumi mocks. `contracts/` holds the JSON schema
  and the per-stack contracts; `policy/` the CrossGuard pack;
  `docs/runbooks/` the runbooks.

  **Offline `ci` stack (readiness F3).** The required `Structural Preview`
  check runs on a local file backend with no credentials (AD-A11). With
  the flags on, the program makes live invokes: the AD-A3 contract checks,
  and the zone lookup that PR #34's certificate code performs. So a third
  stack, `ci` (`Pulumi.ci.yaml`), exists, as USI uses a credential-less
  `dev` stack (USI `.github/workflows/pulumi-pr-guardrails.yml` lines
  29-34). It has:
  - both flags on;
  - fixture contracts under `contracts/user-service-backend/ci.json` and
    a fixture zone;
  - a closed config key `stub_live_invokes: true`, under which
    `backend_contract.py` and `certificate.py` read fixtures instead of
    calling AWS.

  - an AWS provider that needs no credentials: dummy static keys
    (`pulumi-preview`) with `skip_credentials_validation`,
    `skip_metadata_api_check`, `skip_requesting_account_id` and
    `skip_region_validation`, which is the pattern of USI
    `pulumi/app/stack.py` lines 132-147. With the flags on, real
    resources are registered, and a credential-less default provider
    would fail.

  `config.py` builds that provider only for `ci`, and rejects the
  dummy-key provider settings in `test` and `prod`. It rejects
  `stub_live_invokes` in any stack except `ci`, and
  rejects `ci` with a real account id. The `ci` stack uses the local file
  backend and the `passphrase` secrets provider (committed
  `encryptionsalt`, fixed non-secret passphrase; it holds no secret), as
  USI's `dev` stack does. The config rules that forbid a passphrase
  provider and require the S3 backend URL exempt exactly `ci`. Tests:
  - a `ci` preview with both flags on and no AWS credentials succeeds;
  - `test` or `prod` with the dummy-key provider settings fails to load;
  - `test` or `prod` with `stub_live_invokes` fails to load;
  - the `test` and `prod` live checks cannot be disabled by any config
    key.

  `initialize-stack` and the deploy workflow never select `ci`.

## 4. IAM and state boundary; single-writer chains

- **No IAM in this repository.** The program declares no `aws:iam/*`
  resource, no `aws.apigateway.Account` and no `aws:ssm/*`.
- **State.** One stack per environment in the FR-A03 backend; no stack
  reads another stack's state.
- **Chains (one writer at a time):**

  | Chain | Files or objects | Order |
  | --- | --- | --- |
  | C-BI-A (seed operations shared with the USI C-BI queue, XP-A4; then governance and operator changes) | BI seed catalogs, `pulumi/seed/policy_registry.py`, `pulumi/seed/gateway_enrollment_amendment.py`, `scripts/operator_seed_installation.py`, the installed seed stack; `pulumi/repositories.governance.json`, `pulumi/infra/governance.py` (external-identity mode), the operator's governance identity policies | G1.1 → G1.2 → G1.3 → G1.4a → G1.5 → G1.6 → G1.4b → [G1.5b TEST, row 21a] → G1.7 → G1.8 → [G1.5b PROD, row 31b] (TEST before PROD inside each; brackets: D-A12 branch B only) |
  | C-controls | `scripts/configure_github_repository_controls.py`, `_github_*`, CODEOWNERS | G2.1 → G2.2 → XP-A3 |
  | C-pipeline | `.github/workflows/`, `scripts/pulumi_*`, `run_pulumi_command.py`, `Makefile` | G2.1 → G3.1 → G3.2 → G3.3 → G3.4 → G3.5 |
  | C-policy | `policy/` | G3.3 (later rule changes only with the story that needs them, in C-program order) |
  | C-program | `pulumi/__main__.py`, `pulumi/app/*`, stack config | G3.1 → G4.1 → G5.1 → G5.2 → G5.3 → G5.4 → G5.5 → G5.6 (step-11 rule switch) → G4.2 → G6.1 → G6.2a → G6.2 |
  | C-contract | `contracts/` | G3.3 (schema) → G5.1 → G6.1 |

## 5. Validation

| ID | What is verified | Method | Story | Fallback |
| --- | --- | --- | --- | --- |
| V-A1 | REST API → VPC link V2 → internal ALB works in `eu-central-1` | docs (GA-1, GA-2) + live TEST (gate A-T step 2) | G5.3, G5.6 | NLB variant (AD-A4), new plan revision |
| V-A2 | `integration_target` takes the load balancer ARN (not the listener ARN the CloudFormation reference names) | provider source (GR-17) + docs (GA-1) + TEST preview and apply | G5.3 | the listener ARN, if the service rejects the load balancer ARN; recorded |
| V-A3 | The exact caller permissions of `CreateVpcLink` (V2) | simulator matrix in G1.4b + the first TEST apply; CloudTrail read-back by the BI owner | G1.4b, G5.3 | add only the denied action, by a governance grant change inside the admitted policy set |
| V-A4 | API Gateway verifies the ALB certificate against the `uri` host | TEST (gate A-T step 2) | G5.6 | — (a failure is a STOP) |
| V-A5 | `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` with `STRICT` on a Regional custom domain through `pulumi-aws` 7.23.0 | provider source (GR-17) + TEST apply | G5.5 | `TLS_1_2`, recorded |
| V-A6 | WAF logging succeeds with the D-A12 policy and no `logs:PutResourcePolicy` on any CI role; under branch B, that WAF log delivery accepts a resource-scoped policy on the log group | docs in G1.1 (with V-A8), then the TEST apply | G1.1, G5.4 | if WAF rejects a resource-scoped policy, branch A applies (a recorded consequence of D-A12; no new decision). Found live at row 23, the G5.4 contingency rows run, in order 23-F3 (the XP-A1 operator deletes the 21a policy out of CI and removes it from governance state, while the branch-B reads still exist), 23-F1 (a seed amendment dropping the branch-B grants, with a CR-A2 rebase) and 23-F2 (the seed operator's account-scoped write); if WAF logging fails under branch A too, STOP and a new user decision (for example WAF logs to an S3 bucket) |
| V-A7 | Which ACM actions support `aws:ResourceTag`, `acm:DomainNames` and `acm:ValidationMethod` (GA-16) | Service Authorization Reference (ACM), per action | G1.4a | user decision (AD-A7), not defaulted |
| V-A8 | Which actions lack resource-level support (`elasticloadbalancing:Describe*`, `ec2:Describe*` including `DescribeNetworkInterfaces`, `logs:DescribeLogGroups`, `logs:GetQueryResults`, `wafv2` list and capacity, `logs:CreateLogDelivery`, `logs:DescribeResourcePolicies`), and whether `logs:PutResourcePolicy` has a log-group-scoped form (D-A12 branch A or B) | Service Authorization Reference JSON (as the USI plan fetched it, revision 12) | **G1.1 (row 8), before any form is chosen**; G1.4a, G1.4b | none: an action with resource-level support gets exact resources |
| V-A9 | Access logging works with the scoped CloudWatch role and a KMS log group, and API Gateway accepts the role's trust with `aws:SourceAccount` | TEST (gate A-T step 8); the trust condition by the G1.2 activation readback and the first `GetAccount` after G1.5 | G1.2, G1.5, G5.6 | by user decision, either the AWS managed policy or a trust without `aws:SourceAccount`. Because the logging role's identity and trust are seed-owned, the fallback is a seed amendment in its own XP-A4 slot (XP-A1) |
| V-A10 | The BI owner reverses origin/main's documented rule against extending the seed inventory, before any G1.1 code. Today the rule is enforced by `tests/unit/test_poc_installation_boundary.py` 63-79, `specs/219-test-workload-capability/installability-stop.md` 33-39, and the hard-coded counts in `operator_seed_installation.py` 165/204/209/462/517/542. The BI owner then accepts the new seed-created service principal kind, the count and kind changes in `policy_registry.py`, and the Add-row and activation validators. | BI owner, G1.1 review | G1.1 | STOP; escalate to the user. There is no silent fallback to an independent stack. |
| V-A12 | Every new or amended governance ceiling, guard and identity renders at ≤ 6144 characters in canonical JSON | Measured for revision 7 with `policy_registry.canonical_json` (`evidence/render_governance_sizes.py`, rendered documents committed under `evidence/`): dedicated Apply ceiling and identity 5830 (D-A12 branch A) / 6065 (branch B), TEST and PROD; dedicated guard 5565; shared Preview/Drift ceilings, branch A 3789/3799 → 5387/5397 (TEST/PROD; 3889 → 5487 at `ff2eaf29…`), branch B → 5419/5429 (5519); USI's Apply ceiling unchanged at 5752 / 5762. G1.1 re-renders with the final names | G1.1 | **Resolved by D-A11.** If any G1.1 render exceeds 6144: STOP and a user decision (pre-named); no wildcard compaction |
| V-A13 | The shared Preview/Drift ceilings stay ≤ 6144 with both plans' additions: USI's S5.2 (before the gateway slot), the gateway's, and USI's XP-11 and S5.24a/b (after it) | G1.1 renders against the row-34 result catalog; each later USI seed module re-renders on its rebased baseline (CR-A2) | G1.1, and each later USI module | STOP for both owners; restructuring the shared ceiling is a user decision |
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
