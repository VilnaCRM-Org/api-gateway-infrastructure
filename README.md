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
test-lockfile   Fail when pyproject.toml and uv.lock disagree.
up              Start the development container.
```

The Python toolchain is [uv](https://docs.astral.sh/uv/) with the frozen, hash-pinned `uv.lock` at the repository root (Python 3.11, `pulumi-aws` 7.23.0). The Pulumi program lives in `pulumi/`; its stacks are `test`, `prod` and the offline `ci` stack (AD-A15), and `pulumi/app/config.py` refuses any stack config outside that closed shape.

The `ci` stack runs the credential-free Structural Preview on a local file backend. It uses the `passphrase` secrets provider with an **intentionally empty, non-secret passphrase** (`PULUMI_CONFIG_PASSPHRASE=""`, as USI's `dev` stack does), and it holds no secret. Its account is the AWS documentation example account `123456789012`, never a real VilnaCRM account. `test` and `prod` refuse a passphrase provider and pin their own account, region, S3 backend and KMS key.

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
