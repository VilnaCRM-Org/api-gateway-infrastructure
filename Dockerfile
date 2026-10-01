# syntax=docker/dockerfile:1
# Development and CI image (G3.1, FR-A09; G3.2 battery tools). Every downloaded tool is pinned to
# a version and verified against its SHA-256 before use (NFR-A11); the
# Python environment comes only from the frozen, hash-pinned uv.lock.
ARG BASE_IMAGE=python:3.11.15-slim-bookworm@sha256:cd67330292a51e2963156f74ff340455d66b2172e9190e99f40dff9357471177
FROM ${BASE_IMAGE} AS tooling

# TARGETARCH is supplied by BuildKit; do not default it, or a cross-platform
# build can silently fetch the wrong binaries.
ARG TARGETARCH
ARG PULUMI_VERSION=3.223.0
ARG PULUMI_SHA256_AMD64=4297489a17a71981d212c0e47db2b3f59e67fbaf0fddf52226def8b71538d519
ARG PULUMI_SHA256_ARM64=d5f5fc5e2068df8ac018b3297b0c0f38e8d284293a656ad48489a2c6b5a317bf
ARG AWSCLI_VERSION=2.16.9
ARG AWSCLI_SHA256_AMD64=8c09f0aa7743fb04a28ac7a6f3c2822d6ffcc58bcace2beaf55258ee0f67c4cb
ARG AWSCLI_SHA256_ARM64=82636f7ec20c57beeed19a14f8684113e0edfb30e79f1a615809de2dfb482712
ARG UV_VERSION=0.9.21
ARG UV_SHA256_AMD64=0a1ab27383c28ef1c041f85cbbc609d8e3752dfb4b238d2ad97b208a52232baf
ARG UV_SHA256_ARM64=416984484783a357170c43f98e7d2d203f1fb595d6b3b95131513c53e50986ef
# G3.2 battery binaries. Each SHA-256 equals the GitHub release asset digest
# and, where the project publishes one, its checksums file.
ARG ACTIONLINT_VERSION=1.7.12
ARG ACTIONLINT_SHA256_AMD64=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
ARG ACTIONLINT_SHA256_ARM64=325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6
ARG SHELLCHECK_VERSION=0.11.0
ARG SHELLCHECK_SHA256_AMD64=b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6
ARG SHELLCHECK_SHA256_ARM64=68a8133197a50beb8803f8d42f9908d1af1c5540d4bb05fdfca8c1fa47decefc
ARG GITLEAKS_VERSION=8.30.1
ARG GITLEAKS_SHA256_AMD64=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
ARG GITLEAKS_SHA256_ARM64=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080
ARG HADOLINT_VERSION=2.14.0
ARG HADOLINT_SHA256_AMD64=6bf226944684f56c84dd014e8b979d27425c0148f61b3bd99bcc6f39e9dc5a47
ARG HADOLINT_SHA256_ARM64=331f1d3511b84a4f1e3d18d52fec284723e4019552f4f47b19322a53ce9a40ed
ENV DEBIAN_FRONTEND=noninteractive

# Transient download tools only. Bookworm's rolling security repositories do
# not offer stable patch pins for them.
# hadolint ignore=DL3008
RUN printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\n' > /etc/apt/apt.conf.d/99retries \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) pulumi_arch="x64"; pulumi_sha256="${PULUMI_SHA256_AMD64}" ;; \
        arm64) pulumi_arch="arm64"; pulumi_sha256="${PULUMI_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://get.pulumi.com/releases/sdk/pulumi-v${PULUMI_VERSION}-linux-${pulumi_arch}.tar.gz" \
        --output /tmp/pulumi.tar.gz \
    && echo "${pulumi_sha256}  /tmp/pulumi.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/pulumi \
    && tar --extract --gzip --file /tmp/pulumi.tar.gz --strip-components=1 --directory /opt/pulumi \
    && rm -f \
        /opt/pulumi/pulumi-language-dotnet \
        /opt/pulumi/pulumi-language-go \
        /opt/pulumi/pulumi-language-java \
        /opt/pulumi/pulumi-language-nodejs \
        /opt/pulumi/pulumi-language-yaml \
        /opt/pulumi/pulumi-resource-pulumi-nodejs \
        /opt/pulumi/pulumi-watch \
    && rm -rf /tmp/pulumi.tar.gz'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) awscli_arch="linux-x86_64"; awscli_sha256="${AWSCLI_SHA256_AMD64}" ;; \
        arm64) awscli_arch="linux-aarch64"; awscli_sha256="${AWSCLI_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://awscli.amazonaws.com/awscli-exe-${awscli_arch}-${AWSCLI_VERSION}.zip" \
        --output /tmp/awscliv2.zip \
    && echo "${awscli_sha256}  /tmp/awscliv2.zip" | sha256sum -c - \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli \
    && rm -rf /usr/local/aws-cli/v2/current/dist/awscli/examples \
    && rm -rf /tmp/aws /tmp/awscliv2.zip'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) uv_arch="x86_64-unknown-linux-gnu"; uv_sha256="${UV_SHA256_AMD64}" ;; \
        arm64) uv_arch="aarch64-unknown-linux-gnu"; uv_sha256="${UV_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${uv_arch}.tar.gz" \
        --output /tmp/uv.tar.gz \
    && echo "${uv_sha256}  /tmp/uv.tar.gz" | sha256sum -c - \
    && tar --extract --gzip --file /tmp/uv.tar.gz --directory /tmp \
    && install -m 0755 "/tmp/uv-${uv_arch}/uv" /usr/local/bin/uv \
    && install -m 0755 "/tmp/uv-${uv_arch}/uvx" /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz "/tmp/uv-${uv_arch}"'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) actionlint_arch="linux_amd64"; actionlint_sha256="${ACTIONLINT_SHA256_AMD64}" ;; \
        arm64) actionlint_arch="linux_arm64"; actionlint_sha256="${ACTIONLINT_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_${actionlint_arch}.tar.gz" \
        --output /tmp/actionlint.tar.gz \
    && echo "${actionlint_sha256}  /tmp/actionlint.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/actionlint \
    && tar --extract --gzip --file /tmp/actionlint.tar.gz --directory /tmp/actionlint actionlint \
    && install -m 0755 /tmp/actionlint/actionlint /usr/local/bin/actionlint \
    && rm -rf /tmp/actionlint /tmp/actionlint.tar.gz'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) shellcheck_arch="x86_64"; shellcheck_sha256="${SHELLCHECK_SHA256_AMD64}" ;; \
        arm64) shellcheck_arch="aarch64"; shellcheck_sha256="${SHELLCHECK_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.${shellcheck_arch}.tar.gz" \
        --output /tmp/shellcheck.tar.gz \
    && echo "${shellcheck_sha256}  /tmp/shellcheck.tar.gz" | sha256sum -c - \
    && tar --extract --gzip --file /tmp/shellcheck.tar.gz --directory /tmp \
    && install -m 0755 "/tmp/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/shellcheck \
    && rm -rf /tmp/shellcheck.tar.gz "/tmp/shellcheck-v${SHELLCHECK_VERSION}"'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) gitleaks_arch="linux_x64"; gitleaks_sha256="${GITLEAKS_SHA256_AMD64}" ;; \
        arm64) gitleaks_arch="linux_arm64"; gitleaks_sha256="${GITLEAKS_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_${gitleaks_arch}.tar.gz" \
        --output /tmp/gitleaks.tar.gz \
    && echo "${gitleaks_sha256}  /tmp/gitleaks.tar.gz" | sha256sum -c - \
    && mkdir -p /tmp/gitleaks \
    && tar --extract --gzip --file /tmp/gitleaks.tar.gz --directory /tmp/gitleaks gitleaks \
    && install -m 0755 /tmp/gitleaks/gitleaks /usr/local/bin/gitleaks \
    && rm -rf /tmp/gitleaks /tmp/gitleaks.tar.gz'

RUN bash -o pipefail -c 'set -euo pipefail \
    && case "${TARGETARCH}" in \
        amd64) hadolint_arch="x86_64"; hadolint_sha256="${HADOLINT_SHA256_AMD64}" ;; \
        arm64) hadolint_arch="arm64"; hadolint_sha256="${HADOLINT_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl --fail --silent --show-error --location \
        --retry 12 --retry-delay 10 --retry-max-time 240 --retry-all-errors \
        "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-${hadolint_arch}" \
        --output /tmp/hadolint \
    && echo "${hadolint_sha256}  /tmp/hadolint" | sha256sum -c - \
    && install -m 0755 /tmp/hadolint /usr/local/bin/hadolint \
    && rm -f /tmp/hadolint'

FROM ${BASE_IMAGE} AS dev

ARG USERNAME=dev
ARG UID=1000
ARG GID=1000
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/home/${USERNAME}
ENV PATH="/opt/pulumi:${PATH}"
ENV AWS_PAGER=""
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PULUMI_HOME=${HOME}/.pulumi
ENV PULUMI_SKIP_UPDATE_CHECK=true
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=${HOME}/.cache/uv
ENV UV_PROJECT_ENVIRONMENT=${HOME}/.venvs/api-gateway-infrastructure
ENV PULUMI_PYTHON_CMD=${UV_PROJECT_ENVIRONMENT}/bin/python

# Bookworm's rolling security repositories do not offer stable patch pins.
# hadolint ignore=DL3008
RUN printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\n' > /etc/apt/apt.conf.d/99retries \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git make \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    group_name="${USERNAME}"; \
    if getent group "${GID}" >/dev/null; then \
        group_entry="$(getent group "${GID}")"; \
        group_name="${group_entry%%:*}"; \
    elif ! getent group "${USERNAME}" >/dev/null; then \
        groupadd --gid "${GID}" "${USERNAME}"; \
    fi; \
    if ! id -u "${USERNAME}" >/dev/null 2>&1; then \
        if getent passwd "${UID}" >/dev/null; then \
            useradd --gid "${group_name}" --create-home "${USERNAME}"; \
        else \
            useradd --uid "${UID}" --gid "${group_name}" --create-home "${USERNAME}"; \
        fi; \
    fi

COPY --from=tooling /opt/pulumi /opt/pulumi
COPY --from=tooling /usr/local/aws-cli /usr/local/aws-cli
COPY --from=tooling /usr/local/bin/uv /usr/local/bin/uv
COPY --from=tooling /usr/local/bin/uvx /usr/local/bin/uvx
COPY --from=tooling /usr/local/bin/actionlint /usr/local/bin/actionlint
COPY --from=tooling /usr/local/bin/shellcheck /usr/local/bin/shellcheck
COPY --from=tooling /usr/local/bin/gitleaks /usr/local/bin/gitleaks
COPY --from=tooling /usr/local/bin/hadolint /usr/local/bin/hadolint

RUN ln -sf /opt/pulumi/pulumi /usr/local/bin/pulumi \
    && ln -sf /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws

# Keep the uv environment outside /workspace so the bind mount never hides it;
# the dev user owns ~/.cache, where pip-audit and ty keep their caches.
RUN install -d -o "${USERNAME}" -g "${GID}" "${HOME}/.cache" "${HOME}/.cache/uv" "${HOME}/.venvs" "${PULUMI_HOME}"

COPY --chown=${USERNAME}:${GID} pyproject.toml uv.lock /workspace/

WORKDIR /workspace

RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv venv "${UV_PROJECT_ENVIRONMENT}" \
    && uv sync --frozen --all-groups \
    && pulumi version >/dev/null \
    && aws --version >/dev/null \
    && actionlint -version >/dev/null \
    && shellcheck --version >/dev/null \
    && gitleaks version >/dev/null \
    && hadolint --version >/dev/null \
    && uv run --frozen python -c 'import pulumi, pulumi_aws, yaml' \
    && chown -R "${USERNAME}:$(id -g "${USERNAME}")" "${UV_PROJECT_ENVIRONMENT}" "${UV_CACHE_DIR}"

USER "${USERNAME}"
WORKDIR /workspace

CMD ["bash"]
