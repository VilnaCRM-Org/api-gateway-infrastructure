---
artifact: implementation-readiness
workflow: _bmad/bmm/workflows/3-solutioning/bmad-check-implementation-readiness (Validate mode)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 5 (independent readiness round 1 at 3913ccb: FAIL; findings F1-F13 resolved here)
author: the planning agent that wrote revisions 1-5 (NOT an independent reviewer)
independent_reviewer: readiness round 1 (FAIL, 3 major, 5 medium, lows) on revision 4; round 2 not run yet
status: PENDING independent readiness round 2 on revision 5
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
- **Rows blocked by a conditional decision:** if V-A8 finds no scoped
  `logs:PutResourcePolicy` and the BI owner declines it on Resource `*`,
  row 16 stops for a user decision (not decided here).
- **Rows blocked by external preconditions:**
  - XP-A1 → row 9, any later exact-ARN admission, and the API Gateway
    service-linked role in row 16 if XP-A5 finds it missing;
  - XP-A3 → row 12;
  - XP-A4 → every seed slot;
  - XP-A5 → rows 16 and 22;
  - XP-A6 → row 15;
  - XP-A7 → rows 19 and 28;
  - XP-A10 → rows 21 and 31;
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
  - rows 28-32 after USI row 52.

## Checks performed (self-check, revision 5)

| Check | Result |
| --- | --- |
| Every FR and NFR has at least one story (epics FR coverage map) | yes: 25 FRs, 11 NFRs; FR-A25 now maps to G5.1 and G5.6 |
| PRD §1 counts equal the tables | 25 + 11 = 36; offline 23 FRs + 8 NFRs = 31; live-only FRs 2; evidence-only NFRs 3; offline FRs with live evidence 18 (recomputed from the Risk column; FR-A25's Risk is now C, L) |
| Ordered list has no forward dependency | yes, rows 0-32 (33 rows), including test, ownership and feature-flag levels (epics "No forward dependencies") |
| Rows 26-28 of revision 1 removed, later rows renumbered | yes: G1.9, G5.7, G5.8 removed; rows 29-35 → 26-32; every in-bundle reference to a gateway row re-checked (USI row numbers unchanged) |
| No OQ-8 (a) remnant | yes: no recovery role, `test-recovery` environment, teardown manifest, recovery guardrail mode or `detached` flag remains |
| Every story has P, N and E acceptance cases | yes, except G1.7 and G1.8 (they reuse the G1.4a and G1.4b matrices in PROD), G4.2 (as G4.1, in PROD), G5.6 (the gate A-T steps), and G6.1 and G6.3 (as G5.1 and gate A-P) |
| Readiness round 1 findings F1-F13 resolved | yes: F1 CR-A2, #284 precondition, no `ef419680` baseline; F2 dedicated ceiling without role-write actions, guard denies, simulator cases; F3 offline `ci` stack; F4 G2.2 environment variables; F5 per-stack target filter and platform-stack apply; F6 allowed non-exact forms, separate KMS read, no `DeleteResourcePolicy`, conditional STOP; F7 origin/main files and V-A10 reframed; F8 gate A-T steps 8a/8b; F9 real replica names, guard and identity rendered; F10-F12 below; F13 XP-A13 |
| D-A1 honoured: the gateway roles enter through a reviewed seed catalog amendment installed by the human seed operator; the governance-stack route is not used for role creation; the independent CloudFormation owner is not the chosen route | yes (AD-A1, FR-A01, FR-A02, G1.1, G1.2). The departures from USI are listed in AD-A1: role creation by the seed (D-A1), the governance admission (D-A9), no ConfigRead (D-A10) and the stricter trust (PD-14) |
| D-A9 honoured (re-scoped by D-A11): governance writes the gateway's grants, backend, CMK and account settings; the G1.2 change set admits it by exact ARNs (plus the four AD-A1 allowed non-exact forms), now limited to the shared Preview/Drift ceilings (in-place merge), the operator bindings and the five operator guards; USI's `G-GitHubGovernanceApply` and Apply ceiling unchanged; external-identity mode; options (a) and (c) only as rejected alternatives | yes (decisions §1 and §3; AD-A1 "Governance admission"; FR-A02…FR-A06; G1.1…G1.8; XP-A1, XP-A4) |
| D-A11 honoured: dedicated `GitHubGovernanceApply-api-gateway-infrastructure-{env}` with its own exact-ARN ceiling, guard and identity; trust mirrors `governance_trust_policy` with the environment `{env}-governance-api-gateway-infrastructure`; per-target governance job and stack; USI's ceiling and guard untouched; options (b) and (c) rejected | yes (decisions §1, §3; AD-A1; FR-A02; G1.1-G1.3) |
| V-A12 (size) | resolved, re-measured in revision 5 with `policy_registry.canonical_json` (`evidence/render_governance_sizes.py`, real replica names, `SeedKmsKeyArn` bound): dedicated Apply ceiling 5737 and identity 5737 (TEST, PROD), its guard 5198; shared Preview/Drift ceilings 3789/3799 → 5419/5429 (TEST/PROD; 3889 → 5519 at `ff2eaf29…`); USI's Apply ceiling unchanged at 5752/5762. All ≤ 6144; G1.1 re-renders them as tests |
| V-A13 (shared-ceiling budget across both plans) | open check: 625 characters remain on TEST after #284 + gateway for USI's later additions (S5.2 before the slot; XP-11 and S5.24a/b after it); G1.1 renders against the row-34 result catalog; CR-A2 carries the budget; over 6144 → STOP for both owners |
| D-A10 honoured: no ConfigRead roles; c = 0; the Apply guard's secret-read statement has no CI-secret variant; a later reader needs a reviewed amendment | yes (AD-A1; FR-A01; G1.1; G3.4; decisions §3) |
| Counts | per environment 30 principals (24 + 6), 21 existing roles, 9 seed-created principals (3 + 6), **67** policies (55 + 4 boundaries/ceilings + 6 guards + 2 identities: logging role and dedicated governance role). The coordinator's estimate of 66 omitted the dedicated role's seed-owned identity (AD-A1 derivation) |
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

- **Gateway decisions, dated 2026-10-01:** D-A1…D-A11 (`decisions.md` §1).
  They answer OQ-1…OQ-11. The namespace is gateway-local, `D-A#` (PD-1).
- **Reused, dated 2026-09-30:** D-3, D-6, D-15 and the D-4 consequence
  (`decisions.md` §2).
- No other user decision was invented. Every choice the plan needed and
  the user has not made is an OQ or a labelled planning default.

## Remaining user decisions

None. OQ-9, OQ-10 and OQ-11 are answered by D-A9 (option (b),
governance), D-A10 (option (a), none) and D-A11 (option (a), dedicated
governance role); their rejected alternatives are kept in
`decisions.md` §3.

**Cross-plan request for the USI owner:** CR-A1. USI S4.6 step 17 runs
after step 20 and is held for gate A-T step 10 (two weekday drift runs).

The planning defaults PD-1…PD-14 are not decisions; the user may change any
of them. A conditional decision appears only if V-A7 fails (an
account-wide ACM metadata read, AD-A7) or if V-A6 fails (WAF log delivery
without `logs:PutResourcePolicy`; D-A5 excludes the `*` grant).

## Unresolved external prerequisites

XP-A1…XP-A14 (`prd.md` §7). Human and owner roles:

| Role | Items |
| --- | --- |
| BI owner | G1.x authorship; V-A10 (reversing origin/main's rule against extending the seed inventory); XP-A4 slot ordering with the USI queue (CR-A2); XP-A5 and XP-A12 read-backs; accepting the residual that USI's governance Apply can write `governance/*`, including the gateway governance stack's state; the PROD seed stack's installed-state read before G1.2 PROD |
| Human seed operator (XP-A1) | G1.2 install with the dedicated governance role and the re-scoped admission, trust activation and pin evidence; any later exact-ARN admission; the API Gateway SLR if missing |
| Governance stack (gateway target, `{env}-governance-api-gateway-infrastructure`) | G1.3…G1.8 governance PRs and applies under the dedicated role, inside the admitted ARN set (D-A9, D-A11) |
| BI repository admin | G1.3: create the `{test,prod}-governance-api-gateway-infrastructure` environments (`@Kravalg` sole reviewer), per-action authorization |
| `@Kravalg` | seed and stack reviews, BI and AGI PR approvals, every protected-environment apply, XP-A3 admin apply |
| Gateway owner | G0.1 and the D-A6 emptiness check, the certificate hand-offs (XP-A8), PR #34 amendment coordination |
| USI owner | CR-A1; XP-A7 descriptors (TEST after S4.6 step 20); pinning the gateway ARNs (USI XP-10, XP-15); XP-A14 campaign coordination |
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
| bmad-autonomous-planning | the planning chain itself (revisions 1-5) |

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
