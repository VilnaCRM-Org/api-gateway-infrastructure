[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner2-direct.svg)](https://supportukrainenow.org/)

# Infrastructure template for modern DevOps applications

## Possibilities
- Modern stack for services: [Pulumi](https://www.pulumi.com)
- Built-in docker environment and convenient `make` cli command
- A lot of CI checks to ensure the highest code quality that can be (linters and other terraform related checks)
- Configured testing tools
- Much more!

## Why you might need it
Many DevOps engineers need to create new projects from scratch and spend a lot of time.

We decided to simplify this exhausting process and create a public template for modern infrastructures. This template is used for all our microservices in VilnaCRM.

## License
This software is distributed under the [Creative Commons Zero v1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/deed) license. Please read [LICENSE](https://github.com/VilnaCRM-Org/infrastructure-template/blob/main/LICENSE) for information on the software availability and distribution.

### Minimal installation
You can clone this repository locally or use Github functionality "Use this template"

Install the latest [docker](https://docs.docker.com/engine/install/) and [docker compose](https://docs.docker.com/compose/install/)

Use `make` command to set up project and automatically install all needed dependencies
> make start

Check [Getting started](https://www.pulumi.com/docs/iac/get-started/aws/review-project/) section to manage your infrastructure

That's it. You should now be ready to use infrastructure template!

## Using
You can use `make` command to easily control and work with project locally.

Execute `make` or `make help` to see the full list of project commands.

The list of the `make` possibilities:

```
build           Build the development image (pinned, checksum-verified tools).
clean           Remove containers, Python caches and coverage data.
down            Stop the development container.
help            Display the available Make targets.
sh              Open a shell in the running development container (after make start).
start           Build the image and start the development container.
test            Run every test under tests/ on the frozen lockfile.
test-actionlint Actionlint: workflow lint with shellcheck on every run script.
test-bandit     Bandit: security lint that also fails on stale or malformed nosec comments.
test-battery    Run every local battery check (CodeQL and Dependency Review run only on GitHub).
test-coverage   Coverage: every test under tests/ at 100% branch coverage (NFR-A09).
test-deps-security Dependency Audit: pip-audit of every package in the frozen uv.lock.
test-dockerfile Hadolint: Dockerfile lint.
test-lockfile   Fail when pyproject.toml and uv.lock disagree.
test-maintainability Maintainability: radon report, xenon complexity gate.
test-ruff       Ruff: lint and format check of every Python source and test.
test-secrets    Secrets Scan: gitleaks over every commit reachable from HEAD.
test-types      Types: ty static type check of the program, scripts and policy.
test-yaml       Yamllint: every YAML file, warnings fail.
test-zizmor     Zizmor: workflow security audit (offline audits).
up              Start the development container.
```
The Python toolchain is [uv](https://docs.astral.sh/uv/) with the frozen, hash-pinned `uv.lock` at the repository root (Python 3.11, `pulumi-aws` 7.23.0). The Pulumi program lives in `pulumi/`; its stacks are `test`, `prod` and the offline `ci` stack (AD-A15), and `pulumi/app/config.py` refuses any stack config outside that closed shape.

The `ci` stack runs the credential-free Structural Preview on a local file backend. It uses the `passphrase` secrets provider with an **intentionally empty, non-secret passphrase** (`PULUMI_CONFIG_PASSPHRASE=""`, as USI's `dev` stack does), and it holds no secret. Its account is the AWS documentation example account `123456789012`, never a real VilnaCRM account. `test` and `prod` refuse a passphrase provider and pin their own account, region, S3 backend and KMS key.

### PR quality battery (G3.2)

Every pull request, forks included, runs the AD-A11 battery checks with `permissions: contents: read` and no secret (FR-A08, FR-A10). Each job builds the development image (`make build`) and runs one Make target, so `make <target>` reproduces a check locally.

| Check (job name) | Workflow | Make target |
| --- | --- | --- |
| `Ruff` | `python-quality.yml` | `test-ruff` |
| `Types` | `python-quality.yml` | `test-types` |
| `Maintainability` | `python-quality.yml` | `test-maintainability` |
| `Coverage` | `python-quality.yml` | `test-coverage` |
| `Secrets Scan` | `security-scans.yml` | `test-secrets` |
| `Dependency Audit` | `security-scans.yml` | `test-deps-security` |
| `Bandit` | `security-scans.yml` | `test-bandit` |
| `Dependency Review` | `security-scans.yml` | GitHub only |
| `Actionlint` | `security-scans.yml` | `test-actionlint` |
| `Zizmor` | `security-scans.yml` | `test-zizmor` |
| `Yamllint` | `security-scans.yml` | `test-yaml` |
| `Hadolint` | `security-scans.yml` | `test-dockerfile` |
| `CodeQL (python)`, `CodeQL (actions)` | `codeql.yml` | GitHub only |

- **Coverage:** `coverage run -m pytest` over all of `tests/`, then `coverage report` with `fail_under = 100` and branch coverage on `pulumi/` and `scripts/` (`pyproject.toml`). G3.3 adds `policy/`; a test fails until it is listed.
- **Bandit:** `scripts/bandit_gate.py` also fails on bandit's `Test in comment` and `nosec encountered` warnings, on a `# nosec` that does not name rule ids, that is not on a one-line statement, or that suppresses nothing. No rule is skipped, except B101 (`assert`) in `tests/`.
- **CodeQL:** PR jobs cannot hold `security-events: write`, so `analyze` runs with `upload: never` and `scripts/codeql_sarif_gate.py` fails the job on any result in the SARIF output.
- **Zizmor:** `.github/zizmor.yml` requires a commit-SHA pin for every action (its default would let `actions/*` and `github/*` use a tag), so a tag pin fails `Zizmor` as well as the shape test (FR-A08). It runs offline. The online audits (`impostor-commit`, `ref-confusion`, `known-vulnerable-actions`, `stale-action-refs`) need a GitHub token, and PR jobs hold none. Instead, each SHA pin below was checked with `git ls-remote` against its upstream tag when it was written, and dependabot keeps them current.
- **Secrets Scan:** gitleaks over every commit reachable from `HEAD` (full-depth checkout).
- **Tools:** the Python tools are hash-pinned in `uv.lock`; actionlint, shellcheck, gitleaks and hadolint are version- and SHA-256-pinned in the `Dockerfile`.

Action pins (commit SHA, verified with `git ls-remote` on 2026-10-01):

| Action | Tag | Commit |
| --- | --- | --- |
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/dependency-review-action` | `v5.0.0` | `a1d282b36b6f3519aa1f3fc636f609c47dddb294` |
| `github/codeql-action/init`, `/analyze` | `v4.38.2` (annotated tag object `88585263c0627ee42c0e1c5143a112c8d6f4aa18`) | `2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2` |

### Program guardrails and G3.x hand-offs

`pulumi/app/config.py` also refuses a `Pulumi.yaml` with anything beyond `name`, `description` and `runtime: python` (no `main`, `stackConfigDir`, project `config:` or runtime options); every stack sets `pulumi:disable-default-providers: ["*"]`; only the literal YAML booleans `true`/`false` count as booleans; and `pulumi/__main__.py` fails unless the engine's config (`PULUMI_CONFIG`) equals the checked stack file's `config:` mapping. That refuses per-key `PULUMI_CONFIG_<KEY>` overrides and a `--config-file` whose config differs; it does not see a `--config-file` that changes only the top-level `secretsprovider`, `encryptionsalt` or `encryptedkey`, nor the backend in use (hand-off F09).

Recorded hand-offs from the G3.1 gate (attempt 1):

- **F02 (before G3.3 / G4.1):** install the `aws` resource plugin 7.23.0 in the image from a pinned URL with a verified SHA-256, so previews never download an unpinned plugin.
- **F06 (G3.4):** `test` and `prod` set `skip_metadata_api_check=False` (IMDS credential fallback, as USI does); harmless on GitHub-hosted runners, where the account pin still applies; reconsider if self-hosted EC2 runners are ever used.
- **F09 (G3.4):** workflows never pass `--config`, `--config-file` or `--secrets-provider`, and preflight checks that `PULUMI_BACKEND_URL` equals the stack's `pulumiBackendUrl` and that the stack's secrets provider equals `pulumiSecretsProvider`.
- **F07 (G3.2, done):** the 100% branch-coverage gate covers `scripts/` (and `policy/` once G3.3 adds it), and the G3.2 battery replaced the Poetry-era `pulumi/.flake8` and `pulumi/.pre-commit-config.yaml`.

## Documentation
Start reading at the [GitHub wiki](https://github.com/VilnaCRM-Org/infrastructure-template/wiki). If you're having trouble, head for [the troubleshooting guide](https://github.com/VilnaCRM-Org/infrastructure-template/wiki/Troubleshooting) as it's frequently updated.

If the documentation doesn't cover what you need, search the [many questions on Stack Overflow](http://stackoverflow.com/questions/tagged/vilnacrm), and before you ask a question, [read the troubleshooting guide](https://github.com/VilnaCRM-Org/infrastructure-template/wiki/Troubleshooting).

## Tests
[Test status](https://github.com/VilnaCRM-Org/infrastructure-template/actions)

If this isn't passing, is there something you can do to help?

## Local AWS access (SSO debugging only)

The container never receives static AWS keys: `docker-compose.yml` passes only `AWS_PROFILE` and `AWS_REGION`. For local debugging, sign in with IAM Identity Center (SSO) inside the container:

```
make start
make sh
aws configure sso
aws sso login --use-device-code
export AWS_PROFILE=<your-sso-profile>
```

SSO sessions are short-lived. Both the SSO configuration and the session live in the container's home directory, so they are lost when the container is recreated and you must configure and log in again. CI and deployments never use this path: they use GitHub OIDC roles only. Do not create or export long-lived access keys. See [AGENTS.md](AGENTS.md) for the repository rules.

## Releases

Pushes to `main` run `.github/workflows/autorelease.yml`, which derives the next version from conventional commits, then creates the tag and the GitHub release (generated notes) with the job's `GITHUB_TOKEN`. Below 1.0.0 a breaking change (`type!:` or a `BREAKING CHANGE:` footer) bumps the minor version, not the major. The version logic is `scripts/next_release_version.py`. The workflow does not commit to `main`, so `CHANGELOG.md` is no longer updated automatically; the GitHub releases page is the changelog.

## Security
Please disclose any vulnerabilities found responsibly – report security issues to the maintainers privately.

See [SECURITY](https://github.com/VilnaCRM-Org/infrastructure-template/tree/main/SECURITY.md) and [Security advisories on GitHub](https://github.com/VilnaCRM-Org/infrastructure-template/security).

## Contributing
Please submit bug reports, suggestions, and pull requests to the [GitHub issue tracker](https://github.com/VilnaCRM-Org/infrastructure-template/issues).

We're particularly interested in fixing edge cases, expanding test coverage, and updating translations.

If you found a mistake in the docs, or want to add something, go ahead and amend the wiki – anyone can edit it.

## Sponsorship
Development time and resources for this repository are provided by [VilnaCRM](https://vilnacrm.com/), the free and opensource CRM system.

Donations are very welcome, whether in beer 🍺, T-shirts 👕, or cold, hard cash 💰. Sponsorship through GitHub is a simple and convenient way to say "thank you" to maintainers and contributors – just click the "Sponsor" button [on the project page](https://github.com/VilnaCRM-Org/infrastructure-template). If your company uses this template, consider taking part in the VilnaCRM's enterprise support program.
