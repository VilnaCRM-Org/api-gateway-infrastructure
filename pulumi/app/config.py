"""Closed, typed stack configuration for the API gateway program (AD-A15).

The committed stack files are the only source of account ids, the region,
the backend URL and the secrets provider (FR-A09); this module holds rules,
never those values. A stack file loads only if it has exactly the keys its
stack allows:

- `test` and `prod` pin the account (`awsAccountId` and the provider's
  `aws:allowedAccountIds`), the region, the S3 backend URL and the
  `awskms://` secrets provider; a passphrase provider, `stub_live_invokes`
  and every dummy-key provider setting are refused (FR-A03, AD-A15).
- `ci` is the offline stack: a fixture account, `stub_live_invokes: true`,
  the local file backend (no backend URL) and the `passphrase` provider
  (a committed `encryptionsalt`). Its dummy-key provider exists only in
  code (`provider_args`), never in stack config.

The exemptions from "backend URL required" and "no passphrase provider"
apply to exactly `ci`. Every stack file in the program directory is
validated together, so an account id pinned by two stacks fails to load.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from yaml.constructor import ConstructorError

__all__ = [
    "ConfigError",
    "Features",
    "StackSettings",
    "build_provider",
    "check_stack_set",
    "load_stack",
    "parse_stack",
    "provider_args",
    "read_program",
]

PROJECT = "api-gateway-infrastructure"
SHARED_STACKS = ("test", "prod")
OFFLINE_STACK = "ci"
STACKS = (*SHARED_STACKS, OFFLINE_STACK)
FEATURES = ("certificate", "front_door")

# Dummy-key provider settings (USI `pulumi/app/stack.py` lines 132-147).
# They are built in code for `ci` only and are never stack config.
DUMMY_PROVIDER_KEYS = frozenset(
    {
        "aws:accessKey",
        "aws:secretKey",
        "aws:token",
        "aws:skipCredentialsValidation",
        "aws:skipMetadataApiCheck",
        "aws:skipRequestingAccountId",
        "aws:skipRegionValidation",
    }
)
PREVIEW_KEY = "pulumi-preview"  # nosec B105 - non-secret dummy for the offline stack

_ACCOUNT = re.compile(r"[0-9]{12}")
_REGION = re.compile(r"[a-z]{2}(?:-[a-z]+)+-[0-9]+")
_SALT = re.compile(r"v1:\S+")

_REQUIRED_KEYS = {
    "test": (
        "aws:region",
        "aws:allowedAccountIds",
        "awsAccountId",
        "pulumiBackendUrl",
        "pulumiSecretsProvider",
        "features",
    ),
    "ci": ("aws:region", "awsAccountId", "stub_live_invokes", "features"),
}
_TOP_LEVEL_KEYS = {
    "test": {"config", "secretsprovider", "encryptedkey"},
    "ci": {"config", "encryptionsalt"},
}


class ConfigError(ValueError):
    """A stack configuration is outside the closed AD-A15 shape."""


@dataclass(frozen=True)
class Features:
    """The two AD-A15 feature flags."""

    certificate: bool
    front_door: bool


@dataclass(frozen=True)
class StackSettings:
    """One validated stack configuration."""

    stack: str
    account_id: str
    region: str
    features: Features
    stub_live_invokes: bool
    backend_url: str | None
    secrets_provider: str | None

    @property
    def is_offline(self) -> bool:
        """True for the credential-less `ci` stack only."""
        return self.stack == OFFLINE_STACK

    def enabled_features(self) -> tuple[str, ...]:
        """Names of the feature flags that are on, in build order."""
        return tuple(name for name in FEATURES if getattr(self.features, name))


def _require(condition: object, message: str) -> None:
    if not condition:
        raise ConfigError(message)


def _key(name: str) -> str:
    return name if ":" in name else f"{PROJECT}:{name}"


def _kind(stack: str) -> str:
    return "ci" if stack == OFFLINE_STACK else "test"


def _expected_backend(stack: str) -> str:
    return f"s3://pulumi-{PROJECT}-{stack}-state"


def _expected_secrets_provider(stack: str, region: str) -> str:
    return f"awskms://alias/pulumi-{PROJECT}-{stack}-secrets?region={region}"


def _check_top_level(stack: str, document: Mapping[str, Any]) -> None:
    if stack in SHARED_STACKS:
        _require(
            "encryptionsalt" not in document
            and not str(document.get("secretsprovider", "")).startswith("passphrase"),
            f"Stack {stack!r} must not use the passphrase secrets provider "
            "(only 'ci' is exempt).",
        )
        _require(
            isinstance(document.get("secretsprovider"), str),
            f"Stack {stack!r} must pin 'secretsprovider' to its awskms:// key.",
        )
        if "encryptedkey" in document:
            _require(
                isinstance(document["encryptedkey"], str) and document["encryptedkey"],
                f"Stack {stack!r} has an invalid 'encryptedkey'.",
            )
    else:
        _require(
            "secretsprovider" not in document,
            "Stack 'ci' uses the passphrase provider; remove 'secretsprovider'.",
        )
        salt = document.get("encryptionsalt")
        _require(
            isinstance(salt, str) and _SALT.fullmatch(salt),
            "Stack 'ci' needs the committed passphrase 'encryptionsalt'.",
        )
    unknown = sorted(set(document) - _TOP_LEVEL_KEYS[_kind(stack)])
    _require(not unknown, f"Stack {stack!r} has unknown top-level keys: {unknown}.")


def _check_keys(stack: str, values: Mapping[str, Any]) -> None:
    dummy = sorted(DUMMY_PROVIDER_KEYS & set(values))
    _require(
        not dummy,
        f"Stack {stack!r} must not set dummy-key provider settings {dummy}; "
        "the offline provider is built in code for 'ci' only.",
    )
    stub = _key("stub_live_invokes")
    if stack in SHARED_STACKS:
        _require(
            stub not in values,
            f"'stub_live_invokes' is allowed only in 'ci', not in {stack!r}.",
        )
    else:
        _require(
            values.get(stub) is True,
            "Stack 'ci' requires 'stub_live_invokes: true'.",
        )
        for name in (
            "pulumiBackendUrl",
            "pulumiSecretsProvider",
            "aws:allowedAccountIds",
        ):
            _require(
                _key(name) not in values,
                f"Stack 'ci' must not set {name!r}: it uses the local file backend, "
                "the passphrase provider and a fixture account.",
            )
    required = {_key(name) for name in _REQUIRED_KEYS[_kind(stack)]}
    missing = sorted(required - set(values))
    _require(not missing, f"Stack {stack!r} is missing required keys: {missing}.")
    unknown = sorted(set(values) - required)
    _require(not unknown, f"Stack {stack!r} has unknown config keys: {unknown}.")


def _features(stack: str, value: object) -> Features:
    _require(
        isinstance(value, dict)
        and set(value) == set(FEATURES)
        and all(isinstance(value[name], bool) for name in FEATURES),
        f"Stack {stack!r} 'features' must set exactly {list(FEATURES)} to booleans.",
    )
    features = Features(**value)
    _require(
        features.certificate or not features.front_door,
        f"Stack {stack!r}: 'features.front_door' needs 'features.certificate'.",
    )
    return features


def _check_shared_pins(
    stack: str, document: Mapping[str, Any], values: Mapping[str, Any], account: str
) -> tuple[str, str]:
    region = values["aws:region"]
    _require(
        values["aws:allowedAccountIds"] == [account],
        f"Stack {stack!r} 'aws:allowedAccountIds' must be exactly [awsAccountId].",
    )
    backend = values[_key("pulumiBackendUrl")]
    _require(
        isinstance(backend, str),
        f"Stack {stack!r} 'pulumiBackendUrl' must be a plain string.",
    )
    _require(
        backend == _expected_backend(stack),
        f"Stack {stack!r} backend URL must be its own S3 state bucket.",
    )
    secrets = values[_key("pulumiSecretsProvider")]
    _require(
        isinstance(secrets, str) and not secrets.startswith("passphrase"),
        f"Stack {stack!r} must not use the passphrase secrets provider "
        "(only 'ci' is exempt).",
    )
    _require(
        secrets == _expected_secrets_provider(stack, region)
        and document["secretsprovider"] == secrets,
        f"Stack {stack!r} secrets provider must be its own awskms:// key, "
        "in 'secretsprovider' and 'pulumiSecretsProvider'.",
    )
    return backend, secrets


def parse_stack(stack: str, document: object) -> StackSettings:
    """Validate one stack document (a parsed `Pulumi.<stack>.yaml`)."""
    _require(stack in STACKS, f"Unknown stack {stack!r}; allowed: {list(STACKS)}.")
    _require(isinstance(document, dict), f"Stack {stack!r} must be a YAML mapping.")
    _check_top_level(stack, document)
    values = document.get("config")
    _require(isinstance(values, dict), f"Stack {stack!r} 'config' must be a mapping.")
    _check_keys(stack, values)

    account = values[_key("awsAccountId")]
    _require(
        isinstance(account, str) and _ACCOUNT.fullmatch(account),
        f"Stack {stack!r} 'awsAccountId' must be a quoted 12-digit string.",
    )
    region = values["aws:region"]
    _require(
        isinstance(region, str) and _REGION.fullmatch(region),
        f"Stack {stack!r} 'aws:region' is not a region name.",
    )
    features = _features(stack, values[_key("features")])

    backend = secrets = None
    if stack in SHARED_STACKS:
        backend, secrets = _check_shared_pins(stack, document, values, account)
    return StackSettings(
        stack=stack,
        account_id=account,
        region=region,
        features=features,
        stub_live_invokes=stack == OFFLINE_STACK,
        backend_url=backend,
        secrets_provider=secrets,
    )


def check_stack_set(settings: Mapping[str, StackSettings]) -> None:
    """Cross-stack rules: both shared stacks, one region, one account each."""
    missing = [stack for stack in SHARED_STACKS if stack not in settings]
    _require(not missing, f"Shared stack config is missing for {missing}.")
    owners: dict[str, str] = {}
    for stack, item in settings.items():
        other = owners.setdefault(item.account_id, stack)
        _require(
            other == stack,
            f"The account of stack {stack!r} is also pinned by {other!r}; "
            "each stack pins only its own account.",
        )
    regions = sorted({item.region for item in settings.values()})
    _require(len(regions) == 1, f"Stacks disagree on the region: {regions}.")


class _StackFileLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys, so none can hide another."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        self.flatten_mapping(node)
        mapping = super().construct_mapping(node, deep=deep)
        _require(
            len(mapping) == len(node.value),
            f"Duplicate keys in stack file at {node.start_mark}.",
        )
        return mapping


def _read_yaml(path: Path) -> object:
    _require(not path.is_symlink(), f"Stack file {path.name} must not be a symlink.")
    loader = _StackFileLoader(path.read_text(encoding="utf-8"))
    try:
        return loader.get_single_data()
    except (ConstructorError, yaml.YAMLError) as error:
        raise ConfigError(f"Invalid YAML in {path.name}: {error}") from None
    finally:
        loader.dispose()


def read_program(program_dir: Path) -> tuple[str, dict[str, object]]:
    """Return the project name and every stack document in `program_dir`."""
    manifest = _read_yaml(program_dir / "Pulumi.yaml")
    project = manifest.get("name") if isinstance(manifest, dict) else None
    _require(project == PROJECT, f"Pulumi project must be {PROJECT!r}.")
    documents = {
        path.name[len("Pulumi.") : -len(".yaml")]: _read_yaml(path)
        for path in sorted(program_dir.glob("Pulumi.*.yaml"))
    }
    return project, documents


def load_stack(stack: str, program_dir: Path) -> StackSettings:
    """Load `stack` after validating every stack file of the program."""
    _, documents = read_program(program_dir)
    _require(stack in documents, f"No stack file for the selected stack {stack!r}.")
    settings = {name: parse_stack(name, doc) for name, doc in documents.items()}
    check_stack_set(settings)
    return settings[stack]


def provider_args(settings: StackSettings) -> dict[str, Any]:
    """AWS provider arguments: dummy keys for `ci`, the account pin otherwise.

    `test` and `prod` set every `skip_*` flag to false explicitly, because
    `pulumi-aws` defaults `skip_region_validation` to true.
    """
    if settings.is_offline:
        return {
            "region": settings.region,
            "access_key": PREVIEW_KEY,
            "secret_key": PREVIEW_KEY,
            "skip_credentials_validation": True,
            "skip_metadata_api_check": True,
            "skip_requesting_account_id": True,
            "skip_region_validation": True,
        }
    return {
        "region": settings.region,
        "allowed_account_ids": [settings.account_id],
        "skip_credentials_validation": False,
        "skip_metadata_api_check": False,
        "skip_requesting_account_id": False,
        "skip_region_validation": False,
    }


def build_provider(settings: StackSettings, opts: Any = None) -> Any:
    """Register the program's AWS provider for `settings`."""
    import pulumi_aws as aws

    return aws.Provider("aws", opts=opts, **provider_args(settings))
