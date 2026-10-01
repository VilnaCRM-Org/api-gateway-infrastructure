# User decisions and open questions — API gateway Well-Architected track

This file is a planning input. Revision 2 (2026-10-01) records the user's
answers to OQ-1…OQ-8. It holds five kinds of entry, and each is labelled:

1. **Gateway decisions (D-A1…D-A8).** Decisions the user made on 2026-10-01
   for this track. They use a **gateway-local namespace `D-A#`**, as this
   bundle already does for `FR-A#`, `NFR-A#` and `XP-A#` (PD-1). The USI
   bundle owns `D-1…D-15` and may add `D-16+`, so `D-A#` cannot collide with
   it. Each entry gives the date, the user's wording and the OQ it answers.
2. **Reused user decisions.** Decisions the user made on 2026-09-30 for the
   user-service track, recorded in the USI bundle
   (`VilnaCRM-Org/user-service-infrastructure`,
   `specs/workload-wa-hardening/decisions.md`, sha256
   `86df7c4f7b72ad49cbca328ec79884c792c1b3f833567f4a34586eb60d5259c6`, at USI
   commit `9d5df4a`). This plan reuses them where they govern the gateway. It
   does not restate them as new decisions.
3. **Open questions (OQ-n).** Choices only the user can make. None is decided
   here. Each lists its options and the stories that stop until it is
   answered.
4. **Cross-plan change requests (CR-A#).** Changes that a gateway decision
   needs in the USI plan. This plan does not edit the USI bundle; the USI
   owner decides each request.
5. **Planning defaults (PD-n).** Values the plan chose because a story needs
   one. They are not user decisions. The user, the BI owner or `@Kravalg` may
   change any of them in review.

No decision in this file authorizes a live action. Every live action stays
behind the per-action authorization of `prd.md` §2.

## 1. Gateway decisions (dated 2026-10-01, this bundle)

The user gave these answers in chat on 2026-10-01. Only D-A1 was quoted
verbatim; the others are recorded in the words the answer was relayed in.

| ID | Answers | User's wording | Decision | Consequence in this plan |
| --- | --- | --- | --- | --- |
| D-A1 | OQ-1 | "We should create basic roles and permissions in Bootstrap infrastructure for api gateway like we did for user service infrastructure." | **Enrol `api-gateway-infrastructure` in bootstrap-infrastructure the way `user-service-infrastructure` is enrolled: its roles enter the BI independent seed through a reviewed seed catalog amendment (the seed registration route), installed by the human seed operator.** They do not go through the governance-stack route, which the `G-GitHubGovernanceApply` guard statements `dc27f076…` and `8c068aaa…` block (research GR-12). The independent-CloudFormation-owner route (revision 1's recommendation) is **not** the chosen route. | AD-A1 (rewritten); FR-A01, FR-A02; G1.1, G1.2; XP-A1, XP-A4; V-A10. How the route mirrors USI is in AD-A1 and research GR-18…GR-20. AD-A1 lists every point where the gateway departs from the USI pattern. Role creation moves to the seed (decided here). The writer of grants and non-role resources (OQ-9) and the ConfigRead roles (OQ-10) cannot follow the pattern as it stands and are open. The trust subject list is stricter (PD-14). |
| D-A2 | OQ-8 | "gateway after rebuild, recommendation (c)" | **OQ-8 (c).** The TEST front door is applied only after USI S4.6 step 20, against the rebuilt workload, and built once. No gateway teardown, TEST recovery role or rebuild exists. | Rows 26-28 of revision 1 (G1.9, G5.7, G5.8) are removed and the later rows renumbered; FR-A25 rewritten; AD-A3, AD-A7, AD-A10, AD-A12, AD-A15; CR-A1 asks the USI owner for the step change. |
| D-A3 | OQ-3 | "the PROD public hostname is user.vilnacrm.com" | **The PROD FQDN is `user.vilnacrm.com`. Its public hosted zone is in PROD account `933245420672`.** | XP-A11 resolved to "the zone exists, or is created, in the PROD account"; who creates it stays an external precondition (XP-A11). FR-A15, G1.7, G4.2, G6.x. |
| D-A4 | OQ-2 | "accept the recommended defaults" | **OQ-2 (a): a dedicated BI-owned gateway CMK per environment** for the stage access log, the WAF log and the alarm topic. | FR-A06, AD-A14 (OQ-2 (b) and (c) dropped). Which BI owner creates the key is OQ-9. |
| D-A5 | OQ-4 | "accept the recommended defaults" | **OQ-4 (a): BI pre-creates the CloudWatch Logs resource policy for `aws-waf-logs-api-gateway-infrastructure-*`. No gateway role ever gets `logs:PutResourcePolicy` on `*`.** | FR-A05, AD-A9, AD-A7 deny set, V-A6. If V-A6 fails, the story STOPs for a new user decision; `logs:PutResourcePolicy` on `*` is excluded. Which BI owner creates the policy is OQ-9. |
| D-A6 | OQ-5 | "accept the recommended defaults" | **OQ-5 (a): retire any legacy gateway stack or `my-bucket` after an emptiness check.** The new governed backend starts empty; a found legacy bucket is deleted by a reviewed admin action, with its own per-action authorization, only after a read-only check shows it empty. | G0.1 outcome; FR-A24. |
| D-A7 | OQ-6 | "accept the recommended defaults" | **OQ-6: derive the PROD stage throttle and WAF rate limits from the TEST evidence of G5.6, recorded in the G6.2 PR, where the user confirms them.** | FR-A18, G6.2. |
| D-A8 | OQ-7 | "accept the recommended defaults" | **OQ-7 (a): the gateway's own live re-verification of the USI coordinates is the authority.** The USI owner supplies the descriptor values with the USI apply run that created them; a reviewed gateway PR pins them; every gateway preview and drift re-reads each coordinate live, including the listener's certificate. | AD-A3, FR-A16, XP-A7, G5.1, G6.1. |

## 2. Reused user decisions (dated 2026-09-30, USI bundle)

| ID | Decision (short form) | How it governs the gateway |
| --- | --- | --- |
| D-3 | WAF placement: **REST API + WAF, private integration through a VPC link to the internal ALB.** V-10 decides between ALB-direct (VPC link V2) and an NLB fallback. | The whole front door (epic E-G5, E-G6). ALB-direct over VPC link V2 is the target shape; the NLB variant is a reviewed, recorded fallback only (AD-A4, V-A1). |
| D-6 | The hard stop is split into two gates: gate 1 admits TEST, gate 2 admits PROD after TEST evidence exists. | The gateway gates A-T and A-P (AD-A12) sit inside the USI gate order: the TEST route is evidence for USI gate 1 (S4.6 step 17), and the PROD route follows USI gate 2. |
| D-15 | The gateway certificate ARN is pinned in the reviewed USI workload contract and checked only with `acm:DescribeCertificate`. No CI role gets `ssm:GetParameter`. No identity deny, seed guard, seed boundary or catalog hash is loosened for SSM. | The gateway publishes nothing in SSM. PR #34's SSM parameter is dropped (AD-A2). The gateway owner hands the ARN to the USI owner (XP-A8). The same pattern, a reviewed contract pin, carries the USI coordinates into this repository (AD-A3, D-A8). |
| D-4 (consequence, not a new decision) | The runtime CMK encrypts the workload's log groups. The USI bundle records that "log groups outside this workload are outside D-4 (for example an AGI stage log group). The AGI owner decides them." | The user decided it for the gateway: D-A4. |
| D-14 | RPO ≤ 1 hour, RTO ≤ 24 hours for the user-service workload. | Scoped to the workload, not the gateway. The gateway holds no data; its RTO target is a planning default (PD-6), not D-14. |

D-1, D-2, D-5, D-7 and D-8…D-13 do not govern a gateway resource. D-2 (PROD
in-container TLS) concerns the ALB→task hop behind the gateway; this plan
neither depends on it nor changes it.

## 3. Open questions for the user (OQ)

OQ-1…OQ-8 are answered (§1). Two new questions follow from D-A1: the parts
of the USI enrolment that the gateway cannot copy as they stand. This plan
lists the options and their costs. It does not choose between them.

| ID | Question | Stories that stop until answered |
| --- | --- | --- |
| OQ-9 | **After the seed creates and registers the gateway roles (D-A1), which BI owner writes the gateway's permissions and its other BI resources?** These are the roles' identity grants (the basic backend access now, the AD-A7 capability grants later), the state backend (bucket, replica, secrets key), the gateway CMK (D-A4), and the account-level API Gateway logging setting and WAF-log resource policy (D-A5). | G1.1 (which documents the enrolment packet carries), G1.3, G1.4a, G1.5, G1.6, G1.4b, G1.7, G1.8 (rows 8, 10, 11, 16, 17, 18, 26, 29) |
| OQ-10 | **Does the gateway get USI's ConfigRead roles and fixed CI secrets?** | G1.1 (role set), G1.2, G3.4 (where the deploy workflow reads its configuration) (rows 8, 9, 13) |

### OQ-9: why USI cannot simply be copied, and the options

**Why.** For USI, the governance Pulumi stack writes all of these: the
roles' identity documents (`pulumi-backend`, then `secret-read-deny` or
`read-only`, then later capability documents; BI
`pulumi/infra/governance.py` lines 414-476), the backend, its key and its
CI secrets. Governance cannot do the same for the gateway, for two
reasons (research GR-12, GR-18, GR-19, K-17):

- **Its seed guard.** `G-GitHubGovernanceApply` denies `iam:*` outside the
  USI ARNs (`8c068aaa…`) and policy writes outside the USI policies
  (`5366ec11…`).
- **Its seed ceilings,** which admit only USI resources.

**(a) Seed-owned.**

- The seed stack also holds the gateway identity policies. They are
  created with the roles, and changed later by seed amendments of in-place
  policy-document updates (the #284 mechanism).
- The backend, the CMK and the account-level resources become new resource
  types in the seed stack.
- No existing guard statement or ceiling changes.
- Cost: every grant change is a seed operation in the queue shared with
  USI (XP-A4), and the seed stack, which today owns only IAM, gains S3,
  KMS, `AWS::ApiGateway::Account` and `AWS::Logs::ResourcePolicy`
  resources (XP-A1 widened).

**(b) Governance-owned, as for USI.** The G1.2 enrolment change set also
amends the governance roles' seed policies, in the same seed operation per
account:

- **The guard.** The exact gateway role and policy ARNs are added to the
  two closed lists of `G-GitHubGovernanceApply`. Their statement ids
  follow the baseline catalog: TEST `8c068aaa…` and `5366ec11…` at
  origin/main `ef419680…`; `21195ff8…` and `bb116727…` at #284's
  `ff2eaf29…`; PROD `9fb811f6…` and `06267ab9…`. #284 FR6 added one exact
  USI policy ARN to the same two lists.
- **The seed ceilings of the governance roles,** which today admit only
  USI resources:
  - `ceiling/GitHubGovernanceApply`:
    - limits S3 bucket create and delete to the USI buckets (`7a36d2ff…`);
    - allows `kms:CreateKey` only with `aws:RequestTag/Repository` set to
      `user-service-infrastructure` (`a392c269…`);
    - allows role-policy attach and put only on the USI roles with the
      USI boundary (`00257170…`, `d35c02e1…`);
    - allows `iam:PassRole` only of the USI replication role
      (`abfe3f39…`);
    - has no `apigateway` or `logs:PutResourcePolicy` action.
  - `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift` scope their
    IAM, S3, KMS and secret reads to USI (for example `6b2d4e23…`,
    `0d44e2be…`, `011f1685…`).

  Each ceiling needs exact gateway entries. G1.5 also needs
  `apigateway:PATCH` on `/account`, `iam:PassRole` of the logging role to
  `apigateway.amazonaws.com`, and `logs:PutResourcePolicy` scoped to the
  gateway WAF-log policy. #285 likewise records that both "boundary and
  guard" must be amended (`installability-stop.md` lines 55-59).
- **The operator side.** The governance roles' own identity policies for
  the gateway (for example `GitHubGovernanceApply-{env}-api-gateway-infrastructure-storage`
  and `-iam`, which the BI operator stack writes, as it writes the USI
  ones) must be added to the catalog's `operator_bindings` (`policy_write`,
  `policy_read`). The operator executors' guards must also admit them:
  the five `GitHubOperator*` guards that close the governance policy names to the USI ones (TEST `0c5eed92…` in `GitHubOperatorApply-iam-write`, `c18540fb…` in `GitHubOperatorApply-attachments`, `408cdbf9…` in the three `GitHubOperator*-iam-read` guards; PROD `de33acbe…`, `0142330f…`, `7a337042…`). Without that amendment the operator PR could not create,
  attach or read those policies. Both are changes in the same G1.2
  operation, followed by a reviewed operator PR before G1.3.
- **The governance mode.** `dc27f076…` stays unchanged, so governance
  still cannot create, delete or re-bound a role. A BI code change adds an
  external-identity mode, in which governance reads the seed-created roles
  and creates none. The gateway is added to
  `pulumi/repositories.governance.json`. Governance then creates the
  backend, the CMK and the grants through reviewed governance PRs (the USI
  "PR C" flow).
- Cost: the two `NotResource` deny lists gain exact ARNs, which narrows
  those denies, so it needs this decision. The three governance ceilings
  also widen, by exact gateway resources.

**(c) Mixed.**

- The seed owns the roles and their identity grants, as in (a).
- Reviewed independent BI CloudFormation stacks own only the non-IAM
  resources: backend, CMK, account setting and resource policy.
- This keeps S3, KMS and API Gateway resources out of the seed stack and
  changes no guard or ceiling.
- Cost: it brings back an independent owner, for non-role resources only.

### OQ-10: why USI cannot simply be copied, and the options

**Why.** USI has `GitHubCiConfigRead-user-service-infrastructure-{test,test-pr}`
in TEST and `-{prod,prod-preview}` in PROD (seed catalogs). Each reads a
fixed CI secret `/user-service-infrastructure/ci/<suffix>` that governance
creates (BI `pulumi/infra/ci_config.py` line 540). Two parts conflict with
this plan:

1. **The trust.** The `test-pr` reader trusts `repo:<slug>:pull_request`
   for every repository except BI (BI `ci_config.py` lines 213-216;
   `docs/ci-config-trust-contract.md` lines 11-14 say it "intentionally
   retains pull-request subjects"). The `test` and `prod-preview` readers
   also trust `ref:refs/heads/main` (lines 217-229). AD-A1 allows exactly
   one environment subject per role, with no `pull_request` or `ref`
   subject.
2. **The secrets.** On the seed route nothing creates the CI secrets:
   governance creates them for USI, and the seed stack creates no secret.

**(a) No ConfigRead roles** (revision 1's PD-7). Role ARNs, the backend
URL and the key alias are non-secret values, held as protected-environment
variables.

**(b) ConfigRead readers for `test`, `prod-preview` and `prod` only.** Each
trusts exactly its one environment subject; there is no `test-pr` reader.
The OQ-9 owner creates the fixed CI secrets
`/api-gateway-infrastructure/ci/<suffix>`. Across the two accounts this
adds three principals, their guards and three secrets.

**(c) Full USI mirror, including `test-pr` with its `pull_request`
subject.** This contradicts AD-A1's no-`pull_request` rule; the user would
accept PR-triggered config reads.

## 4. Cross-plan change requests to the USI plan (CR-A#)

| ID | From | Requested USI change | Why | Gateway rows affected |
| --- | --- | --- | --- | --- |
| CR-A1 | D-A2 (OQ-8 (c)) | **USI S4.6: run step 17 after step 20, against the rebuilt workload, and hold step 17 for two weekday drift runs of the gateway TEST front door.** Concretely: (1) move step 17 ("AGI TEST route through VPC link V2 → ALB and WAF sampled requests") after step 20; (2) step 17 starts only when gateway gate A-T steps 1-10 have passed. Step 10 is two consecutive clean weekday scheduled drift runs with successful probes, inside the USI TEST daytime window. Its evidence bundle is handed over at gate A-T step 12. Gate A-T step 11 (seven days of WAF logs, then the CommonRuleSet switch to block) is **not** part of the step-17 bundle and never holds step 17. | USI S4.6 step 18 requires "no foreign ENI" in the application subnets; step 19 deletes them, and step 20 rebuilds them with new ids (USI `epics-stories.md` lines 2866-2900; `prd.md` lines 393-402). A VPC link built before step 18 would sit in those subnets and pin their ids. | Rows 19-25 run after USI step 20 and before USI step 17. |

The USI owner decides CR-A1 in the USI bundle. Until it is accepted, row 19
(the TEST descriptor) does not start; XP-A14 carries the timing.

## 5. Planning defaults (not user decisions)

| ID | Default | Why | Who may change it |
| --- | --- | --- | --- |
| PD-1 | External-precondition numbering uses a **gateway-local namespace `XP-A1…XP-A14`**, not `XP-19+`; user decisions of this track use **`D-A#`**, and change requests to USI use **`CR-A#`**. | The USI bundle owns `XP-1…XP-18` and `D-1…D-15`, and the USI plan may add more. A separate namespace avoids collisions. USI items keep their names when cited (USI XP-10, XP-15, XP-17; USI D-3). | User |
| PD-2 | The toolchain moves from Poetry to **uv with a frozen lockfile**, Python 3.11, `pulumi-aws` pinned to **7.23.0**. | BI `AGENTS.md` lines 91-103 say to model a new service scaffold on `pulumi/user-service-infrastructure/`. USI runs `uv run --frozen` (USI `Makefile` line 96). 7.23.0 is the SDK whose `integration_target` and `DomainName.endpoint_access_mode` this plan verified (GA-1, GA-6). | BI owner, user |
| PD-3 | TEST stage throttle: **rate 50 requests/s, burst 100**, on every method (`*/*`). | Bounded below the account-level quota (GA-12) and sized for a TEST service with no load data. | User (D-A7 sets PROD) |
| PD-4 | TEST WAF rate rules: **2,000 requests per 5 minutes per source IP (block)** for all paths, plus **100 per 5 minutes per source IP** on the token path that G5.4 names from the user-service routes. | The WAF minimum is 10 (GA-10); these values stop crude floods without touching normal TEST use. | User (D-A7 sets PROD) |
| PD-5 | Log retention: **TEST 90 days, PROD 365 days** for the access and WAF log groups. | Enough for incident review; the cost pillar caps it. | User |
| PD-6 | Gateway recovery target: **rebuild from IaC within 24 hours**, the same bound as D-14's RTO. | The gateway holds no data; a rebuild through the saved-plan path restores it. D-14 itself names only the workload. | User |
| PD-7 | **Superseded by OQ-10.** Revision 1 defaulted to no ConfigRead roles. D-A1 asks for USI-like roles, so the choice is now the user's (OQ-10 option (a) keeps it). | — | User |
| PD-8 | WAF managed rule groups use the **default (auto-updating) version**, with `AWSManagedRulesCommonRuleSet` first in **Count** in TEST and switched to **Block** by G5.6 evidence. | The documented rollout for managed rules (GA-11). | User |
| PD-9 | PR #34 is **adopted and amended**, not superseded (AD-A2). | Its certificate logic is fail-closed and tested; only the SSM parameter, the legacy bucket and the in-code pins conflict with this plan. | PR author, user |
| PD-10 | Dependabot PRs #26, #32 and #33 are **closed, not rebased** (AD-A13). | Each is superseded by a story of this plan. | Repository maintainer |
| PD-11 | `autorelease.yml` uses only the job's short-lived `GITHUB_TOKEN`, creates the tag and the GitHub release, and **stops committing `CHANGELOG.md` to `main`**; no workflow of this repository uses the `VILNACRM_APP_*` App private key any more. | The `main` ruleset has no bypass actor, so a bot commit to `main` would fail; the App private key is a long-lived secret this repository does not need. The org owner rotates or retires the key for other repositories. | User, org owner |
| PD-12 | The state bucket is **replicated as BI replicates the USI backend**, so the seed enrolment also creates `PulumiStateRepl-api-gateway-infrastructure-{env}` with its replication boundary, as USI has `PulumiStateRepl-user-service-infrastructure-{env}`. | Same durability as the USI backend (BI `pulumi/infra/pulumi_state.py` lines 21, 84-150). | BI owner (may drop replication; then no replication role, boundary or guard) |
| PD-13 | The TEST drift job and its probe run **on weekdays inside the USI TEST daytime window**; the TEST 5XX alarm needs a minimum request count. | USI TEST scales to zero on nights and weekends (USI FR-14 (c)), when the ALB answers 503. | User |
| PD-14 | **Each gateway CI role trusts exactly one environment subject** (`{env}-preview`, `{env}` or `{env}-drift`), with no `ref:refs/heads/main` subject. This is stricter than USI, whose Preview and Drift roles also trust the `main` ref (BI `pulumi/infra/ci_bootstrap.py` lines 353-380). | Every gateway job that assumes a role runs in a protected environment (AD-A11), so the `ref` subject adds no needed path. Only the subject list differs from USI; the role names, boundary, guards and registration follow the USI pattern. | User, BI owner |
