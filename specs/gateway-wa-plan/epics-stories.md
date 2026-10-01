---
artifact: epics-stories
workflow: _bmad/bmm/workflows/3-solutioning/bmad-create-epics-and-stories (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 6 (2026-10-01: readiness round 2 N1-N6/L1-L12 resolved; D-A12, D-A13, D-A14)
inputDocuments: [prd.md, architecture.md, decisions.md]
---

# Epics and stories: the API gateway Well-Architected track

## Requirements inventory

- 25 FRs (FR-A01…FR-A25) and 11 NFRs (NFR-A01…NFR-A11): `prd.md` §3-§4.
- Gateway decisions D-A1…D-A14 (2026-10-01; D-A1…D-A11 answer
  OQ-1…OQ-11, D-A12 and D-A13 answer readiness round 2, D-A14 records the
  user's acceptance of the four non-exact forms; no question is open);
  reused user decisions D-3, D-6, D-15 (and the D-4 consequence);
  cross-plan change requests CR-A1 and CR-A2; planning defaults
  PD-1…PD-14: `decisions.md`.
- External preconditions XP-A1…XP-A14 (gateway-local namespace, PD-1):
  `prd.md` §7.
- Repositories: AGI = `VilnaCRM-Org/api-gateway-infrastructure` (this
  repository); BI = `VilnaCRM-Org/bootstrap-infrastructure`; USI =
  `VilnaCRM-Org/user-service-infrastructure` (external only).

Every story follows these rules:

- **Source only.** A story changes source and tests in its owning
  repository through a reviewed PR. Live steps are listed separately and
  each needs the per-action authorization of `prd.md` §2.
- **Tests first.** Offline tests (pytest with Pulumi mocks, policy-pack
  tests, template and simulator-fixture tests) land with the code, at
  100% branch coverage for AGI (NFR-A09) and at BI's own gate for BI.
- **STOP** conditions halt the story and escalate to the named owner. No
  retry with wider permissions, removed checks or overrides.

## FR coverage map

| FR | Stories |
| --- | --- |
| FR-A01 | G1.1, G1.2 |
| FR-A02 | G1.1, G1.2 |
| FR-A03 | G1.3 |
| FR-A04 | G1.4a, G1.4b (TEST); G1.7, G1.8 (PROD) |
| FR-A05 | G1.1 (logging role), G1.2, G1.5 |
| FR-A06 | G1.6 |
| FR-A07 | G2.2, XP-A3 |
| FR-A08 | G2.1 |
| FR-A09 | G3.1 |
| FR-A10 | G3.2 |
| FR-A11 | G3.3 |
| FR-A12 | G3.4 |
| FR-A13 | G3.5, G6.3 |
| FR-A14 | G4.1 |
| FR-A15 | G4.2 |
| FR-A16 | G5.1, G6.1 |
| FR-A17 | G5.3, G6.2 |
| FR-A18 | G5.2, G5.3, G6.2 |
| FR-A19 | G5.4, G6.2 |
| FR-A20 | G5.5, G6.2 |
| FR-A21 | G5.2, G6.2 |
| FR-A22 | G5.6 |
| FR-A23 | G6.2, G6.3 |
| FR-A24 | G0.1, G0.2, G4.1 |
| FR-A25 | G5.1, G5.6 |
| NFR-A01, -A11 | G2.1, G3.2 |
| NFR-A02 | G1.4a, G1.4b, G1.7, G1.8 |
| NFR-A03, -A04 | G3.3, G5.2-G5.5, G5.6 |
| NFR-A05, -A06 | G5.6, G6.3 |
| NFR-A07 | G3.3, G5.4 |
| NFR-A08 | G3.3, G3.4, XP-A4 |
| NFR-A09 | G3.2 |
| NFR-A10 | G5.2, G5.6 |

## Epic list

| Epic | Goal | Stories |
| --- | --- | --- |
| E-G0 | Dispositions and inventory | G0.1, G0.2 |
| E-G1 | Bootstrap enrolment (BI; D-A1) | G1.1, G1.2, G1.3, G1.4a, G1.4b, G1.5 … G1.8 |
| E-G2 | Repository hygiene and controls | G2.1, G2.2 |
| E-G3 | Governed pipeline | G3.1 … G3.5 |
| E-G4 | Certificates | G4.1, G4.2 |
| E-G5 | TEST front door (USI S5.16, TEST) | G5.1 … G5.6 |
| E-G6 | PROD front door (USI S5.16, PROD) | G6.1 … G6.3 |

## Epic E-G0: Dispositions and inventory

### G0.1 (AGI owner, read-only): Legacy stack inventory (XP-A9)

- **Needs:** nothing.
- **Work:** the gateway owner lists, read-only, every place a gateway
  Pulumi stack could live (a Pulumi Cloud organisation, any S3 backend
  the owner used, the local backend of the PR #34 author) and, in each
  account, whether a bucket created by the template's `my-bucket` exists
  (bucket names with the Pulumi auto-name prefix `my-bucket-`). No
  credential, state content or secret is copied into the record.
- **Acceptance:** P: a dated record in the G0.1 issue lists each place and
  its result. N: an unlisted place makes the record incomplete. E: a found
  stack or bucket is not touched by G0.1. Under D-A6 it is retired later,
  after a read-only emptiness check, by a reviewed admin action that has
  its own per-action authorization.
- **STOP:** a found stack that holds a resource other than `my-bucket`, or
  a `my-bucket-*` bucket that is not empty → escalate to the user before
  G4.1.

### G0.2 (AGI maintainer): Close dependabot PRs #26, #32, #33 (AD-A13)

- **Needs:** rows 3 and 4 merged (G3.1 lockfile and pins; G3.2 pip-audit).
- **Work:** close each PR with a comment naming the superseding story and
  the reason in AD-A13. Closing is a live GitHub action that needs the
  per-action authorization of `prd.md` §2.
- **Acceptance:** P: three closed PRs, each with its reason. N: none is
  merged or rebased. E: if dependabot opens an equivalent PR against the
  new uv lockfile, it is reviewed normally.

## Epic E-G1: Bootstrap enrolment (BI)

Rules for every BI story:

- CODEOWNERS `@Kravalg`.
- A BI security review of identity changes, and a seed review of every
  seed change.
- One seed operation open at a time, in the queue shared with the USI plan
  (XP-A4), inside a freeze window from install to catalog pin.
- TEST, then PROD, inside the story unless stated otherwise.
- Every seed change set is installed by the human seed operator (XP-A1).
- Every governance change is a reviewed governance PR. Its gateway target
  is applied TEST then PROD in the `{env}-governance-api-gateway-infrastructure`
  environment under the dedicated role (D-A11), with `@Kravalg`'s
  approval.

D-A1 fixes the route for the roles: the seed creates and registers them.
D-A9 fixes the writer of their grants and of the non-role BI resources:
governance, as for USI. D-A11: the gateway's governance apply runs under a
dedicated seed-created role with its own exact-ARN ceiling. D-A10: no
ConfigRead roles.

### G1.1 (BI): Gateway seed enrolment packet (source only)

- **Needs:** D-A1, D-A9, D-A10, D-A11; V-A10 (the BI owner reverses
  origin/main's documented rule against extending the seed inventory,
  **before** any G1.1 code; AD-A1); **V-A8 resolved first** (the actions
  without resource-level support, and whether a log-group-scoped
  `logs:PutResourcePolicy` exists, which picks D-A12 branch A or B before
  any form is chosen); V-A12 (every new or amended ceiling,
  guard and identity ≤ 6144, measured in AD-A1); V-A13 (the shared
  Preview/Drift ceilings re-rendered against the row-34 result catalog).
- **Files:**
  - `pulumi/seed/gateway_enrollment_amendment.py` and its manifest (new,
    modelled on `test_poc_prerequisite_amendment.py` and
    `test_poc_prerequisites.json`);
  - `scripts/operator_seed_installation.py` (the gateway CREATE change-set
    validator, the activation packet and its validator, `_role_resource`
    beyond the three executors);
  - `pulumi/seed/policy_registry.py` (code paths for the new seed-created
    service kind; the mixed-phase verifier `verify_gateway_enrollment`
    (proposed name) for the window between CREATE and activation; exact
    active-trust verification; attachment rules; AD-A1);
  - tests (`tests/unit/test_seed_policy_registry.py` and a new
    `tests/unit/test_gateway_seed_amendment.py`);
  - the origin/main files that today enforce the opposite rule (readiness
    F7). Each changes only after V-A10:
    - `tests/unit/test_poc_installation_boundary.py` (lines 63-79 pin 55
      policies, 24 principals and 58 resources);
    - `specs/219-test-workload-capability/installability-stop.md` (lines
      33-39);
    - the hard-coded counts in `scripts/operator_seed_installation.py`
      (lines 165, 204, 209, 462, 517, 542);
  - `scripts/operator_seed_observation.py`, which exists on origin/main.
    Its `--active` mode comes only with #284 (`wt-boot-pr280` lines 185
    and 219). G1.1 adds the new kind's `--active` and mixed-phase
    handling.
- **Work:** AD-A1's source packet. The packet renders, per environment, the
  candidate result catalog and the candidate seed template. Their contents:
  - the five gateway principals (Preview, Apply, Drift, replication,
    logging) and the dedicated governance Apply role
    `GitHubGovernanceApply-api-gateway-infrastructure-{env}` (D-A11); no
    ConfigRead reader (D-A10);
  - four boundaries/ceilings, six guards and two seed-owned identity
    policies (logging role, dedicated governance role): 30 principals, 9
    seed-created, 67 policies per environment;
  - the re-scoped D-A9 admission (architecture AD-A1): exact gateway reads
    in `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift`, merged
    in place into the statements those two ceilings share only with each
    other (architecture AD-A1 lists the ids) and never into statements
    shared with USI's Apply ceiling, the four governance Preview/Drift gateway policy ARNs in the
    catalog's `operator_bindings`, and the five operator executor guards.
    USI's `G-GitHubGovernanceApply` and `ceiling/GitHubGovernanceApply`
    are unchanged;
  - the fixed set of governance-owned gateway documents that later grant
    stories may change: the Apply role's managed policy ARNs and the
    inline policy names on the Preview, Drift and replication roles, with
    the registry's inline-policy allowance for exactly those names.

  The packet pins the baseline catalog hash in force at its slot, the
  installed template digest, the result hash, the Add rows and the
  admission Modify rows. As in #284,
  this PR changes **neither** the active catalogs, nor `CATALOG_HASHES`,
  nor the active counts. Those change together in G1.2's pin PR.
- **Acceptance:**
  - P: `build_catalog()` from the pinned baseline reproduces the pinned
    result hash. With the candidate catalog's hash substituted for
    `CATALOG_HASHES[env]` (a test fixture) and a fixture `SeedKeyBinding`,
    the candidate passes `build_registry`. It passes the
    mixed-phase verifier against fixtures of the post-CREATE state, with
    the `GitHubOperator*` executors **active** (TEST today) and, separately,
    **disabled** (PROD, unless G1.2 step 1 observes them active), and the
    gateway principals disabled. It passes `verify_active_enrollment` against a fixture with
    every trust active, including the AD-A1 trusts and the dedicated
    role's governance trust. The rendered template adds exactly the
    expected logical ids. The rendered dedicated ceiling, guard and
    identity and the amended Preview/Drift ceilings are each ≤ 6144
    characters, and USI's Apply ceiling and guard are byte-identical to
    the baseline.
  - N: a test that compares every pre-existing statement, policy,
    principal, attachment and binding with the baseline finds no change
    (the re-scoped D-A9 entries are the only exception, and each adds only
    an exact gateway ARN or resource, or uses one of the four allowed
    non-exact forms that architecture AD-A1 lists). `verify_active_enrollment` refuses
    an inline policy name outside the fixed set on Preview, Drift or
    replication, and any inline policy on the Apply or logging role (P:
    exactly the fixed inline names pass). The mixed-phase verifier refuses an
    active gateway trust, a disabled trust on an executor **that G1.2 step 1
    observed active** (a PROD executor observed disabled is checked as
    disabled), and any changed pre-existing attachment. A simulator matrix of the rendered dedicated
    role (identity ∩ ceiling, with its guard) denies:
    - `iam:UpdateAssumeRolePolicy`, `UpdateRole`, `UpdateRoleDescription`,
      `TagRole` and
      `UntagRole` on each of the five gateway roles;
    - `iam:AttachRolePolicy` of any policy other than the four fixed
      Apply-role ARNs, including an AWS-managed admin policy;
    - `iam:PutRolePolicy` on the CI Apply and logging roles;
    - `iam:AttachRolePolicy` of any of the four fixed Apply-role policies
      to the Preview, Drift, replication or logging role (round-2 L4);
    - `logs:PutResourcePolicy` on `*` (both branches), and under branch B
      on any log group other than the gateway WAF log group (D-A12);
    - `s3:PutObject` on USI's governance checkpoint
      (`governance/.pulumi/stacks/governance/{env}.json`);
    - any IAM action on a USI or BI role.

    It allows `s3:PutObject` on the gateway stack's
    `{stack}.json`, `{stack}.json.bak`, `{stack}.pulumi-tags`, its
    history, backups and lock paths.

    The CREATE validator refuses a change set with any Modify,
    Remove, replacement, dynamic or extra Add row, except the exact Modify rows of the shared Preview/Drift ceilings and the five operator guards (the operator bindings are catalog metadata, not rows); any Modify row on USI's `G-GitHubGovernanceApply` or `ceiling/GitHubGovernanceApply` is refused. The activation validator
    refuses any row other than the gateway trust Modify rows, and any
    CI-role trust with a `pull_request` or `ref` subject, another
    repository id or a wildcard; the dedicated governance role's trust
    must name exactly the environment
    `{env}-governance-api-gateway-infrastructure` and the BI repository
    claims of `governance_trust_policy`. Replaying the module against its result fails.
  - E: the `GitHubOperator*` executor path is unchanged. Each boundary
    renders at ≤ 6144 characters (6144 passes, 6145 fails). Each role name
    is ≤ 64 characters, and every new policy basename is unique across the
    catalog regardless of path and case.
- **STOP:** V-A10 declined (escalate to the user; no fallback to an
  independent stack); a result that would change `dc27f076…` or any
  Resource-`*` deny other than the D-A9 operator guards `c18540fb…` /
  `0142330f…`; an admission entry that is not an exact ARN or exact
  resource (for example a prefix or wildcard), other than the four
  allowed non-exact forms that architecture AD-A1 lists; any new or amended
  ceiling, guard or identity that renders above 6144 characters (V-A12;
  escalate, never compact).

### G1.2 (BI; human seed operator, live): Install, activate and pin (TEST, then PROD)

- **Needs:** G1.1 merged; **#284 merged and installed**, including its
  activation PR pinning `ff2eaf29…` and the `--active` mode of
  `scripts/operator_seed_observation.py` (the script itself is on main);
  CR-A2 accepted by the USI owner (the gateway slot after USI row 34 and
  before USI row 42); XP-A1; XP-A2; an XP-A4 slot per environment.
- **Work:** AD-A1 "Installation and activation", per environment:
  - absent-name checks, and the observed lifecycle phase (active or
    disabled) of each `GitHubOperator*` executor, recorded for the
    mixed-phase verifier;
  - the CREATE change set (exact Add rows enforced by the change-set
    validator, `TemplateURL` bound to its digest, plus the exact Modify rows of the shared Preview/Drift ceilings and the five operator guards under a
    temporary `Update:Modify` stack policy on those ids), the deny-update policy
    restored, a readback, and the mixed-phase verifier;
  - the activation change set (the gateway trust Modify rows only, under a
    temporary `Update:Modify` stack policy on those role ids), a readback
    and `operator_seed_observation.py --active`
    (`verify_active_enrollment`);
  - one reviewed pin PR. It writes the result catalog into
    `pulumi/seed/catalogs/{env}.json`, moves `CATALOG_HASHES[env]` to the
    result, activates the count, kind and attachment-rule changes, updates
    the README counts, and records the evidence as a PR comment (#284
    NFR8).

  The freeze window closes after the pin PR merges.
- **Acceptance:**
  - P: every readback equals the result catalog. The mixed-phase verifier
    passes after CREATE, and `verify_active_enrollment` passes after
    activation. The pinned hash
    equals the module's result.
  - N: the dedicated governance role refuses a token from
    `{env}-governance` (the USI apply environment), and USI's
    `GitHubGovernanceApply-{env}` refuses the gateway environment.
    Simulated trust evaluation refuses, for each CI role,
    `repo:VilnaCRM-Org/api-gateway-infrastructure:pull_request`,
    `…:ref:refs/heads/main`, another environment, another repository id
    and a fork. `iam:SimulatePrincipalPolicy` (BI identity) denies
    `iam:CreateRole` and `ssm:GetParameter` to each CI role.
    `iam:SimulatePrincipalPolicy` on the installed dedicated role
    reproduces G1.1's denies: no trust, role or tag update on the five
    roles, and no attach outside the four fixed ARNs.
  - E: no operator run happens between install and pin, except those the
    #284 runbook requires inside the window. The logging role's trust with
    `aws:SourceAccount` is accepted (V-A9).
- **Evidence:** both change-set listings and ids, the template digests,
  the readbacks, the verifier outputs, the absent-name results, and
  `@Kravalg`'s seed-review approval.
- **STOP:**
  - an existing role or policy with a target name;
  - a change set with any row outside the validator;
  - a partial result (reconcile it first; never replay a change set);
  - the live seed template or catalog differs from the pinned baseline;
  - **the PROD seed stack, or its baseline template, is absent or
    unobserved.** #284 was TEST-only, so PROD's installed state must be
    read first. Escalate to the BI owner and do not install.

### G1.3 (BI): Gateway backend (TEST, then PROD)

- **Needs:** G1.2 (roles, the dedicated governance role and the
  re-scoped admission installed); D-A9, D-A11, D-A13.
- **Work (governance, D-A9, D-A11, D-A13):** the FR-A03 bucket, replica
  and key, using BI's `PulumiStateBuckets` and `PulumiSecretsKeys`
  unchanged: AES256 with SSE-C blocked, the TLS-only bucket policy, and
  the existing key policy. Access is limited by the IAM roles and their
  boundaries. Replication follows PD-12 through `PulumiStateBuckets(…,
  manage_replication_role=False)`, an existing parameter (`pulumi_state.py`
  lines 308 and 581-586) that reads the seed-created
  `PulumiStateRepl-api-gateway-infrastructure-{env}` instead of creating
  it. The external-identity mode writes that role's fixed inline policy
  from BI's `_replication_role_policy` document (line 145). The mode also
  skips `CiConfiguration`: no CI secrets and no ConfigRead roles
  (`governance.py` lines 657 and 765-778; D-A10).
  1. A reviewed BI operator PR adds the shared governance Preview and
     Drift roles' gateway read policies
     (`GitHubGovernance{Preview,Drift}-{env}-api-gateway-infrastructure-{iam,storage}`,
     the ARNs G1.2 admitted). This includes an operator code change:
     the gateway documents enumerate every read the shared ceilings admit
     (architecture AD-A1, "Identity grants matching the ceiling
     admissions"): `apigateway:GET /account`,
     `logs:DescribeResourcePolicies`, and the KMS read for both
     `pulumi-secrets` and `gateway-logs`, beyond today's
     `governance_repo_storage_policy` (`governance_automation.py` lines
     551-567) and metadata document (lines 714-736). A test fails if any
     gateway admission in either shared ceiling lacks a matching grant.
     `GovernanceAutomation` today creates `{role}-{repo}-iam`/`-storage`
     for every purpose and every catalog repository (BI
     `governance_automation.py` lines 652, 739-764). For a dedicated-target
     repository it must create them for Preview and Drift only, with
     gateway-specific documents: the five gateway roles including the
     logging role, no ConfigRead role, the four Apply-role policies and
     two boundaries, and no CI secret. The existing `-backend` documents
     are unchanged.
  2. A reviewed BI code change adds governance's external-identity mode
     (it reads the seed-created roles and creates none) and **per-target
     selection**: the workflow wiring of architecture AD-A1. This covers
     the target-keyed `AWS_GOVERNANCE_{ENV}_APPLY_GATEWAY_ROLE_ARN` read in
     `resolve`, the per-target apply environment (line 433), and
     `PULUMI_STACK` with the four stack checks (lines 249, 392, 483, 621).
     A workflow fixture test shows that the gateway target's
     `role-to-assume` is the dedicated ARN and the USI target's is
     unchanged. `pulumi-governance-account.yml` runs the gateway as its
     own target: its own stack `{env}-api-gateway-infrastructure` of the
     `governance` project in the same `governance/` backend prefix (so
     `_validate_backend` and the shared guards' lock deny hold); apply in the
     environment `{env}-governance-api-gateway-infrastructure` under
     `GitHubGovernanceApply-api-gateway-infrastructure-{env}`; preview and
     drift in the existing `{env}-governance-preview`/`-drift`
     environments under the shared roles. The USI target is unchanged.
     **Per-stack target filter (readiness F5).** The governance program
     builds every repository in the catalog (`governance.py` lines
     969-972, 1033-1035; `governance/Pulumi.test.yaml` line 20 reads
     `repositories.governance.json`). So a new stack-config key selects
     the target repositories, and each stack builds only its own:
     - the existing `test`/`prod` stacks select USI only;
     - the gateway stacks select the gateway only.

     Negative tests: the USI stacks plan no gateway resource, and the
     gateway stacks plan no USI resource.
  2a. **Governance stack config and init (round-2 N6).** Add
     `pulumi/governance/Pulumi.test-api-gateway-infrastructure.yaml` and
     `Pulumi.prod-api-gateway-infrastructure.yaml`, each with the target
     filter, the `secretsprovider` and the external-identity mode. The
     workflow's per-target change also covers the `PULUMI_PREVIEW_STACKS`
     and `PULUMI_DRIFT_STACKS` checks (lines 250-251) and the
     `--scope governance --environment` admission call (lines 114-119).
     The live `pulumi stack init` of each gateway governance stack comes
     after step 3 and before step 4 (architecture AD-A1). The reviewed
     non-root human operator of XP-A1 runs it, TEST then PROD, with MFA.
     The operator's own role is assumed with the committed session policy
     `pulumi/governance/stack-init-session-policy-{env}.json`, which is
     the init session policy (`s3:GetBucketLocation` on the governance state bucket; `s3:ListBucket` with `s3:prefix` limited to `governance/.pulumi/stacks/governance/`, so a missing `{stack}.json` answers 404, not 403; `s3:GetObject`, `GetObjectVersion` and `PutObject` on `governance/.pulumi/stacks/governance/{stack}.*`; `s3:GetObject` on `governance/.pulumi/meta.yaml`; and the governance secrets key by exact ARN for `kms:Encrypt`, `Decrypt`, `GenerateDataKey` and `DescribeKey`). Each run has per-action authorization and `@Kravalg`'s
     approval. Acceptance: a simulator run of the session policy allows
     `HeadObject` on a missing `{stack}.json`, `PutObject` on
     `{stack}.json` and `GetObject` on `meta.yaml`, and denies
     `PutObject` on USI's `{env}.json`. The dedicated role cannot run it: it trusts only the
     workflow's OIDC, and the workflow requires an existing checkpoint
     (`scripts/_pulumi_stack_config.py` lines 147-152 and 286-308). The
     readback of the checkpoint's `VersionId` and `ETag` is recorded.
  3. The BI repository admin creates the protected environments
     `test-governance-api-gateway-infrastructure` and
     `prod-governance-api-gateway-infrastructure` (`@Kravalg` as sole
     required reviewer, `main` only). The admin also sets the repository
     variables `AWS_GOVERNANCE_{TEST,PROD}_APPLY_GATEWAY_ROLE_ARN` from the
     G1.2 readback. These are live admin actions with their own per-action
     authorization.
  4. A governance catalog PR adds the gateway to
     `pulumi/repositories.governance.json` in that mode. It creates the
     backend and writes the basic `pulumi-backend` and `secret-read-deny`
     or `read-only` documents (AD-A7, first row), applied TEST then PROD
     under the dedicated role.
  **How the catalog change is applied.** BI applies from the PR head,
  before merge, through `.github/workflows/pulumi-pr-command-runner.yml`.
  The step-4 PR's `/pulumi` run therefore applies the stacks that read
  `repositories.governance.json` in the runner's own order: for each
  environment, TEST before PROD, operator → governance → platform.
  - TEST: `operator_test` line 132, then `governance_test` line 154 (needs
    `operator_test`), then `platform_test` line 178.
  - PROD: `operator_prod` line 261, then `governance_prod` line 288, then
    `platform_prod` line 317.

  The governance account workflow checks out the PR head
  (`pulumi-governance-account.yml` lines 233-241).
  - The operator stack (`pulumi/github-ci-bootstrap/__main__.py` lines
    41-45 and 141-145 build `GovernanceAutomation` from the catalog)
    therefore creates the shared Preview/Drift gateway read policies of
    step 1 before the gateway governance target runs.
  - The runner's governance jobs must include the gateway target. That is
    step 2's per-target selection, and a workflow fixture test checks it.
  - Each environment's apply is `@Kravalg`-approved under the runner's
    protected environments, with the user's per-action authorization.
  - The USI governance stacks plan nothing new (the target filter).
  5. **Platform-stack apply (authorized step).** The platform stack derives
     the central-logging bucket policy from the same catalog
     (`infra/bootstrap_infrastructure.py` lines 18-30;
     `infra/logging_bucket.py` lines 165-178). Adding the gateway changes
     that policy, so a reviewed platform-stack plan shows only the
     gateway state bucket added as a logging source. It is applied TEST
     then PROD under the platform's own protected environments, each with
     its own per-action authorization.
- **Acceptance:**
  - P: the BI verifier reads back the bucket: versioning, AES256 default
    encryption with SSE-C blocked, public access blocked, the TLS-only
    policy, and replication to the replica through the seed-created
    replication role. It also reads back the key alias with the existing
    key policy. The first use of the backend is G3.4's `initialize-stack`
    (row 13). Every gateway admission in the shared ceilings has a
    matching operator-document grant (test).
  - N: a non-TLS request is denied by the bucket policy. A role whose
    identity has no grant on the gateway backend (for example a USI CI
    role) is denied by IAM and its boundary (simulator), since the bucket
    policy names no principals (D-A13). The governance plan creates no
    `aws:iam/role` and no CI secret. The operator plan creates no
    `GitHubGovernanceApply-{env}-api-gateway-infrastructure-*` policy, and
    USI's `GitHubGovernanceApply-{env}` attachment set is unchanged. A
    gateway preview under `GitHubGovernancePreview-{env}` can write its
    lock under `governance/.pulumi/locks/*`.
  - E: the rendered bucket, replica and key resources equal the USI
    backend's apart from names (no shared BI code change). A gateway
    governance stack with no versioned checkpoint fails stack-config
    preparation (step 2a not done).
- **STOP:** a governance plan that touches an ARN outside the G1.2
  admission (then a new admission in its own seed slot), that creates or
  deletes any role, or that runs the gateway target under USI's
  `GitHubGovernanceApply-{env}`.

### G1.4a (BI): TEST certificate and read grants

- **Needs:** G1.2, G1.3; V-A7, V-A8 resolved offline.
- **Work:** the AD-A7 rows marked **cert**, for `{zone}` =
  `Z04999481RZ4UQK2NANVH` and `{fqdn}` = `user.vilnacrmtest.com`, written
  by a governance capability PR (D-A9) that changes only documents in the
  admitted policy set. A new policy ARN would first need its own seed
  admission.

  The V-A7 per-action result and V-A8's Resource-`*` list are committed
  with their Service Authorization Reference source.
- **Acceptance (simulator matrix, BI identity, run URL recorded):**
  - P: each **cert** row is `allowed` for its role.
  - N: these are denied: `acm:RequestCertificate` for another domain or
    with `EMAIL` validation; `route53:ChangeResourceRecordSets` on
    `x._domainkey.user.vilnacrmtest.com`, on `other.vilnacrmtest.com` and
    with action `DELETE` on the validation name; `iam:CreateRole`,
    `iam:PassRole`, `iam:CreateServiceLinkedRole`, `ssm:GetParameter`,
    `ssm:PutParameter` and `secretsmanager:GetSecretValue`. Preview and
    Drift have no write.
  - E: a `ChangeResourceRecordSets` request without the name key is denied
    (`Null` guard).
- **STOP:** V-A7 shows that a needed read lacks tag-condition support
  (then a user decision, AD-A7).

### G1.5 (BI): Gateway account prerequisites (TEST, then PROD)

- **Needs:** G1.2 (the logging role and the admission); G1.3 (governance
  mode); XP-A5; XP-A12.
- **Work:** AD-A9. Governance (D-A9) sets `AWS::ApiGateway::Account` with
  the G1.2 logging role. The D-A5 WAF-log resource policy follows D-A12:
  - **branch A**, no scoped form: the human seed operator writes it once,
    outside CI, in its own XP-A4 slot (XP-A1). The BI owner owns it. The
    evidence is the written document, a `DescribeResourcePolicies`
    readback and `@Kravalg`'s approval;
  - **branch B**: governance writes it with `logs:PutResourcePolicy`
    scoped to the gateway WAF log group. If XP-A5 shows the API Gateway service-linked role missing, the
  human seed operator or the XP-A1 installer creates it, outside CI,
  before G5.3. The governance guard denies
  `iam:CreateServiceLinkedRole` for this service (`05f77e26…`).
- **Acceptance:**
  - P: `GetAccount` returns the logging role's ARN, and the SLR reads
    back.
  - N: the gateway Apply role is denied `apigateway:PATCH` on `/account`
    (simulator).
  - E: a `cloudWatchRoleArn` already set by another owner is a STOP, not
    an overwrite.
- **STOP:** XP-A12 finds another owner and no agreement; any role found
  holding `logs:PutResourcePolicy` on `*` (D-A12).

### G1.6 (BI): Gateway CMK (TEST, then PROD)

- **Needs:** D-A4; G1.2; G1.3 (governance mode).
- **Work:** AD-A14, by governance (D-A9).
- **Acceptance:**
  - P: the key policy statements equal AD-A14 (template test).
  - N: the encryption-context condition refuses another log group
    (fixture simulation).
  - E: rotation enabled.

### G1.4b (BI): TEST front-door grants

- **Needs:** G1.4a, G1.5, G1.6; V-A3, V-A11 resolved offline.
- **Work:** every other AD-A7 row for TEST, by a governance capability PR
  inside the admitted policy set: API Gateway (including `apigateway:SetWebACL`), WAF (including
  `DeleteLoggingConfiguration`), logs (including the Drift evidence
  reads and `ec2:DescribeNetworkInterfaces` for gate A-T step 8b),
  CloudWatch (including the Drift `PutMetricData` and the Apply
  `SetAlarmState`), SNS, KMS, and the ELB and EC2 describes. It also
  carries the deny exceptions of AD-A7, the token path and the alarm
  prefix.
- **Acceptance (simulator matrix):**
  - P: every row is `allowed` for its role, including
    `apigateway:SetWebACL` on a `live` stage ARN with
    `wafv2:AssociateWebACL`.
  - N: these are denied: `apigateway:PATCH /account`,
    `logs:PutResourcePolicy`, `apigateway:DELETE /restapis/x`,
    `wafv2:DeleteWebACL`, `logs:DeleteLogGroup`, `cloudwatch:PutMetricData`
    in another namespace, and any write by Preview.
  - E: `apigateway:DELETE /restapis/x/deployments/y`,
    `wafv2:DeleteLoggingConfiguration` and `logs:DeleteLogDelivery` are
    allowed despite the delete deny.
- **STOP:** an allow outside AD-A1's ceiling (then a boundary amendment in
  a new seed slot).

### G1.7 (BI): PROD certificate and read grants

- **Needs:** D-A3 and XP-A11 (the `user.vilnacrm.com` zone id in account
  `933245420672`); G1.4a (its pattern); and, only if the conditional PROD
  boundary amendment below is needed, XP-A1 and an XP-A4 seed slot. TEST acceptance is **not**
  needed: the PROD certificate must precede USI row 49.
- **Work:** the PROD **cert** rows for `user.vilnacrm.com` and the XP-A11
  zone, by a governance capability PR. A PROD boundary amendment (a seed slot) is
  needed only if G1.1's PROD ceiling does not already cover that zone.
- **Acceptance:** the G1.4a matrix in PROD, with `user.vilnacrm.com`.

### G1.8 (BI): PROD front-door grants

- **Needs:** G5.6 (TEST acceptance), G1.7.
- **Work:** the remaining AD-A7 rows for PROD, by governance, with the
  action set observed in TEST (V-A3) and nothing wider.
- **Acceptance:** the G1.4b matrix, in PROD.

## Epic E-G2: Repository hygiene and controls

### G2.1 (AGI): Hygiene

- **Needs:** nothing.
- **Files:** `.github/workflows/*`, `.github/CODEOWNERS` (new, `*
  @Kravalg`), `.github/dependabot.yml`, `docker-compose.yml`,
  `AGENTS.md` (new: the governance rules of USI `AGENTS.md`, adapted: no
  IAM, OIDC only, stack-config pins, saved plans, TEST before PROD,
  Kravalg-gated, no destructive override, no SSM writes), `README.md`.
- **Work:** delete `tempate-sync-pat.yml`, `template-sync-app.yml` and
  `super-linter.yml`; rewrite `autorelease.yml` per PD-11 (SHA-pinned
  actions, `GITHUB_TOKEN` only, tag and release, no commit to `main`, no
  `VILNACRM_APP_*` secret); dependabot for `uv` and `github-actions`;
  remove the static-key passthrough from `docker-compose.yml` and
  document local SSO debugging only.
- **Acceptance:** P: a workflow-shape test finds every `uses:` pinned by a
  40-hex SHA and every `pull_request` job at `contents: read`. N: a
  repository grep finds no `PERSONAL_ACCESS_TOKEN`, no `VILNACRM_APP_`,
  no `git-auto-commit-action`, no `pull_request_target`. E: `autorelease`
  still runs on `main` only and pushes no commit.

### G2.2 (AGI): Repository-controls definition

- **Needs:** G3.2 and G3.3 (every required check exists as a job).
- **Files:** ported `scripts/configure_github_repository_controls.py`,
  `scripts/_github_repository_controls.py`,
  `scripts/_github_environment_controls.py`, their tests.
- **Work:** the FR-A07 ruleset with the AD-A11 required checks; the
  environments `test-preview`, `test`, `test-drift`, `prod-preview`,
  `prod`, `prod-drift` with
  `@Kravalg` as the sole reviewer of `test` and `prod`,
  admin bypass off, self-review prevented, deployment limited to `main`
  and the dispatch path; **the environment variables the pipeline reads**
  (D-A10, readiness F4): `AWS_PREVIEW_ROLE_ARN` in `{env}-preview`,
  `AWS_APPLY_ROLE_ARN` in `{env}`, `AWS_DRIFT_ROLE_ARN` in `{env}-drift`,
  and `PULUMI_BACKEND_URL` and `PULUMI_SECRETS_PROVIDER` in all three. BI
  has the operator set the same variables for USI (BI `AGENTS.md` lines
  101-102). There is a `--check` mode that reads back and diffs
  rulesets, environments and variables.
- **Acceptance:** P: the dry-run payload equals the fixture. N: a
  required check without a workflow job (or the reverse) fails the pin
  test. A one-directional name-match test fails on any workflow `vars.*`
  read with no defined variable; at row 7 no workflow reads them yet. The
  reverse direction (every defined variable is read by a workflow) is
  added by G3.5 (row 14), once `deploy.yml` (row 13) and
  `scheduled-drift.yml` (row 14) exist. E:
  `--check` against a fixture readback with an extra bypass actor, or a
  wrong role ARN, fails.
- **Live (XP-A3, row 12):** the admin applies it, with the variable values
  taken from the row 9 (role ARNs) and row 10 (backend) readbacks; the
  `--check` output is attached.

## Epic E-G3: Governed pipeline

### G3.1 (AGI): Toolchain and stack skeleton

- **Needs:** G2.1.
- **Files:** `pyproject.toml`, `uv.lock` (replacing `pulumi/pyproject.toml`,
  `pulumi/poetry.lock`), `pulumi/Pulumi.yaml` (project
  `api-gateway-infrastructure`), `pulumi/Pulumi.test.yaml`,
  `pulumi/Pulumi.prod.yaml`, `pulumi/Pulumi.ci.yaml` (the offline stack
  of AD-A15: `stub_live_invokes: true`, a fixture account, the local file
  backend, and the `passphrase` secrets provider with a committed
  `encryptionsalt` and a fixed, non-secret passphrase set by the
  Structural Preview job, because the stack holds no secret; USI's `dev`
  stack uses the same provider, USI `pulumi/Pulumi.dev.yaml`; deleting
  `Pulumi.example.yaml`),
  `pulumi/__main__.py` (registers nothing while both feature flags are
  off), `pulumi/app/config.py` (closed config with
  `features.certificate` and `features.front_door`, AD-A15), `Makefile`,
  `Dockerfile` (pinned tool versions with checksums).
- **Acceptance:** P: each stack's config loads and, with the flags off,
  the program registers nothing. N: a config without the backend URL,
  with a passphrase provider, with an account id that does not match the
  stack, or with `front_door` on and `certificate` off fails;
  `stub_live_invokes` in `test` or `prod` fails to load; `test` or `prod`
  with the dummy-key provider settings (static keys or any `skip_*` flag)
  fails to load. The exemption from
  the "no passphrase provider" and "backend URL required" rules applies
  to exactly `ci`; `test` and `prod` with a passphrase provider still fail.
  E: an account id
  in a Python constant fails a source-scan test.

### G3.2 (AGI): PR quality battery

- **Needs:** G3.1.
- **Files:** `.github/workflows/python-quality.yml`, `security-scans.yml`,
  `codeql.yml`, `Makefile` targets, a counts test for `prd.md` §1.
- **Acceptance:** P: every AD-A11 battery check runs on a PR with
  `contents: read` and no secret. N: branch coverage below 100% fails
  `Coverage`. E: a PR from a fork runs the battery and gets no secret.

### G3.3 (AGI): Guardrails, policy pack, contract schema

- **Needs:** G3.2.
- **Files:** `scripts/pulumi_ci_guardrails.py` (ported, AD-A10),
  `.github/workflows/pulumi-pr-guardrails.yml` (jobs `Structural
  Preview`, `Destructive Diff Gate`, `IAM Gate`, `Policy`, `Contract
  Schema`), `policy/` (CrossGuard pack), `contracts/schema/agi-user-service-backend-v1.json`,
  tests.
- **Work:** `Structural Preview` runs `pulumi preview --stack ci` on a
  local file backend with no AWS credentials (AD-A15).
- **Acceptance:** P: a create-only structural preview of the `ci` stack passes all gates;
  `Contract Schema` passes with only the schema present. N: fixtures with
  a delete, a replace, a `delete-replaced`, an `aws:iam/*` resource, an
  `aws:ssm/*` resource, a stage without access logs, an API without
  `disable_execute_api_endpoint`, a log group without a key, a stage that
  a base path mapping references but no web ACL protects, and a contract
  file with an extra field each fail. E: a Deployment replace passes only
  as create-before-delete with the stage moved in the same plan; a stage
  that no mapping references passes without a web ACL.

### G3.4 (AGI): ChatOps with saved plans

- **Needs:** G3.3, G1.2, G1.3, XP-A3 (row 12). The deploy workflow reads
  its role ARNs and backend from protected-environment variables (D-A10).
- **Files:** `.github/workflows/pulumi-pr-commands.yml`, `deploy.yml`,
  `initialize-stack.yml`, `scripts/pulumi_pr_comment.py`,
  `pulumi_command_preflight.py`, `run_pulumi_command.py`,
  `_pulumi_command_support.py`, tests.
- **Acceptance:** P: `initialize-stack` creates the backend metadata of
  both stacks only (live, per-action authorization); `/pulumi test plan`
  on the flag-off program saves a plan with its sha256 and reports no
  changes (gate A-0). N: workflow-shape and unit tests refuse a
  non-member, a fork, a closed or merged PR, a stale head, a changed plan
  hash, and `/pulumi prod up` without a successful TEST up of the same
  head. E: two commands on one PR serialize (concurrency group, no
  cancel).

### G3.5 (AGI): Scheduled drift and probe

- **Needs:** G3.4.
- **Files:** `.github/workflows/scheduled-drift.yml`, a probe script, tests
  (including the reverse direction of G2.2's variable name-match test:
  every variable G2.2 defines is read by `deploy.yml` or
  `scheduled-drift.yml`).
- **Acceptance:** P: a scheduled run per initialized stack under
  `{env}-drift` runs `preview --refresh --expect-no-changes` and passes;
  the TEST schedule sits inside the USI weekday daytime window (PD-13).
  N: a fixture diff fails the job. E: the probe is skipped with a
  recorded reason until the stack exports a domain (row 24 TEST, row 31
  PROD), and nothing is published while it is skipped; once the probe
  runs (after the Drift `PutMetricData` grant of row 18 TEST, row 29
  PROD), its result is published to the `ApiGatewayInfrastructure/{env}`
  namespace.

## Epic E-G4: Certificates

### G4.1 (AGI): TEST certificate (PR #34 amended, AD-A2)

- **Needs:** G3.4, G1.4a; XP-A6; G0.1 recorded.
- **Files:** `pulumi/app/certificate.py` (from #34's `poc_gateway.py`),
  `pulumi/__main__.py`, `tests/unit/test_certificate.py` (from #34's two
  test files), `Pulumi.test.yaml` (`features.certificate: true`, zone,
  FQDN).
- **Work:** AD-A2. After the apply, the issued ARN goes to the USI owner
  (XP-A8).
- **Acceptance:** P: Pulumi-mock tests show one certificate requested for
  exactly the FQDN with DNS validation and the `Owner` tag, one CNAME with
  `allow_overwrite=False`, one validation, `protect` and `retainOnDelete`,
  and **no `aws:ssm/*` resource**; the live apply reaches `ISSUED`. N:
  another stack, account, region, zone name or a private zone is refused
  before registration (kept tests). E: a second validation option or a
  non-CNAME type is refused (kept tests).
- **STOP:** the validation name already exists in the zone; the
  certificate stays `PENDING_VALIDATION` beyond 72 hours.
- **Offline stack:** `Pulumi.ci.yaml` turns `features.certificate` on with
  a fixture zone, and `certificate.py` reads the fixture under
  `stub_live_invokes`. A `ci` preview with no credentials passes.
- **Hand-off:** the ARN, the apply run URL and the plan sha256 to the USI
  owner, **before USI row 42**.

### G4.2 (AGI): PROD certificate

- **Needs:** G4.1, G1.7; D-A3; XP-A11; G5.6's step-11 PR merged. G4.2
  follows it in C-program, at least 7 days of WAF logs after row 23. USI
  row 49 (XP-15) therefore waits on that too (architecture AD-A12).
- **Acceptance:** as G4.1 for PROD, for `user.vilnacrm.com` in the XP-A11
  zone of account `933245420672` (`Pulumi.prod.yaml`
  `features.certificate: true`); the ARN goes to the USI owner for USI
  XP-15, **before USI row 49**.

## Epic E-G5: TEST front door

### G5.1 (AGI): TEST backend contract pin

- **Needs:** G4.1, G1.4b; XP-A7 (row 19, after USI S4.6 step 20, D-A2);
  D-A8.
- **Files:** `contracts/user-service-backend/test.json`,
  `pulumi/app/backend_contract.py`, `Pulumi.test.yaml`
  (`features.front_door: true`), `contracts/user-service-backend/ci.json`
  and `Pulumi.ci.yaml` (`features.front_door: true`; fixture invokes under
  `stub_live_invokes`), tests. A `ci` preview with both flags on and no
  credentials passes, and the `test` contract's live invokes run on
  every `test` preview and cannot be disabled.
- **Acceptance:** P: offline checks and the live invokes of AD-A3 pass in
  `/pulumi test plan`. N: fixtures with an extra field, a wrong account
  or region, a listener on another load balancer, an HTTP listener, a
  certificate other than G4.1's, an ALB group with a second ingress rule,
  a VPC-link group with an ingress rule, or a source without the USI
  step-20 run reference (FR-A25) each fail. E: the derived load balancer
  ARN equals the live listener's `LoadBalancerArn`.

### G5.2 (AGI): Log groups, topic, alarms, runbooks

- **Needs:** G5.1, G1.6; XP-A10.
- **Files:** `pulumi/app/observability.py`, `docs/runbooks/*.md`, tests.
- **Acceptance:** P: two log groups with the CMK and PD-5 retention; the
  topic on the CMK with the XP-A10 subscription; alarms per FR-A21, each
  with a `runbook` tag that resolves to a file. N: a log group without a
  key fails the policy pack. E: alarm thresholds and the 5XX minimum
  request count are stack config.

### G5.3 (AGI): VPC link, REST API, stage

- **Needs:** G5.2; G1.5 (the account logging setting with the G1.2 logging role; XP-A5).
- **Files:** `pulumi/app/front_door.py`, tests.
- **Acceptance:** P: AD-A4 and AD-A5 resources; the TEST apply succeeds
  (V-A1, V-A2, V-A3 recorded); the stage has no mapping yet, so the
  policy pack's web ACL rule does not apply. N: an integration without
  `VPC_LINK`, with `insecure_skip_verification`, or with a target other
  than the derived ALB ARN fails the tests. E: a definition change
  replaces only the Deployment, create-before-delete.

### G5.4 (AGI): WAF

- **Needs:** G5.3; G1.5 (WAF-log policy, D-A5).
- **Files:** `pulumi/app/waf.py`, tests.
- **Work:** AD-A6; the token path is read from the user-service routes
  and recorded in stack config with its source.
- **Acceptance:** P: the TEST apply associates the web ACL with the stage
  and logs to the KMS log group (V-A6). N: a WCU sum above 1,500 fails; a
  rule without visibility config fails. E: the CommonRuleSet override is
  `count` in TEST until gate A-T step 11.

### G5.5 (AGI): Custom domain and DNS

- **Needs:** G5.4.
- **Files:** `pulumi/app/domain.py`, tests.
- **Acceptance:** P: the TEST apply creates the domain with the AD-A4 TLS
  policy and `STRICT` (V-A5) on the G4.1 certificate, the empty base path
  to `live` and alias A and AAAA. N: an edge-optimized endpoint, a
  certificate from another Region, a non-empty base path, or a mapping to
  a stage without a web ACL fails the tests. E: the V-A5 fallback is
  accepted only with its recorded reason.

### G5.6 (AGI + USI live): TEST acceptance, gate A-T

- **Needs:** G5.5, G3.5.
- **Work:** the steps of AD-A12 gate A-T (1-12, with 8a latency and 8b
  availability), from one exercise
  workflow inside the USI TEST daytime window: probes are unauthenticated
  HTTPS and TLS; evidence reads (Logs Insights, `GetSampledRequests`)
  run under the Drift role in `test-drift`; only step 9 uses the Apply
  role in `test`. Step 11's rule switch is a reviewed C-program PR.
  Results are artifacts with sha256.
- **Acceptance:** every step passes. The evidence of steps 1-10 is handed
  to the USI owner for USI S4.6 step 17 as soon as step 10 passes (CR-A1);
  step 11 follows and must pass before gate A-P.
- **STOP:** any step fails → fix in the owning story; V-A1 fails → NLB
  fallback as a new plan revision; V-A4 fails → escalate to the USI owner
  (listener certificate).

## Epic E-G6: PROD front door

### G6.1 (AGI): PROD backend contract pin

- **Needs:** G5.6, G4.2, G1.8; XP-A7 (PROD descriptor, row 28); D-A8.
- **Acceptance:** as G5.1 for PROD (`Pulumi.prod.yaml`
  `features.front_door: true`).

### G6.2 (AGI): PROD front door, gate A-P

- **Needs:** G6.1; the D-A7 values derived from the G5.6 evidence;
  XP-A10 (the PROD alarm endpoint).
- **Work:** stack config for PROD only (the program is shared); the
  CommonRuleSet in block from the start with the TEST overrides.
- **Acceptance:** P: `/pulumi prod plan` and `up` after the same head's
  TEST up; all FR-A16…FR-A21 resources. N: `prod up` without the TEST up
  of that head is refused. E: the D-A7 values are in the PR, with their
  G5.6 evidence and the user's confirmation.

### G6.3 (AGI): PROD acceptance, drift and probe

- **Needs:** G6.2.
- **Acceptance:** gate A-P steps 1-10 and 12 in PROD, with the PROD Drift
  and Apply roles; daily PROD drift clean with the probe.

## Independent vs shared changes

- **Shared or serialized:** the chains of `architecture.md` §4. C-BI-A
  shares the one-open seed queue with the USI plan (XP-A4).
- **Independent (at most three agents in parallel, after their heads):**
  G0.1; G2.1 with G0.1; the BI rows with the AGI rows G3.1…G3.3 (different
  repositories), as long as C-BI-A keeps its own order.

## Ordered story list

| # | Story | Repo | Kind |
| --- | --- | --- | --- |
| 0 | D-A1…D-A14 recorded (2026-10-01); D-3, D-6, D-15 (and the D-4 consequence) reused from the USI bundle; no open question; CR-A1 and CR-A2 sent to the USI owner; PD-1…PD-14 recorded | user | done (decisions.md) |
| 1 | G0.1 legacy stack inventory (XP-A9; D-A6) | AGI owner | read-only |
| 2 | G2.1 hygiene | AGI | C-controls head, C-pipeline head |
| 3 | G3.1 toolchain and stack skeleton | AGI | C-pipeline, C-program head |
| 4 | G3.2 PR quality battery | AGI | C-pipeline |
| 5 | G0.2 close #26, #32, #33 | AGI maintainer | live GitHub action |
| 6 | G3.3 guardrails, policy pack, contract schema | AGI | C-pipeline, C-policy, C-contract head |
| 7 | G2.2 repository-controls definition | AGI | C-controls |
| 8 | G1.1 gateway seed enrolment, dedicated governance role and re-scoped admission packet, source only (D-A1, D-A9, D-A10, D-A11, D-A12, D-A14, V-A8, V-A10, V-A12, V-A13) | BI | C-BI-A head |
| 9 | G1.2 seed install with the dedicated governance role and the re-scoped admission, trust activation and catalog pin, TEST then PROD (XP-A1; after #284; the CR-A2 slot after USI row 34 and before USI row 42) | BI (human seed operator) | C-BI-A; seed slot per environment |
| 10 | G1.3 governance mode and per-target selection, the BI environment, operator read policies and backend, TEST then PROD (D-A9, D-A11) | BI | C-BI-A; governance apply |
| 11 | G1.4a TEST certificate and read grants (governance) | BI | C-BI-A; governance apply |
| 12 | XP-A3 admin applies the G2.2 controls and environment variables (values from the row 9 and row 10 readbacks); readback attached | admin (`@Kravalg`) | external |
| 13 | G3.4 ChatOps with saved plans; `initialize-stack` TEST and PROD; gate A-0 | AGI | C-pipeline |
| 14 | G3.5 scheduled drift and probe | AGI | C-pipeline |
| 15 | G4.1 TEST certificate (PR #34 amended); ARN to USI (XP-A8) **before USI row 42** | AGI | C-program |
| 16 | G1.5 account prerequisites, TEST then PROD (XP-A5, XP-A12, D-A5, D-A12; governance; under D-A12 branch A, the seed operator's WAF-log policy write in its own seed slot) | BI | C-BI-A; governance apply (+ seed slot under branch A) |
| 17 | G1.6 gateway CMK, TEST then PROD (D-A4; governance) | BI | C-BI-A; governance apply |
| 18 | G1.4b TEST front-door grants (governance) | BI | C-BI-A; governance apply |
| 19 | XP-A7 TEST descriptor from the USI owner (D-A8), **after USI S4.6 step 20 (D-A2; CR-A1)** | USI | external |
| 20 | G5.1 TEST backend contract pin | AGI | C-contract, C-program |
| 21 | G5.2 log groups, topic, alarms, runbooks (XP-A10) | AGI | C-program |
| 22 | G5.3 VPC link, REST API, stage | AGI | C-program |
| 23 | G5.4 WAF | AGI | C-program |
| 24 | G5.5 custom domain and DNS | AGI | C-program |
| 25 | G5.6 TEST acceptance, gate A-T; evidence of steps 1-10 **before USI S4.6 step 17** (CR-A1) | AGI (+USI live) | live TEST |
| 26 | G1.7 PROD certificate and read grants (D-A3, XP-A11; governance) | BI | C-BI-A; governance apply |
| 27 | G4.2 PROD certificate for `user.vilnacrm.com`; ARN to USI **before USI row 49** | AGI | C-program |
| 28 | XP-A7 PROD descriptor from the USI owner, **after USI row 52** | USI | external |
| 29 | G1.8 PROD front-door grants (governance) | BI | C-BI-A tail; governance apply |
| 30 | G6.1 PROD backend contract pin | AGI | C-contract tail |
| 31 | G6.2 PROD front door, gate A-P (D-A7) | AGI | C-program tail |
| 32 | G6.3 PROD acceptance, drift and probe | AGI | live PROD |

Revision 1's rows 26-28 (G1.9, G5.7, G5.8, which existed only under
OQ-8 (a)) are removed by D-A2. Its rows 29-35 are now rows 26-32.

**No forward dependencies (checked over all 33 rows, 0-32).** Every
story's "Needs" names only lower-numbered rows, user decisions (D-A…),
external preconditions (XP-A…) or verification items. No question is
open.

- G0.2 (5) needs 3 and 4.
- G3.3 (6) needs 4.
- G2.2 (7) needs 4 and 6.
- G1.1 (8) needs D-A1, D-A9, D-A10, D-A11, D-A12, D-A14, V-A8, V-A10, V-A12 and V-A13 (USI row 34's result catalog must exist; cross-plan, AD-A12).
- G1.2 (9) needs 8.
- G1.3 (10) needs 9.
- G1.4a (11) needs 9 and 10.
- XP-A3 (12) applies row 7, with values from rows 9 and 10.
- G3.4 (13) needs 6, 9, 10 and 12.
- G3.5 (14) needs 13.
- G4.1 (15) needs 1, 11 and 13.
- G1.5 (16) and G1.6 (17) need 9 and 10.
- G1.4b (18) needs 11, 16 and 17.
- G5.1 (20) needs 15, 18 and 19.
- G5.2 (21) needs 20 and 17.
- G5.3 (22) needs 21 and 16.
- G5.4 (23) needs 22 and 16.
- G5.5 (24) needs 23.
- G5.6 (25) needs 14 and 24.
- G1.7 (26) needs 11, D-A3 and XP-A11.
- G4.2 (27) needs 15, 25 (the step-11 PR) and 26.
- G1.8 (29) needs 25 and 26.
- G6.1 (30) needs 25, 27, 28 and 29.
- G6.2 (31) needs 30.
- G6.3 (32) needs 31.

Other levels of the check:

- **Test level.** The G1.4a and G1.4b matrices (11, 18) use the resource
  names fixed in `architecture.md` AD-A6/AD-A7, not code from rows 15-24.
  G1.1's tests (8) use the candidate catalog and fixtures, not installed
  state from row 9. G2.2's required-check pin test (7) reads the
  workflows of rows 4 and 6, which define every required check, including
  `Contract Schema`. Its variable name-match test is one-directional at
  row 7, and the reverse direction lands in G3.5 (14), after the
  workflows of rows 13 and 14 exist. G3.3's policy rule for web ACLs (6) applies only to
  mapped stages, so G5.3 (22) passes before G5.4 (23) adds the ACL.
- **Ownership level.** No row edits a file whose chain head is a later
  row (architecture §4). In C-BI-A, the pin PR of row 9 is the only change
  to `CATALOG_HASHES` before row 10, and every later seed change set runs
  on its predecessor's result catalog.
- **Feature flags.** PROD drift from row 14 previews an empty program
  until row 27 turns `features.certificate` on, so it needs no PROD grant
  beyond the backend (AD-A15). The TEST `features.front_door` turns on in
  row 20, with a contract that cites the USI step-20 run (FR-A25).
- **Cross-plan rows.** USI rows 42, 43 (with S4.6 steps 17 and 20), 49
  and 52 are external ordering constraints between the two plans, not
  dependencies of a lower gateway row on a higher one. Architecture AD-A12
  lists them; CR-A1 asks the USI owner for the step-17 move.
