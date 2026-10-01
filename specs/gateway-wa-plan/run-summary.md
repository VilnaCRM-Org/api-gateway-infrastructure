# Run summary: BMAD planning, gateway-wa-plan

This file is the execution ledger. It is not a planning input.

## Identity and scope

| Field | Value |
| --- | --- |
| Task | The API gateway Well-Architected track (USI S5.16 expanded) |
| Repository | VilnaCRM-Org/api-gateway-infrastructure |
| Worktree | wt-agi-plan |
| Branch | feat/gateway-wa-plan |
| Source baseline | f056c8b32c64e502101ec573191d8f229881bc7a (origin/main) |
| Bundle revision | 5 (readiness round 1 at `3913ccb`: FAIL; F1-F13 resolved; revisions 1 `3d511f1`, 2 `d5007b3`, 3 `d775081`, 4 `3913ccb`) |
| Specs directory | `specs/gateway-wa-plan/` |
| Target | pulumi (Python Pulumi), stacks test and prod |
| Environment | none selected; planning is offline |
| Date (UTC) | 2026-10-01 |

## Tooling

| Item | Result |
| --- | --- |
| bmalph | 2.11.0 (`~/.local/bin/bmalph --version`) |
| BMAD workflows | read from `wt-usi-hardening/_bmad` (`_bmad/COMMANDS.md` sha256 `da2f78200b2b0a77e4a6db87a6f30de55200fb7494b697301e72387e1757c722`, the same file the USI run used). `bmalph init` was **not** run in this worktree, so that only `specs/` changes; no `_bmad/`, `.ralph/`, `bmalph/` or `CLAUDE.md` was created. |
| devops-sdlc profile | absent for this repository (XP-A13); `attempts.json` absent (no implementation attempt recorded) |

## Scope limits

- No `aws` or `pulumi` command ran against any account.
- No `.env` file and no `~/.aws` file was read. No secret value was read.
- No repository test, lint or preview ran; this was analysis only.
- Nothing was pushed, commented, closed or merged. No AGI source, BI or USI
  file was changed.
- Revision 2 edited only `specs/gateway-wa-plan/`. The BI worktrees were
  read only.

## Inputs

- **This repository** at `f056c8b`: the whole tree (research GR-1, GR-2).
  PR #34 read with `git show origin/feat/test-user-service-gateway:<path>`
  after `git fetch origin` (head `cd8f790`). PRs #26, #32, #33, #34
  metadata with `gh pr view … --json` and `gh pr list`. Repository
  metadata, rulesets, `rules/branches/main`, branch protection,
  environments and CODEOWNERS with `gh api` GET on 2026-10-01 (GR-3); the
  Actions-permissions GET returned 403 and is not used.
- **USI** (`wt-usi-hardening`, HEAD `0721d93`; bundle commit `9d5df4a`):
  `specs/workload-wa-hardening/` (`decisions.md` whole, sha256
  `86df7c4f…`; `brief.md` whole; `run-summary.md` whole; `prd.md` §1, §7
  lines 355-486 and 684-817; `architecture.md` §2 lines 34-92, AD-26
  lines 1631-2060 in part, V-10 line 2919; `epics-stories.md` Epic 5
  preamble lines 3531-3725 in part, S4.6 steps 15-18 lines 2840-2870,
  S4.7 lines 3436-3446, the ordered list lines 3759-3870; `research.md`
  §2.4-§4); `specs/poc-api-gateway-backend.md` (whole, sha256
  `6cd1b9ac…`); `scripts/poc_gateway_backend.py` (whole, sha256
  `5410ad7d…`); `Makefile` lines 38-42; `scripts/_github_repository_controls.py`
  lines 10-45; `scripts/pulumi_ci_guardrails.py` lines 1-30;
  `.github/workflows/self-deploy.yml` lines 1-12;
  `.github/workflows/pulumi-pr-commands.yml` lines 1-30; the workflow list;
  `pyproject.toml` line 6.
- **BI** (`wt-boot-urllib3` `862b4bf` ≈ `origin/main` `bea5252`):
  `AGENTS.md` lines 30-130; `docs/governance-stack.md` lines 60-100;
  `pulumi/repositories.bootstrap.json`, `repositories.governance.json`
  (whole); `pulumi/infra/ci_bootstrap.py` lines 295-375 and 700-770;
  `pulumi/infra/governance.py` lines 360-412 and 478-520;
  `pulumi/infra/github_identity.py` lines 31-69; `pulumi/seed/README.md`
  lines 1-40; `pulumi/seed/policy_registry.py` lines 15-24 and greps;
  `pulumi/seed/catalogs/test.json` lines 596-616 and read-only Python over
  the principals and the `dc27f076…`, `8c068aaa…`, `8f75c4a5…` and
  `G-GitHubGovernanceApply` statements; `prod.json` principals (Python).
  `wt-boot-pr280` and `wt-boot-219`: commit identity only (their facts
  enter through the USI bundle's citations).
- **Revision 2, BI seed route (D-A1), read only:**
  - `wt-boot-urllib3` (origin/main proxy, `862b4bf`):
    - `pulumi/seed/README.md` (whole);
    - `pulumi/seed/policy_registry.py` (whole);
    - `scripts/operator_seed_installation.py` (lines 1-30, 104-130, and
      the function list);
    - `pulumi/infra/governance.py` (lines 414-517, 540-700);
    - `pulumi/infra/ci_config.py` (lines 202-330);
    - `pulumi/infra/ci_bootstrap.py` (lines 347-390);
    - `docs/ci-config-trust-contract.md` (lines 1-30);
    - read-only Python over both seed catalogs: principals, policy kinds,
      operator bindings, and the statements of the USI guards and of
      `G-GitHubGovernanceApply`.
  - `wt-boot-pr280` (#284, `e85534c`):
    `specs/test-poc-prerequisite-capability/amendment-installation.md`
    (whole), `requirements.md` (lines 1-80), and `post-seed-activation.md`
    (lines 105-125 and a grep).
  - `wt-boot-219` (#285, `54e9e2f`):
    `specs/219-test-workload-capability/installability-stop.md` (whole) and
    a grep of `runtime-enrollment.md`.
  - Two read-only `claude-router:recon` agents summarized #284 and #285.
    Every claim used was re-read at the cited lines, and one claim was
    corrected: the #285 recon recommended an independent stack, which D-A1
    rejects as the route.
- **Revision 5, readiness round 1 (all read only):**
  - BI `wt-boot-urllib3` (origin/main proxy for `bea5252`):
    - `pulumi/infra/pulumi_state.py` lines 255-275 (replica names);
    - `pulumi/infra/governance_automation.py` lines 266-272;
    - `pulumi/infra/governance.py` lines 965-975 and 1030-1037;
    - `pulumi/governance/Pulumi.test.yaml` lines 15-25;
    - `pulumi/infra/bootstrap_infrastructure.py` lines 18-30;
    - `pulumi/infra/logging_bucket.py` (function list);
    - `AGENTS.md` lines 95-105;
    - `tests/unit/test_poc_installation_boundary.py` lines 60-80;
    - a grep of the count pins in `scripts/operator_seed_installation.py`.
  - USI `wt-usi-hardening`:
    - `specs/workload-wa-hardening/architecture.md` lines 2762-2778 (the
      C-BI seed order);
    - the ordered rows 8-43 and lines 2900-2908 of `epics-stories.md`;
    - `.github/workflows/pulumi-pr-guardrails.yml` lines 25-40.
  - Sizes were re-rendered with `evidence/render_governance_sizes.py`
    from `wt-boot-urllib3/pulumi` and `wt-boot-pr280/pulumi`.
- **SDK:** `pulumi_aws` 7.23.0 in `wt-boot-219/.venv` (grep of
  `apigateway/integration.py`, `domain_name.py`, `rest_api.py`).
- **AWS documentation** (aws-knowledge MCP, 2026-10-01): the pages listed
  in research §5 (GA-1…GA-17).
- **Subagents (read-only):** two `claude-router:recon` agents (BI
  enrolment; pipeline pattern). Their claims used in the bundle were
  re-read at the cited lines; one claim was corrected (the BI recon said
  the governance runbook needs only a catalog entry; GR-12 shows the seed
  guards block it).

## Artifacts (sha256, revision 5)

`run-summary.md` is not hashed here, because it contains the hashes. Check
with `sha256sum -c` over the block below, from `specs/gateway-wa-plan/`.

```
046e8421d35ab03f49a6be8d80923347404e1482637d9866b139608e8374c0ad  research.md
387039d33cd78c13a33a4b72e51e50362d9f0971f801cbbf0c5d6552188f3b22  brief.md
09eb1cffc76ce52878b0821a434dd039419f3243d125613abc02887901544539  prd.md
a9927a2057beb19e92c9f2023243bde0c69a56db6fc8080c50f3d0f5f68d5e5e  architecture.md
1cdc6aed0bc6cfdc5dab8ca808bfeb98dd81631a6728fc4319adf9edfaa6eb64  epics-stories.md
a67bfe73d858c7eb6b47308ae0dd2bd97acd1e21238fa0e228ad436e95b0ca8c  decisions.md
5294fd53ed1bf8132b539b764c6dd8eef55c902edc638e28bc90a18d0e621428  readiness.md
9c70e4768a4771214a165df308ccb501e8432397d3552d3cf9bcee7f7d5ed981  evidence/render_governance_sizes.py
```

## Gates

| Gate | Result |
| --- | --- |
| Self-check (readiness.md) | complete; not a PASS |
| Revision 1 pre-commit audit and recheck | REFUTED, then REFUTED narrowly; all findings folded into `3d511f1` (readiness.md, "Revision 1 audit history") |
| Revision 2 pre-commit audit (`claude-router:audit`) | REFUTED narrowly: 2 major, 2 minor, 4 nits; all folded in |
| Revision 2 recheck | REFUTED narrowly: 7 of 8 fixed, #2 partly; new N1 (minor), N2-N3 (nits); all folded in; no third round |
| Revision 3 pre-commit audit (`claude-router:audit`) | REFUTED: 1 major (governance Apply ceiling cannot hold the exact-ARN admission → OQ-11, V-A12), 3 medium, 1 minor; all folded in |
| Revision 3 recheck | REFUTED narrowly: 4 of 5 fixed, #4 partly; new N1 (minor), N2 (nit); all folded in; no third round |
| Revision 4 pre-commit audit (`claude-router:audit`) | REFUTED: 1 major (lock deny outside `governance/`), 2 medium, 2 low, 1 nit; all folded in |
| Revision 4 recheck | REFUTED narrowly: 5 of 6 fixed, #4 partly; new N1 (medium, apply-role wiring); folded in; no third round |
| Independent readiness round 1 (on `3913ccb`, BI baseline `bea5252`) | FAIL: 3 major, 5 medium, lows, nits, 1 process; resolved in revision 5 |
| Revision 5 pre-commit audit (`claude-router:audit`) | REFUTED narrowly: 3 P2, 2 P3, 4 nits; all folded in |
| Revision 5 recheck | REFUTED narrowly: 2 of 6 fixed, 4 partly (apply mechanism per BI runner, row-8 cross-plan order, exact-ARN wording, ci provider in PRD); all folded in; no third round |
| Independent readiness round | not run yet |

## Report summary

- **Decisions recorded:** D-A1…D-A11 (2026-10-01), gateway-local namespace.
  They answer OQ-1…OQ-11. Revision 4 adds D-A11 (a dedicated, seed-created
  governance Apply role for the gateway; USI's governance Apply ceiling and
  guard untouched). Revision 3 adds D-A9 (governance owns the
  gateway's grants, backend, CMK and account settings after an exact-ARN
  seed admission) and D-A10 (no ConfigRead roles).
- **Epics:**
  - E-G0 dispositions (G0.1, G0.2);
  - E-G1 BI enrolment by the seed registration route (G1.1 packet, G1.2
    install, activation and pin, G1.3, G1.4a, G1.5, G1.6, G1.4b, G1.7,
    G1.8);
  - E-G2 repository hygiene and controls (G2.1, G2.2);
  - E-G3 pipeline (G3.1-G3.5);
  - E-G4 certificates (G4.1 = PR #34 amended, G4.2 for
    `user.vilnacrm.com`);
  - E-G5 TEST front door (G5.1-G5.6);
  - E-G6 PROD front door (G6.1-G6.3).
- **Ordered list:** 33 rows (0-32), no forward dependency. Revision 1's
  OQ-8 (a)-only rows 26-28 are removed.
- **External preconditions:** XP-A1…XP-A14 (gateway-local namespace).
  XP-A1 is now the human seed operator; XP-A11 is resolved to "the zone
  exists, or is created, in the PROD account".
- **Open user questions:** none. Cross-plan request to USI: CR-A1.
- **Counts per environment:** 30 principals, 9 seed-created, 67 seed
  policies. Measured sizes (`evidence/render_governance_sizes.py`):
  dedicated governance Apply ceiling 5737, its identity 5737, its guard
  5198, shared Preview/Drift ceilings 5419/5429 (TEST/PROD), all ≤ 6144
  (revision 5).
