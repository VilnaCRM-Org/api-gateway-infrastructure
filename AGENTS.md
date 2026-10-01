# AGENTS

Repo-local rules for `api-gateway-infrastructure`, the Pulumi program for the VilnaCRM API gateway. Humans and agents MUST follow them. They mirror the governance posture of `user-service-infrastructure` and the central governance stack in `bootstrap-infrastructure`.

## Working rules

1. Make the smallest change that satisfies the task; preserve the local Docker workflow (`make start`, `make sh`).
2. Run the narrowest useful validation for the files you touched. All tests, including the workflow and hygiene checks: `make test` (`uv run --frozen pytest` in the development image). The lockfile check is `make test-lockfile`. The PR quality battery is `make test-battery` (one target per required check; see README "PR quality battery"). PyYAML is a locked dependency; the tests fail (never skip) when it is missing.
3. Use `pulumi -C pulumi ...` for direct Pulumi CLI commands, and only against a stack the task names.
4. Prefer Make targets and Python helpers over new bash scripts for CI orchestration.

## Hard rules

### 1. No IAM

Do NOT add `aws.iam.Role`, `aws.iam.Policy`, `aws.iam.RolePolicy`, `aws.iam.OpenIdConnectProvider`, `aws.apigateway.Account` or any `assume_role_policy` / `sts:AssumeRoleWithWebIdentity` trust to this repository's Pulumi program, and no `aws:iam/*` resource of any kind.

Role ownership (D-A1, D-A9, D-A11):
- The bootstrap-infrastructure (BI) independent seed creates this repository's roles, through a reviewed seed catalog amendment installed by the human seed operator.
- The central governance stack owns the identity grants, the Pulumi backend and the KMS key, and applies them through the dedicated governance Apply role `GitHubGovernanceApply-api-gateway-infrastructure-{env}`.
- This repository references the roles by ARN through stack config or environment variables and never redefines them.

### 2. OIDC only

All AWS credentials in CI come from GitHub OIDC role assumption. Never commit or wire (except the AD-A15 `ci` stack, rule 3) a static AWS access key, a Pulumi access token, a passphrase, a personal access token or a GitHub App private key. Workflows use only the job's short-lived `GITHUB_TOKEN`, at the least permission the job needs (`contents: read` on every pull-request job). Locally, use SSO only (see README). Never request or attach `AdministratorAccess`.

### 3. Stack-config pins

Account IDs, role ARNs, the Pulumi backend URL, the secrets provider and the region live in stack config and repository environment variables, never in Python program code. Each stack pins only its own account. Every `uses:` in a workflow is pinned to a 40-hex commit SHA.

Exception: the offline `ci` stack (AD-A15) and nothing else. It runs the Structural Preview on a local file backend with no credentials, so it may use dummy static keys (`pulumi-preview`) with `skip_credentials_validation`, `skip_metadata_api_check`, `skip_requesting_account_id` and `skip_region_validation`, and a committed `encryptionsalt` with a fixed non-secret passphrase. The `test` and `prod` stacks reject these settings, and the config loader fails if they appear there.

### 4. Saved plans

Applies run only from a saved plan that was previewed, uploaded as an artifact and re-checked by SHA-256 before `pulumi up --plan`. Never run a direct `pulumi up` in CI.

### 5. TEST before PROD

Every change reaches the TEST environment first. A PROD apply requires a successful TEST apply of the same head SHA.

### 6. Kravalg-gated

`.github/CODEOWNERS` assigns `* @Kravalg`. `@Kravalg` is the sole reviewer of the `test` and `prod` environments. Do not weaken CODEOWNERS, rulesets or environment protections, and do not self-approve.

### 7. No destructive override

A Pulumi diff that deletes or replaces a resource blocks the pipeline. Do not add an override label, flag or input that bypasses that block.

The one reviewed exception (AD-A10, FR-A11): replacing `aws:apigateway/deployment:Deployment` is allowed only as a create-before-delete in a plan where the stage moves to the new deployment. Nothing else is exempt.

### 8. No SSM reads or writes

This repository neither reads nor writes SSM parameters (D-15). Do not add `aws:ssm/*` resources or `ssm:GetParameter*` / `ssm:Put*` calls, and publish nothing in SSM. The gateway certificate ARN is a reviewed contract pin, checked only with `acm:DescribeCertificate`.

## Secret handling

1. Never read, print, summarize, diff or copy raw secret material.
2. Off limits unless the task is explicitly secret management: `.env`, `.env.*`, AWS shared credentials and config files, access keys, session tokens, Pulumi stack files containing `secure:` values, GitHub Actions secrets, private keys and token files.
3. Never run commands that reveal secrets: `env`, `printenv`, `docker compose config`, `docker inspect`, `pulumi config --show-secrets`, `pulumi stack output --show-secrets`.
4. Prefer metadata-only checks such as `aws sts get-caller-identity`, `pulumi stack ls` and `pulumi config` without secret-revealing flags.
5. Never commit secret values, decrypted outputs, stack exports or temporary files that contain them.
