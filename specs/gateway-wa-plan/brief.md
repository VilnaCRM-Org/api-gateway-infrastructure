---
artifact: product-brief
workflow: _bmad/bmm/workflows/1-analysis/bmad-create-product-brief (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 2 (2026-10-01: user decisions D-A1…D-A8 recorded)
inputDocuments: [research.md, decisions.md, USI specs/workload-wa-hardening (commit 9d5df4a), USI specs/poc-api-gateway-backend.md]
---

# Product brief: the API gateway Well-Architected track

## Vision

The user-service is reachable from the internet only through this
repository's front door:

- a Regional **REST API** on a custom domain with TLS 1.2 or later;
- an **AWS WAF** web ACL on its stage, with managed rule groups and
  per-IP rate limits;
- a **private integration over a VPC link V2** straight to the USI internal
  ALB, which has no other ingress;
- stage throttling, KMS-encrypted access and WAF logs, alarms to an owned
  topic;
- deployed only by GitHub PR ChatOps with OIDC roles and saved plans, TEST
  before PROD, behind `@Kravalg`'s protected environments, and checked for
  drift every day.

This is user decision D-3 (REST API + WAF + VPC link to the internal ALB),
delivered as its own governed track instead of the single USI story S5.16.

## Problem

- **The repository is a bare template** (research GR-1, GR-2). It deploys an
  example bucket, uses a passphrase secrets provider, has no deploy, preview
  or drift workflow, runs a linter that cannot fail, pushes auto-fixes to PR
  heads with an App token, and syncs from a PHP template with a personal
  access token.
- **Nothing guards `main`** (GR-3). No branch ruleset, no CODEOWNERS, no
  environments.
- **It is not enrolled in bootstrap** (GR-9). It has no OIDC roles, no
  state bucket and no KMS key, and the documented enrolment route is
  blocked by the seed guards (GR-12).
- **The USI plan waits on it.** USI gate 1 needs the gateway's TEST
  certificate ARN (USI XP-10, D-15) and the TEST route's evidence (USI S4.6
  step 17). USI gate 2 needs the PROD certificate ARN (USI XP-15).
- **Open PRs are stale or conflict with decisions**: PR #34 publishes the
  certificate ARN to SSM, which D-15 made unused; three dependabot PRs fail
  or target a provider line too old for VPC link V2 (GR-5).

## Users and stakeholders

| Actor | Need |
| --- | --- |
| Gateway owner (this repository; PR #34 author `@dmytrocraft`) | A governed, testable path to ship the front door. |
| Governance owner `@Kravalg` (BI CODEOWNERS, protected environments) | Reviewable IAM, seed and repository-control changes; sole approver of every apply. |
| BI owner and seed operator | Enrolment work that fits the seed's one-open serialization and loosens no guard. |
| USI owner | The certificate ARN on time, and a route that reaches only the internal ALB through the USI-owned VPC-link security group. |
| End users | A TLS-protected, rate-limited, WAF-filtered endpoint. |
| AI implementation agents | File-scoped stories with offline tests and no access to secrets. |

## Success metrics

1. **Enrolled, least-privilege CI.** Gateway Preview, Apply and Drift roles
   exist per environment, trust only this repository's protected
   environments (no `pull_request` subject), and pass a simulator matrix
   that denies every action outside the gateway resources.
2. **Guarded `main`.** A ruleset requires the quality battery, the preview,
   the destructive-diff gate, the IAM gate, the policy pack and a code-owner
   review; the readback matches the reviewed definition.
3. **Saved-plan deploys only.** Every apply replays a plan saved for the
   exact PR head and approved by `@Kravalg`; PROD refuses a head without a
   successful TEST apply.
4. **TEST front door accepted (gate A-T).** Through `https://user.vilnacrmtest.com`:
   requests reach the service; WAF sampled requests and logs show the rules;
   a burst above the stage limit gets 429; TLS 1.1 is refused; the default
   `execute-api` endpoint returns 403; the ALB is unreachable from outside
   the VPC. The evidence closes USI S4.6 step 17.
5. **Certificates delivered.** The TEST ARN reaches USI before USI row 42
   (XP-11), the PROD ARN before USI row 49 (XP-15). Nothing is written to
   SSM.
6. **PROD front door accepted (gate A-P)** after USI gate 2, with the same
   checks.
7. **Daily drift is clean**, and the drift job's probe keeps the TEST VPC
   link active.

## Scope

**In scope:**

- BI: the gateway's enrolment the way USI is enrolled (D-A1): a reviewed
  seed catalog amendment that creates and registers the gateway roles,
  their boundaries and guards, installed by the human seed operator; the
  backend, the capability grants, the account-level API Gateway logging
  role and setting, the WAF log resource policy (D-A5) and the gateway CMK
  (D-A4), each by the BI owner that OQ-9 chooses.
- This repository: hygiene, repository controls, the governed pipeline,
  the certificate (PR #34 amended), the TEST and PROD front door, alarms,
  runbooks.
- The disposition of PRs #34, #33, #32 and #26.
- The PROD front door on `user.vilnacrm.com` (D-A3).

**Out of scope:**

- Any change to the USI workload (ALB, listener, security groups,
  descriptor code). A USI wording follow-up is recorded as USI-F1, not
  planned here.
- Running any `aws` or `pulumi` command against an account in this
  planning task.
- WAF Bot Control, Fraud Control or other paid managed rule groups (no user
  decision asks for them).
- CloudFront in front of the API (rejected in the USI options analysis:
  origin lock-down would need a shared header secret).

## Constraints

- D-3, D-6 and D-15 (decisions.md §2); D-A1…D-A8 (decisions.md §1).
- OIDC only; no long-lived keys or personal access tokens in CI.
- Saved-plan apply; TEST before PROD; `@Kravalg` as the sole approver of
  protected environments.
- No seed guard deny on Resource `*` is narrowed without a user decision
  (the USI AD-26 rule, reused).
- No IAM resource is declared in this repository's program.

## Assumptions

- **AS-1.** No live gateway resource that this plan needs to keep exists in
  either account. XP-A9 checks it; D-A6 retires any finding after an
  emptiness check.
- **AS-2.** The USI workload keeps the network contract of
  `specs/poc-api-gateway-backend.md`: internal ALB in two application
  subnets, HTTPS listener on 443 with the gateway certificate, ALB ingress
  only from the USI VPC-link security group.
- **AS-3.** The TEST public zone `vilnacrmtest.com`
  (`Z04999481RZ4UQK2NANVH`) stays in the TEST account and may hold the
  gateway's records (XP-A6).
