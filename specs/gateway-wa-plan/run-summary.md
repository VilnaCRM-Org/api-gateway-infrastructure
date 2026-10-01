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
| Bundle revision | 2 (user decisions D-A1…D-A8 of 2026-10-01; revision 1 is commit `3d511f1`) |
| Specs directory | `specs/gateway-wa-plan/` |
| Target | pulumi (Python Pulumi), stacks test and prod |
| Environment | none selected; planning is offline |
| Date (UTC) | 2026-10-01 |

## Tooling

| Item | Result |
| --- | --- |
| bmalph | 2.11.0 (`~/.local/bin/bmalph --version`) |
| BMAD workflows | read from `wt-usi-hardening/_bmad` (`_bmad/COMMANDS.md` sha256 `da2f78200b2b0a77e4a6db87a6f30de55200fb7494b697301e72387e1757c722`, the same file the USI run used). `bmalph init` was **not** run in this worktree, so that only `specs/` changes; no `_bmad/`, `.ralph/`, `bmalph/` or `CLAUDE.md` was created. |
| devops-sdlc profile | absent for this repository (XP-A13) |

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
- **SDK:** `pulumi_aws` 7.23.0 in `wt-boot-219/.venv` (grep of
  `apigateway/integration.py`, `domain_name.py`, `rest_api.py`).
- **AWS documentation** (aws-knowledge MCP, 2026-10-01): the pages listed
  in research §5 (GA-1…GA-17).
- **Subagents (read-only):** two `claude-router:recon` agents (BI
  enrolment; pipeline pattern). Their claims used in the bundle were
  re-read at the cited lines; one claim was corrected (the BI recon said
  the governance runbook needs only a catalog entry; GR-12 shows the seed
  guards block it).

## Artifacts (sha256, revision 2)

`run-summary.md` is not hashed here, because it contains the hashes. Check
with `sha256sum -c` over the block below, from `specs/gateway-wa-plan/`.

```
14846a596346622c53e40a2372ad256bd909f283f197b19b205df5d9eef9403e  research.md
8810238e1348dc8ab0a8cb3e4f76bc190a828202708f5d35b15f87a2dfd2f939  brief.md
039f7a292d973c5a58b4aa1d7d4a49d600e09472e8b73a70a7e9b276df445b96  prd.md
5f56fc5e68292e541018b742a37b9c9608e9d7314081a3676c53dbfbc32be189  architecture.md
fe22fd3180a7f5840ecbd10b0ab4ec5bca48c1d47f33ccc2e170d5591e3ad58f  epics-stories.md
ad392338c3377c28a7de2591296e0aebc73fd698b55af6e980bb2e9a3d044d7f  decisions.md
cbec463c33e10e16d43b85805ef3f20825c66faa190335fc697a346c44778b57  readiness.md
```

## Gates

| Gate | Result |
| --- | --- |
| Self-check (readiness.md) | complete; not a PASS |
| Revision 1 pre-commit audit and recheck | REFUTED, then REFUTED narrowly; all findings folded into `3d511f1` (readiness.md, "Revision 1 audit history") |
| Revision 2 pre-commit audit (`claude-router:audit`) | REFUTED narrowly: 2 major, 2 minor, 4 nits; all folded in |
| Revision 2 recheck | REFUTED narrowly: 7 of 8 fixed, #2 partly; new N1 (minor), N2-N3 (nits); all folded in; no third round |
| Independent readiness round | not run yet |

## Report summary

- **Decisions recorded:** D-A1…D-A8 (2026-10-01), gateway-local namespace.
  They answer OQ-1…OQ-8.
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
- **Open user questions:** OQ-9 (the writer of the gateway's grants and
  non-role BI resources) and OQ-10 (ConfigRead roles). Cross-plan request
  to USI: CR-A1.
