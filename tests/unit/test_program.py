"""Program tests under Pulumi mocks (G3.1, AD-A15).

P: with both feature flags off, `pulumi/__main__.py` registers nothing and
makes no invoke, in every committed stack.
The harness is shown to observe registrations (the provider control tests),
so "registers nothing" is not vacuous.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest
from app import config
from app.config import ConfigError
from stack_fixtures import PROJECT, PULUMI_DIR, ci_document, committed_documents, key

import pulumi


class RecordingMocks(pulumi.runtime.Mocks):
    """Record every resource registration and refuse every invoke."""

    def __init__(self) -> None:
        self.resources: list[pulumi.runtime.MockResourceArgs] = []
        self.invokes: list[pulumi.runtime.MockCallArgs] = []

    def new_resource(self, args: pulumi.runtime.MockResourceArgs):
        self.resources.append(args)
        return [f"{args.name}-id", args.inputs]

    def call(self, args: pulumi.runtime.MockCallArgs):
        self.invokes.append(args)
        return {}


def run_under_mocks(stack: str, body) -> RecordingMocks:
    """Run `body` as a Pulumi program for `stack` and wait for its RPCs."""
    mocks = RecordingMocks()
    pulumi.runtime.set_mocks(mocks, project=PROJECT, stack=stack, preview=True)

    @pulumi.runtime.test
    def program():
        body()

    program()
    return mocks


def run_entry_point(stack: str) -> RecordingMocks:
    """Run the real `pulumi/__main__.py` for `stack` under mocks."""
    return run_under_mocks(
        stack,
        lambda: runpy.run_path(str(PULUMI_DIR / "__main__.py"), run_name="__main__"),
    )


@pytest.fixture
def stack_files_from(monkeypatch):
    """Make the entry point read its stack files from another directory."""

    def redirect(program_dir: Path) -> None:
        real = config.load_stack
        monkeypatch.setattr(
            config, "load_stack", lambda stack, _ignored: real(stack, program_dir)
        )

    return redirect


@pytest.mark.parametrize("stack", sorted(committed_documents()))
def test_flags_off_registers_nothing(stack: str) -> None:
    mocks = run_entry_point(stack)
    assert mocks.resources == []
    assert mocks.invokes == []


def test_offline_stack_with_flags_off_registers_nothing(
    program_copy, documents, stack_files_from
) -> None:
    stack_files_from(program_copy("ci", ci_document(documents)))
    mocks = run_entry_point("ci")
    assert mocks.resources == []
    assert mocks.invokes == []


@pytest.mark.parametrize(
    "features",
    [
        {"certificate": True, "front_door": False},
        {"certificate": True, "front_door": True},
    ],
)
def test_a_flag_without_its_module_fails_closed(
    features: dict, program_copy, documents, stack_files_from
) -> None:
    documents["test"]["config"][key("features")] = features
    stack_files_from(program_copy("test", documents["test"]))
    with pytest.raises(ConfigError, match="certificate"):
        run_entry_point("test")


def test_invalid_stack_config_stops_the_program(
    program_copy, documents, stack_files_from
) -> None:
    del documents["prod"]["config"][key("pulumiBackendUrl")]
    stack_files_from(program_copy("prod", documents["prod"]))
    with pytest.raises(ConfigError, match="pulumiBackendUrl"):
        run_entry_point("prod")


# --- provider: dummy keys only in `ci` ------------------------------------------------


def test_ci_provider_uses_dummy_keys_and_skip_flags(documents) -> None:
    documents["ci"] = ci_document(documents)
    settings = config.parse_stack("ci", documents["ci"])
    assert config.provider_args(settings) == {
        "region": settings.region,
        "access_key": "pulumi-preview",
        "secret_key": "pulumi-preview",
        "skip_credentials_validation": True,
        "skip_metadata_api_check": True,
        "skip_requesting_account_id": True,
        "skip_region_validation": True,
    }


SKIP_ARGS = (
    "skip_credentials_validation",
    "skip_metadata_api_check",
    "skip_requesting_account_id",
    "skip_region_validation",
)


@pytest.mark.parametrize("stack", ["test", "prod"])
def test_shared_provider_pins_the_account_and_has_no_dummy_settings(
    stack: str,
) -> None:
    settings = config.load_stack(stack, PULUMI_DIR)
    args = config.provider_args(settings)
    assert args == {
        "region": settings.region,
        "allowed_account_ids": [settings.account_id],
        **{name: False for name in SKIP_ARGS},
    }
    assert "access_key" not in args
    assert "secret_key" not in args


def plain(value):
    """Unwrap a mock-serialised secret to its value."""
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


@pytest.mark.parametrize("stack", ["test", "prod", "ci"])
def test_build_provider_registers_one_aws_provider(stack: str, documents) -> None:
    documents.setdefault("ci", ci_document(documents))
    settings = config.parse_stack(stack, documents[stack])
    mocks = run_under_mocks(stack, lambda: config.build_provider(settings))
    assert [r.typ for r in mocks.resources] == ["pulumi:providers:aws"]
    inputs = {name: plain(value) for name, value in mocks.resources[0].inputs.items()}
    assert inputs["region"] == settings.region
    skips = {
        name: inputs.get(name)
        for name in (
            "skipCredentialsValidation",
            "skipMetadataApiCheck",
            "skipRequestingAccountId",
            "skipRegionValidation",
        )
    }
    if stack == "ci":
        assert inputs["accessKey"] == inputs["secretKey"] == "pulumi-preview"
        assert set(skips.values()) <= {True, "true"} and None not in skips.values()
        assert "allowedAccountIds" not in inputs
    else:
        assert "accessKey" not in inputs
        assert "secretKey" not in inputs
        assert set(skips.values()) <= {False, "false"} and None not in skips.values()
        assert inputs["allowedAccountIds"] in (
            [settings.account_id],
            f'["{settings.account_id}"]',
        )
