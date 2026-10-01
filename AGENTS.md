# AGENTS

Repo-local rules for `api-gateway-infrastructure`, the Pulumi program for the VilnaCRM API gateway. Humans and agents MUST follow them. They mirror the governance posture of `user-service-infrastructure` and the central governance stack in `bootstrap-infrastructure`.

## Working rules

1. Make the smallest change that satisfies the task; preserve the local Docker workflow (`make start`, `make sh`).
2. Run the narrowest useful validation for the files you touched. Workflow and hygiene checks: `python3 -m unittest discover -s tests -v`.
3. Use `pulumi -C pulumi ...` for direct Pulumi CLI commands, and only against a stack the task names.
4. Prefer Make targets and Python helpers over new bash scripts for CI orchestration.

## Hard rules

### 1. No IAM

Do NOT add `aws.iam.Role`, `aws.iam.Policy`, `aws.iam.RolePolicy`, `aws.iam.OpenIdConnectProvider` or any `assume_role_policy` / `sts:AssumeRoleWithWebIdentity` trust to this repository's Pulumi program. The deploy roles are owned by the central governance stack; reference them by name or ARN through stack config and never redefine them.

### 2. OIDC only

All AWS credentials in CI come from GitHub OIDC role assumption. Never commit or wire a static AWS access key, a Pulumi access token, a passphrase, a personal access token or a GitHub App private key. Workflows use only the job's short-lived `GITHUB_TOKEN`, at the least permission the job needs (`contents: read` on every pull-request job). Locally, use SSO only (see README). Never request or attach `AdministratorAccess`.

### 3. Stack-config pins

Account IDs, role ARNs, the Pulumi backend URL, the secrets provider and the region live in stack config and repository environment variables, never in Python program code. Each stack pins only its own account. Every `uses:` in a workflow is pinned to a 40-hex commit SHA with the tag in a trailing comment.

### 4. Saved plans

Applies run only from a saved plan that was previewed, uploaded as an artifact and re-checked by SHA-256 before `pulumi up --plan`. Never run a direct `pulumi up` in CI.

### 5. TEST before PROD

Every change reaches the TEST environment first. A PROD apply requires a successful TEST apply of the same head SHA.

### 6. Kravalg-gated

`.github/CODEOWNERS` assigns `* @Kravalg`. `@Kravalg` is the sole reviewer of the `test` and `prod` environments. Do not weaken CODEOWNERS, rulesets or environment protections, and do not self-approve.

### 7. No destructive override

A Pulumi diff that deletes or replaces a resource blocks the pipeline. Do not add an override label, flag or input that bypasses that block.

### 8. No SSM writes

This repository reads configuration and never writes SSM parameters or any secret store. Do not add `aws.ssm.*` resources or `ssm:Put*` calls.

## Secret handling

1. Never read, print, summarize, diff or copy raw secret material.
2. Off limits unless the task is explicitly secret management: `.env`, `.env.*`, AWS shared credentials and config files, access keys, session tokens, Pulumi stack files containing `secure:` values, GitHub Actions secrets, private keys and token files.
3. Never run commands that reveal secrets: `env`, `printenv`, `docker compose config`, `docker inspect`, `pulumi config --show-secrets`, `pulumi stack output --show-secrets`.
4. Prefer metadata-only checks such as `aws sts get-caller-identity`, `pulumi stack ls` and `pulumi config` without secret-revealing flags.
5. Never commit secret values, decrypted outputs, stack exports or temporary files that contain them.
