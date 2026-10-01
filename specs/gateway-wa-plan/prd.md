---
artifact: prd
workflow: _bmad/core/tasks/bmad-create-prd (non-interactive; steps resolved from the task intent)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 1
inputDocuments: [research.md, brief.md, decisions.md, USI specs/workload-wa-hardening (9d5df4a), USI specs/poc-api-gateway-backend.md]
---

# PRD: the API gateway Well-Architected track

## 1. Executive summary

This PRD turns user decision D-3 (REST API + WAF, private integration over a
VPC link to the USI internal ALB) and USI story S5.16 into a governed track
for `VilnaCRM-Org/api-gateway-infrastructure` (AGI). It covers:

- the enrolment of AGI in bootstrap-infrastructure (BI);
- AGI's repository controls and governed CI/CD pipeline;
- the TEST and PROD certificates (PR #34 amended) and their hand-off to USI
  under D-15;
- the TEST and PROD front door: REST API, VPC link V2, WAF, custom domain,
  stage logging and throttling, alarms;
- the cross-repository contract with USI and the gate order against the USI
  gates;
- the disposition of PRs #34, #33, #32 and #26.

Each requirement names its owning repository: **AGI** (this repository),
**BI** (bootstrap-infrastructure) or **USI** (user-service-infrastructure,
external precondition only).

**Counts.** 25 FRs and 11 NFRs, 36 requirements.

| Category | Count | Requirements |
| --- | --- | --- |
| Offline-testable (a unit, policy, template or simulator-fixture test proves the source) | 31 | FR-A01…FR-A21, FR-A24, FR-A25 (23 FRs); NFR-A01, -A02, -A03, -A04, -A07, -A08, -A09, -A11 (8 NFRs) |
| Live-evidence-only FRs (TEST or PROD runs; their offline fixtures check only the evidence format) | 2 | FR-A22, FR-A23 |
| Evidence-only NFRs | 3 | NFR-A05, NFR-A06, NFR-A10 |
| Offline-testable FRs that also need live evidence (the Risk column contains L) | 18 | FR-A01…FR-A07, FR-A12…FR-A21, FR-A25 |

A test in G3.2 recomputes these counts from the tables below.

## 2. Authorized actions and failure states

- **Authorized by this plan:** nothing live. Stories may change source and
  tests in their owning repository through reviewed PRs.
- **Needs separate, explicit, per-action authorization from the user in
  chat, then the protected-environment gate:**
  - every `/pulumi <env> up` (AGI) and every BI apply;
  - every seed catalog amendment, independent stack install or stack
    amendment (BI seed operator, reviewed installer XP-A1, `@Kravalg`);
  - applying the repository ruleset and environments (repository admin,
    XP-A3);
  - closing PRs #26, #32 and #33 and pushing to PR #34;
  - any deletion (the legacy bucket of OQ-5, the OQ-8 (a) TEST teardown, a
    recovery).
- **Failure states.** Every story lists STOP conditions. A STOP halts the
  story, records evidence and escalates to the named owner. No story
  retries a STOP with wider permissions, a removed check or a label
  override.

## 3. Functional requirements

Risk letters: **I** IAM, **S** state, **N** network exposure, **L** live
evidence, **C** cross-repository.

### E-G1 Bootstrap enrolment (BI)

| ID | Requirement | Owner | Env | Risk |
| --- | --- | --- | --- | --- |
| FR-A01 | **Gateway CI identities.** Per environment, roles `GitHubCiPreview-api-gateway-infrastructure-{env}`, `GitHubCiApply-…-{env}` and `GitHubCiDrift-…-{env}` exist, created by an independent CloudFormation identity stack (OQ-1 (a)), each with the boundary `GovernanceBoundary-api-gateway-infrastructure-{env}` and an immutable guard policy created in the same stack (no unguarded window). Under PD-12 the stack also creates `PulumiStateRepl-api-gateway-infrastructure-{env}` with `GovernanceReplicationBoundary-api-gateway-infrastructure-{env}`. Trust: the GitHub OIDC provider; `aud sts.amazonaws.com`; `repository_id 887871673` and `repository_owner_id 114362548`; Apply only `environment:{env}`; Preview only `environment:{env}-preview`; Drift only `environment:{env}-drift`. **No `pull_request`, `ref` or wildcard subject.** `MaxSessionDuration` 3600 s. | BI | TEST, PROD | I, L |
| FR-A02 | **Seed registration.** After the identity stack exists, a seed catalog amendment per environment registers its principals (`existing: true`), boundaries and guards in `pulumi/seed/catalogs/{env}.json`, updates `CATALOG_HASHES`, the fixed principal counts and the attachment rules in `pulumi/seed/policy_registry.py`, and passes `verify_active_enrollment`. No existing guard statement on Resource `*` is narrowed. The boundary renders at ≤ 6144 characters. | BI | TEST, PROD | I, S, L |
| FR-A03 | **Backend.** State bucket `pulumi-api-gateway-infrastructure-{env}-state` (versioning, SSE-KMS, public access blocked, TLS-only bucket policy, `Retain`) and Pulumi secrets key alias `pulumi-api-gateway-infrastructure-{env}-secrets`, replicated as BI replicates the USI backend. No passphrase secrets provider. | BI | TEST, PROD | S, L |
| FR-A04 | **Capability grants.** Identity allows for the three CI roles cover exactly the gateway resources of architecture AD-A7 (names, prefixes, conditions), with the deny set of AD-A7. No `iam:*`, `ssm:*`, `secretsmanager:GetSecretValue`, `iam:PassRole` or `iam:CreateServiceLinkedRole`. A simulator matrix proves each allow and each deny. | BI | TEST (G1.4a, G1.4b), PROD (G1.7, G1.8) | I, L |
| FR-A05 | **Account prerequisites.** Per account, an independent BI stack owns (a) the API Gateway CloudWatch role, trusted by `apigateway.amazonaws.com` with a policy scoped to the gateway access-log group, (b) the account's `cloudWatchRoleArn` setting for `eu-central-1`, and (c) under OQ-4 (a), the CloudWatch Logs resource policy for `aws-waf-logs-api-gateway-infrastructure-*`. The API Gateway service-linked role exists before the first gateway apply. | BI | TEST, PROD | I, L |
| FR-A06 | **Gateway CMK** (OQ-2 (a)). One symmetric CMK per environment, rotation on, alias `alias/api-gateway-infrastructure-{env}-logs`; the key policy lets `logs.eu-central-1.amazonaws.com` use it only with `kms:EncryptionContext:aws:logs:arn` matching the two gateway log groups, and lets the gateway Apply role call `kms:DescribeKey` through `logs`. The SNS topic uses the same key, for the reason D-8 records for the workload topic (CloudWatch alarms cannot publish to a topic on the AWS-managed SNS key). | BI | TEST, PROD | I, L |

### E-G2 Repository controls and hygiene (AGI)

| ID | Requirement | Owner | Env | Risk |
| --- | --- | --- | --- | --- |
| FR-A07 | **Repository controls.** A reviewed, tested definition (ported `configure_github_repository_controls.py`) holds: a `main` branch ruleset (no bypass actors; deletion and non-fast-forward blocked; pull request with 1 approval, code-owner review, last-push approval, thread resolution, stale-review dismissal, squash only; the required checks of architecture AD-A11); CODEOWNERS `* @Kravalg`; environments `test-preview`, `test`, `test-drift`, `prod-preview`, `prod`, `prod-drift` (plus `test-recovery` only under OQ-8 (a)), each limited to `main` or to the dispatch path the pipeline uses, with `@Kravalg` as the sole required reviewer of `test` and `prod` and self-review prevented. The admin applies it (XP-A3); a readback equals the definition. | AGI | repo | L |
| FR-A08 | **Hygiene.** Remove both template-sync workflows (PAT, wrong source) and the privileged auto-commit linter; pin every action by full commit SHA; run every PR job with `permissions: contents: read` and no secret; replace `docker-compose.yml`'s static-key passthrough with an SSO-profile note for local debugging only; dependabot covers the uv lockfile and GitHub Actions. | AGI | repo | — |

### E-G3 Governed pipeline (AGI)

| ID | Requirement | Owner | Env | Risk |
| --- | --- | --- | --- | --- |
| FR-A09 | **Toolchain and stacks.** uv with a frozen lockfile, Python 3.11, `pulumi-aws` 7.23.0 (PD-2); project `api-gateway-infrastructure`; `Pulumi.test.yaml` and `Pulumi.prod.yaml` pin the account, region, backend URL and `awskms://` secrets provider; account ids live only in stack config and the contracts, never in Python constants. | AGI | TEST, PROD | S |
| FR-A10 | **Quality battery** on every PR, unprivileged: ruff, type check, maintainability, bandit, pip-audit, gitleaks, actionlint, zizmor, yamllint, hadolint, CodeQL (python, actions), dependency review, unit tests with Pulumi mocks at **100% branch coverage**. | AGI | — | — |
| FR-A11 | **Guardrails.** A structural preview on a local file backend; the destructive-diff gate (`delete`, `replace`, `delete-replaced` blocked, no label override) with one reviewed allowance for `aws:apigateway/deployment:Deployment` replacement (AD-A10); an IAM gate that fails on **any** `aws:iam/*` resource; a policy pack that enforces AD-A10's front-door rules. | AGI | — | I |
| FR-A12 | **ChatOps with saved plans.** `/pulumi <env> plan` and `/pulumi <env> up` on a PR, from a write-permission member, on the PR head SHA, never from a fork; plan under the Preview role in `{env}-preview`, saved with sha256; up under the Apply role in `{env}` after `@Kravalg`'s approval, replaying exactly that plan for exactly that head; PROD refuses a head without a successful TEST up of the same head; results commented on the PR. `initialize-stack` creates backend metadata only. | AGI | TEST, PROD | I, S, L |
| FR-A13 | **Scheduled drift and probe.** On a schedule (TEST: weekdays inside the USI daytime window, PD-13; PROD: daily), per initialized stack, under the Drift role in `{env}-drift`: `pulumi preview --refresh --expect-no-changes` (the USI drift invocation, USI `scripts/_pulumi_command_support.py` line 68), which also runs the live contract checks of FR-A16; then, once the stack exports a domain, one unauthenticated HTTPS `GET` of the health path through the custom domain (keeps the VPC link active, GA-2), whose result is published as a custom metric for the FR-A21 alarm. A failure fails the job. | AGI | TEST, PROD | L |

### E-G4 Certificates (AGI)

| ID | Requirement | Owner | Env | Risk |
| --- | --- | --- | --- | --- |
| FR-A14 | **TEST certificate** (PR #34 amended): an ACM certificate for `user.vilnacrmtest.com`, DNS-validated by one CNAME in `Z04999481RZ4UQK2NANVH` (`allow_overwrite=False`), `retainOnDelete` and `protect` on both, the stack/account/zone checks kept. **No SSM parameter.** The issued ARN is exported and handed to the USI owner (XP-A8 → USI XP-10). | AGI | TEST | N, C, L |
| FR-A15 | **PROD certificate**, the same for the OQ-3 FQDN and zone in account `933245420672`; ARN handed over for USI XP-15. | AGI | PROD | N, C, L |

### E-G5 TEST front door, E-G6 PROD front door (AGI)

| ID | Requirement | Owner | Env | Risk |
| --- | --- | --- | --- | --- |
| FR-A16 | **Backend contract pin.** `contracts/user-service-backend/{env}.json` (schema `agi-user-service-backend/v1`) embeds the USI `poc-api-gateway-backend/v1` descriptor verbatim, its source (USI commit, run URL, descriptor sha256) and the derived `integration_target` (the load balancer ARN derived from `listener_arn`). Offline checks: closed schema, account and region equal the stack's, the derivation, `tls_server_name` equal to the stack FQDN, `certificate_arn` equal to this stack's certificate. Live checks (every preview and drift): the listener is HTTPS 443 on that load balancer with that certificate; the load balancer is internal, `application`, in the two subnets, with only the ALB group; the ALB group's only ingress is 443 from the VPC-link group; the VPC-link group has no ingress. | AGI | TEST, PROD | N, C, L |
| FR-A17 | **VPC link and REST API.** A VPC link V2 on the two pinned subnets with only the pinned VPC-link group; a Regional REST API with `disableExecuteApiEndpoint`; `ANY /` and `ANY /{proxy+}` as `HTTP_PROXY` over `VPC_LINK` with `integration_target` the pinned ALB, `uri` `https://<fqdn>/{proxy}` (TLS name verified, GA-1), `{proxy}` mapped from `method.request.path.proxy`, `tlsConfig.insecureSkipVerification` false, the default 29 s timeout. No NLB unless V-A1 fails and the fallback is reviewed. | AGI | TEST, PROD | N, L |
| FR-A18 | **Stage.** One stage `live`: access logging in JSON to the KMS log group (request id, source IP, method, path, status, latency, integration latency, `wafResponseCode`, `tlsVersion`, `cipherSuite`, user agent; no headers, no body); execution logging off and data trace off; method-level metrics on; throttling on `*/*` at PD-3 (TEST) or the OQ-6 values (PROD); no cache. | AGI | TEST, PROD | L |
| FR-A19 | **WAF.** A Regional web ACL `api-gateway-infrastructure-{env}`, default Allow, associated with the stage: `AWSManagedRulesAmazonIpReputationList` (block), `AWSManagedRulesKnownBadInputsRuleSet` (block), `AWSManagedRulesCommonRuleSet` (count, then block per PD-8), `AWSManagedRulesAnonymousIpList` (count), the PD-4 rate rules (block); WCU within the 1,500 default; CloudWatch metrics and sampled requests on every rule; logging to `aws-waf-logs-api-gateway-infrastructure-{env}` with the `authorization` and `cookie` headers redacted. | AGI | TEST, PROD | N, L |
| FR-A20 | **Custom domain and DNS.** A Regional custom domain for the FQDN on the FR-A14/FR-A15 certificate, `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` with `STRICT` (fallback `TLS_1_2`, V-A5), an empty base path mapping to stage `live` (the app path is preserved), and Route 53 alias A and AAAA records to the domain's Regional target. | AGI | TEST, PROD | N, L |
| FR-A21 | **Alarms.** An SNS topic `api-gateway-infrastructure-{env}-alarms` on the gateway CMK with the XP-A10 subscription; alarms on 5XXError (with a minimum request count, so TEST's scaled-to-zero 503s outside the USI daytime window do not page, PD-13), 4XXError rate, Latency p99, WAF `BlockedRequests` spike, and the probe metric of FR-A13; each alarm links a runbook in `docs/runbooks/`. | AGI | TEST, PROD | L |
| FR-A22 | **TEST acceptance (gate A-T).** The campaign of AD-A12 passes and its evidence is published for USI S4.6 step 17. | AGI (+USI live) | TEST | L, C |
| FR-A23 | **PROD front door (gate A-P).** After USI gate 2 and with the PROD contract pinned, the PROD stack applies FR-A16…FR-A21 and passes the same campaign. | AGI | PROD | L, C |
| FR-A24 | **PR dispositions.** PR #34 is amended to FR-A14 (AD-A2); #26, #32 and #33 are closed with the recorded reasons (AD-A13); the legacy-stack inventory (XP-A9) is recorded and OQ-5 decides it. | AGI | repo | — |
| FR-A25 | **Coexistence with the USI abandon rehearsal (OQ-8).** Under OQ-8 (c) the TEST front door is built after USI S4.6 step 20 and nothing more is needed. Under OQ-8 (a): before USI step 18, a reviewed manifest lists, by Pulumi URN, exactly the gateway TEST resources to delete (VPC link, REST API with every child the plan removes, base path mapping, web ACL association), a TEST-only gateway recovery role in `test-recovery` (`@Kravalg` sole reviewer) applies the saved destroy plan that matches the manifest 1:1, and a read-back shows no gateway ENI in the USI subnets; after step 20, the new descriptor is pinned and the front door is re-applied. | AGI, BI | TEST | I, L |

## 4. Non-functional requirements

| ID | Requirement | Category | How proved |
| --- | --- | --- | --- |
| NFR-A01 | No long-lived credential in CI: OIDC only, no PAT, no static AWS key, no App-token write on PR events. | Security | workflow-shape tests; G2.1 grep |
| NFR-A02 | Least privilege: every allow names exact ARNs or prefixes; Resource `*` only for actions without resource-level support, each listed in AD-A7 with its source (V-A8). | Security | simulator matrix |
| NFR-A03 | TLS 1.2 or later on both hops: client → API Gateway (FR-A20); API Gateway → ALB HTTPS with the name verified (FR-A17) against the USI listener's `ELBSecurityPolicy-TLS13-1-2-Res-2021-06`. | Security | policy pack; G5.6 |
| NFR-A04 | Every gateway log group is KMS-encrypted (OQ-2), has PD-5 retention and carries no credential or body. | Security, operations | policy pack; G5.6 |
| NFR-A05 | Availability: two AZs; the VPC link is kept active; rebuild within PD-6. | Reliability | G5.6, runbook |
| NFR-A06 | Latency: gateway overhead p99 ≤ 100 ms over the ALB's target response time in TEST at the PD-3 rate. | Performance | G5.6 measurement |
| NFR-A07 | Cost: one web ACL per environment, ≤ 1,500 WCU, no paid rule group; log retention per PD-5; TEST resources tagged for cost allocation. | Cost | policy pack |
| NFR-A08 | Change safety: saved-plan only; destructive gate without override; TEST before PROD; `@Kravalg` approval; one seed operation open at a time. | Operations | workflow tests; XP-A4 |
| NFR-A09 | 100% branch coverage on `pulumi/`, `policy/`, `scripts/`. | Quality | Coverage check |
| NFR-A10 | Runbooks for each alarm, the VPC-link `INACTIVE` state, certificate replacement and a rebuild. | Operations | doc review |
| NFR-A11 | Supply chain: actions SHA-pinned, frozen lockfile, pip-audit and CodeQL blocking. | Security | zizmor, actionlint, pip-audit |

## 5. Acceptance cases (P positive, N negative, E edge)

| ID | P | N | E |
| --- | --- | --- | --- |
| FR-A01 | Each role's trust lists exactly its one environment subject and the two id claims. | A token for `pull_request`, another environment, another repository id or a fork is refused (simulated trust evaluation, then live `AssumeRoleWithWebIdentity` from the real environment only). | A role name over 64 characters fails the template test. |
| FR-A02 | `verify_active_enrollment` passes with the amended catalog; the hash pin matches. | Any narrowed statement on Resource `*` fails the amendment test. | Boundary at 6144 characters exactly passes; 6145 fails. |
| FR-A03 | `pulumi login` and `stack init` against the new backend succeed in `initialize-stack`. | A passphrase provider in stack config fails the stack-config test. | An existing bucket name collision stops the install (absent-name check). |
| FR-A04 | Simulator: each AD-A7 allow is `allowed`. | Simulator: `iam:CreateRole`, `ssm:GetParameter`, `apigateway:PATCH` on `/account`, `logs:PutResourcePolicy`, `route53:ChangeResourceRecordSets` on `x._domainkey.user.vilnacrmtest.com` are denied. | The record-name condition with a missing key is denied (`Null` guard). |
| FR-A05 | `GetAccount` shows the BI role; the SLR exists. | The gateway Apply role cannot change `/account`. | `cloudWatchRoleArn` already set by another owner → STOP (XP-A12). |
| FR-A06 | A log group created with the key accepts events. | Another log group cannot use the key (encryption-context condition). | Key rotation on. |
| FR-A07 | Readback equals the definition. | A push to `main` without a PR is rejected; a PR without the required checks cannot merge. | A missing check name in the definition fails the unit test. |
| FR-A08 | No workflow references `PERSONAL_ACCESS_TOKEN`; all `uses:` are SHA-pinned. | A tag-pinned action fails actionlint/zizmor. | A workflow with `pull_request_target` fails the shape test. |
| FR-A09 | Program imports under `pulumi-aws` 7.23.0. | A Python constant holding an account id fails a test. | `Pulumi.example.yaml` removed. |
| FR-A10 | All battery jobs run with `contents: read`. | A coverage drop below 100% fails. | A job requesting `id-token: write` on `pull_request` fails the shape test. |
| FR-A11 | A create-only preview passes. | A delete or replace of any other type fails; any `aws:iam/*` resource fails. | A Deployment replace passes only as create-before-delete of the same stage. |
| FR-A12 | `/pulumi test up` replays the saved plan of the same head. | A comment from a non-member, a fork, a stale head or `/pulumi prod up` without a TEST up of the same head is refused. | A plan artifact whose sha256 differs is refused. |
| FR-A13 | Clean drift and a 2xx/3xx probe pass. | A manual console change fails drift; a changed USI security group fails the contract check. | Probe skipped (recorded) before G5.5 is applied. |
| FR-A14 | ACM status `ISSUED`; the ARN is in the stack outputs and the hand-off record. | Another stack, account, zone or a private zone is refused before registration. | An existing record with the validation name fails (`allow_overwrite=False`). |
| FR-A15 | As FR-A14 in PROD. | PROD apply without OQ-3 is refused by the contract test. | — |
| FR-A16 | Offline and live checks pass. | A descriptor with an extra field, another account, a listener on another load balancer, or an ALB group with an extra ingress fails. | The derived load balancer ARN must equal the listener's `LoadBalancerArn` read live. |
| FR-A17 | Requests through the custom domain reach the service. | The default `execute-api` URL returns 403 (GA-7); the ALB DNS name is not resolvable to a reachable target from outside the VPC. | A certificate name mismatch on the ALB makes API Gateway fail the integration (5xx), observed once in TEST by a reviewed negative test or recorded as not exercised. |
| FR-A18 | An access-log line has every listed field. | No header or body appears in a log line. | A burst above PD-3 gets 429. |
| FR-A19 | Sampled requests show each rule; a known-bad input is blocked. | A request carrying an `authorization` header shows it redacted in the WAF log. | The rate rule blocks after the limit within the window (GA-10). |
| FR-A20 | TLS 1.2 and TLS 1.3 handshakes succeed with the policy's suites. | TLS 1.1 and a non-ECDHE TLS 1.2 suite fail; a request with an SNI/Host mismatch is rejected under `STRICT`. | Base path mapping preserves `/api/...` paths unchanged. |
| FR-A21 | `SetAlarmState` on each alarm delivers to the topic. | An alarm without a runbook link fails the policy test. | — |
| FR-A22 | All AD-A12 gate A-T rows pass. | Any row failing is a STOP. | Step 17 of USI S4.6 cites the evidence artifact. |
| FR-A23 | All gate A-P rows pass in PROD. | PROD up before USI gate 2 is refused. | — |
| FR-A24 | Each PR has a comment with its disposition reason. | — | The #34 amendment keeps the author's commits. |
| FR-A25 | (a) only: the destroy plan equals the manifest 1:1 and the ENI read-back is empty. | A plan with any delete outside the manifest, or a PROD stack, is refused. | Under (c) the story is not applicable and is recorded so. |

## 6. User-owned decisions

Reused: D-3, D-6, D-15 (and the D-4 consequence) — decisions.md §1.
Open: OQ-1…OQ-8 — decisions.md §2. Planning defaults: PD-1…PD-13 —
decisions.md §3. A story that depends on an open question STOPs until the
user answers it (epics-stories.md, each story's "Needs").

## 7. External preconditions (not satisfiable by AGI)

This plan uses a **gateway-local namespace, XP-A1…XP-A14** (PD-1). USI items
keep their USI names.

- **XP-A1. Reviewed installer, widened.** A reviewed, non-root installer
  role of USI XP-17's class (human, MFA, outside GitHub CI) runs every
  independent stack install and amendment of this plan (G1.2, G1.3, G1.5,
  G1.6, G1.9 and their amendments). The USI XP-17 installer is scoped to
  IAM role, policy, service-linked-role and Lambda handlers (USI `prd.md`
  lines 726-765); this plan also needs S3 and KMS (G1.3, G1.6),
  `AWS::ApiGateway::Account` with `iam:PassRole` of the logging role to
  `apigateway.amazonaws.com`, `AWS::Logs::ResourcePolicy` and the API
  Gateway service-linked role (G1.5). The widened permission set is its
  own BI review with `@Kravalg`'s approval. STOP without it.
- **XP-A2. `@Kravalg` approvals.** The seed review, each stack review, each
  BI and AGI PR, and every protected-environment apply.
- **XP-A3. Repository admin applies AGI controls.** A repository admin
  (`@Kravalg`) runs the reviewed controls script (G2.2) with an admin token,
  and the readback is attached to the PR. Admin token use is outside CI.
- **XP-A4. Seed serialization slot.** The BI owner places each gateway seed
  operation (G1.2, G1.1, G1.3, G1.4a, G1.5, G1.6, G1.4b, G1.9, G1.7, G1.8) in
  the same one-open queue as the USI plan's seed operations (USI
  architecture §4 C-BI), each on its predecessor's result catalog. The plan
  recommends the TEST certificate path (rows 8-11, then row 15) before USI row 42, because USI XP-11 needs
  the gateway's TEST certificate (K-4).
- **XP-A5. API Gateway service-linked role.** `AWSServiceRoleForAPIGateway`
  exists in each account (read-only `iam:GetRole` by the BI owner), or the
  installer creates it before G5.3. No CI role gets
  `iam:CreateServiceLinkedRole` (GR-12 `05f77e26…`).
- **XP-A6. TEST zone owner.** The owner of `Z04999481RZ4UQK2NANVH` confirms
  that this repository may create `user.vilnacrmtest.com` A/AAAA and its ACM
  validation CNAME, and a read-only listing shows no such record today.
- **XP-A7. USI descriptor hand-off.** The USI owner supplies the
  `poc-api-gateway-backend/v1` field values for the stack, with the USI
  apply run that created those resources: for TEST after USI S4.6 step 2
  (OQ-8 (a)) or step 20 (OQ-8 (c)); for PROD after USI S4.7's PROD apply.
  The authenticated USI publication does not exist (OQ-7); under OQ-7 (a)
  the gateway's live re-verification (AD-A3) is the authority.
- **XP-A8. Certificate hand-off.** The gateway owner supplies the issued
  TEST ARN for USI XP-10 and the PROD ARN for USI XP-15 to the USI owner,
  who pins them by a reviewed USI contract PR (D-15).
- **XP-A9. Legacy stack inventory.** The gateway owner reports, read-only,
  whether any gateway Pulumi state or `my-bucket` exists, and where.
- **XP-A10. Alarm endpoint.** The user supplies the SNS subscription
  endpoint for each environment.
- **XP-A11. PROD domain** (OQ-3): the FQDN and its zone owner.
- **XP-A12. API Gateway account settings.** A read-only `GetAccount` per
  account shows whether `cloudWatchRoleArn` is set, and by whom. If another
  owner set it, that owner and the BI owner agree on the change first.
- **XP-A13. Implementation profile.** The devops-sdlc profile for this
  repository exists before implementation (as USI XP-7).
- **XP-A14. USI campaign coordination.** The USI owner tells the gateway
  owner when USI S4.6 steps 2, 17, 18 and 20 start and finish, so the
  gateway rows of AD-A12 run in their windows.

**USI-F1 (outside this plan).** USI `specs/poc-api-gateway-backend.md` and
the descriptor's `request_parameters` describe an HTTP API. Under D-3 the
gateway is a REST API; the gateway treats `request_parameters` as an opaque
v1 constant. A USI owner may reword the spec or version the descriptor; this
plan needs neither.
