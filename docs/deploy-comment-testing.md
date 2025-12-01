# Testing the `/deploy` Comment Workflow

This guide walks through every requirement for exercising the `/deploy` GitHub comment workflow locally and on a pull request. Use it whenever you need to validate changes to `.github/workflows/deploy-on-comment.yml` or the helper scripts.

## Prerequisites

1. **Bootstrap infrastructure** – The `bootstrap-infrastructure` stack must already have:
   - The Pulumi S3 backend bucket for this repo, e.g. `s3://pulumi-api-gateway-infrastructure-test-state/state`.
   - The IAM role `arn:aws:iam::891377212104:role/PulumiDeploy-api-gateway-infrastructure` that GitHub Actions assumes via OIDC.
2. **Workflow files in scope** – Make sure your branch/PR includes:
   - `.github/workflows/deploy-on-comment.yml`
   - `.github/scripts/gate.py`, `authorize.py`, `deploy.py`, and `report.py`
3. **Pulumi passphrase and configs** – The stack targeted by `/deploy` must already contain any required configuration values (for this repo: `vilnacrm:region`, `vilnacrm:app_runner_url`) and share the same `PULUMI_CONFIG_PASSPHRASE` as the repo secret.

## GitHub Repository Settings

Set these **Repository Variables** (Settings → Secrets and Variables → Actions → *Variables*):

| Name | Example | Purpose |
| --- | --- | --- |
| `PULUMI_STACK` | `test` | Stack that `/deploy` selects before running Pulumi. |
| `AWS_REGION` | `eu-central-1` | Primary region for resources and CLI defaults. |
| `PULUMI_BACKEND_URL` | `s3://pulumi-api-gateway-infrastructure-test-state/state` | Matches the shared S3 backend created by bootstrap infra. |

Set these **Repository Secrets** (Settings → Secrets and Variables → Actions → *Secrets*):

| Name | Value |
| --- | --- |
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::891377212104:role/PulumiDeploy-api-gateway-infrastructure` |
| `PULUMI_ACCESS_TOKEN` | Pulumi service token (used for policy/metadata even with S3 state). |
| `PULUMI_CONFIG_PASSPHRASE` | Same passphrase used locally (stored at `pulumi/.pulumi-pass`). |
| `ALLOWED_DEPLOYERS` | Comma or newline list of GitHub usernames allowed to run `/deploy`. |

> Tip: keep `ALLOWED_DEPLOYERS` small (your test account + maintainers) while validating changes so the workflow only reacts to known people.

## Local Verification (optional but recommended)

1. Copy `.env.example` → `.env` and set:
   ```env
   PULUMI_STACK=test
   AWS_REGION=eu-central-1
   PULUMI_BACKEND_URL=s3://pulumi-api-gateway-infrastructure-test-state/state
   AWS_PROFILE=<profile that can assume PulumiDeploy role>
   AWS_SDK_LOAD_CONFIG=1
   ```
2. Log in to AWS (e.g. `aws sso login --profile <profile>` or ensure your source profile has valid STS creds).
3. Run:
   ```bash
   make pulumi-login
   STACK=test make pulumi-preview
   ```
   This mirrors what `/deploy` executes inside CI. Fix any errors before involving GitHub.

## Triggering `/deploy`

1. Push your branch and open a pull request (or use an existing PR/issue).
2. Post a **new** comment whose entire body is `/deploy`. The gate script ignores edits or additional text.
3. Watch the Actions tab:
   - `gate` job confirms the comment is exactly `/deploy`.
   - `authorize` job checks that the commenter is in `ALLOWED_DEPLOYERS` or already has `maintain/admin` rights.
   - `deploy` job assumes `AWS_ROLE_TO_ASSUME`, logs in to the S3 backend, selects `PULUMI_STACK`, and runs `pulumi up --stack <stack> --yes`.
   - `report` job posts the summarized plan/apply output back to the comment thread.

If a step fails, the workflow writes the reason to the job logs and (except for authorization failures) the `report` script posts an error reply in the same thread.

## Troubleshooting Checklist

- **“Missing config” errors** – Run `pulumi config set <key> <value> --stack <stack>` locally and ensure the same `PULUMI_CONFIG_PASSPHRASE` is available to GitHub (secret + stack config).
- **Role assumption failures** – Verify `AWS_ROLE_TO_ASSUME` matches the bootstrap role ARN and that the role trust policy allows the repo’s GitHub OIDC provider.
- **Comment ignored** – Make sure the comment body is exactly `/deploy` with no spaces or code blocks, and that it’s a fresh comment (not an edit).
- **Unauthorized commenter** – Add the username to `ALLOWED_DEPLOYERS` secret or grant `maintain/admin` repo privileges, then comment again.

Once all checks pass, `/deploy` is ready for collaborators to use confidently.
