# syntax=docker/dockerfile:1
# Development and CI image (G3.1, FR-A09). Every downloaded tool is pinned to
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

RUN ln -sf /opt/pulumi/pulumi /usr/local/bin/pulumi \
    && ln -sf /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws

# Keep the uv environment outside /workspace so the bind mount never hides it.
RUN install -d -o "${USERNAME}" -g "${GID}" "${HOME}/.cache/uv" "${HOME}/.venvs" "${PULUMI_HOME}"

COPY --chown=${USERNAME}:${GID} pyproject.toml uv.lock /workspace/

WORKDIR /workspace

RUN --mount=type=cache,target=/home/${USERNAME}/.cache/uv,uid=${UID},gid=${GID} \
    uv venv "${UV_PROJECT_ENVIRONMENT}" \
    && uv sync --frozen --all-groups \
    && pulumi version >/dev/null \
    && aws --version >/dev/null \
    && uv run --frozen python -c 'import pulumi, pulumi_aws, yaml' \
    && chown -R "${USERNAME}:$(id -g "${USERNAME}")" "${UV_PROJECT_ENVIRONMENT}" "${UV_CACHE_DIR}"

USER "${USERNAME}"
WORKDIR /workspace

CMD ["bash"]
