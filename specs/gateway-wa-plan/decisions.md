# User decisions and open questions — API gateway Well-Architected track

This file is a planning input. Revision 2 (2026-10-01) records the user's
answers to OQ-1…OQ-8; revision 3 (2026-10-01) records the answers to OQ-9
and OQ-10; revision 4 (2026-10-01) records the answer to OQ-11; revision 5
(2026-10-01) adds CR-A2 and the readiness round-1 corrections; revision 6
(2026-10-01) records D-A12, D-A13 and D-A14 from readiness round 2; revision 7
(2026-10-01) applies readiness round 3 (no new decision). It holds five kinds of entry, and each is labelled:

1. **Gateway decisions (D-A1…D-A14).** Decisions the user made on 2026-10-01
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
3. **Open questions (OQ-n).** Choices only the user can make. OQ-1…OQ-10
   are answered, and OQ-11 is answered by D-A11. §3 keeps the OQ-9, OQ-10 and OQ-11 analysis and
   their rejected alternatives.
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
| D-A1 | OQ-1 | "We should create basic roles and permissions in Bootstrap infrastructure for api gateway like we did for user service infrastructure." | **Enrol `api-gateway-infrastructure` in bootstrap-infrastructure the way `user-service-infrastructure` is enrolled: its roles enter the BI independent seed through a reviewed seed catalog amendment (the seed registration route), installed by the human seed operator.** They do not go through the governance-stack route, which the `G-GitHubGovernanceApply` guard statements `dc27f076…` and `8c068aaa…` block (research GR-12). The independent-CloudFormation-owner route (revision 1's recommendation) is **not** the chosen route. | AD-A1 (rewritten); FR-A01, FR-A02; G1.1, G1.2; XP-A1, XP-A4; V-A10. How the route mirrors USI is in AD-A1 and research GR-18…GR-20. AD-A1 lists every point where the gateway departs from the USI pattern. Role creation moves to the seed (decided here). The writer of grants and non-role resources (OQ-9) and the ConfigRead roles (OQ-10) could not follow the pattern as it stood; the user decided them as D-A9 and D-A10. The trust subject list is stricter (PD-14). |
| D-A2 | OQ-8 | "gateway after rebuild, recommendation (c)" | **OQ-8 (c).** The TEST front door is applied only after USI S4.6 step 20, against the rebuilt workload, and built once. No gateway teardown, TEST recovery role or rebuild exists. | Rows 26-28 of revision 1 (G1.9, G5.7, G5.8) are removed and the later rows renumbered; FR-A25 rewritten; AD-A3, AD-A7, AD-A10, AD-A12, AD-A15; CR-A1 asks the USI owner for the step change. |
| D-A3 | OQ-3 | "the PROD public hostname is user.vilnacrm.com" | **The PROD FQDN is `user.vilnacrm.com`. Its public hosted zone is in PROD account `933245420672`.** | XP-A11 resolved to "the zone exists, or is created, in the PROD account"; who creates it stays an external precondition (XP-A11). FR-A15, G1.7, G4.2, G6.x. |
| D-A4 | OQ-2 | "accept the recommended defaults" | **OQ-2 (a): a dedicated BI-owned gateway CMK per environment** for the stage access log, the WAF log and the alarm topic. | FR-A06, AD-A14 (OQ-2 (b) and (c) dropped). Governance creates the key (D-A9). |
| D-A5 | OQ-4 | "accept the recommended defaults" | **OQ-4 (a): BI pre-creates the CloudWatch Logs resource policy for `aws-waf-logs-api-gateway-infrastructure-*`. No gateway role ever gets `logs:PutResourcePolicy` on `*`.** | FR-A05, AD-A9, AD-A7 deny set, V-A6. If V-A6 fails, the story STOPs for a new user decision; `logs:PutResourcePolicy` on `*` is excluded. **Re-scoped by D-A12, per branch:** under branch A the human seed operator writes an account-scoped policy for this name pattern once; under branch B governance writes a resource-scoped policy on the exact log group in G1.5b (rows 21a and 31b). "BI pre-creates" holds for branch A only. |
| D-A6 | OQ-5 | "accept the recommended defaults" | **OQ-5 (a): retire any legacy gateway stack or `my-bucket` after an emptiness check.** The new governed backend starts empty; a found legacy bucket is deleted by a reviewed admin action, with its own per-action authorization, only after a read-only check shows it empty. | G0.1 outcome; FR-A24. |
| D-A7 | OQ-6 | "accept the recommended defaults" | **OQ-6: derive the PROD stage throttle and WAF rate limits from the TEST evidence of G5.6, recorded in the G6.2 PR, where the user confirms them.** | FR-A18, G6.2. |
| D-A8 | OQ-7 | "accept the recommended defaults" | **OQ-7 (a): the gateway's own live re-verification of the USI coordinates is the authority.** The USI owner supplies the descriptor values with the USI apply run that created them; a reviewed gateway PR pins them; every gateway preview and drift re-reads each coordinate live, including the listener's certificate. | AD-A3, FR-A16, XP-A7, G5.1, G6.1. |
| D-A9 | OQ-9 | option (b), "Governance, like USI" | **Governance owns the gateway's identity grants, backend, CMK and account-level settings, as it does for USI.** The G1.2 seed change set admits governance to the gateway by exact ARNs only (the #284 FR6 precedent; the four non-exact forms the user accepted are recorded separately as D-A14), under the BI owner's review and `@Kravalg`'s approval: (1) [superseded by D-A11] the exact gateway role and policy ARNs added to the two `NotResource` lists of `G-GitHubGovernanceApply` (TEST `8c068aaa…`/`5366ec11…` at `ef419680…`, `21195ff8…`/`bb116727…` at `ff2eaf29…`; PROD `9fb811f6…`/`06267ab9…`); (2) exact gateway entries in `C-GitHubGovernancePreview` and `C-GitHubGovernanceDrift` (the `ceiling/GitHubGovernanceApply` part is superseded by D-A11); (3) the governance roles' gateway identity policies added to the catalog's `operator_bindings`; (4) the five operator executor guards that name those policies amended (TEST `0c5eed92…`, `c18540fb…`, `408cdbf9…`; PROD `de33acbe…`, `0142330f…`, `7a337042…`). Governance gains an external-identity mode that reads the seed-created roles and creates none; `dc27f076…` is unchanged. | AD-A1 ("Governance admission"), AD-A7, AD-A9, AD-A14; FR-A02…FR-A06; G1.1, G1.2, G1.3…G1.8; **Re-scoped by D-A11:** amendments (1) and the `ceiling/GitHubGovernanceApply` part of (2) are dropped, because the gateway's governance apply runs under a dedicated role and USI's Apply ceiling and guard stay untouched. What remains: the exact gateway reads in `C-GitHubGovernancePreview`/`-Drift`, (3) and (4). Those are the recorded exception to the "no deny narrowed without a user decision" constraint (brief; readiness). Options (a) and (c) are rejected (§3). |
| D-A11 | OQ-11 | option (a), "Dedicated gov role" | **The seed creates a dedicated governance Apply role for the gateway, `GitHubGovernanceApply-api-gateway-infrastructure-{env}`, with its own exact-ARN ceiling, guard and identity.** USI's `ceiling/GitHubGovernanceApply` and `G-GitHubGovernanceApply` stay untouched, and every gateway admission stays exact-ARN only, except the forms of D-A14. Its trust mirrors the governance Apply trust (BI repository, "Pulumi PR Command Runner", `pulumi-governance-account.yml` on `main`), but uses the environment `{env}-governance-api-gateway-infrastructure`. The governance workflow runs the gateway as its own target: its own stack `{env}-api-gateway-infrastructure` of the `governance` project in the same `governance/` backend prefix, and apply in the new environment under the dedicated role. | AD-A1 ("Governance admission"), V-A12 resolved: the ceiling and identity measure 5830 characters (D-A12 branch A) or 6065 (branch B), and the guard 5565 (revision 7); the shared Preview/Drift ceilings measure 5387/5397 (TEST/PROD, branch A) or 5419/5429 (branch B) after an in-place merge plus a separate gateway KMS-read statement (5487 or 5519 at `ff2eaf29…`), rendered by `evidence/render_governance_sizes.py`. Counts: 30 principals, 9 seed-created, 67 policies. The coordinator's estimate of 66 assumed no seed-owned identity; the derivation is in AD-A1. G1.1, G1.2, G1.3 (the new BI environment and target selection), G1.4a…G1.8. Options (b) and (c) are rejected (§3). |
| D-A12 | readiness round 2, N1 | as relayed: D-A5 covers every gateway role, including the dedicated governance Apply role | **No CI or governance role ever gets `logs:PutResourcePolicy` on `*`, including `GitHubGovernanceApply-api-gateway-infrastructure-{env}`.** V-A8 runs in G1.1 (row 8), before any form is chosen. **(A)** If no log-group-scoped form of `logs:PutResourcePolicy` exists, the reviewed non-root human seed operator writes the WAF-log resource policy once, as the service-linked roles are handled. That write has its own XP-A4 slot, the BI owner as owner, and evidence: the written document, a `DescribeResourcePolicies` readback and `@Kravalg`'s approval. **(B)** If a scoped form exists, the dedicated role holds it, scoped to exactly the gateway WAF log group. | **Recorded consequence (revision 7, not a new decision):** a scoped form that WAF log delivery does not accept (V-A6) is treated as no usable scoped form, so branch A applies; G5.4's contingency rows (23-F3, then 23-F1, then 23-F2) cover a late discovery; no governance role ever holds `logs:DeleteResourcePolicy`. Under branch B the policy is resource-scoped and written in G1.5b (rows 21a, 31b). AD-A1 (dedicated ceiling and identity), AD-A9, FR-A05, G1.1 Needs, G1.5, XP-A1, V-A8; the dedicated ceiling measures 5830 (A) / 6065 (B). |
| D-A13 | readiness round 2, N5 | as relayed: the gateway state backend matches the BI/USI `PulumiStateBuckets` pattern | **The gateway state backend uses the BI/USI `PulumiStateBuckets` pattern unchanged:** AES256 with SSE-C blocked, a TLS-only bucket policy, the existing key-policy pattern, and access limited by the IAM roles and their boundaries. No shared BI code changes. | FR-A03 (and its P/N/E), G1.3 (P/N/E), PD-12 (replication as BI replicates USI). |
| D-A14 | readiness round 2, L3 (acknowledgement) | the user explicitly accepted the four forms | **Four non-exact forms are accepted for the gateway's BI admissions:** (1) Resource `*` for actions without resource-level support, (2) KMS `key/*` with exact tag conditions, (3) governance state paths bounded by the exact stack name (rendered as the exact stack paths), (4) IAM statements also confined by the guard. Anything else is a G1.1 STOP. | AD-A1 "Allowed non-exact forms", NFR-A02, G1.1 STOP and N; D-A9 and D-A11 reference this record. |
| D-A10 | OQ-10 | option (a), "None" | **No ConfigRead roles for the gateway.** Role ARNs, backend URL and key alias are non-secret protected-environment variables. | c = 0 (with D-A11: 30 principals, 9 seed-created, 67 policies); the Apply guard's secret-read statement has Resource `*` with no CI-secret exception (AD-A1); G3.4. Adding a reader later needs a reviewed seed catalog amendment and a new user decision. Options (b) and (c) are rejected (§3). |

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

**No question is open.** OQ-11, which the revision-3 audit raised while
checking D-A9, is answered by D-A11. OQ-1…OQ-8 are answered by D-A1…D-A8, and OQ-9
and OQ-10, which followed from D-A1, are answered by D-A9 and D-A10 (§1). The
analysis behind OQ-9 and OQ-10 is kept below, with the alternatives the
user rejected, so that a later reviewer can see why the gateway departs
from the USI pattern where it does.

### OQ-9 (answered by D-A9): why USI could not simply be copied

For USI, the governance Pulumi stack writes the roles' identity documents
(`pulumi-backend`, then `secret-read-deny` or `read-only`, then later
capability documents; BI `pulumi/infra/governance.py` lines 414-476), the
backend, its key and its CI secrets. For the gateway, governance is
blocked by its seed guard (`8c068aaa…`, `5366ec11…`), by its USI-scoped
seed ceilings, and by the operator executor guards that close the
governance policy names to the USI ones (research GR-12, GR-18, GR-19,
K-17). D-A9 removes those blocks by an exact-ARN admission in the G1.2
change set (architecture AD-A1, "Governance admission").

**Rejected alternatives (not live):**

- **(a) Seed-owned.** The seed stack would hold the gateway identity
  policies, the backend, the CMK and the account-level resources. No
  guard or ceiling change, but every grant change becomes a seed
  operation, and the seed stack, which today owns only IAM, would gain S3,
  KMS and API Gateway resources.
- **(c) Mixed.** The seed would own the grants, and independent BI
  CloudFormation stacks the non-IAM resources. This brings back an
  independent owner for non-role resources.

### OQ-10 (answered by D-A10): why USI could not simply be copied

USI has `GitHubCiConfigRead-user-service-infrastructure-{test,test-pr}` in
TEST and `-{prod,prod-preview}` in PROD, each reading a fixed CI secret
that governance creates (BI `pulumi/infra/ci_config.py` line 540). The
`test-pr` reader trusts `repo:<slug>:pull_request`, and the `test` and
`prod-preview` readers also trust `ref:refs/heads/main` (lines 202-230;
`docs/ci-config-trust-contract.md` lines 11-14). AD-A1 allows exactly one
environment subject per role.

**Rejected alternatives (not live):**

- **(b)** ConfigRead readers for `test`, `prod-preview` and `prod` only,
  each with one environment subject, plus their CI secrets.
- **(c)** A full USI mirror, including `test-pr` with its `pull_request`
  subject.

Adding a reader later needs a reviewed seed catalog amendment (a new
principal, its guard and the count change), a CI-secret owner, and a new
user decision.

### OQ-11 (answered by D-A11): the governance Apply ceiling had no room

**Question.** D-A9 admits governance to the gateway by exact ARNs only.
How should the admission into `ceiling/GitHubGovernanceApply` have
been restructured, given that it could not fit?

**Why it cannot fit.**

- A managed policy is limited to 6144 characters. The ceiling is the
  governance Apply role's permissions boundary, and a role has exactly one
  boundary, so the ceiling cannot be split into two policies.
- The ceiling is already 5752 characters (TEST) and 5762 (PROD) in
  canonical JSON, which leaves about 390.
- The exact-ARN gateway additions take more than that:
  - S3 buckets, CreateKey, KMS key management and aliases, role-policy
    attach and put, `iam:PassRole` of the replication and logging roles,
    `/account`, and the WAF-log resource policy.
  - The audit rendered 7187-7924 characters, and about 8729 with the KMS
    management entries (architecture AD-A1, "Size blocker"; V-A12).
- The Preview and Drift ceilings (3789 / 3799) have room.

**Options.** The user chose (a); (b) and (c) are rejected alternatives,
no longer live.

- **(a) A dedicated governance Apply role for the gateway (chosen, D-A11).**
  - The seed creates `GitHubGovernanceApply-api-gateway-infrastructure-{env}`
    (name illustrative) with its own exact-ARN ceiling and a guard of the
    `G-GitHubGovernanceApply` shape, and governance applies the gateway
    entry under that role.
  - USI's ceiling stays untouched, and exact ARNs are kept.
  - Cost: governance needs a per-repository apply role. That is a BI code
    change to governance's role selection, plus one more principal, its
    ceiling and its guard per environment (the derivation in AD-A1 also
    counts its seed-owned identity: 30 principals, 9 seed-created, 67
    policies).
- **(b) Restructure the shared ceiling into a service-family form (rejected).**
  - For example, resource patterns such as
    `arn:aws:s3:::pulumi-*-infrastructure-*`, and conditions on
    `aws:ResourceTag/Repository` listing both repositories.
  - Cost: this departs from "exact ARNs only" in D-A9, and it rewrites
    USI's existing ceiling, so it needs the user's decision and a USI
    impact review.
- **(c) Keep the non-IAM resources out of governance (rejected).**
  - Revert the backend, the CMK and the account-level resources to D-A9's
    rejected alternatives (a) or (c), and keep only the grants with
    governance (the role-policy entries).
  - Cost: this partly reverses D-A9.

D-A11 unblocks G1.1 (row 8) and every row that depends on it.

## 4. Cross-plan change requests to the USI plan (CR-A#)

| ID | From | Requested USI change | Why | Gateway rows affected |
| --- | --- | --- | --- | --- |
| CR-A1 | D-A2 (OQ-8 (c)) | **USI S4.6: run step 17 after step 20, against the rebuilt workload, and hold step 17 for two weekday drift runs of the gateway TEST front door.** Concretely: (1) move step 17 ("AGI TEST route through VPC link V2 → ALB and WAF sampled requests") after step 20; (2) step 17 starts only when gateway gate A-T steps 1-10 have passed. Step 10 is two consecutive clean weekday scheduled drift runs with successful probes, inside the USI TEST daytime window. Its evidence bundle is handed over at gate A-T step 12. Gate A-T step 11 (seven days of WAF logs, then the CommonRuleSet switch to block) is **not** part of the step-17 bundle and never holds step 17. (3) Because step 17 now runs after step 20, USI S4.6 step 21 (the campaign receipt, which includes step 17's evidence; USI `epics-stories.md` lines 2903-2906) and gate-1 completion also wait for it. USI row 42's XP-11 still needs the gateway TEST certificate earlier (row 15). | USI S4.6 step 18 requires "no foreign ENI" in the application subnets; step 19 deletes them, and step 20 rebuilds them with new ids (USI `epics-stories.md` lines 2866-2900; `prd.md` lines 393-402). A VPC link built before step 18 would sit in those subnets and pin their ids. | Rows 19-25 run after USI step 20 and before USI step 17. |
| CR-A2 | D-A1, D-A11 (readiness F1) | **USI C-BI seed queue: insert the gateway's seed operations.** Gateway G1.2 TEST and G1.2 PROD each run as one seed operation (install, admission, activation and pin) in the queue that architecture §4 C-BI fixes (USI `architecture.md` line 2770). The slot is **after USI row 34 (S5.7) and before USI row 42 (S5.18a, then XP-11)**: gateway row 15 needs row 9, and XP-11 needs the gateway TEST certificate. #284 must be merged and installed first. **Every later USI seed module (row 42 S5.18a and XP-11, row 43 S5.5/S5.18b, row 45 S4.8, row 47 S5.19, row 48 XP-14, row 50 S5.24a/b) rebases its pinned baseline catalog hash onto the gateway result catalog**, because each takes its predecessor's result catalog as its baseline. The gateway's own later exact-ARN admissions, if any, take further slots by the same rule. Under D-A12 branch A, the seed operator's one-time WAF-log resource-policy write also takes a slot in this queue, after G1.2's and before gateway row 16. It changes no catalog, so nothing rebases. **Shared-ceiling budget (V-A13):** the gateway adds 1598 (D-A12 branch A) or 1630 (branch B) characters to each shared governance Preview/Drift ceiling. On TEST after #284 that leaves 657 (D-A12 branch A) or 625 (branch B) of 6144 for USI's TEST additions to the same statements (S5.2 TEST, XP-11); on PROD it leaves 747 (A) or 715 (B) for USI's PROD additions (S5.2 PROD, S5.24a/b, which are PROD-only). Each rebased USI module re-renders both ceilings, and exceeding 6144 is a STOP for both owners. | The seed queue is closed and one-open across both plans; inserting an operation changes every later baseline. | Row 9 (G1.2); rows 10-11 and 15 wait for it. |

The USI owner decides CR-A1 and CR-A2 in the USI bundle. Until CR-A1 is
accepted, row 19 (the TEST descriptor) does not start; XP-A14 carries the
timing. Until CR-A2 is accepted, row 9 (G1.2) does not start.

## 5. Planning defaults (not user decisions)

| ID | Default | Why | Who may change it |
| --- | --- | --- | --- |
| PD-1 | External-precondition numbering uses a **gateway-local namespace `XP-A1…XP-A14`**, not `XP-19+`; user decisions of this track use **`D-A#`**, and change requests to USI use **`CR-A#`**. | The USI bundle owns `XP-1…XP-18` and `D-1…D-15`, and the USI plan may add more. A separate namespace avoids collisions. USI items keep their names when cited (USI XP-10, XP-15, XP-17; USI D-3). | User |
| PD-2 | The toolchain moves from Poetry to **uv with a frozen lockfile**, Python 3.11, `pulumi-aws` pinned to **7.23.0**. | BI `AGENTS.md` lines 91-103 say to model a new service scaffold on `pulumi/user-service-infrastructure/`. USI runs `uv run --frozen` (USI `Makefile` line 96). 7.23.0 is the SDK whose `integration_target` and `DomainName.endpoint_access_mode` this plan verified (GA-1, GA-6). | BI owner, user |
| PD-3 | TEST stage throttle: **rate 50 requests/s, burst 100**, on every method (`*/*`). | Bounded below the account-level quota (GA-12) and sized for a TEST service with no load data. | User (D-A7 sets PROD) |
| PD-4 | TEST WAF rate rules: **2,000 requests per 5 minutes per source IP (block)** for all paths, plus **100 per 5 minutes per source IP** on the token path that G5.4 names from the user-service routes. | The WAF minimum is 10 (GA-10); these values stop crude floods without touching normal TEST use. | User (D-A7 sets PROD) |
| PD-5 | Log retention: **TEST 90 days, PROD 365 days** for the access and WAF log groups. | Enough for incident review; the cost pillar caps it. | User |
| PD-6 | Gateway recovery target: **rebuild from IaC within 24 hours**, the same bound as D-14's RTO. | The gateway holds no data; a rebuild through the saved-plan path restores it. D-14 itself names only the workload. | User |
| PD-7 | **Superseded by D-A10** (no ConfigRead roles), which confirms revision 1's default as a user decision. | — | User |
| PD-8 | WAF managed rule groups use the **default (auto-updating) version**, with `AWSManagedRulesCommonRuleSet` first in **Count** in TEST and switched to **Block** by G5.6 evidence. | The documented rollout for managed rules (GA-11). | User |
| PD-9 | PR #34 is **adopted and amended**, not superseded (AD-A2). | Its certificate logic is fail-closed and tested; only the SSM parameter, the legacy bucket and the in-code pins conflict with this plan. | PR author, user |
| PD-10 | Dependabot PRs #26, #32 and #33 are **closed, not rebased** (AD-A13). | Each is superseded by a story of this plan. | Repository maintainer |
| PD-11 | `autorelease.yml` uses only the job's short-lived `GITHUB_TOKEN`, creates the tag and the GitHub release, and **stops committing `CHANGELOG.md` to `main`**; no workflow of this repository uses the `VILNACRM_APP_*` App private key any more. | The `main` ruleset has no bypass actor, so a bot commit to `main` would fail; the App private key is a long-lived secret this repository does not need. The org owner rotates or retires the key for other repositories. | User, org owner |
| PD-12 | The state bucket is **replicated as BI replicates the USI backend**, so the seed enrolment also creates `PulumiStateRepl-api-gateway-infrastructure-{env}` with its replication boundary, as USI has `PulumiStateRepl-user-service-infrastructure-{env}`. | Same durability as the USI backend (BI `pulumi/infra/pulumi_state.py` lines 21, 84-150). | BI owner (may drop replication; then no replication role, boundary or guard) |
| PD-13 | The TEST drift job and its probe run **on weekdays inside the USI TEST daytime window**; the TEST 5XX alarm needs a minimum request count. | USI TEST scales to zero on nights and weekends (USI FR-14 (c)), when the ALB answers 503. | User |
| PD-14 | **Each gateway CI role trusts exactly one environment subject** (`{env}-preview`, `{env}` or `{env}-drift`), with no `ref:refs/heads/main` subject. This is stricter than USI, whose Preview and Drift roles also trust the `main` ref (BI `pulumi/infra/ci_bootstrap.py` lines 353-380). | Every gateway job that assumes a role runs in a protected environment (AD-A11), so the `ref` subject adds no needed path. Only the subject list differs from USI; the role names, boundary, guards and registration follow the USI pattern. | User, BI owner |
