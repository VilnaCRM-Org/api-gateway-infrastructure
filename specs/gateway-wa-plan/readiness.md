---
artifact: implementation-readiness
workflow: _bmad/bmm/workflows/3-solutioning/bmad-check-implementation-readiness (Validate mode)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 8 (independent readiness round 4 at 7e644b7: FAIL, 2 medium, 2 low, 3 nits; all resolved here)
author: the planning agent that wrote revisions 1-8 (NOT an independent reviewer)
independent_reviewer: readiness round 1 (FAIL) on revision 4; round 2 (FAIL, no major) on revision 5; round 3 (FAIL, 1 medium) on revision 6; round 4 (FAIL, 2 medium) on revision 7; round 5 not run yet
status: PENDING independent readiness round 5 on revision 8
---

# Implementation readiness

## Verdict

**Not PASS; pending an independent review.** The author of this file wrote
the bundle, so this is a self-check, not a gate result. A fresh-context
pre-commit audit and its recheck ran on each revision before its commit
(below). The self-check finds the bundle complete enough for an
independent readiness round. These items block implementation:

- **Open user questions:** none. D-A1…D-A11 answer OQ-1…OQ-11; D-A11
  (dedicated governance Apply role) resolves V-A12 and unblocks row 8 and
  every row that depends on it.
- **Row blocked by a verification item:** V-A10 → row 8. The BI owner
  must reverse origin/main's documented rule against extending the seed
  inventory (`test_poc_installation_boundary.py` 63-79,
  `installability-stop.md` 33-39, the hard-coded counts in
  `operator_seed_installation.py`) before any G1.1 code. This is a STOP.
- **Row blocked by an external merge:** #284 merged and installed → row 9
  (and therefore every later BI row).
- **V-A8 in row 8:** it picks D-A12 branch A (the seed operator writes
  the WAF-log resource policy once, in its own slot) or branch B (a scoped
  grant) before any form is chosen. No user decision is pending.
- **Rows blocked by external preconditions:**
  - XP-A1 → row 9, any later exact-ARN admission, the API Gateway
    service-linked role in row 16 if XP-A5 finds it missing, the live
    `pulumi stack init` in row 10, under branch A the WAF-log write
    (row 16), and under the branch-B fallback the 23-F1 install and the
    23-F2 write;
  - XP-A3 → row 12;
  - XP-A4 → every seed slot;
  - XP-A5 → rows 16 and 22;
  - XP-A6 → row 15;
  - XP-A7 → rows 19 and 28;
  - XP-A10 → rows 21, 31a and 31c;
  - XP-A11 → rows 26 and 27;
  - XP-A12 → row 16;
  - XP-A13 → all implementation (the profile and `attempts.json` are absent today);
  - XP-A14 → rows 19 and 25.
- **Cross-plan requests:**
  - CR-A1 must be accepted by the USI owner before row 19 starts and
    before the row-25 hand-off. It also holds USI step 21 and gate-1
    completion.
  - CR-A2 must be accepted before row 9. It inserts the gateway seed
    operations after USI row 34 and before USI row 42, and rebases every
    later USI seed module.
- **Cross-plan ordering** (architecture AD-A12):
  - row 8 after USI row 34's result catalog exists (G1.1 renders against
    it, V-A13);
  - row 9 between USI rows 34 and 42 in the seed queue, after #284
    (CR-A2);
  - row 15 before USI row 42;
  - rows 19-25 after USI S4.6 step 20 and before step 17, which USI runs
    after step 20 and holds for gate A-T step 10 (CR-A1);
  - row 27 before USI row 49, and row 27 waits for G5.6's step-11 PR
    (at least 7 days after row 23), so USI row 49 waits on it too.
    Splitting the PROD seed and governance work (the PROD half of rows 9,
    10, 16 and 17) off the critical path to USI row 42 is possible. The
    BI owner and USI owner may choose it at slot planning. It is recorded
    here, not decided.
  - rows 28-32 (with 31a-31c) after USI row 52.

## Checks performed (self-check, revision 8)

| Check | Result |
| --- | --- |
| Every FR and NFR has at least one story (epics FR coverage map) | yes: 25 FRs, 11 NFRs; FR-A25 now maps to G5.1 and G5.6 |
| PRD §1 counts equal the tables | 25 + 11 = 36; offline 23 FRs + 8 NFRs = 31; live-only FRs 2; evidence-only NFRs 3; offline FRs with live evidence 18 (recomputed from the Risk column; FR-A25's Risk is now C, L) |
| Ordered list has no forward dependency | yes, 36 rows (0-32 with 21a and 31a-31c), checked by `evidence/check_ordered_list.py` for both D-A12 branches, plus model checks of both fallback cases (the per-stack key keeps the PROD policy out of rows 26 and 29; the contingency halves are placed before the row-23 retry and before 31c), including test, ownership and feature-flag levels (epics "No forward dependencies") |
| Rows 26-28 of revision 1 removed, later rows renumbered | yes: G1.9, G5.7, G5.8 removed; rows 29-35 → 26-32; every in-bundle reference to a gateway row re-checked (USI row numbers unchanged) |
| No OQ-8 (a) remnant | yes: no recovery role, `test-recovery` environment, teardown manifest, recovery guardrail mode or `detached` flag remains |
| Every story has P, N and E acceptance cases | yes, except G1.7 and G1.8 (they reuse the G1.4a and G1.4b matrices in PROD), G4.2 (as G4.1, in PROD), G5.6 (the gate A-T steps), G6.1 (the offline checks of G5.1; its live checks first run at row 31a) and G6.3 (gate A-P) |
| Readiness round 1 findings F1-F13 resolved | yes: F1 CR-A2, #284 precondition, no `ef419680` baseline; F2 dedicated ceiling without role-write actions, guard denies, simulator cases; F3 offline `ci` stack; F4 G2.2 environment variables; F5 per-stack target filter and platform-stack apply; F6 allowed non-exact forms, separate KMS read, no `DeleteResourcePolicy`, conditional STOP; F7 origin/main files and V-A10 reframed; F8 gate A-T steps 8a/8b; F9 real replica names, guard and identity rendered; F10-F12 below; F13 XP-A13 |
| D-A1 honoured: the gateway roles enter through a reviewed seed catalog amendment installed by the human seed operator; the governance-stack route is not used for role creation; the independent CloudFormation owner is not the chosen route | yes (AD-A1, FR-A01, FR-A02, G1.1, G1.2). The departures from USI are listed in AD-A1: role creation by the seed (D-A1), the governance admission (D-A9), no ConfigRead (D-A10) and the stricter trust (PD-14) |
| D-A9 honoured (re-scoped by D-A11): governance writes the gateway's grants, backend, CMK and account settings; the G1.2 change set admits it by exact ARNs (plus the four AD-A1 allowed non-exact forms), now limited to the shared Preview/Drift ceilings (in-place merge), the operator bindings and the five operator guards; USI's `G-GitHubGovernanceApply` and Apply ceiling unchanged; external-identity mode; options (a) and (c) only as rejected alternatives | yes (decisions §1 and §3; AD-A1 "Governance admission"; FR-A02…FR-A06; G1.1…G1.8; XP-A1, XP-A4) |
| D-A11 honoured: dedicated `GitHubGovernanceApply-api-gateway-infrastructure-{env}` with its own exact-ARN ceiling, guard and identity; trust mirrors `governance_trust_policy` with the environment `{env}-governance-api-gateway-infrastructure`; per-target governance job and stack; USI's ceiling and guard untouched; options (b) and (c) rejected | yes (decisions §1, §3; AD-A1; FR-A02; G1.1-G1.3) |
| V-A12 (size) | resolved; re-measured in revision 8 with `policy_registry.canonical_json` (`evidence/render_governance_sizes.py`; rendered documents committed under `evidence/`). Dedicated Apply ceiling and identity 5830 under D-A12 branch A, 6095 under branch B (TEST, PROD; revision 8 adds the exact-ARN delete, PD-15); dedicated guard 5565; shared Preview/Drift ceilings branch A 3789/3799 → 5387/5397 (TEST/PROD; 3889 → 5487 at `ff2eaf29…`), branch B → 5419/5429 (5519); USI's Apply ceiling unchanged at 5752/5762. All ≤ 6144; branch B has 49 characters of headroom; G1.1 re-renders with the final names, and an overflow is a STOP and a user decision |
| V-A13 (shared-ceiling budget across both plans) | open check: after #284 + gateway, TEST keeps 657 (branch A) or 625 (branch B) characters for USI's TEST additions (S5.2 TEST before the slot, XP-11 after it); PROD keeps 747 (A) or 715 (B) for USI's PROD additions (S5.2 PROD, S5.24a/b, PROD only); G1.1 renders against the row-34 result catalog; CR-A2 carries the budget; over 6144 → STOP for both owners |
| D-A10 honoured: no ConfigRead roles; c = 0; the Apply guard's secret-read statement has no CI-secret variant; a later reader needs a reviewed amendment | yes (AD-A1; FR-A01; G1.1; G3.4; decisions §3) |
| Counts (re-verified in revision 8; PD-15 adds an action, not a policy; D-A12 branch A's resource policy is not an IAM policy and adds nothing) | per environment 30 principals (24 + 6), 21 existing roles, 9 seed-created principals (3 + 6), **67** policies (55 + 4 boundaries/ceilings + 6 guards + 2 identities: logging role and dedicated governance role). The coordinator's estimate of 66 omitted the dedicated role's seed-owned identity (AD-A1 derivation) |
| No story narrows an existing seed guard statement on Resource `*` | yes. **Recorded exception (D-A9, re-scoped by D-A11):** the shared governance Preview/Drift ceilings and the five operator guards (TEST `0c5eed92…`, `c18540fb…`, `408cdbf9…`; PROD `de33acbe…`, `0142330f…`, `7a337042…`) gain exact gateway entries. Two of those guards (`c18540fb…`, `0142330f…`) are Resource-`*` denies with an `ArnNotEquals` condition and are named in the exception. USI's `G-GitHubGovernanceApply` (`8c068aaa…`, `5366ec11…`, `dc27f076…`) and `ceiling/GitHubGovernanceApply` do not change (brief, Constraints) |
| No CI role gets `ssm:*`, `iam:*`, `iam:PassRole`, `iam:CreateServiceLinkedRole` | yes (AD-A7 deny set; AD-A1 guards; G1.4a and G1.4b matrices) |
| D-15 honoured: no SSM write or read anywhere | yes (AD-A2 drops PR #34's parameter; the policy pack refuses `aws:ssm/*`) |
| D-3 honoured: REST API + WAF + VPC link V2 → ALB; NLB only as reviewed fallback | yes (AD-A4, V-A1) |
| D-A2…D-A8 applied | yes: D-A2 (FR-A25, AD-A3, AD-A12, CR-A1); D-A3 (FR-A15, AD-A8, XP-A11, G1.7, G4.2); D-A4 (FR-A06, AD-A14); D-A5 (FR-A05, AD-A9, V-A6); D-A6 (G0.1, FR-A24); D-A7 (FR-A18, AD-A5, G6.2); D-A8 (AD-A3, XP-A7, G5.1, G6.1) |
| Gate order against USI gates stated, including the USI abandon rehearsal | yes (AD-A12 table; CR-A1) |
| Every AWS claim cites a source | yes (research §5, GA-1…GA-17) |
| Every repository claim cites file and line or a read-only API call | yes (research §2-§4; GR-18…GR-20 added for D-A1) |
| Long-lived secrets | none created; the App private key use is dropped (PD-11); no PAT; no CI secrets (D-A10) |

## User decisions

- **Gateway decisions, dated 2026-10-01:** D-A1…D-A14 (`decisions.md` §1).
  D-A1…D-A11 answer OQ-1…OQ-11. D-A12 (`logs:PutResourcePolicy`) and
  D-A13 (the backend pattern) answer readiness round 2. D-A14 records the
  user's acceptance of the four non-exact forms. The namespace is gateway-local, `D-A#` (PD-1).
- **Reused, dated 2026-09-30:** D-3, D-6, D-15 and the D-4 consequence
  (`decisions.md` §2).
- No other user decision was invented. Every choice the plan needed and
  the user has not made is an OQ or a labelled planning default.

## Remaining user decisions

None. OQ-9, OQ-10 and OQ-11 are answered by D-A9 (option (b),
governance), D-A10 (option (a), none) and D-A11 (option (a), dedicated
governance role); their rejected alternatives are kept in
`decisions.md` §3.

**Cross-plan requests for the USI owner:**
- CR-A1: USI S4.6 step 17 runs after step 20 and is held for gate A-T
  step 10 (two weekday drift runs), which also holds step 21 and gate-1
  completion.
- CR-A2: the gateway seed slot after USI row 34, with the rebase and the
  shared-ceiling budget.

The planning defaults PD-1…PD-16 are not decisions; the user may change any
of them. A conditional decision appears only if V-A7 fails (an
account-wide ACM metadata read, AD-A7) or if V-A6 fails (WAF log delivery
without `logs:PutResourcePolicy`; D-A5 excludes the `*` grant).

## Unresolved external prerequisites

XP-A1…XP-A14 (`prd.md` §7). Human and owner roles:

| Role | Items |
| --- | --- |
| BI owner | G1.x authorship; V-A10 (reversing origin/main's rule against extending the seed inventory); XP-A4 slot ordering with the USI queue (CR-A2); XP-A5 and XP-A12 read-backs; accepting the residual that USI's governance Apply can write `governance/*`, including the gateway governance stack's state; the PROD seed stack's installed-state read before G1.2 PROD |
| Human seed operator (XP-A1) | G1.2 install with the dedicated governance role and the re-scoped admission, trust activation and pin evidence; any later exact-ARN admission; the API Gateway SLR if missing; the live `pulumi stack init` under the session policy, including its self-assume precondition; under D-A12 branch A, the one-time account-scoped WAF-log policy write; under the branch-B fallback (PD-16), the 23-F1 seed amendment install and the 23-F2 account-scoped write |
| Governance stack (gateway target, `{env}-governance-api-gateway-infrastructure`) | G1.3…G1.8 governance PRs and applies under the dedicated role, inside the admitted ARN set (D-A9, D-A11); under branch B, G1.5b at rows 21a and 31b and the 23-F3 governance PR that deletes the policy through CI (PD-15) |
| BI repository admin | G1.3: create the `{test,prod}-governance-api-gateway-infrastructure` environments (`@Kravalg` sole reviewer), per-action authorization |
| `@Kravalg` | seed and stack reviews, BI and AGI PR approvals, every protected-environment apply, XP-A3 admin apply |
| Gateway owner | G0.1 and the D-A6 emptiness check, the certificate hand-offs (XP-A8), PR #34 amendment coordination |
| USI owner | CR-A1, CR-A2 (slot, rebase, shared-ceiling budget); XP-A7 descriptors (TEST after S4.6 step 20); pinning the gateway ARNs (USI XP-10, XP-15); XP-A14 campaign coordination |
| Owner of the `vilnacrm.com` PROD zone | XP-A11: the zone exists or is created in account `933245420672`; the zone id and the record permission |
| User | XP-A10 endpoints, the D-A7 PROD values in the G6.2 PR, per-action authorizations |

## Skill applicability (devops-sdlc)

| Skill | Applies to |
| --- | --- |
| python-pulumi | G3.1, G4.x, G5.x, G6.x |
| security-iam | G1.x, AD-A1, AD-A7 |
| drift-management | G3.5, G6.3 |
| delivery-and-rollback | G3.4, AD-A12 |
| observability | G5.2 |
| cost-optimization | NFR-A07, AD-A6 |
| infrastructure-quality | G3.2, G3.3 |
| evidence-and-coverage | G5.6, G6.3 |
| environment-lifecycle | G3.4 `initialize-stack`, D-A6, AD-A15 feature flags |
| state-migration | not applicable (new backend; D-A6 retires any legacy state) |
| backup-recovery | PD-6 rebuild |
| incident-response | runbooks (NFR-A10) |
| terraform-terraspace | not applicable |
| bmad-autonomous-planning | the planning chain itself (revisions 1-7) |

## Readiness round 4 (on `7e644b7`, FAIL: 2 medium, 2 low, 3 nits): resolution table

| # | Finding (short) | Where resolved (revision 8) |
| --- | --- | --- |
| R4-1 | The `get_log_group` lookup needs `DescribeLogGroups` and `ListTagsForResource`, which no role holds; the PROD policy entered the PROD governance plans at rows 26 and 29 before its log group exists | G1.5b builds the log-group ARN from stack config (no lookup). The closed per-stack key `gateway_waf_log_policy` (default `false`; TEST set at 21a, PROD at 31b) gates the declaration. An N test asserts that the PROD stack plans no `aws:cloudwatch/logResourcePolicy:LogResourcePolicy` while the key is `false`. E case: an absent log group fails `PutResourcePolicy` in a single-resource PR with no partial write. The dependency claims (epics ordered list, the self-check above) are re-checked by script for both branches |
| R4-2 | 23-F3 ran outside CI | PD-15: under branch B only, `logs:DeleteResourcePolicy` on the exact log-group ARN, in the `PutResourcePolicy` statement; branch B re-measured at 6095 (≤ 6144, no wildcard). 23-F3 is a reviewed governance PR (`/pulumi plan|up`); BI `scripts/pulumi_ci_guardrails.py` lines 17-30 list no `aws:cloudwatch/` type as critical, and `find_destructive_steps` (lines 115-125) flags only critical types. 23-F1 drops all three `logs:` actions. The round-1 F6 rule is retired in PD-15, not in the D-A12 cell. XP-A1 holds no delete role |
| R4-3 | 23-F1 packet, CR-A2/XP-A4, branch-A slot, role tables, retry order | G5.4 23-F1 lists the source packet (amendment module, Modify-row change-set validator, tests, seed review). CR-A2 and XP-A4 list 23-F1 as a catalog change that rebases later USI modules and lands after the S4.6 step-20 seed amendments of USI row 43 (S5.5/S5.18b) are installed and pinned and before USI row 45 (the queue stays one-open). The branch-A slot before row 16 is the normal position; 23-F2 after row 23 is the fallback position. prd §2 and the role table list the 23-F actions. The row-23 retry waits only for the TEST halves; the PROD halves (23-F1, 23-F2) run after 31a and before 31c, and row 31b is then not applicable |
| R4-4 | Test and acceptance gaps | G6.2a E: a mock test that `front_door: observability` and `true` give identical URNs and parents for the observability resources. G6.2 N: no delete or replace of `aws:cloudwatch/logGroup:LogGroup`. G6.1: the offline checks of G5.1, live checks first at 31a. FR coverage lists G6.2a for FR-A18 and FR-A21 |
| Nit 1 | Session-policy `ListBucket` | The `StringLike` prefix also covers the lock prefix, only if `pulumi stack init` takes a lock |
| Nit 2 | Self-assume precondition owner | The XP-A1 operator (architecture session policy; role table above) |
| Nit 3 | Plan rules in the D-A12 cell | Moved to PD-15 and PD-16; the cell points to them |

## Revision 8 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 8: REFUTED, narrowly** (3 P3, 6 P4). It confirmed:
- every size, re-rendered from the BI `pulumi/` directory: 5830 (A) and 6095 (B) dedicated, guard 5565, shared 5387/5397 (A) and 5419/5429 (B);
- that the committed `evidence/*.json` are byte-equal to the in-memory render;
- that branch B holds exactly Put+Delete on the exact log-group ARN plus `DescribeResourcePolicies` on `*`, and branch A holds no `logs:` statement;
- BI `scripts/pulumi_ci_guardrails.py` lines 17-30 and 115-125 (no `aws:cloudwatch/` critical type), so 23-F3 runs as a governance PR;
- no forward dependency in the 36 rows; that only `specs/` changed.

Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | G5.4 said nothing is applied by hand, but 23-F2 is a seed-operator write | G5.4 names the exceptions: the 23-F1 seed change-set install and the 23-F2 write (branch A's user-decided write, D-A12) |
| 2 | No negative case for the new `DeleteResourcePolicy` | G1.1 matrix: denied on `*`, on an account-scoped policy by `policyName` and on other log groups; allowed on the exact ARN. G1.5b N covers Put and Delete |
| 3 | The fallback left the branch-B operator read grant | 23-F1 removes `logs:DescribeResourcePolicies` from the gateway operator documents; the AD-A1 coverage test checks both directions |
| 4 | Placeholders and stale hash block | Filled; hashes regenerated |
| 5 | Branch-A slot text stale in architecture, FR-A05 and the XP-A1 blocked rows | 23-F2 after row 23 named; XP-A1 list completed |
| 6 | 23-F1 statement id | "the merged `logs:DescribeResourcePolicies` statement (back to `2be63eb2…`)" |
| 7 | "may land while USI row 43 runs" against the one-open queue | See recheck |
| 8 | Architecture "Measured (revision 7)" | Revision 8 |
| 9 | No PROD-only fallback | G5.4 adds a PROD 23-F3 after 31b, then the PROD halves, then the 31c retry |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1, 2, 5, 6 and 8 FIXED; 3 and 7 PARTLY; 9 fixed with a gap; 4 expected. It ran `evidence/check_ordered_list.py` and confirmed it fails on four injected forward edges. New and residual:
- **NEW-1 (P3):** the operator-document removal in the packet PR would fail the two-direction test while the pinned catalog still admits the read. Resolved: the removal lands in each environment's `CATALOG_HASHES` re-pin PR, so catalog and grant change in one commit.
- **NEW-2 (P4):** the PROD half of 23-F1 has its own packet on the PROD catalog current at its slot (after USI rows 47-50); the CR-A2 rebase rule applies per environment.
- **NEW-3 (P4):** the two fallback orders in the script are labelled model checks (script docstring, epics and the self-check above); the 21a parse splits on sentence ends.
- **7 (residual):** 23-F1's TEST half lands after the S4.6 step-20 seed amendments of USI row 43 are installed and pinned, before USI row 45 (CR-A2, XP-A4, G5.4).
- **9 (gap):** a PROD-only fallback leaves the branch per environment (TEST stays on branch B, PROD ends on branch A), stated in PD-16 and G5.4.

No third round ran.

## Revision 7 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 7: REFUTED, narrowly** (3 P3, 3 P4). It confirmed:
- every size, re-rendered in both BI worktrees;
- that the committed `evidence/*.json` are byte-equal to the in-memory render;
- that branch A carries no `logs:` statement;
- the pinned `pulumi_aws` and workflow citations and the budgets;
- 36 rows with no forward edge under either branch;
- that only `specs/` changed.

Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | The branch-B to branch-A fallback (V-A6 failing live) had no rows | G5.4 STOP with contingency rows 23-F3, 23-F1 and 23-F2 (see recheck); the D-A12 cell records it as a consequence (moved to PD-16 in revision 8), not a new decision |
| 2 | The G1.3 operator grant of `logs:DescribeResourcePolicies` was unqualified | Qualified "branch B only" |
| 3 | The per-target change missed the receipt call | `deployment_worker_receipt.py` (workflow 680-689) added in AD-A1 and G1.3 |
| 4 | Stale AD-A15 flag text | "G4.2, G6.2a (`observability`) and G6.2" |
| 5 | G1.5b details | `aws.cloudwatch.get_log_group` lookup (revision 8, R4-1: dropped; the ARN comes from stack config); the row-29 order is stated; row 29's tail label is fixed |
| 6 | G6.2a had no Files line | Files listed; `observability` accepted only in `prod`; G3.1's certificate rule applies |

**Recheck (same auditor): REFUTED, narrowly.** Findings 2-6 FIXED; 1 PARTLY. New:
- **N1 (P3):** 23-F3 could not run, because no role held `DeleteResourcePolicy` and 23-F1 removed the reads first. Resolved: 23-F3 runs first, out of CI, by the XP-A1 operator under a narrowed session (`logs:DeleteResourcePolicy` and `DescribeResourcePolicies` on the exact log group, plus the stack checkpoint paths for `pulumi state delete`), then a governance PR removes the declaration. Branch B's size is unchanged; no governance role holds `DeleteResourcePolicy`. *Superseded in revision 8 (R4-2, PD-15): 23-F3 is a governance PR through CI; the out-of-CI delete is removed.*
- **N2 (P4):** 23-F1 and 23-F2 now run TEST then PROD, and G6.2 Needs names the PROD write.
- **N3:** G1.5b's STOP points to the sequence.
- **N4:** 23-F1 cites the CR-A2 rebase and the `CATALOG_HASHES` re-pin.

No third round ran.

## Readiness round 3 (on `854b7c4`, FAIL: 1 medium, 5 low, 5 nits): resolution table

| # | Finding (short) | Where resolved (revision 7) |
| --- | --- | --- |
| R3-1 | Branch-B scoped policy needs the WAF log group, which the CI Apply role creates later | The scoped form is a resource-scoped policy (`resource_arn`; pinned `pulumi_aws` 7.23.0 `cloudwatch/log_resource_policy.py` 33-35, 85, 108-111), recorded in G1.1/V-A8. New story G1.5b in its own rows: 21a (TEST, after row 21) and 31b (PROD). G6.2 is split into 31a (G6.2a: `features.front_door: observability`, creates the log group), 31b, and 31c (G6.2). G5.4, G6.2, AD-A9, FR-A05 (the name pattern holds only under branch A), C-BI-A, C-program, AD-A15 and the ordered list (36 rows) are updated. V-A6 covers WAF accepting a resource-scoped policy, falling back to branch A within D-A12. Governance never creates the log group. |
| R3-2 | Stack-init session policy | Placeholder `<XP-A1-operator-role-arn>` with a self-assume trust; a call set derived from the pinned CLI (prefix listing with `StringLike` `…/{stack}.*`, BI `governance_automation.py` 291-296; lock paths only if init locks); an absence proof by a 0-key prefix listing; the BI doc update (`docs/governance-stack.md` 240-247) as a BI-owner item; narrowed-session evidence (session ARN, CloudTrail `AssumeRole` event id, a 403 `head-object` on USI's checkpoint); `encryptedkey` never committed (BI docs 258-260) |
| R3-3 | Replication trust lacks `aws:SourceArn` | AD-A1 trust and activation step 6; the G1.1 activation validator asserts both conditions (BI `pulumi_state.py` 123-142) |
| R3-4 | Stale "governance writes the WAF-log policy" | D-A5 consequence, brief, the architecture tree, AD-A9 and FR-A05 are annotated per branch (re-scoped by D-A12) |
| R3-5 | Wrong planning-name claim; live re-derivation; escalation | AD-A1 corrected (no Apply-policy names in the dedicated ceiling or identity). The rendered documents are pinned under `evidence/` with the copied USI action lists. Overflow is a STOP and a user decision (pre-named) |
| R3-6 | No environment readback before the first gateway-target run | G1.3 step 3: a readback of `@Kravalg` as required reviewer and `main`-only deployment branches |
| Nit 1 | TEST budget listed S5.24a/b | V-A13: TEST 657 (A) / 625 (B) for S5.2 TEST and XP-11; PROD 747 (A) / 715 (B) for S5.2 PROD and S5.24a/b |
| Nit 2 | G1.5 SLR sentence; Needs | The SLR sentence moved out of the branch-B bullet; XP-A1 and the XP-A4 slot (branch A) added to Needs |
| Nit 3 | Workflow citations | Stack checks 249-251, 392-394, 483-485, 621-623; admission calls 114-119, 226-231, 369, 460, 521, 598 |
| Nit 4 | Stale text | prd XP-A13 "As of revision 7"; readiness skill row; research K-6 |
| Nit 5 | `logs:DescribeResourcePolicies` unused under branch A | Dropped under branch A from the dedicated and shared ceilings and the operator grants; kept under branch B for the governance refresh |

## Revision 6 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 6: REFUTED, narrowly** (2 P2, 3 P3, 5 P4). It confirmed:
- D-A12, D-A13 and D-A14 are recorded faithfully;
- every size reproduces from both BI worktrees;
- `PulumiStateBuckets(manage_replication_role=False)` (`pulumi_state.py` 308, 581-586) reads the seed-created role;
- the USI provider pattern, the PROD id mapping, the counts and the ordered list;
- no stale current text;
- only `specs/` changed.

Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | Exact stack paths missed `{stack}.pulumi-tags` | `stacks/governance/{stack}.*`; re-rendered: 5905 (A) / 6065 (B), guard 5565 |
| 2 | Stack init could not run under the dedicated role (OIDC-only trust, no init path, environment created later) | The init runs after G1.3 step 3, by the XP-A1 human operator under a committed session policy (see recheck) |
| 3 | No tests for the L4 deny, D-A12 or the state paths | G1.1 simulator rows (attach of fixed policies to other roles denied; `logs:PutResourcePolicy` on `*` and on other log groups denied; USI checkpoint denied; gateway stack objects allowed) |
| 4 | Branch-A seed-operator slot not in the cross-plan queue | XP-A4 and CR-A2: after G1.2 and before row 16; no catalog change, no rebase |
| 5 | N2 test missing from G3.1 | Added to G3.1 N |
| 6 | Nits | XP-A14 names CR-A2; observation-script wording; row 8 Needs; NFR-A02 cites D-A14; step 8a waits 5 minutes after step 7 and fails on any 429/403 |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1 and 3-6 FIXED; 2 PARTLY. New:
- **N1 (P3):** the init scope lacked a prefix-limited `s3:ListBucket`, so a missing stack would answer 403, and it named no principal or enforcement.
- **N2 (P4):** the init scope wording differed between files.

Both are folded in. The operator's own non-root role is assumed with a committed session policy, `pulumi/governance/stack-init-session-policy-{env}.json`, with:
- `GetBucketLocation`;
- `ListBucket` with an `s3:prefix` limit;
- object read and write on `stacks/governance/{stack}.*`;
- read of `meta.yaml`;
- the governance key by exact ARN.

A simulator run is part of acceptance, and the wording is unified in AD-A1, G1.3 and prd §2. No third round ran.

## Readiness round 1 (on `3913ccb`, FAIL): resolution table

| # | Finding (short) | Where resolved (revision 5, kept or refined in 6) |
| --- | --- | --- |
| F1 | Gateway seed operations missing from USI's closed seed queue | decisions CR-A2; prd XP-A4 (#284 precondition); G1.2 Needs; AD-A1 source packet (no `ef419680…` baseline); AD-A12 order table |
| F2 | Dedicated role could rewrite trust and attach foreign policies | AD-A1 ceiling without role-write actions; guard denies (role, trust and tag updates; attach outside the four ARNs; inline on Apply and logging; revision 6 adds the L4 attach deny); G1.1 and G1.2 simulator cases |
| F3 | Structural Preview cannot work with the flags on | AD-A15 offline `ci` stack (revision 6 adds the N2 provider); G3.1, G3.3, G4.1, G5.1; FR-A09, FR-A11 |
| F4 | Nobody sets the AGI environment variables | G2.2 and FR-A07 variables, `--check`, one-directional name-match test (reverse direction in G3.5); row 12 |
| F5 | Catalog change affects other stacks | G1.3 target filter; BI runner apply order; platform-stack apply (prd §2) |
| F6 | Non-exact entries | D-A14 (user-accepted forms); separate KMS read; no `DeleteResourcePolicy` (retired in revision 8 for the exact WAF log-group ARN under branch B, PD-15); revision 6 removes `logs:PutResourcePolicy` on `*` (D-A12) |
| F7 | BI main enforces the opposite of the seed extension | G1.1 Files; V-A10 reframed; research GR-19, K-16 |
| F8 | NFR-A05 and NFR-A06 untested | gate A-T steps 8a and 8b (revision 6 fixes the rate and defines the dry run) |
| F9 | Size evidence incomplete | `evidence/render_governance_sizes.py` (real replica names, guard and identity rendered; re-measured in revision 6) |
| F10 | `sns:GetSubscriptionAttributes`; API Gateway prefixes; logging-role trust | AD-A7; NFR-A02; V-A9 |
| F11 | CR-A1 scope; G4.2 wait; G1.7 slot Needs; XP-A10; split option | CR-A1; G4.2 Needs; G1.7 Needs; XP-A10 rows 21 and 31; readiness note |
| F12 | Nits | P/N/E exceptions; skill row; FR-A06 `CreateGrant`; citations; fixture substitution; `governance/*` residual; PROD-baseline STOP |
| F13 | Profile and `attempts.json` absent | XP-A13; run-summary |

## Readiness round 2 (on `7ed5397`, FAIL: no major, 6 medium, 12 low): resolution table

| # | Finding (short) | Where resolved (revision 6) |
| --- | --- | --- |
| N1 | `logs:PutResourcePolicy` on `*` on the dedicated role contradicts D-A5 | **D-A12** (user): removed from the dedicated ceiling and identity; branch A (seed operator writes once, own slot, owner, evidence) or B (scoped grant); V-A8 in G1.1 Needs (row 8); AD-A1, AD-A9, FR-A05, G1.5, XP-A1 |
| N2 | `ci` stack has no credential-less provider | AD-A15: dummy static keys with the four `skip_*` flags (USI `pulumi/app/stack.py` 132-147), only in `ci`; `config.py` rejects them in `test`/`prod`; test |
| N3 | Gate A-T step 8a cannot pass at 50/s | Step 8a at ≤ 5 req/s from one IP for ≥ 10 minutes, below PD-3 and PD-4, 2xx only; NFR-A06 reworded |
| N4 | Shared Preview/Drift roles lack identity grants for the new admissions | AD-A1 "Identity grants matching the ceiling admissions"; G1.3 step 1 enumerates them; matching-grant test |
| N5 | Backend pattern | **D-A13** (user): FR-A03 and G1.3 P/N/E rewritten to the `PulumiStateBuckets` pattern; `manage_replication_role=False` keeps PD-12 consistent with no shared-code change |
| N6 | No init step or stack config for the gateway governance stack | Stack config files; live `stack init` with owner, identity and readback before step 4; `PULUMI_PREVIEW_STACKS`/`PULUMI_DRIFT_STACKS` and admission call (AD-A1, G1.3 step 2a) |
| L1 | `94a9f77e…` not a listed form | Replaced by the governance secrets key's exact ARN, pinned in G1.1 from an authenticated `DescribeKey` |
| L2 | Form 3 not exact | Exact stack paths, following the BI operator-bindings layout; redundant lock wildcard removed |
| L3 | Four forms need user acknowledgement | **D-A14** (user acknowledgement), its own record |
| L4 | Apply-role policies attachable to other roles | Guard deny of `AttachRolePolicy` on every gateway role except the CI Apply role |
| L5 | PROD id mapping wrong | `ec801503…` role reads, `6227eeae…` policy reads, `3899b5e7…` bucket reads |
| L6 | Stale "CR-A1 only" text | prd §6, epics inventory and row 0, readiness, run-summary now name CR-A2 too |
| L7 | No resolution tables | These two tables |
| L8 | Observation script origin | On origin/main; only `--active` comes with #284 (G1.1 Files) |
| L9 | Step 8b lacks `ec2:DescribeNetworkInterfaces`; dry run undefined | Drift grant (AD-A7, G1.4b); dry run is a preview of TEST against an empty local backend |
| L10 | Mixed-phase N contradicts P | Qualified "an executor that G1.2 step 1 observed active" |
| L11 | External-identity mode must skip `CiConfiguration` | AD-A1 and G1.3 (`governance.py` 657, 765-778) |
| L12 | CR-A2 TEST budget lists PROD-only S5.24a/b | TEST: 625 for S5.2 TEST and XP-11; PROD: 715 for S5.2 PROD and S5.24a/b |

## Revision 5 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 5: REFUTED, narrowly** (3 P2, 2 P3, 4 nits).

It confirmed:
- every size by re-running the render script in both BI worktrees (5737/5737/5198; 5419/5429; 5519 at `ff2eaf29…`);
- the real replica names;
- the dropped actions;
- that the guard does not block what governance needs;
- the shared-statement ids;
- the USI seed-order citation;
- the line citations;
- that only `specs/` changed.

Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | G2.2's variable name-match test read workflows from later rows | One-directional at row 7; the reverse direction is in G3.5 (row 14); the invariant is updated |
| 2 | G1.3 had no operator-stack apply after the catalog change | First an apply-order block; corrected in the recheck (below) |
| 3 | The shared Preview/Drift headroom is also USI's (625 left on TEST) | V-A13; AD-A1 "Shared headroom"; CR-A2 budget and STOP; G1.1 renders against USI row 34's result |
| 4 | G1.1 N contradicted the allowed non-exact forms | N and D-A11 qualified |
| 5 | The `ci` stack's secrets provider was unspecified | Local file backend and `passphrase` provider (committed salt, non-secret passphrase), exempt only in `ci` |
| 6 | Nits | G6.2 Needs XP-A10; K-16; "five new statements"; `UpdateRoleDescription` in the simulator list |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1 and 6 FIXED; 2-5 PARTLY. All remaining parts are now folded in:
- **2.** BI applies from the PR head through `pulumi-pr-command-runner.yml`, per environment, operator → governance → platform (lines 132/154/178, 261/288/317). G1.3 now says so, with a fixture test that the runner includes the gateway target.
- **3.** Row 8 is placed after USI row 34's result in the AD-A12 order table and in readiness, and V-A13 is in the dependency list.
- **4.** AD-A1, readiness and D-A9 are qualified. The refinement is recorded as the plan's, which the user may veto.
- **5.** prd FR-A03 and its N case are scoped to `test`/`prod`.

The auditor's stray `evidence/__pycache__` was removed. No third round ran.

## Revision 4 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 4: REFUTED** (1 major, 2 medium, 2 low, 1 nit). It confirmed:
- the 30/9/67 arithmetic;
- the dedicated guard at 3867;
- the trust mirror of `governance_trust_policy`;
- that no operator ceiling, `668edd62…` or `415affc4…` blocks the dedicated role;
- the statement-sharing facts;
- no forward dependency;
- that only `specs/` changed.

Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | The shared Preview/Drift guards deny lock writes outside `governance/` (`167f653d…`, `e90f172a…`), so a separate prefix broke gateway preview and drift | The gateway stack stays inside `governance/` as `{env}-api-gateway-infrastructure` of project `governance`. No guard change. The dedicated role is confined to its stack paths. USI Apply's `governance/*` write is recorded as a residual |
| 2 | Preview/Drift 5210/5220 cannot be reproduced as "new statements" (6648/6658) | In-place merge into the Preview/Drift-only statements, with ids. Re-measured 5104/5114 (5204 at `ff2eaf29…`). The render script is committed (`evidence/render_governance_sizes.py`) |
| 3 | The operator fan-out would attach gateway policies to USI's Apply role | Operator code change in G1.3 step 1 (Preview/Drift purposes only, gateway-specific documents). N case: USI Apply attachments unchanged |
| 4 | The dedicated target's wiring was unnamed | Workflow wiring specified (see recheck N1) |
| 5 | Preview/Drift reads omitted the gateway boundaries | Added to the policy-read merge |
| 6 | Leftovers | D-A9 items marked superseded; readiness, research K-17, the tree and epics row 0 fixed |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1, 2, 3, 5 and 6 are FIXED; #4 is PARTLY fixed.
- **New N1 (medium):** an environment-scoped variable cannot override the apply role. The `resolve` job declares no environment, and the apply environment and the stack checks are hard-coded.
- **N1 resolution:** a target-keyed `AWS_GOVERNANCE_{ENV}_APPLY_GATEWAY_ROLE_ARN` read in `resolve`, a per-target apply environment and `PULUMI_STACK`/stack checks, and a workflow fixture test (AD-A1 "Workflow wiring"; G1.3 steps 2-3).
- The KMS cross-combination note was added.
- No third round ran.

## Revision 3 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 3: REFUTED** (1 major, 3 medium, 1 minor). It confirmed every statement id per baseline (guard lists, operator guards), the 55/24/21 baseline and the 64 arithmetic, the PRD counts, no forward dependency, no live OQ-9/OQ-10 leftover, and that only `specs/` changed. Resolutions:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | The exact-ARN admission into `ceiling/GitHubGovernanceApply` exceeds 6144 characters (5752/5762 now; 7187-8729 after) and the ceiling cannot be split | Recorded as a blocker, not compacted: AD-A1 "Size blocker", V-A12, G1.1 STOP and Needs; new open question **OQ-11** with options (decisions §3); research K-18 |
| 2 | KMS management statements missing from the ceiling admission | `81c3805b`/`6f28ae7e`/`37942811` (PROD `c453626c`/`8fa820e5`/`baf46019`), a second Purpose value, both aliases (AD-A1) |
| 3 | Operator guards `c18540fb`/`0142330f` are Resource-`*` denies | Named in the D-A9 exception (brief, readiness, AD-A1, G1.1 STOP) |
| 4 | Preview, Drift and replication grants are inline, not ARNs | Fixed policy set split into managed ARNs and inline names; the new kind's inline allowance (AD-A1 registry list; G1.1 Work and acceptance; FR-A02) |
| 5 | Operator bindings are catalog metadata, not rows; `policy_read_resources` missing | Removed from the Modify-row lists; `policy_read_resources` added |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1, 2, 3 and 5 FIXED; 4 PARTLY (the inline allowance was missing from the registry change list and G1.1). New: N1 (minor, the counts were stated unconditionally while OQ-11 is open) and N2 (nit, OQ-11's reach understated). All folded in: the inline allowance in AD-A1, G1.1 and FR-A02; counts qualified as "under OQ-11 (b) or (c); under (a) 30 / 9 / 66"; OQ-11 blocks row 8 and every dependent row. No third round ran.

## Revision 2 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted revision 2: REFUTED, narrowly** (2 major, 2 minor, 4 nits). It confirmed the D-A1…D-A8 records, the D-A# namespace, the removal and renumbering of rows, the absence of forward dependencies, the BI line and statement citations, the 55/24/21 counts, the 64/68 totals and the PRD counts. All eight findings were folded in:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | `verify_enrollment` cannot pass after CREATE (the executors are active) | AD-A1 mixed-phase verifier; G1.1, G1.2, FR-A02 |
| 2 | OQ-9 (b) understated: governance seed ceilings | OQ-9 (b) restructured (ceilings, plus operator bindings found while fixing); AD-A1 validator; G1.3; K-17; readiness |
| 3 | A stack policy cannot gate an Add; activation needs `Update:Modify` | AD-A1 steps 3 and 6; G1.2 |
| 4 | Statement ids depend on the baseline | OQ-9 (b) ids per baseline; AD-A1 PROD ids |
| 5-8 | brief §-reference; "two parts" wording; G1.2 Needs OQ-10; Apply guard variant for OQ-10 (b)/(c) | fixed |

**Recheck (same auditor): REFUTED, narrowly.** Findings 1 and 3-8 FIXED; finding 2 PARTLY (the five operator executor guards that close the governance policy names, TEST `0c5eed92…`, `c18540fb…`, `408cdbf9…`, PROD `de33acbe…`, `0142330f…`, `7a337042…`, were missing). New: N1 (minor, the mixed-phase verifier assumed active PROD executors), N2 (nit, G1.1 validator wording lacked the OQ-9 (b) exception), N3 (nit, this table's attribution). All folded in: OQ-9 (b), AD-A1 validator and verifier, G1.1, G1.2, K-17, this file. No third round ran.

## Revision 1 audit history

The tables below record revision 1's audit. Findings #2, N1, N3 and N6
concerned the OQ-8 (a) path, which D-A2 removed. Finding #8 and K-15
concerned the registration shape, which D-A1 replaced (AD-A1, V-A10).

### Revision 1 pre-commit audit (fresh context, `claude-router:audit`)

**Audit of the uncommitted draft: REFUTED** (10 major, 10 minor, 2 nits).
It confirmed the BI seed lines, the `pulumi_aws` 7.23.0 citations, the PR
metadata, the USI decisions hash, the reuse of D-3, D-6 and D-15, and that
no user decision was invented. Every finding was folded in before the
first commit:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| 1 | `apigateway:SetWebACL` missing for the stage association | AD-A7 row, G1.4b matrix; research GA-17 (WAF IAM page) |
| 2 | Gate order ignored USI S4.6 steps 18-20 (no foreign ENI, subnet deletion, rebuild) | OQ-8 (recommend (c)); FR-A25; conditional G1.9, G5.7, G5.8; AD-A3, AD-A12 table; K-12 |
| 3 | XP-A7 asked for a USI publication that does not exist | OQ-7 (recommend live re-verification); XP-A7 reworded; K-14 |
| 4 | `Contract Schema` required before any job defined it | G3.3 creates the job and the schema; AD-A11; C-contract head is G3.3 |
| 5 | Policy pack's web ACL rule broke G5.3 before G5.4 | the rule applies only to mapped stages (AD-A10); G3.3 and G5.5 tests |
| 6 | Gate A-T evidence reads had no grant | Drift evidence reads (Logs Insights, `GetSampledRequests`) in AD-A7 and G1.4b; G5.6 wording |
| 7 | "Refresh-free" drift cannot see drift | `preview --refresh --expect-no-changes` (FR-A13, AD-A11, G3.5) |
| 8 | `existing: false` means an operator executor; fixed counts | AD-A1: create, then register as `existing: true` with verifier changes; G1.2 before G1.1; V-A10; K-15 |
| 9 | Replication role missing | PD-12; FR-A01; G1.2, G1.3 |
| 10 | USI TEST scales to zero at night and weekends | PD-13; FR-A13, FR-A21; gate A-T in the daytime window; K-13 |
| 11 | Delete deny contradicted needed deletes | AD-A7 deny exceptions; `wafv2:DeleteLoggingConfiguration` added; G1.4b E case |
| 12 | Route 53 alias changes may be delete-and-create | `DELETE` allowed for the exact alias names only; a lone delete is still gated |
| 13 | The two-step exact-ARN ACM fallback cannot work | tag-conditioned reads (GA-16); the fallback is a user decision, not defaulted |
| 14 | KMS and WAF-log questions blocked the certificate path | G1.4 split into G1.4a (certificate, row 11) and G1.4b (front door, row 18) |
| 15 | XP-17's installer is too narrow for S3, KMS, API Gateway account and Logs | XP-A1 "widened", its own BI review |
| 16 | PROD drift would fail for weeks | feature flags (AD-A15, G3.1); PROD drift previews an empty program until row 30 |
| 17 | `DescribeLogGroups` scope disagreed | AD-A9 aligned with AD-A7 (V-A8) |
| 18 | C-program chain incomplete | architecture §4 chains rewritten (C-policy, C-contract, conditional rows) |
| 19 | XP-A10 not in G5.2 Needs; probe metric needs `PutMetricData` | G5.2 Needs; Drift `PutMetricData` with a namespace condition |
| 20 | autorelease's App private key unaddressed; live count | PD-11; G2.1; PRD §1 category recomputed from the Risk column |
| 21 | "D-8 by analogy" | reworded to D-8's recorded reason |
| 22 | `_*.{fqdn}` does not match DKIM names | AD-A8 and K-8 reworded; the deny kept as defence in depth |

**Recheck of the fixes (same auditor, fresh read of the revised files):
REFUTED, narrowly.** 21 of 22 findings FIXED, #2 PARTLY (coherent under
OQ-8 (c); the (a) path incomplete). New: 1 major (OQ-8 (a) only), 3
minor, 2 nits. The recommended OQ-1 (a) / OQ-8 (c) path held under every
check. All six were folded in before the commit:

| # | Finding (short) | Resolution |
| --- | --- | --- |
| N1 | OQ-8 (a) teardown: recovery role lacked state write, stage `PATCH`, backend-policy amendment, seed-registration row and the `test-recovery` environment row | AD-A7 recovery role (state and key read/write, `PATCH` on stages); G1.9 rewritten as backend amendment, seed registration and G2.2/XP-A3 environment parts in row 26; C-controls chain; epics Needs |
| N2 | A skipped probe would publish a metric before the grant exists | G3.5: publish only when the probe runs (after rows 18 TEST, 32 PROD) |
| N3 | Recovery deletes on every REST API and VPC link | `aws:ResourceTag/Owner` condition, else the manifest's exact ids |
| N4 | OQ-8 (c) held USI step 17 for seven days | gate A-T step 11 moved out of the step-17 bundle (AD-A12 step 12); OQ-8 states the two-weekday hold of step 10 |
| N5 | K-4 stale row range | research K-4 reworded |
| N6 | Manifest not URN-level | FR-A25 and G5.7: manifest by Pulumi URN, every child listed |

No further audit round ran after these wording and grant fixes; the next
independent readiness round verifies them.
