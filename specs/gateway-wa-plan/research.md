---
artifact: research
workflow: _bmad/bmm/workflows/1-analysis/research (technical research, non-interactive; bmalph 2.11.0 workflow tree read from wt-usi-hardening/_bmad, not initialized in this worktree)
task: gateway-wa-plan
repository: VilnaCRM-Org/api-gateway-infrastructure
branch: feat/gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a (origin/main)
date: 2026-10-01
status: planning-only
revision: 4 (2026-10-01: GR-18…GR-20 added for D-A1; the options and risks tables carry the user decisions D-A1…D-A11)
---

# Technical research: the API gateway Well-Architected track

## 1. Scope and method

The user-service runs behind `VilnaCRM-Org/api-gateway-infrastructure` (AGI,
this repository). The USI hardening plan (`VilnaCRM-Org/user-service-infrastructure`,
`specs/workload-wa-hardening/`, readiness PASS in round 15 against `56e247b`,
bundle commit `9d5df4a`) names the gateway work as one story, S5.16 (AGI). This
research collects the facts a full gateway track needs:

- the state of this repository and its open PRs;
- how bootstrap-infrastructure (BI) enrols a service repository, and why the
  documented route is blocked for this one;
- the governed pipeline pattern of USI and BI;
- the cross-repository contract with USI;
- the AWS capabilities the front door relies on.

Method. Everything was read-only:

- `git show`, `sed`, `grep` and read-only Python over the files cited;
- `gh pr view`, `gh pr list` and `gh api` GET calls for repository metadata;
- the aws-knowledge MCP for AWS documentation (`search_documentation`,
  `read_documentation`), on 2026-10-01;
- a read-only grep of the installed `pulumi_aws` 7.23.0 SDK
  (`wt-boot-219/.venv`).

No `aws` or `pulumi` command ran. No `.env` file or `~/.aws` was read. No
secret value was read. Two read-only reconnaissance subagents
(`claude-router:recon`) mapped BI enrolment and the pipeline pattern; their
key claims were re-checked at the cited lines before use (run-summary.md).

ID scheme: `GR-n` are repository facts, `GA-n` are AWS facts. Both are local to
this bundle. USI identifiers keep their names and are prefixed "USI" where
ambiguous (for example USI XP-10, USI AD-26).

## 2. This repository (baseline `f056c8b`)

- **GR-1 `[SRC]` The program is a bare template.**
  - `pulumi/__main__.py` creates one `s3.BucketV2("my-bucket")` and exports
    `bucket_name`.
  - `pulumi/Pulumi.yaml` names the project `vilnacrm` and the Poetry
    toolchain. The only stack file is `pulumi/Pulumi.example.yaml`
    (`aws:region: eu-central-1`). It carries an `encryptionsalt`, which is
    the marker of the passphrase secrets provider.
  - `pulumi/pyproject.toml` pins `pulumi = "^3.138"`, `pulumi-aws = "^6.58"`
    and `python = "^3.9"`.
  - `docker-compose.yml` passes `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
    and `AWS_SESSION_TOKEN` into the local container. The `Dockerfile`
    installs Pulumi, Poetry and the AWS CLI with `curl … | bash`.
- **GR-2 `[SRC]` Workflows: four, none deploys.** `.github/workflows/`:
  - `autorelease.yml`: on push to `main`; GitHub App token from
    `VILNACRM_APP_ID` and `VILNACRM_APP_PRIVATE_KEY`; `actions/checkout@v2`,
    `tibdex/github-app-token@v1`, `actions/create-release@v1`.
  - `super-linter.yml`: on `pull_request`; App token; `super-linter@v7.1.0`
    with `continue-on-error: true` (it never fails a PR); then
    `stefanzweifel/git-auto-commit-action@v5` pushes fixes to the PR head
    with the App token.
  - `tempate-sync-pat.yml` (sic): monthly; checks out with
    `secrets.PERSONAL_ACCESS_TOKEN`; syncs from
    `VilnaCRM-Org/php-service-template`, which is a PHP service template,
    not an infrastructure template.
  - `template-sync-app.yml`: weekly; the same source repository, App token.

  Every action is referenced by tag, none by commit SHA. There is no OIDC
  credential step, no preview, no apply, no saved plan, no drift job and no
  `environment:` key.
- **GR-3 `[LIVE, read-only]` Repository controls, read back 2026-10-01 with
  `gh api` GET.**
  - Repository id `887871673`, owner id `114362548`, public, squash merge
    only, auto-merge allowed, branch deletion on merge.
  - Rulesets: exactly one, `Protect release tags` (id `23183036`, target
    `tag`, `refs/tags/v*` and `refs/tags/[0-9]*`, rules `deletion`,
    `non_fast_forward`, `update`). **No ruleset applies to `main`:**
    `GET /rules/branches/main` returns `[]`, and branch protection on
    `main` returns 404. (The coordinator's 2026-09-30 readback said "no
    ruleset"; the tag ruleset exists, but nothing guards `main`.)
  - Environments: `total_count: 0`.
  - `.github/CODEOWNERS`: absent (404).
  - `.github/dependabot.yml`: `pip` in `/pulumi`, monthly, reviewer
    `Kravalg`, one group `all-deps`.
- **GR-4 `[SRC]` PR #34 (draft, `dmytrocraft`, head `cd8f790`, base
  `f056c8b`, three commits; read with `git show
  origin/feat/test-user-service-gateway:<path>`).**
  - `pulumi/poc_gateway.py` (88 lines): constants `TEST_ACCOUNT_ID
    891377212104`, `TEST_REGION eu-central-1`, `TEST_ZONE_ID
    Z04999481RZ4UQK2NANVH`, `TEST_DOMAIN user.vilnacrmtest.com`,
    `CERTIFICATE_PARAMETER /vilnacrm/test/user-service/gateway-certificate-arn`.
    `assert_test_target` rejects another account, region, zone name or a
    private zone. `only_validation_option` requires exactly one DNS option
    for the exact domain, of type CNAME. `provision_test_certificate`
    requires stack `test`, then creates `aws.acm.Certificate` (DNS
    validation), one `aws.route53.Record` (`allow_overwrite=False`, TTL
    300), `aws.acm.CertificateValidation` and an `aws.ssm.Parameter`
    (`String`) holding the validated ARN, and exports `certificate_arn`,
    `certificate_parameter_arn` and `certificate_parameter_version`.
  - `pulumi/__main__.py` keeps `my-bucket` and its export "if the `test`
    stack already owns it", then calls `provision_test_certificate()`.
  - Tests: `pulumi/tests/test_poc_gateway.py` (61 lines, `unittest`) and
    `pulumi/tests/test_gateway_graph.py` (145 lines).
  - Checks on the head: `lint`, CodeQL `Analyze (python)`, `Analyze
    (actions)` and `CodeQL` succeeded; review decision
    `REVIEW_REQUIRED`; mergeable.
  - The PR body says it still needs "a protected OIDC and saved-plan
    deployment route" and an inspection of "the live `test` stack". No
    file in any repository records where that stack's state lives.
- **GR-5 `[LIVE, read-only]` The three dependabot PRs.**

  | PR | Change | Base | Checks on the head | Last update |
  | --- | --- | --- | --- | --- |
  | #33 | `super-linter/super-linter` 7.1.0 → 8.3.1 in `super-linter.yml` | `f056c8b` | `lint` FAILURE; `Infracost` SKIPPED | 2026-02-09 |
  | #32 | `virtualenv` 20.27.1 → 20.36.1 in `pulumi/poetry.lock` | `f056c8b` | `lint` FAILURE; `Infracost` SKIPPED | 2026-01-13 |
  | #26 | group: `pulumi` 3.148.0, `pulumi-aws` 6.62.2, `black` 25.1.0, `flake8` 7.2.0, `pre-commit` 4.2.0 (`pyproject.toml`, `poetry.lock`) | `f056c8b` | none reported | 2026-04-01 |

  All three are `REVIEW_REQUIRED` and mergeable. #26 stays on `pulumi-aws`
  6.x.
- **GR-17 `[SDK]` `pulumi_aws` 7.23.0** (read-only grep of
  `wt-boot-219/.venv/lib/python3.11/site-packages/pulumi_aws`):
  - `apigateway/integration.py` line 63: `integration_target` is "The ALB
    or NLB ARN to send the request to. Used for private integrations with
    VPC Link V2. When using VPC Link V2, this parameter specifies the load
    balancer ARN, while `uri` is used to set the Host header."
  - `apigateway/domain_name.py` lines 30-96: `endpoint_access_mode`
    (`BASIC`, `STRICT`, only with `SecurityPolicy_*` policies) and
    `security_policy`.
  - `apigateway/rest_api.py` line 45: `disable_execute_api_endpoint`.

## 3. Bootstrap-infrastructure (BI)

Read through the worktrees `wt-boot-urllib3` (`862b4bf`, `origin/main`
`bea5252` plus a `uv.lock` change), `wt-boot-pr280` (#284, `e85534c`) and
`wt-boot-219` (#285, `54e9e2f`).

- **GR-9 `[SRC]` Catalogs.** `pulumi/repositories.bootstrap.json` lists only
  `bootstrap-infrastructure`. `pulumi/repositories.governance.json` lists only
  `user-service-infrastructure` (`repositoryId 911736693`,
  `repositoryOwnerId 114362548`, `project user-service-infrastructure`,
  `owner team-user-service`, `expectedEnvironments 2`). This repository is in
  neither.
- **GR-10 `[SRC]` The documented onboarding route** (BI `AGENTS.md` lines
  38-104; `docs/governance-stack.md` lines 75-83):
  1. OPERATOR: resolve the real repository and owner ids;
  2. OPERATOR: a reviewed `github-ci-bootstrap` change provisions the
     immutable service and replication boundaries and extends the
     governor's inventory, before the first governance apply;
  3. PR A: add the repository to `repositories.governance.json`; the
     governance stack then creates the state bucket, replica, KMS key and
     alias, "bounded preview/apply/drift roles, config-read roles and fixed
     CI secrets", applied TEST then PROD under the `governance` environment
     with `@Kravalg`'s approval;
  4. PR B: the repository scaffold, "modelled on
     `pulumi/user-service-infrastructure/`";
  5. OPERATOR: publish the scaffold, set variables and protected
     environments;
  6. PR C: the reviewed service capabilities, applied TEST then PROD.
- **GR-11 `[SRC]` The TEST preview trust adds `pull_request` for new
  repositories.** `pulumi/infra/ci_bootstrap.py` `_deployment_role_subjects`
  (lines 347-375): for `preview` in TEST, the subjects are the `main` ref,
  `pull_request` **unless the repository is `bootstrap-infrastructure` or
  `user-service-infrastructure`** (lines 361-366), `environment:test` and
  `environment:test-preview`. `apply` trusts only `environment:{env}`.
  `governance.py` `_governance_role_specs` (lines 478-517) uses the same
  function, so a catalog-enrolled gateway repository would get a TEST
  Preview role that a `pull_request` workflow can assume. BI retired that
  trust for USI in #276 ("Retire generic TEST PR preview trust for user
  service", `origin/main` `bea5252`).
- **GR-12 `[SRC]` The seed guards block the documented route.** The
  governance apply role `GitHubGovernanceApply-{env}` carries the guard
  `G-GitHubGovernanceApply` (`pulumi/seed/catalogs/test.json` lines
  599-614), whose statements include:
  - `dc27f076…`: Deny `iam:CreateRole`, `iam:DeleteRole`,
    `iam:PutRolePermissionsBoundary`, `iam:DeleteServiceLinkedRole` and the
    `sts:AssumeRole*` family on Resource `*`;
  - `8c068aaa…` (lines 2915-2931): Deny `iam:*` with a `NotResource` list
    that names only the GitHub OIDC provider and the USI roles, boundaries
    and Apply policies;
  - `5366ec11…`: Deny the policy-write actions outside the USI policies;
  - `05f77e26…`: Deny `iam:CreateServiceLinkedRole` unless the service is
    `budgets`, `guardduty` or `securityhub`.

  So today the governance stack cannot create any role, and cannot touch
  any IAM resource that is not a USI one. The documented PR A cannot
  enrol a second service without a seed amendment, and creating roles
  through it would need the `dc27f076…` Resource-`*` deny narrowed.
- **GR-13 `[SRC]` Seed catalog and registry.**
  - `pulumi/seed/README.md` lines 14-24: each catalog holds 24 principals
    and 55 managed policies, and "an inventory change requires a reviewed
    catalog and code update".
  - The TEST catalog's principals include six USI roles, each with
    `owner_project: governance`, the boundary
    `GovernanceBoundary-user-service-infrastructure-test` (or
    `GovernanceReplicationBoundary-…` for `PulumiStateRepl-…`) and one
    guard: `GitHubCiApply-`, `GitHubCiPreview-`, `GitHubCiDrift-`,
    `GitHubCiConfigRead-` and `GitHubCiConfigRead-…-test-pr`, and
    `PulumiStateRepl-user-service-infrastructure-test`. PROD has the same
    six with `-prod` and `-prod-preview`. The three proposed operator roles
    carry `owner_project: independent_seed` and `existing: false`.
  - `pulumi/seed/policy_registry.py` lines 17-20 pin `CATALOG_HASHES`
    (TEST `ef419680…`, PROD `d4b56073…`); `_mutable_attachment_sets`
    (line 532) and `verify_active_enrollment` (line 570) enforce the exact
    attachment closure. Line 355 requires exactly 21 existing roles;
    `existing: false` principals are verified as operator executors
    (`_verify_role` lines 431-446, `_active_executor_trust` lines 505-514).
  - The amendment pattern is `pulumi/seed/test_poc_prerequisite_amendment.py`
    (baseline policy hashes, a result catalog hash, a 6144-character
    boundary size check). The USI plan serializes every seed operation
    one at a time across both catalogs (USI architecture §4, C-BI).
- **GR-14 `[SRC]` Record-name-scoped Route 53 precedent.** BI
  `pulumi/infra/governance.py` lines 363-408 give the USI TEST roles
  `route53:GetHostedZone` and `ListResourceRecordSets` on
  `hostedzone/Z04999481RZ4UQK2NANVH`, and the Apply role
  `route53:ChangeResourceRecordSets` on that zone only for names
  `*._domainkey.user.vilnacrmtest.com`, type `CNAME`, action `CREATE`, with
  `Null` guards on all three condition keys. The same public TEST zone
  therefore already holds USI's SES DKIM records.
- **GR-15 `[SRC]` USI AD-26, the six IAM layers** (USI `architecture.md`
  lines 1786-2060): identity allows; identity denies; the seed-owned
  permissions boundary (one managed policy, at most 6144 characters); the
  hash-pinned seed guard; the seed attachment constraint; and principal
  creation by **an independent CloudFormation stack per role family**
  (reviewed template and hash, `Retain`, a permanent deny-update stack
  policy, a human non-root installer (USI XP-17), CREATE change-set
  evidence, a post-create verifier, `@Kravalg`'s approval; every later
  grant a reviewed stack amendment). No guard's Resource-`*` deny is
  narrowed without a user decision.
- **GR-18 `[SRC]` How the USI CI roles entered the seed (revision 2, for
  D-A1).** Read in `wt-boot-urllib3` (origin/main proxy) and `wt-boot-pr280`
  (#284).
  1. **Creation by governance.** The governance Pulumi stack created the USI
     roles from `_governance_role_specs` (BI `pulumi/infra/governance.py`
     lines 478-517), each bound to the operator-provisioned boundary
     `GovernanceBoundary-user-service-infrastructure-{env}`, the replication
     role on `GovernanceReplicationBoundary-…`, and their identity documents
     `pulumi-backend` plus `secret-read-deny` (Apply) or `read-only`
     (Preview, Drift) (lines 414-476: new service repositories "initially
     receive only their Pulumi backend access"). Governance also created the
     backend, the key and the fixed CI secrets (`ci_config.py` line 540).
  2. **Registration by the independent seed.** The issue-215 seed is a
     CloudFormation stack. It is generated by
     `scripts/operator_seed_installation.py` (docstring lines 1-18: import the
     six existing boundaries, "then add the remaining policies and disabled
     roles", deny-update stack policy, a validated change set before each
     execution, non-root installer). The TEST and PROD catalogs record each
     USI role as `existing: true`, `owner_project: governance`, with its
     boundary transferred to seed ownership (kind
     `existing_capability_boundary`, ownership
     `existing_operator_policy_transfer_to_seed`). Each role also has one
     new seed-owned guard under `policy/issue215-seed/{env}/guard/`:
     `GitHubCiApply-user-service-infrastructure` = statements `dc27f076…`,
     `415affc4…`, `668edd62…`, `6bd9deea…`, `05f77e26…`, `d413d73a…`,
     `9f269660…`. `GitHubCiPreview-` and `GitHubCiDrift-` = `ae950d73…`, the
     same five shared statements and `119623e2…` (state writes only under
     `.pulumi/locks/*`). `PulumiStateRepl-` = `dc27f076…` and the five shared
     statements. The ConfigRead readers have their own guards. (Read-only
     Python over BI `pulumi/seed/catalogs/{test,prod}.json`.)
  3. **New principals created by the seed itself.** The three
     `GitHubOperator{Preview,Apply,Drift}-{env}` executors are `existing:
     false`, `owner_project: independent_seed`. The seed stack created them
     "with disabled trust, bind boundaries, attach every identity/guard, then
     verify" (BI `pulumi/seed/README.md` lines 176-179). Their trust was
     activated by a separate change set that changes "only three executor
     trusts" (`operator_seed_installation.py` lines 325-462). `_role_resource`
     (lines 108-128) creates "only the three bounded executors".
  4. **Seed amendments.** #284 amended the installed TEST seed stack:
     `scripts/operator_seed_installation.build_amendment` renders a
     candidate template; "an independently authenticated non-root operator"
     reviews it, creates one change set "under the narrow temporary stack
     policy", executes "only that change-set ID", restores the permanent
     deny-update stack policy and reads everything back. "Only after exact
     live readback" a reviewed PR moves `CATALOG_HASHES` to the result hash
     (`specs/test-poc-prerequisite-capability/amendment-installation.md`
     lines 11-60). The amendment module
     `pulumi/seed/test_poc_prerequisite_amendment.py` pins the baseline
     policy hashes and the result catalog hash `ff2eaf29…` against the
     baseline `ef419680…`. Between install and pin, every operator TEST run
     fails closed at enrollment, so both happen inside one announced
     freeze window (`post-seed-activation.md` lines 107-125, NFR7). #284 FR6
     also admitted one exact USI policy ARN to the two closed resource lists
     of the governance apply guard (`requirements.md`, FR6).
  5. **Fixed inventory.** `_validate_closure` requires exactly 55 policies,
     24 principals and 21 existing roles (`policy_registry.py` lines
     347-362). `_validate_policy_inventory` fixes the kind counts (lines
     323-332), `verify_enrollment` returns three disabled executors (line
     502), and `_active_executor_trust` maps only the `GitHubOperator*` ARNs
     (lines 505-513). The README states that "an inventory change requires a
     reviewed catalog and code update" (lines 35-36). New seed-owned
     policies under `policy/issue215-seed/{env}/*` are already covered by
     the shared protected-resource deny `668edd62…` (TEST; `94b8d964…` PROD)
     and the guard-detach deny `415affc4…` ("The new guard namespace is
     already protected", README lines 145-147).
- **GR-19 `[SRC]` #285's installability stop.** `wt-boot-219`
  `specs/219-test-workload-capability/installability-stop.md` lines 5-26:
  "The existing operator seed and governor cannot install runtime roles."
  The installer "rebuilds the complete pinned packet; adding … three runtime
  principals is rejected". `G-GitHubGovernanceApply` "unconditionally denies
  `iam:CreateRole`", and its `iam:*`/`NotResource` statement denies all IAM
  operations on new roles; "Removing those Denies globally … is forbidden".
  Its next-amendment plan amends "the existing governor boundary and guard
  documents" (lines 55-59).
  #285 chose a separate three-resource CloudFormation stack for its
  publisher role, and stated that its principals did not enter the
  catalogs (lines 34-54; `runtime-enrollment.md` lines 315-327). So the seed
  registration route of D-A1 needs the inventory, installer and validator
  code changes of G1.1. Today's code would reject the gateway principals.
- **GR-20 `[SRC]` USI ConfigRead trust.** BI `pulumi/infra/ci_config.py`
  lines 202-230: the `test-pr` reader trusts `repo:<slug>:pull_request` for
  every repository except BI; the `test` and `prod-preview` readers also
  trust `ref:refs/heads/<branch>`. `docs/ci-config-trust-contract.md` lines
  11-14: "`test-pr` intentionally retains pull-request subjects". The USI
  Preview and Drift deployment roles also trust the `main` ref
  (`ci_bootstrap.py` lines 353-380). This bears on D-A10 and PD-14.

## 4. The user-service side (USI)

- **GR-6 `[SRC]` The gateway backend contract already exists.**
  `specs/poc-api-gateway-backend.md` (sha256 `6cd1b9ac…`) and
  `scripts/poc_gateway_backend.py` (sha256 `5410ad7d…`, last changed in
  `a47b3fc`):
  - USI owns the internal ALB, its HTTPS listener, the ALB security group
    and a dedicated **VPC-link security group** (`user-service-vpc-link-sg`).
    The ALB group's sole ingress is TCP 443 from the VPC-link group
    (`_gateway_ingress`, lines 94-118); the VPC-link group has no ingress
    (line 71) and HTTPS egress only to the application subnet CIDRs (spec
    lines 49-52). The gateway attaches that existing group to its VPC link
    and "never adds standalone rules".
  - The projector returns the closed descriptor `poc-api-gateway-backend/v1`
    (lines 37-91): `account_id`, `region`, `integration_type HTTP_PROXY`,
    `connection_type VPC_LINK`, `listener_arn`, `vpc_id`, two `subnet_ids`,
    `alb_security_group_id`, `vpc_link_security_group_id`,
    `tls_server_name` (the admitted FQDN), `certificate_arn`, and
    `request_parameters {"overwrite:path": "$request.path"}`.
  - Two parts are stale. The spec says "HTTP API" (lines 3, 36, 63) and
    `request_parameters` is HTTP API syntax, but D-3 chose a REST API. Its
    certificate text (line 30, lines 41-60) describes the SSM publication
    that D-15 removed; USI S4.14 rewrites those lines.
  - "The accepted-workload observer and authenticated publication remain
    unimplemented; there is no usable live descriptor yet" (spec lines
    14-15).
- **GR-7 `[SRC]` The USI plan's gateway touch points.**
  - S5.16 (AGI): "REST API + WAF + VPC link V2 directly to the internal ALB
    (`integration_target`), custom domain, pipeline (D-3, decided). V-10
    (docs and provider source)." Acceptance: the route reaches the service;
    direct ALB access from outside the VPC fails; an NLB target without a
    recorded fallback fails; 60-day inactivity documented (USI
    `epics-stories.md` line 3755). Ordered row 26, independent.
  - XP-10 (TEST) and XP-15 (PROD), rewritten by D-15: the gateway owner
    supplies the issued certificate's ARN, and a reviewed USI contract PR
    pins it as `workload.external.domain.certificate_arn` (USI `prd.md`
    §7). XP-11 (USI row 42) "needs the XP-10 ARN"; XP-15 is USI row 49, a
    gate-2a prerequisite.
  - S4.6 step 17 (USI row 43, gate 1 campaign): "AGI TEST route through VPC
    link V2 → ALB and WAF sampled requests … Runs only when S5.16 has
    merged … Required before any public exposure and before gate 2 if PROD
    is public."
  - S4.7 (USI row 52) gate 2 preconditions include "S5.16 with S4.6 step 17
    evidence if PROD is publicly exposed" and XP-15.
- **GR-8 `[SRC]` The governed pipeline pattern** (USI worktree
  `wt-usi-hardening`, `0721d93`):
  - Unprivileged PR checks: `python-quality.yml` (`permissions: contents:
    read`), `pulumi-pr-guardrails.yml` (a structural preview on a local
    file backend), `security-scans.yml`, `codeql.yml`; `Makefile` line 40
    `BRANCH_COVERAGE_MIN ?= 100`.
  - ChatOps: `pulumi-pr-commands.yml` (`issue_comment`, lines 1-30) parses
    `/pulumi <env> <command>`, checks author association, pins the PR head
    SHA, rejects forks, and dispatches `repository_dispatch` type
    `pulumi-pr-command` to `self-deploy.yml` (lines 1-12), which runs
    preview (saved plan, artifact with sha256), the destructive-diff gate
    and the Kravalg-gated apply that replays the plan.
  - `scripts/pulumi_ci_guardrails.py` lines 16-30: `DESTRUCTIVE_OPS`
    (`delete`, `replace`, `delete-replaced`) and `CRITICAL_TYPE_PATTERNS`
    (including `aws:iam/`, `aws:kms/`, `aws:route53/`); the IAM gate
    validates extracted documents with Access Analyzer. USI `AGENTS.md`
    line 20: the `allow-destructive-infra-change` label "is not an
    authorization override".
  - `scheduled-drift.yml`: daily, `test-drift` and `prod-drift`
    environments, the Drift role.
  - `scripts/_github_repository_controls.py` lines 12-39: 25 required
    status checks; pull-request rule with one approval, code-owner review,
    last-push approval, thread resolution, stale-review dismissal, squash
    only; environments with `Kravalg` as the PROD reviewer.
  - Backend per stack config: `s3://pulumi-user-service-infrastructure-{env}-state`
    and `awskms://alias/pulumi-user-service-infrastructure-{env}-secrets`
    (`pulumi/Pulumi.test.yaml` lines 16-20).
  - The PoC-only parts (`scripts/poc_*.py`, `scripts/service_execution_*.py`,
    the registry and workload stages of `self-deploy.yml`) are not part of
    the generic pattern.
- **GR-16 `[SRC]` No PROD gateway domain exists anywhere.** A grep of the
  USI `specs/`, `docs/`, `schemas/` and `scripts/` finds
  `user.vilnacrmtest.com` and the bare `vilnacrm.com`, and no PROD FQDN for
  the user service.

## 5. AWS capability verification (aws-knowledge MCP, 2026-10-01)

| ID | Fact | Source |
| --- | --- | --- |
| GA-1 | A REST API private integration to an ALB or NLB uses a VPC link V2: type `HTTP_PROXY`, `connectionType VPC_LINK`, `connectionId` the VPC link V2 id (or a stage variable), `integrationTarget` the **load balancer ARN** (`…:loadbalancer/app/<name>/<id>`). The `uri` sets the `Host` header and, for HTTPS, "is used to verify the stated domain name against the one in the certificate installed on the VPC endpoint". The CloudFormation property reference words `IntegrationTarget` as "the ALB or NLB listener"; the developer guide, the CLI example and the provider (GR-17) all use the load balancer ARN, so V-A2 confirms it live. | [AWS] apigateway/latest/developerguide/set-up-private-integration.html; CloudFormation `AWS::ApiGateway::Method` Integration `IntegrationTarget` (via the CDK `CfnMethod.IntegrationProperty` reference) |
| GA-2 | VPC link V2: all resources in one account; subnets and security groups are immutable after creation; API Gateway creates and manages the ENIs; after 60 days without traffic the link becomes `INACTIVE`, its ENIs are deleted and requests fail until it is reprovisioned (a few minutes). Supported in `eu-central-1` in `euc1-az1`, `euc1-az2` and `euc1-az3`. | [AWS] apigateway/latest/developerguide/apigateway-vpc-links-v2.html |
| GA-3 | API Gateway creates its service-linked role when an API, custom domain or VPC link is created; creating a service-linked role requires `iam:CreateServiceLinkedRole`. | [AWS] apigateway/latest/developerguide/using-service-linked-roles.html; AWS Security Blog "Introducing an easier way to delegate permissions to AWS services: service-linked roles" |
| GA-4 | REST API CloudWatch logging (execution and access) needs an IAM role trusted by `apigateway.amazonaws.com`, set as the account's `cloudWatchRoleArn`, **per Region**; the AWS managed policy `AmazonAPIGatewayPushToCloudWatchLogs` has the permissions. `AWS::ApiGateway::Account` sets it. | [AWS] apigateway/latest/developerguide/set-up-logging.html; rest-api-execution-logging.html; CloudFormation aws-resource-apigateway-account.html |
| GA-5 | WAF logs to CloudWatch Logs need a log group named `aws-waf-logs-…`, in the web ACL's account and Region; one destination per web ACL; on `PutLoggingConfiguration` WAF creates a resource policy on the log group. | [AWS] waf/latest/developerguide/logging-cw-logs.html; WAFV2 API `LoggingConfiguration` |
| GA-6 | REST API and custom-domain security policies: legacy `TLS_1_0`, `TLS_1_2`; enhanced `SecurityPolicy_*`, which need an endpoint access mode; `STRICT` enforces SNI host matching for Regional endpoints; changes take about 15 minutes. `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` accepts TLS 1.3 and TLS 1.2 with ECDHE GCM suites only. | [AWS] apigateway/latest/developerguide/apigateway-security-policies.html; apigateway-security-policies-list.html; Compute Blog "Enhancing API security with Amazon API Gateway TLS security policies" |
| GA-7 | `disableExecuteApiEndpoint: true` makes the default `execute-api` endpoint return HTTP 403 for REST APIs; the IAM condition key `apigateway:Request/DisableExecuteApiEndpoint` can require it. | [AWS] repost knowledge-center/api-gateway-disable-endpoint; apigateway/latest/developerguide/security_iam_id-based-policy-examples.html |
| GA-8 | HTTP APIs have no WAF integration; WAF associates with REST API stages (USI research A-15, re-used). | [AWS] apigateway/latest/developerguide/http-api-vs-rest.html |
| GA-9 | The caller that enables WAF logging to CloudWatch Logs needs `wafv2:PutLoggingConfiguration` and `DeleteLoggingConfiguration`, and `logs:CreateLogDelivery`, `DeleteLogDelivery`, `PutResourcePolicy`, `DescribeResourcePolicies`, `DescribeLogGroups`, documented on Resource `*`. | [AWS] waf/latest/developerguide/logging-cw-logs.html |
| GA-10 | WAF rate-based rules: evaluation windows 60, 120, 300 (default) or 600 s; lowest limit 10; per aggregation instance (for example source IP); a scope-down statement narrows what is counted. | [AWS] waf/latest/developerguide/waf-rule-statement-type-rate-based-high-level-settings.html |
| GA-11 | Add AWS managed rule groups in Count mode first, review the logs and metrics, then switch to Block; `AmazonIpReputationList` targets IPs engaged in DDoS activity. | [AWS] repost knowledge-center/waf-block-common-attacks; repost knowledge-center/waf-mitigate-ddos-attacks |
| GA-12 | API Gateway throttling: account-level 10,000 requests/s per Region with a 5,000 burst; per-stage, per-method limits apply first and cannot exceed the account limits. | [AWS] apigateway/latest/developerguide/api-gateway-request-throttling.html; repost knowledge-center/api-gateway-throttling |
| GA-13 | Route 53 `ChangeResourceRecordSets` can be limited by `route53:ChangeResourceRecordSetsNormalizedRecordNames`, `…RecordTypes` and `…Actions`. | [AWS] service-authorization/latest/reference/list_route53.html; Route53/latest/DeveloperGuide/resource-record-sets-permissions.html |
| GA-14 | A Regional custom domain needs an ACM certificate in the same Region as the API, with the domain in its names. | [AWS] repost knowledge-center/custom-domain-name-amazon-api-gateway; ACM FAQs |
| GA-15 | ACM renews a DNS-validated certificate automatically, using the same validation CNAME, 60 days before expiry; renewal fails if the CNAME is missing. | [AWS] repost knowledge-center/acm-dns-certificate-renewal; acm/latest/userguide/troubleshooting-renewal.html |
| GA-16 | ACM condition keys include `acm:DomainNames` (restricts the domains in a certificate request), `acm:ValidationMethod`, `acm:KeyAlgorithm`, `aws:RequestTag/${TagKey}` and `aws:ResourceTag/${TagKey}`; which action supports which key is per action (V-A7). | [AWS] service-authorization/latest/reference/list_acm.html |
| GA-17 | Associating a web ACL with a REST API stage needs `wafv2:AssociateWebACL` on the web ACL **and** `apigateway:SetWebACL` on `arn:aws:apigateway:*::/restapis/*/stages/*`; disassociation needs only `apigateway:SetWebACL`; `GetWebACLForResource` (with `GetWebACL`) and `ListResourcesForWebACL` are authorized on the web ACL ARN. | [AWS] waf/latest/developerguide/security_iam_service-with-iam.html ("Actions that require additional permissions settings") |

## 6. Options analysis

| Topic | Options | Recommendation or decision |
| --- | --- | --- |
| Front-door shape | Fixed by **D-3**: REST API + WAF, VPC link V2 → internal ALB; NLB fallback only after a failed V-A1. | D-3 (user, 2026-09-30). |
| CI identity creation | (a) independent CloudFormation owner; (b) governance catalog route with guard narrowing (GR-12); (c) the BI seed registration route: a reviewed seed catalog amendment that creates and registers the roles (GR-18). | **D-A1** (user, 2026-10-01): the seed registration route, (c). Governance writes the later grants and the non-role resources after an exact-ARN seed admission (D-A9); no ConfigRead roles (D-A10). |
| Cross-repo coordinates | (a) Pulumi `StackReference` to the USI stack (needs read access to the USI state bucket and KMS key: a broad cross-repository read); (b) SSM publication by USI (contradicts D-15's direction); (c) **a reviewed contract pin in this repository**, the D-15 pattern in the other direction, verified live by read-only describe calls. | **(c)**, the coordinator's instruction and the D-15 pattern; AD-A3. |
| Certificate | (a) adopt PR #34 as is (SSM parameter, legacy bucket); (b) **adopt and amend**; (c) supersede with a new PR. | **(b)**, AD-A2, PD-9. |
| Log KMS key | OQ-2. | **D-A4**: dedicated BI-owned gateway CMK per environment. |
| WAF log delivery | OQ-4. | **D-A5**: BI pre-created resource policy; never `logs:PutResourcePolicy` on `*`. |
| TLS policy | (a) legacy `TLS_1_2`; (b) **enhanced `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` with `STRICT`**. | (b), with (a) as the recorded fallback if V-A5 finds a provider or service gap. |
| Execution logging | (a) on at `INFO` with data trace; (b) **off; access logs only**. | (b): data trace can log bodies; access logs carry the request id, source IP, status, latency, TLS version and cipher (GA-6). |

## 7. Risks discovered

| ID | Risk | Handling |
| --- | --- | --- |
| K-1 | The documented onboarding is blocked by the seed guards (GR-12). | D-A1: the seed registration route; G1.1, G1.2. |
| K-2 | A catalog-enrolled repository gets a TEST Preview `pull_request` trust (GR-11). | AD-A1: the gateway trust has no `pull_request` subject; G1.2 asserts it. |
| K-3 | Seed amendments for the gateway change `CATALOG_HASHES` and collide with the USI plan's one-open seed serialization (USI C-BI rows 8-50). | XP-A4: the BI owner gives each gateway seed operation a slot in the same queue. |
| K-4 | The gateway TEST certificate gates USI XP-10 → XP-11 (USI row 42) → gate 1 (row 43). A slow gateway enrolment delays USI gate 1. | The certificate path (rows 1-11 and 15) is scheduled first; rows 16-17 are not needed before USI row 42 (AD-A12). |
| K-5 | The VPC link goes `INACTIVE` after 60 idle days (GA-2), so a quiet TEST front door fails cold. | The scheduled drift job also sends one HTTPS probe through the custom domain (FR-A13); the runbook names the recovery time. |
| K-6 | `AmazonAPIGatewayPushToCloudWatchLogs` grants CloudWatch Logs writes on `*`, and `cloudWatchRoleArn` is account-wide (GA-4). | AD-A9: a BI-owned role with a policy scoped to the gateway log groups, set by the BI prerequisites stack; XP-A12 reads the current value first. |
| K-7 | WAF log delivery may need `logs:PutResourcePolicy` on `*` (GA-9). | D-A5, V-A6. |
| K-8 | The TEST zone is shared with USI's DKIM records (GR-14). The gateway's `_*.{fqdn}` pattern does not match them, but a later pattern could. | AD-A8: an explicit deny on `*._domainkey.*` names for the gateway roles, as defence in depth. |
| K-9 | The USI descriptor is written for an HTTP API (GR-6). | AD-A3: the gateway consumes only the coordinates and checks `request_parameters` as an opaque v1 constant; the REST mapping is the gateway's own. The wording fix is a USI follow-up (USI-F1, outside this plan). |
| K-10 | A legacy gateway stack may exist in an unknown backend (GR-4). | XP-A9, D-A6. |
| K-11 | `cloudWatchRoleArn` or the API Gateway service-linked role may already be set or missing in an account. | XP-A5, XP-A12 (read-only checks before G1.5). |
| K-12 | USI S4.6 steps 18-20 require no foreign ENI in the application subnets, then delete and rebuild them with new ids (USI `epics-stories.md` lines 2866-2900; `prd.md` lines 393-402); a gateway VPC link built for step 17 sits in those subnets. | D-A2 (OQ-8 (c)): the TEST front door is built after USI step 20; CR-A1; AD-A3; AD-A12 order table. |
| K-13 | USI TEST scales to zero on nights and weekends (USI FR-14 (c)); probes and the 5XX alarm would fail or page then. | PD-13; FR-A13, FR-A21. |
| K-14 | The USI descriptor's authenticated publication is unimplemented (GR-6). | D-A8; AD-A3 live re-verification. |
| K-15 | The seed registry hard-codes its principal counts and treats `existing: false` as an operator executor (BI `pulumi/seed/policy_registry.py` lines 355, 431-446, 505-514, 570-590). | AD-A1: the seed creates the gateway principals as a new seed-created service kind and registers them, with inventory, installer and verifier changes in G1.1 (GR-18, GR-19; V-A10). |
| K-16 | For new runtime roles, the BI owner chose a separate CloudFormation stack, not an extension of the seed inventory (GR-19). The BI owner may decline the inventory extension that D-A1 needs. | V-A10: the BI owner confirms the extension shape in G1.1's review. If it is declined, the story STOPs and goes back to the user. There is no silent fallback to an independent stack. |
| K-17 | Governance cannot write any gateway IAM resource or create the gateway's S3, KMS and account-level resources. Its guard (`8c068aaa…`, `5366ec11…`) and its USI-scoped seed ceilings (`ceiling/GitHubGovernanceApply` `7a36d2ff…`, `a392c269…`, `00257170…`, `abfe3f39…`; `C-GitHubGovernancePreview`/`-Drift`) both block it, and the operator executor guards (`0c5eed92…`, `c18540fb…`, `408cdbf9…` in TEST) close the governance policy names to the USI ones. So the gateway's grants and non-role BI resources need an owner that the USI pattern does not give (GR-12, GR-18). | D-A9, re-scoped by D-A11: the gateway's governance apply runs under a dedicated seed-created role; only the shared Preview/Drift ceilings, the operator bindings and the five operator guards are amended (AD-A1). |
| K-18 | `ceiling/GitHubGovernanceApply` is 5752 (TEST) / 5762 (PROD) characters of 6144, and the D-A9 exact-ARN additions need 7187-8729 (revision-3 audit). | Resolved by D-A11: a dedicated governance Apply role with its own ceiling (measured 5866); USI's ceiling untouched; V-A12. |
