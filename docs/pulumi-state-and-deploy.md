# Pulumi State & `/deploy` Workflow

This project stores Pulumi state in the S3 buckets that the `bootstrap-infrastructure` stack provisions and relies on a `/deploy` GitHub comment workflow for shared deployments. Use this document as the single source of truth for all required configuration.

## Remote State Buckets

- **Bucket naming:** `pulumi-<repo>-<stack>-state`. For this repo (`api-gateway-infrastructure`) the test bucket is `pulumi-api-gateway-infrastructure-test-state`. A matching replica bucket (`…-state-replication`) in `us-east-1` is created automatically for cross‑region replication.
- **Provisioning:** add the repo to `bootstrap-infrastructure:managedRepositories` and run `pulumi up` there. The stack exports:
  - `pulumiStateBuckets.api-gateway-infrastructure`
  - `pulumiBackendUrls.api-gateway-infrastructure`
  - `deployRoleArns.api-gateway-infrastructure`
- **Backend URL:** use `s3://pulumi-api-gateway-infrastructure-test-state/state` (replace `test` with the stack name if/when prod is added).

## Local Environment Variables (`.env`)

Copy `.env.example` to `.env` and set the following before running `make start`:

| Variable | Example | Purpose |
| --- | --- | --- |
| `PULUMI_STACK` | `test` | Pulumi stack name selected by Makefile/CLI. |
| `AWS_REGION` | `eu-central-1` | Primary region for resources and state bucket. |
| `AWS_DEFAULT_REGION` | `eu-central-1` | Matches `AWS_REGION` for SDK defaults. |
| `PULUMI_BACKEND_URL` | `s3://pulumi-api-gateway-infrastructure-test-state/state` | Remote backend pointing at the shared bucket. |
| `AWS_PROFILE` | _(your profile name)_ | CLI/SDK profile that assumes the shared IAM role. Each developer can pick any profile name, but the profile must target `arn:aws:iam::891377212104:role/PulumiDeploy-api-gateway-infrastructure`. |
| `AWS_SDK_LOAD_CONFIG` | `1` | Forces SDKs to read `~/.aws/config` for profile/SSO directives. |

> ⚠️ Composer now mounts `${HOME}/.aws` into the container. Make sure that directory exists and contains the profile described below (with the name you reference via `AWS_PROFILE`).

Recommended AWS CLI profile (`~/.aws/config`):

```ini
[profile <your-profile-name>]
region = eu-central-1
role_arn = arn:aws:iam::891377212104:role/PulumiDeploy-api-gateway-infrastructure
# Pick either an AWS SSO session (example below) or a source_profile that can assume the role.
sso_start_url = https://<your-directory>.awsapps.com/start
sso_region = eu-central-1
sso_account_id = 891377212104
sso_role_name = PulumiDeploy-api-gateway-infrastructure
```

Run `aws sso login --profile <your-profile-name>` (or obtain credentials from your chosen IdP) before invoking `make start`. No access keys are stored in `.env`; the container reads the cached SSO session/role credentials via the mounted `~/.aws` directory. Update `AWS_PROFILE` in `.env` whenever you change the profile name.

If you are not using AWS SSO, replace the `sso_*` keys with `source_profile = <profile-that-holds-short-lived-creds>` so the CLI can call `sts:AssumeRole` on your behalf.

Run `make pulumi-login` once per environment so the Pulumi CLI records the backend URL.

## Manual Pulumi Preview (outside Docker)

If you want to run a one-off `pulumi preview` from the host machine instead of via Docker, follow the exact sequence below so the CLI talks to the shared S3 backend.

1. **Install Poetry in your user site-packages** (requires Python 3.10+, since the repo targets 3.10):

    ```bash
    python3.10 -m pip install --user poetry
    ```

2. **Create the in-project virtualenv and install dependencies** from the `pulumi/` folder:

    ```bash
    cd pulumi
    poetry env use python3.10
    poetry install --no-interaction
    ```

3. **Verify AWS access** with the profile that can assume `PulumiDeploy-api-gateway-infrastructure` (replace `testvilna` with your profile name if needed):

    ```bash
    AWS_PROFILE=testvilna aws sts get-caller-identity
    ```

4. **Export the runtime environment** so Pulumi points at the bootstrap state bucket and uses the shared config passphrase. The passphrase is committed inside the repo at `pulumi/.pulumi-pass`.

    ```bash
    export AWS_PROFILE=testvilna
    export AWS_REGION=eu-central-1
    export AWS_DEFAULT_REGION=eu-central-1
    export PULUMI_STACK=test
    export PULUMI_BACKEND_URL=s3://pulumi-api-gateway-infrastructure-test-state/state
    export PULUMI_CONFIG_PASSPHRASE="$(cat pulumi/.pulumi-pass)"
    ```

5. **Log in to the backend and select the stack**:

    ```bash
    pulumi login "$PULUMI_BACKEND_URL"
    pulumi stack select "$PULUMI_STACK"
    ```

6. **Run the preview** (or `pulumi up` once you are satisfied with the plan):

    ```bash
    pulumi preview --stack "$PULUMI_STACK"
    ```

The first preview will download the `aws-6.58.0` plugin and then show the resource changes (e.g., creation of the initial demo bucket). Subsequent previews reuse the cached plugin and only require fresh AWS credentials plus the same environment variables.

## GitHub Actions Configuration

Define these repository **variables** (Settings → Variables) so workflows stay aligned with the shared backend:

- `PULUMI_STACK` – e.g. `test`.
- `AWS_REGION` – `eu-central-1`.
- `PULUMI_BACKEND_URL` – `s3://pulumi-api-gateway-infrastructure-test-state/state`.

Define these repository **secrets** (Settings → Secrets). None of them contain AWS access keys—we rely solely on IAM roles with GitHub OIDC:

- `AWS_ROLE_TO_ASSUME` – `arn:aws:iam::891377212104:role/PulumiDeploy-api-gateway-infrastructure` (created by bootstrap stack). GitHub Actions uses OIDC to assume this role and receives short-lived credentials automatically.
- `PULUMI_ACCESS_TOKEN` – service token for the Pulumi Service backend metadata (still required even with S3 state).
- `PULUMI_CONFIG_PASSPHRASE` – protects encrypted config values.
- `ALLOWED_DEPLOYERS` – comma/newline separated GitHub usernames that can always run `/deploy`.

## `/deploy` Comment Workflow

The `.github/workflows/deploy-on-comment.yml` job chain works as follows:

1. **Gate (`.github/scripts/gate.py`)** – only reacts to brand‑new comments whose entire body is `/deploy` (case-insensitive). Manual `workflow_dispatch` triggers skip this gate.
2. **Authorization (`.github/scripts/authorize.py`)** – allows the run when:
   - The commenter appears in `ALLOWED_DEPLOYERS`, or
   - The commenter already has `admin` or `maintain` permission on this repository.  
   Others get an automatic denial comment.
3. **Deploy** – assumes `AWS_ROLE_TO_ASSUME`, logs into the shared backend URL, selects `PULUMI_STACK`, and runs `pulumi up --stack <stack> --json`.
4. **Report** – posts a summary back to the original issue/PR comment thread.

To test locally, you can replicate what the workflow does:

```bash
STACK=test make pulumi-preview
STACK=test make pulumi-up
```

Keep this document updated whenever new environments, secrets, or workflow behaviors are introduced.
