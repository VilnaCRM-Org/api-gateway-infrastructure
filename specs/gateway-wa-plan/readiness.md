---
artifact: implementation-readiness
workflow: _bmad/bmm/workflows/3-solutioning/bmad-check-implementation-readiness (Validate mode)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 1
author: the planning agent that wrote revision 1 (NOT an independent reviewer)
independent_reviewer: none yet for revision 1
status: PENDING independent review of revision 1
---

# Implementation readiness

## Verdict

**Not PASS; pending an independent review.** The author of this file wrote
the bundle, so this is a self-check, not a gate result. A fresh-context
pre-commit audit and its recheck ran before the first commit (below). The
self-check finds the bundle complete enough for an independent readiness
round, with these blockers for implementation:

- **Rows blocked by open user questions** (each row's "Needs"): OQ-1 →
  row 8 and every later BI row; OQ-2 → rows 17, 21; OQ-3 → rows 29, 30,
  32-35; OQ-4 → rows 16 (WAF-log part), 23; OQ-6 → row 34; OQ-7 → rows
  19, 20, 31, 33; OQ-8 → the timing of rows 19-25 and the existence of
  rows 26-28. OQ-5 decides only the outcome of row 1.
- **Rows blocked by external preconditions:** XP-A1 (rows 8, 10, 11,
  16-18, 26, 29, 32 and every stack amendment), XP-A3 (rows 12 and, under OQ-8 (a), 26), XP-A4 (every
  seed slot), XP-A5 (rows 16, 22), XP-A6 (row 15), XP-A7 (rows 19, 31),
  XP-A10 (row 21), XP-A12 (row 16), XP-A13 (all implementation), XP-A14
  (rows 19, 27, 28).
- **Cross-plan ordering** (architecture AD-A12): row 15 before USI row
  42; rows 19-25 after USI S4.6 step 20 and before step 17 (which USI
  would run after step 20 under OQ-8 (c)), or between steps 2 and 17
  with rows 26-28 around steps 18-20 (OQ-8 (a)); row 30 before USI row
  49; rows 31-35 after USI row 52.

## Checks performed (self-check, after the audit fixes)

| Check | Result |
| --- | --- |
| Every FR and NFR has at least one story (epics FR coverage map) | yes: 25 FRs, 11 NFRs |
| PRD §1 counts equal the tables | 25 + 11 = 36; offline 23 FRs + 8 NFRs = 31; live-only FRs 2; evidence-only NFRs 3; offline FRs with live evidence 18 (recomputed from the Risk column) |
| Ordered list has no forward dependency | yes, rows 0-35, including test, ownership and feature-flag levels (epics "No forward dependencies") |
| Every story has P, N and E acceptance cases | yes, except G1.7 and G1.8, which reuse the G1.4a and G1.4b matrices in PROD, and G5.8, which re-runs listed gate A-T steps |
| No story narrows an existing seed guard statement on Resource `*` | yes, under OQ-1 (a); OQ-1 (b) is the user's to choose |
| No CI role gets `ssm:*`, `iam:*`, `iam:PassRole`, `iam:CreateServiceLinkedRole` | yes (AD-A7 deny set; G1.4a and G1.4b matrices) |
| D-15 honoured: no SSM write or read anywhere | yes (AD-A2 drops PR #34's parameter; the policy pack refuses `aws:ssm/*`) |
| D-3 honoured: REST API + WAF + VPC link V2 → ALB; NLB only as reviewed fallback | yes (AD-A4, V-A1) |
| Gate order against USI gates stated, including the USI abandon rehearsal | yes (AD-A12 table; OQ-8) |
| Every AWS claim cites a source | yes (research §5, GA-1…GA-17) |
| Every repository claim cites file and line or a read-only API call | yes (research §2-§4) |
| Long-lived secrets | none created; the App private key use is dropped (PD-11); no PAT |

## User decisions

Reused, dated 2026-09-30: D-3, D-6, D-15 and the D-4 consequence
(`decisions.md` §1). No new user decision was invented; every choice the
plan needed and the user has not made is an OQ or a labelled planning
default.

## Remaining user decisions

| ID | Question | Recommendation |
| --- | --- | --- |
| OQ-1 | Enrolment route for the gateway CI identities | (a) independent CloudFormation owner; no guard narrowed |
| OQ-2 | KMS key for gateway log groups and topic | (a) dedicated BI-owned gateway CMK per environment |
| OQ-3 | PROD FQDN and zone owner | name them; the zone in PROD account `933245420672` |
| OQ-4 | WAF log resource policy | (a) BI pre-creates it; never default to `logs:PutResourcePolicy` on `*` |
| OQ-5 | Legacy stack or `my-bucket`, if found | (a) retire after an emptiness check |
| OQ-6 | PROD throttle and WAF rate values | from the G5.6 TEST evidence, confirmed in the G6.2 PR |
| OQ-7 | Provenance of the USI descriptor | (a) the gateway's live re-verification is the authority |
| OQ-8 | TEST front door vs the USI abandon rehearsal | (c) USI runs S4.6 step 17 after step 20; (a) if the USI plan must stay unchanged |

The planning defaults PD-1…PD-13 are not decisions; the user may change
any of them. A conditional decision appears only if V-A7 fails (an
account-wide ACM metadata read, AD-A7).

## Unresolved external prerequisites

XP-A1…XP-A14 (`prd.md` §7). Human and owner roles:

| Role | Items |
| --- | --- |
| BI owner | G1.x authorship; XP-A4 slot ordering with the USI queue; XP-A5 and XP-A12 read-backs; the G5.7 ENI read-back under OQ-8 (a) |
| Seed operator | G1.1 and every conditional catalog amendment (G1.4a, G1.4b, G1.7, G1.9) |
| Reviewed installer (XP-A1, widened) | every independent stack install and amendment |
| `@Kravalg` | seed and stack reviews, BI and AGI PR approvals, every protected-environment apply, XP-A3 admin apply |
| Gateway owner | G0.1, the certificate hand-offs (XP-A8), PR #34 amendment coordination |
| USI owner | XP-A7 descriptors; pinning the gateway ARNs (USI XP-10, XP-15); XP-A14 campaign coordination; the USI-side S4.6 reorder under OQ-8 (c) |
| User | OQ-1…OQ-8, XP-A10 endpoints, per-action authorizations |

## Skill applicability (devops-sdlc)

| Skill | Applies to |
| --- | --- |
| python-pulumi | G3.1, G4.x, G5.x, G6.x |
| security-iam | G1.x, AD-A7 |
| drift-management | G3.5, G6.3 |
| delivery-and-rollback | G3.4, AD-A12, G5.7-G5.8 |
| observability | G5.2 |
| cost-optimization | NFR-A07, AD-A6 |
| infrastructure-quality | G3.2, G3.3 |
| evidence-and-coverage | G5.6, G6.3 |
| environment-lifecycle | G3.4 `initialize-stack`, OQ-5, AD-A15 feature flags |
| state-migration | not applicable (new backend; OQ-5 decides any legacy state) |
| backup-recovery | PD-6 rebuild; G5.7-G5.8 under OQ-8 (a) |
| incident-response | runbooks (NFR-A10) |
| terraform-terraspace | not applicable |

## Pre-commit audit (fresh context, `claude-router:audit`)

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
