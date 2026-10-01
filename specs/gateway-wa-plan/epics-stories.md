---
artifact: epics-stories
workflow: _bmad/bmm/workflows/3-solutioning/bmad-create-epics-and-stories (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 2 (2026-10-01: user decisions D-A1…D-A8; E-G1 rewritten for the seed registration route; OQ-8 (a)-only stories removed; rows renumbered)
inputDocuments: [prd.md, architecture.md, decisions.md]
---

# Epics and stories: the API gateway Well-Architected track

## Requirements inventory

- 25 FRs (FR-A01…FR-A25) and 11 NFRs (NFR-A01…NFR-A11): `prd.md` §3-§4.
- Gateway decisions D-A1…D-A8 (2026-10-01; they answer OQ-1…OQ-8); reused
  user decisions D-3, D-6, D-15 (and the D-4 consequence); open questions
  OQ-9 and OQ-10; cross-plan change request CR-A1; planning defaults
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

D-A1 fixes the route for the roles. Where a story's owner depends on OQ-9,
the story lists the work under each option, and the user's answer selects
one.

### G1.1 (BI): Gateway seed enrolment packet (source only)

- **Needs:** D-A1; OQ-9 and OQ-10 answered; V-A10 (the BI owner's review).
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
    `tests/unit/test_gateway_seed_amendment.py`).
- **Work:** AD-A1's source packet. The packet renders, per environment, the
  candidate result catalog and the candidate seed template. Their contents:
  - the five gateway principals (Preview, Apply, Drift, replication,
    logging) and, under OQ-10 (b) or (c), the ConfigRead readers;
  - their three boundaries and their guards;
  - the identity policies the OQ-9 option puts in the seed: the logging
    role's always, plus the CI and replication roles' under (a) or (c);
  - under OQ-9 (b), the governance guard and ceiling amendments that
    OQ-9 (b) lists.

  The packet pins the baseline catalog hash in force at its slot, the
  installed template digest, the result hash and the Add rows. As in #284,
  this PR changes **neither** the active catalogs, nor `CATALOG_HASHES`,
  nor the active counts. Those change together in G1.2's pin PR.
- **Acceptance:**
  - P: `build_catalog()` from the pinned baseline reproduces the pinned
    result hash. The candidate passes `build_registry`. It passes the
    mixed-phase verifier against fixtures of the post-CREATE state, with
    the `GitHubOperator*` executors **active** (TEST today) and, separately,
    **disabled** (PROD, unless G1.2 step 1 observes them active), and the
    gateway principals disabled. It passes `verify_active_enrollment` against a fixture with
    every trust active, including the AD-A1 trusts.
    The rendered template adds exactly the expected logical ids.
  - N: a test that compares every pre-existing statement, policy,
    principal, attachment and binding with the baseline finds no change
    (the OQ-9 (b) governance guard and ceiling amendments are the only
    exception, and only if chosen). The mixed-phase verifier refuses an
    active gateway trust, a disabled executor trust, and any changed
    pre-existing attachment. The CREATE validator refuses a change set with any Modify,
    Remove, replacement, dynamic or extra Add row, except, under OQ-9 (b),
    the exact listed governance guard, governance ceiling and operator
    guard Modify rows. The activation validator
    refuses any row other than the gateway trust Modify rows, and any
    trust with a `pull_request` or `ref` subject, another repository id or
    a wildcard. Replaying the module against its result fails.
  - E: the `GitHubOperator*` executor path is unchanged. Each boundary
    renders at ≤ 6144 characters (6144 passes, 6145 fails). Each role name
    is ≤ 64 characters, and every new policy basename is unique across the
    catalog regardless of path and case.
- **STOP:** V-A10 declined (escalate to the user; no fallback to an
  independent stack); a result that would change `dc27f076…` or any other
  Resource-`*` deny.

### G1.2 (BI; human seed operator, live): Install, activate and pin (TEST, then PROD)

- **Needs:** G1.1 merged; OQ-10 (the role set, through G1.1); XP-A1;
  XP-A2; an XP-A4 slot per environment.
- **Work:** AD-A1 "Installation and activation", per environment:
  - absent-name checks, and the observed lifecycle phase (active or
    disabled) of each `GitHubOperator*` executor, recorded for the
    mixed-phase verifier;
  - the CREATE change set (exact Add rows enforced by the change-set
    validator, `TemplateURL` bound to its digest; under OQ-9 (b) also the
    exact governance guard, governance ceiling and operator executor guard
    Modify rows, under a temporary
    `Update:Modify` stack policy on those ids), the deny-update policy
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
  - N: simulated trust evaluation refuses, for each CI role,
    `repo:VilnaCRM-Org/api-gateway-infrastructure:pull_request`,
    `…:ref:refs/heads/main`, another environment, another repository id
    and a fork. `iam:SimulatePrincipalPolicy` (BI identity) denies
    `iam:CreateRole` and `ssm:GetParameter` to each CI role.
  - E: no operator run happens between install and pin, except those the
    #284 runbook requires inside the window.
- **Evidence:** both change-set listings and ids, the template digests,
  the readbacks, the verifier outputs, the absent-name results, and
  `@Kravalg`'s seed-review approval.
- **STOP:** an existing role or policy with a target name; a change set
  with any row outside the validator; a partial result (reconcile it
  first; never replay a change set).

### G1.3 (BI): Gateway backend (TEST, then PROD)

- **Needs:** G1.2; OQ-9.
- **Work:** the FR-A03 bucket, replica (PD-12) and key, whose bucket and
  key policies grant only the gateway CI roles and the replication role.
  By the OQ-9 option:
  - **(a)** A seed amendment that adds these resources (Add rows only;
    XP-A1 widened).
  - **(b)** The G1.2 change set has already amended the governance guard,
    the governance ceilings and the catalog's operator bindings (OQ-9
    (b)). A reviewed BI operator PR then adds the governance roles'
    gateway storage and IAM identity policies. Then a governance catalog
    PR adds the gateway
    to `pulumi/repositories.governance.json`, in an external-identity mode
    that `get()`s the G1.2 roles and creates none (a reviewed BI code
    change). It is applied TEST, then PROD, under the `governance`
    environment, and the same PR writes the basic `pulumi-backend` and
    `secret-read-deny` or `read-only` documents (AD-A7, first row).
  - **(c)** An independent BI CloudFormation backend stack (the XP-A1 (c)
    installer).
- **Acceptance:**
  - P: the BI verifier reads back the bucket (versioning, SSE-KMS with the
    key, public access blocked, TLS-only policy, replication) and the key
    alias. The first use of the backend is G3.4's `initialize-stack`
    (row 13).
  - N: the bucket policy denies a principal outside the gateway roles and
    BI administration (simulator).
  - E: the replica matches the USI backend pattern.
- **STOP:** the chosen route would need a narrowed Resource-`*` deny
  (escalate to the user).

### G1.4a (BI): TEST certificate and read grants

- **Needs:** G1.2, G1.3; OQ-9; V-A7, V-A8 resolved offline.
- **Work:** the AD-A7 rows marked **cert**, for `{zone}` =
  `Z04999481RZ4UQK2NANVH` and `{fqdn}` = `user.vilnacrmtest.com`, written
  by the OQ-9 owner:
  - under (a) or (c), a seed amendment of in-place identity-policy updates
    (the #284 mechanism, with the result hash pinned after readback);
  - under (b), a governance capability PR, after a seed amendment admits
    any new exact policy ARN.

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

- **Needs:** G1.2 (the logging role); XP-A5; XP-A12; OQ-9.
- **Work:** AD-A9 by the OQ-9 owner: the `AWS::ApiGateway::Account`
  setting with the G1.2 logging role, and the D-A5 WAF-log resource
  policy. If XP-A5 shows the API Gateway service-linked role missing, the
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
- **STOP:** XP-A12 finds another owner and no agreement.

### G1.6 (BI): Gateway CMK (TEST, then PROD)

- **Needs:** D-A4; G1.2; OQ-9.
- **Work:** AD-A14, by the OQ-9 owner.
- **Acceptance:**
  - P: the key policy statements equal AD-A14 (template test).
  - N: the encryption-context condition refuses another log group
    (fixture simulation).
  - E: rotation enabled.

### G1.4b (BI): TEST front-door grants

- **Needs:** G1.4a, G1.5, G1.6; OQ-9; V-A3, V-A11 resolved offline.
- **Work:** every other AD-A7 row for TEST, by the OQ-9 owner's grant
  change: API Gateway (including `apigateway:SetWebACL`), WAF (including
  `DeleteLoggingConfiguration`), logs (including the Drift evidence
  reads), CloudWatch (including the Drift `PutMetricData` and the Apply
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
  `933245420672`); G1.4a (its pattern); OQ-9. TEST acceptance is **not**
  needed: the PROD certificate must precede USI row 49.
- **Work:** the PROD **cert** rows for `user.vilnacrm.com` and the XP-A11
  zone, by the OQ-9 owner. A PROD boundary amendment (a seed slot) is
  needed only if G1.1's PROD ceiling does not already cover that zone.
- **Acceptance:** the G1.4a matrix in PROD, with `user.vilnacrm.com`.

### G1.8 (BI): PROD front-door grants

- **Needs:** G5.6 (TEST acceptance), G1.7; OQ-9.
- **Work:** the remaining AD-A7 rows for PROD, by the OQ-9 owner, with the
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
  and the dispatch path; a `--check` mode that reads back and diffs.
- **Acceptance:** P: the dry-run payload equals the fixture. N: a
  required check without a workflow job (or the reverse) fails the pin
  test. E: `--check` against a fixture readback with an extra bypass
  actor fails.
- **Live (XP-A3, row 12):** the admin applies it; the `--check` output is
  attached.

## Epic E-G3: Governed pipeline

### G3.1 (AGI): Toolchain and stack skeleton

- **Needs:** G2.1.
- **Files:** `pyproject.toml`, `uv.lock` (replacing `pulumi/pyproject.toml`,
  `pulumi/poetry.lock`), `pulumi/Pulumi.yaml` (project
  `api-gateway-infrastructure`), `pulumi/Pulumi.test.yaml`,
  `pulumi/Pulumi.prod.yaml` (deleting `Pulumi.example.yaml`),
  `pulumi/__main__.py` (registers nothing while both feature flags are
  off), `pulumi/app/config.py` (closed config with
  `features.certificate` and `features.front_door`, AD-A15), `Makefile`,
  `Dockerfile` (pinned tool versions with checksums).
- **Acceptance:** P: each stack's config loads and, with the flags off,
  the program registers nothing. N: a config without the backend URL,
  with a passphrase provider, with an account id that does not match the
  stack, or with `front_door` on and `certificate` off fails. E: an
  account id in a Python constant fails a source-scan test.

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
- **Acceptance:** P: a create-only structural preview passes all gates;
  `Contract Schema` passes with only the schema present. N: fixtures with
  a delete, a replace, a `delete-replaced`, an `aws:iam/*` resource, an
  `aws:ssm/*` resource, a stage without access logs, an API without
  `disable_execute_api_endpoint`, a log group without a key, a stage that
  a base path mapping references but no web ACL protects, and a contract
  file with an extra field each fail. E: a Deployment replace passes only
  as create-before-delete with the stage moved in the same plan; a stage
  that no mapping references passes without a web ACL.

### G3.4 (AGI): ChatOps with saved plans

- **Needs:** G3.3, G1.2, G1.3, XP-A3 (row 12); OQ-10 (whether the deploy
  workflow reads its role ARNs and backend from protected-environment
  variables or from a ConfigRead secret).
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
- **Files:** `.github/workflows/scheduled-drift.yml`, a probe script, tests.
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
- **Hand-off:** the ARN, the apply run URL and the plan sha256 to the USI
  owner, **before USI row 42**.

### G4.2 (AGI): PROD certificate

- **Needs:** G4.1, G1.7; D-A3; XP-A11.
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
  (`features.front_door: true`), tests.
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
- **Work:** the twelve steps of AD-A12 gate A-T, from one exercise
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

- **Needs:** G6.1; the D-A7 values derived from the G5.6 evidence.
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
| 0 | D-A1…D-A8 recorded (2026-10-01); D-3, D-6, D-15 (and the D-4 consequence) reused from the USI bundle; OQ-9, OQ-10 open; CR-A1 sent to the USI owner; PD-1…PD-14 recorded | user | done (decisions.md); each OQ blocks only the rows that list it in "Needs" |
| 1 | G0.1 legacy stack inventory (XP-A9; D-A6) | AGI owner | read-only |
| 2 | G2.1 hygiene | AGI | C-controls head, C-pipeline head |
| 3 | G3.1 toolchain and stack skeleton | AGI | C-pipeline, C-program head |
| 4 | G3.2 PR quality battery | AGI | C-pipeline |
| 5 | G0.2 close #26, #32, #33 | AGI maintainer | live GitHub action |
| 6 | G3.3 guardrails, policy pack, contract schema | AGI | C-pipeline, C-policy, C-contract head |
| 7 | G2.2 repository-controls definition | AGI | C-controls |
| 8 | G1.1 gateway seed enrolment packet, source only (D-A1, OQ-9, OQ-10, V-A10) | BI | C-BI-A head |
| 9 | G1.2 seed install, trust activation and catalog pin, TEST then PROD (XP-A1) | BI (human seed operator) | C-BI-A; seed slot per environment |
| 10 | G1.3 backend, TEST then PROD (OQ-9) | BI | C-BI-A; seed slot or governance apply |
| 11 | G1.4a TEST certificate and read grants (OQ-9) | BI | C-BI-A; seed slot |
| 12 | XP-A3 admin applies the G2.2 controls; readback attached | admin (`@Kravalg`) | external |
| 13 | G3.4 ChatOps with saved plans; `initialize-stack` TEST and PROD; gate A-0 (OQ-10) | AGI | C-pipeline |
| 14 | G3.5 scheduled drift and probe | AGI | C-pipeline |
| 15 | G4.1 TEST certificate (PR #34 amended); ARN to USI (XP-A8) **before USI row 42** | AGI | C-program |
| 16 | G1.5 account prerequisites, TEST then PROD (XP-A5, XP-A12, D-A5, OQ-9) | BI | C-BI-A; seed slot |
| 17 | G1.6 gateway CMK, TEST then PROD (D-A4, OQ-9) | BI | C-BI-A; seed slot |
| 18 | G1.4b TEST front-door grants (OQ-9) | BI | C-BI-A; seed slot |
| 19 | XP-A7 TEST descriptor from the USI owner (D-A8), **after USI S4.6 step 20 (D-A2; CR-A1)** | USI | external |
| 20 | G5.1 TEST backend contract pin | AGI | C-contract, C-program |
| 21 | G5.2 log groups, topic, alarms, runbooks (XP-A10) | AGI | C-program |
| 22 | G5.3 VPC link, REST API, stage | AGI | C-program |
| 23 | G5.4 WAF | AGI | C-program |
| 24 | G5.5 custom domain and DNS | AGI | C-program |
| 25 | G5.6 TEST acceptance, gate A-T; evidence of steps 1-10 **before USI S4.6 step 17** (CR-A1) | AGI (+USI live) | live TEST |
| 26 | G1.7 PROD certificate and read grants (D-A3, XP-A11, OQ-9) | BI | C-BI-A; seed slot |
| 27 | G4.2 PROD certificate for `user.vilnacrm.com`; ARN to USI **before USI row 49** | AGI | C-program |
| 28 | XP-A7 PROD descriptor from the USI owner, **after USI row 52** | USI | external |
| 29 | G1.8 PROD front-door grants (OQ-9) | BI | C-BI-A tail; seed slot |
| 30 | G6.1 PROD backend contract pin | AGI | C-contract tail |
| 31 | G6.2 PROD front door, gate A-P (D-A7) | AGI | C-program tail |
| 32 | G6.3 PROD acceptance, drift and probe | AGI | live PROD |

Revision 1's rows 26-28 (G1.9, G5.7, G5.8, which existed only under
OQ-8 (a)) are removed by D-A2. Its rows 29-35 are now rows 26-32.

**No forward dependencies (checked over all 33 rows, 0-32).** Every
story's "Needs" names only lower-numbered rows, user decisions (D-A…),
open questions, external preconditions (XP-A…) or verification items.

- G0.2 (5) needs 3 and 4.
- G3.3 (6) needs 4.
- G2.2 (7) needs 4 and 6.
- G1.1 (8) needs D-A1, OQ-9, OQ-10 and V-A10.
- G1.2 (9) needs 8.
- G1.3 (10) needs 9.
- G1.4a (11) needs 9 and 10.
- XP-A3 (12) applies row 7.
- G3.4 (13) needs 6, 9, 10 and 12.
- G3.5 (14) needs 13.
- G4.1 (15) needs 1, 11 and 13.
- G1.5 (16) and G1.6 (17) need 9.
- G1.4b (18) needs 11, 16 and 17.
- G5.1 (20) needs 15, 18 and 19.
- G5.2 (21) needs 20 and 17.
- G5.3 (22) needs 21 and 16.
- G5.4 (23) needs 22 and 16.
- G5.5 (24) needs 23.
- G5.6 (25) needs 14 and 24.
- G1.7 (26) needs 11, D-A3 and XP-A11.
- G4.2 (27) needs 15 and 26.
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
  `Contract Schema`. G3.3's policy rule for web ACLs (6) applies only to
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
