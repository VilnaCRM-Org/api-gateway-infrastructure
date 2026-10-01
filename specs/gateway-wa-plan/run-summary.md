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
| Bundle revision | 9 (readiness round 5 at `2c949ab`: PASS, 5 low, 2 nits; all folded in; revisions 1 `3d511f1`, 2 `d5007b3`, 3 `d775081`, 4 `3913ccb`, 5 `7ed5397`, 6 `854b7c4`, 7 `7e644b7`, 8 `2c949ab`) |
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

## Artifacts (sha256, revision 9)

`run-summary.md` is not hashed here, because it contains the hashes. Check
with `sha256sum -c` over the block below, from `specs/gateway-wa-plan/`.

```
cdc3398b76e67d94ea93086042726ed9243b55e1040560d1282d00546b869e92  research.md
72e63cd812cfdb91f410b5d95c495b3771d6fd6acf89a553abf5c59667645cd3  brief.md
7ce58e234665b4397aa9ab5a0479a1bcc7f1897004bb3865fd5d8eae719de820  prd.md
e12660518f23ae5ae7150a200053c3ff76be94d9dd7d1030a7a5a1373d2418d3  architecture.md
5d7eed9aad688513b750849c9c48d046632321a8648b24b59ad29091f9f44e8b  epics-stories.md
24121d717b52b6a5e6df26a78cba476c14fca48f129275c2700731ed606f590b  decisions.md
ff31aadcc07dcab789903c439b3bb48e45dfd3ec5de1a741f2a10d660f9e79c9  readiness.md
058f758e472220a021b5926821fa9298bdd3a79571bba8437af2934b2701065c  evidence/render_governance_sizes.py
8a41f9db591cfbfe6ec9e9c1669e29cd43e44bbeda01c5a419d497e0508766dc  evidence/check_ordered_list.py
03f155c8ed6ff3f5c4d6d3c153de3435c55a9260464ebcde3bf66cb228ffbed7  evidence/dedicated-apply-ceiling-A-prod.json
9d3d9561e3da26d421654c973ab4127bfeb170da37729c4f7b0ee6b29b596e52  evidence/dedicated-apply-ceiling-A-test.json
349d2ce3563532c570e66fc13abcfe2b634ccaeca700e1f07feee50d07d5596b  evidence/dedicated-apply-ceiling-B-prod.json
779c16232a0596aeeb422ac714fe75504c49a6993777ca2704faab5ab7c23546  evidence/dedicated-apply-ceiling-B-test.json
337e0550335935e3ddbca22132f9743cc7ae8d7d6d6f07668beb7926172de514  evidence/dedicated-apply-guard-prod.json
5f0048591328484f2b37d8eb1810f9bd8dca747817b4b038128e5f78563a6cd8  evidence/dedicated-apply-guard-test.json
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
| Independent readiness round 2 (on `7ed5397`) | FAIL: no major, 6 medium, 12 low; user decisions D-A12, D-A13 and acknowledgement D-A14; resolved in revision 6 |
| Revision 6 pre-commit audit (`claude-router:audit`) | REFUTED narrowly: 2 P2, 3 P3, 5 P4; all folded in |
| Revision 6 recheck | REFUTED narrowly: 5 of 6 fixed, #2 partly; new N1 (P3, init session policy), N2 (P4); folded in; no third round |
| Independent readiness round 3 (on `854b7c4`) | FAIL: 1 medium (branch-B forward dependency), 5 low, 5 nits; resolved in revision 7 |
| Revision 7 audit (`claude-router:audit`) | REFUTED narrowly: 3 P3, 3 P4; all folded in |
| Revision 7 recheck | REFUTED narrowly: 5 of 6 fixed, #1 partly; new N1 (P3, contingency delete), N2 (P4), 2 nits; all folded in; no third round |
| Independent readiness round 4 (on `7e644b7`) | FAIL: 2 medium (branch-B log-group lookup and forward dependency; contingency outside CI), 2 low, 3 nits; resolved in revision 8 |
| Revision 8 audit (`claude-router:audit`) | REFUTED narrowly: 3 P3, 6 P4; all folded in |
| Revision 8 recheck | REFUTED narrowly: 5 of 9 fixed, 3 and 7 partly, 9 with a gap, 4 expected; new NEW-1 (P3, re-pin PR), NEW-2 and NEW-3 (P4); all folded in; no third round |
| Independent readiness round 5 (on `2c949ab`) | PASS: 5 low (R5-1…R5-5), 2 nits; folded in in revision 9 |
| Revision 9 targeted recheck (`claude-router:audit`, round-5 items only) | REFUTED narrowly: 4 of 7 fixed, 3 partly; new NEW-1 (P3, protect mock test), NEW-2…NEW-6 (P4); all folded in; no second recheck |

## Report summary

- **Decisions recorded:** D-A1…D-A14 (2026-10-01), gateway-local namespace.
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
- **Ordered list:** 36 rows (0-32 with 21a and 31a-31c, revision 9), no forward dependency under either D-A12 branch (scripted check). Revision 1's
  OQ-8 (a)-only rows 26-28 are removed.
- **External preconditions:** XP-A1…XP-A14 (gateway-local namespace).
  XP-A1 is now the human seed operator; XP-A11 is resolved to "the zone
  exists, or is created, in the PROD account".
- **Open user questions:** none. Cross-plan requests to USI: CR-A1 and CR-A2.
- **Counts per environment:** 30 principals, 9 seed-created, 67 seed
  policies. Measured sizes (`evidence/render_governance_sizes.py`):
  dedicated governance Apply ceiling and identity 5830 (D-A12 branch A) /
  6095 (branch B), its guard 5565, shared Preview/Drift ceilings
  5387/5397 (branch A) or 5419/5429 (branch B) (TEST/PROD), all ≤ 6144
  (revision 9).
