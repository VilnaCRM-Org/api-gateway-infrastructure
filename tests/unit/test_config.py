"""Closed stack-config tests for `pulumi/app/config.py` (G3.1, AD-A15, FR-A09).

P: every committed stack loads with both feature flags off.
N: a missing backend URL, a passphrase provider, an account that does not
match the stack, `front_door` without `certificate`, `stub_live_invokes`
outside `ci` and dummy-key provider settings in `test`/`prod` each fail.
The passphrase and backend-URL exemptions apply to exactly `ci`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from app import config
from app.config import ConfigError
from stack_fixtures import (
    PULUMI_DIR,
    ROOT,
    SHARED_STACKS,
    ci_document,
    committed_documents,
    key,
)

DUMMY_PROVIDER_KEYS = (
    "aws:accessKey",
    "aws:secretKey",
    "aws:token",
    "aws:skipCredentialsValidation",
    "aws:skipMetadataApiCheck",
    "aws:skipRequestingAccountId",
    "aws:skipRegionValidation",
)


def check(stack: str, documents: dict[str, dict]) -> config.StackSettings:
    """Validate `stack` the way the program does: alone, then as a set."""
    settings = {name: config.parse_stack(name, doc) for name, doc in documents.items()}
    config.check_stack_set(settings)
    return settings[stack]


# --- P: committed stacks --------------------------------------------------------------


def test_committed_stack_set_is_closed() -> None:
    names = set(committed_documents())
    assert names == {"test", "prod", "ci"}
    assert not (PULUMI_DIR / "Pulumi.example.yaml").exists()


@pytest.mark.parametrize("stack", sorted(committed_documents()))
def test_each_committed_stack_loads_with_flags_off(stack: str) -> None:
    settings = config.load_stack(stack, PULUMI_DIR)
    assert settings.stack == stack
    assert settings.features == config.Features(certificate=False, front_door=False)
    assert settings.enabled_features() == ()


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_shared_stack_pins_backend_secrets_region_account(stack: str) -> None:
    settings = config.load_stack(stack, PULUMI_DIR)
    doc = committed_documents()[stack]
    assert settings.region == "eu-central-1"
    assert settings.backend_url == (
        f"s3://pulumi-api-gateway-infrastructure-{stack}-state"
    )
    assert settings.secrets_provider == (
        f"awskms://alias/pulumi-api-gateway-infrastructure-{stack}-secrets"
        "?region=eu-central-1"
    )
    assert doc["secretsprovider"] == settings.secrets_provider
    assert "encryptionsalt" not in doc
    assert settings.account_id == doc["config"][key("awsAccountId")]
    assert doc["config"]["aws:allowedAccountIds"] == [settings.account_id]
    assert settings.stub_live_invokes is False


def test_shared_stacks_pin_distinct_accounts() -> None:
    test = config.load_stack("test", PULUMI_DIR)
    prod = config.load_stack("prod", PULUMI_DIR)
    assert test.account_id != prod.account_id
    assert len(test.account_id) == len(prod.account_id) == 12


def test_project_manifest() -> None:
    project, _ = config.read_program(PULUMI_DIR)
    assert project == "api-gateway-infrastructure"


# --- N: backend URL -------------------------------------------------------------------


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_missing_backend_url_fails(stack: str, documents: dict) -> None:
    del documents[stack]["config"][key("pulumiBackendUrl")]
    with pytest.raises(ConfigError, match="pulumiBackendUrl"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_backend_url_of_another_stack_fails(stack: str, documents: dict) -> None:
    other = "prod" if stack == "test" else "test"
    documents[stack]["config"][key("pulumiBackendUrl")] = documents[other]["config"][
        key("pulumiBackendUrl")
    ]
    with pytest.raises(ConfigError, match="backend URL"):
        check(stack, documents)


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/state",
        "s3://pulumi-api-gateway-infrastructure-{stack}-state/",
        "s3://pulumi-api-gateway-infrastructure-{stack}-state?region=x",
        "",
    ],
)
def test_backend_url_must_be_exact(url: str, documents: dict) -> None:
    documents["test"]["config"][key("pulumiBackendUrl")] = url.format(stack="test")
    with pytest.raises(ConfigError, match="backend URL"):
        check("test", documents)


# --- N: passphrase provider -----------------------------------------------------------


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_encryptionsalt_in_shared_stack_fails(stack: str, documents: dict) -> None:
    documents[stack]["encryptionsalt"] = ci_document(documents)["encryptionsalt"]
    with pytest.raises(ConfigError, match="passphrase"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_passphrase_secretsprovider_in_shared_stack_fails(
    stack: str, documents: dict
) -> None:
    documents[stack]["secretsprovider"] = "passphrase"
    with pytest.raises(ConfigError, match="passphrase"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_passphrase_in_secrets_provider_key_fails(stack: str, documents: dict) -> None:
    documents[stack]["config"][key("pulumiSecretsProvider")] = "passphrase"
    with pytest.raises(ConfigError, match="passphrase"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_missing_secretsprovider_fails(stack: str, documents: dict) -> None:
    del documents[stack]["secretsprovider"]
    with pytest.raises(ConfigError, match="secretsprovider"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_secretsprovider_must_equal_pinned_key(stack: str, documents: dict) -> None:
    other = "prod" if stack == "test" else "test"
    documents[stack]["secretsprovider"] = documents[other]["secretsprovider"]
    with pytest.raises(ConfigError, match="secrets provider"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_secrets_provider_of_another_stack_fails(stack: str, documents: dict) -> None:
    other = "prod" if stack == "test" else "test"
    value = documents[other]["secretsprovider"]
    documents[stack]["secretsprovider"] = value
    documents[stack]["config"][key("pulumiSecretsProvider")] = value
    with pytest.raises(ConfigError, match="secrets provider"):
        check(stack, documents)


def test_encryptedkey_from_stack_init_is_accepted(documents: dict) -> None:
    documents["test"]["encryptedkey"] = "AQICAHh-opaque-ciphertext"
    assert check("test", documents).stack == "test"


@pytest.mark.parametrize("value", [123, ""])
def test_encryptedkey_must_be_text(value: object, documents: dict) -> None:
    documents["test"]["encryptedkey"] = value
    with pytest.raises(ConfigError, match="encryptedkey"):
        check("test", documents)


# --- N: account -----------------------------------------------------------------------


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_account_of_another_stack_fails(stack: str, documents: dict) -> None:
    other = "prod" if stack == "test" else "test"
    account = documents[other]["config"][key("awsAccountId")]
    documents[stack]["config"][key("awsAccountId")] = account
    documents[stack]["config"]["aws:allowedAccountIds"] = [account]
    with pytest.raises(ConfigError, match="account"):
        check(stack, documents)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_allowed_account_ids_must_match_account(stack: str, documents: dict) -> None:
    other = "prod" if stack == "test" else "test"
    documents[stack]["config"]["aws:allowedAccountIds"] = [
        documents[other]["config"][key("awsAccountId")]
    ]
    with pytest.raises(ConfigError, match="allowedAccountIds"):
        check(stack, documents)


@pytest.mark.parametrize("value", ["12345", "12345678901a", 891, None, "0123456789012"])
def test_account_must_be_twelve_digits(value: object, documents: dict) -> None:
    documents["test"]["config"][key("awsAccountId")] = value
    with pytest.raises(ConfigError, match="awsAccountId"):
        config.parse_stack("test", documents["test"])


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_ci_with_a_shared_account_fails(stack: str, documents: dict) -> None:
    ci = ci_document(documents)
    ci["config"][key("awsAccountId")] = documents[stack]["config"][key("awsAccountId")]
    documents["ci"] = ci
    with pytest.raises(ConfigError, match="account"):
        check("ci", documents)


def test_regions_must_agree(documents: dict) -> None:
    ci = ci_document(documents)
    ci["config"]["aws:region"] = "eu-west-1"
    documents["ci"] = ci
    with pytest.raises(ConfigError, match="region"):
        check("ci", documents)


@pytest.mark.parametrize("region", ["EU-central-1", "", 5])
def test_region_must_be_well_formed(region: object, documents: dict) -> None:
    documents["test"]["config"]["aws:region"] = region
    with pytest.raises(ConfigError, match="region"):
        config.parse_stack("test", documents["test"])


@pytest.mark.parametrize("missing", ["test", "prod", "ci"])
def test_every_stack_is_required(missing: str, documents: dict) -> None:
    del documents[missing]
    selected = "prod" if missing == "test" else "test"
    with pytest.raises(ConfigError, match=missing):
        check(selected, documents)


def test_committed_ci_account_is_not_a_real_account() -> None:
    ci = config.load_stack("ci", PULUMI_DIR)
    shared = {config.load_stack(name, PULUMI_DIR).account_id for name in SHARED_STACKS}
    assert len(shared) == 2
    assert ci.account_id not in shared
    assert ci.is_offline and ci.stub_live_invokes
    assert ci.backend_url is None and ci.secrets_provider is None


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_shared_stack_with_the_ci_fixture_account_fails(
    stack: str, documents: dict
) -> None:
    account = documents["ci"]["config"][key("awsAccountId")]
    documents[stack]["config"][key("awsAccountId")] = account
    documents[stack]["config"]["aws:allowedAccountIds"] = [account]
    with pytest.raises(ConfigError, match="account"):
        check(stack, documents)


# --- N: feature flags -----------------------------------------------------------------


@pytest.mark.parametrize("stack", [*SHARED_STACKS, "ci"])
def test_front_door_without_certificate_fails(stack: str, documents: dict) -> None:
    documents.setdefault("ci", ci_document(documents))
    documents[stack]["config"][key("features")] = {
        "certificate": False,
        "front_door": True,
    }
    with pytest.raises(ConfigError, match="front_door"):
        check(stack, documents)


def test_both_flags_on_are_accepted_by_config(documents: dict) -> None:
    documents["test"]["config"][key("features")] = {
        "certificate": True,
        "front_door": True,
    }
    settings = check("test", documents)
    assert settings.enabled_features() == ("certificate", "front_door")


def test_certificate_alone_is_accepted_by_config(documents: dict) -> None:
    documents["prod"]["config"][key("features")] = {
        "certificate": True,
        "front_door": False,
    }
    assert check("prod", documents).enabled_features() == ("certificate",)


@pytest.mark.parametrize(
    "features",
    [
        {"certificate": False},
        {"certificate": False, "front_door": False, "waf": False},
        {"certificate": "false", "front_door": False},
        {"certificate": False, "front_door": "observability"},
        ["certificate"],
        None,
    ],
)
def test_features_are_closed(features: object, documents: dict) -> None:
    documents["test"]["config"][key("features")] = features
    with pytest.raises(ConfigError, match="features"):
        config.parse_stack("test", documents["test"])


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_missing_features_fails(stack: str, documents: dict) -> None:
    del documents[stack]["config"][key("features")]
    with pytest.raises(ConfigError, match="features"):
        check(stack, documents)


# --- N: stub_live_invokes -------------------------------------------------------------


@pytest.mark.parametrize("stack", SHARED_STACKS)
@pytest.mark.parametrize("value", [True, False])
def test_stub_live_invokes_outside_ci_fails(
    stack: str, value: bool, documents: dict
) -> None:
    documents[stack]["config"][key("stub_live_invokes")] = value
    with pytest.raises(ConfigError, match="stub_live_invokes"):
        check(stack, documents)


@pytest.mark.parametrize("value", [False, "true", None])
def test_ci_requires_stub_live_invokes_true(value: object, documents: dict) -> None:
    ci = ci_document(documents)
    ci["config"][key("stub_live_invokes")] = value
    with pytest.raises(ConfigError, match="stub_live_invokes"):
        config.parse_stack("ci", ci)


def test_ci_without_stub_live_invokes_fails(documents: dict) -> None:
    ci = ci_document(documents)
    del ci["config"][key("stub_live_invokes")]
    with pytest.raises(ConfigError, match="stub_live_invokes"):
        config.parse_stack("ci", ci)


# --- N: dummy-key provider settings ---------------------------------------------------


@pytest.mark.parametrize("stack", SHARED_STACKS)
@pytest.mark.parametrize("setting", DUMMY_PROVIDER_KEYS)
def test_dummy_provider_settings_in_shared_stack_fail(
    stack: str, setting: str, documents: dict
) -> None:
    documents[stack]["config"][setting] = (
        "pulumi-preview" if setting.endswith(("Key", "token")) else True
    )
    with pytest.raises(ConfigError, match="dummy-key"):
        check(stack, documents)


@pytest.mark.parametrize("setting", DUMMY_PROVIDER_KEYS)
def test_dummy_provider_settings_are_code_only_in_ci(
    setting: str, documents: dict
) -> None:
    ci = ci_document(documents)
    ci["config"][setting] = True
    with pytest.raises(ConfigError, match="dummy-key"):
        config.parse_stack("ci", ci)


# --- the `ci` exemptions apply to exactly `ci` ----------------------------------------


def test_ci_loads_without_backend_url_and_with_passphrase(documents: dict) -> None:
    documents["ci"] = ci_document(documents)
    settings = check("ci", documents)
    assert settings.backend_url is None
    assert settings.secrets_provider is None
    assert settings.stub_live_invokes is True
    assert settings.is_offline is True


@pytest.mark.parametrize("name", ["pulumiBackendUrl", "pulumiSecretsProvider"])
def test_ci_rejects_a_shared_backend_or_kms_key(name: str, documents: dict) -> None:
    ci = ci_document(documents)
    ci["config"][key(name)] = documents["test"]["config"][key(name)]
    with pytest.raises(ConfigError, match=name):
        config.parse_stack("ci", ci)


def test_ci_rejects_allowed_account_ids(documents: dict) -> None:
    ci = ci_document(documents)
    ci["config"]["aws:allowedAccountIds"] = [ci["config"][key("awsAccountId")]]
    with pytest.raises(ConfigError, match="allowedAccountIds"):
        config.parse_stack("ci", ci)


def test_ci_requires_encryptionsalt(documents: dict) -> None:
    ci = ci_document(documents)
    del ci["encryptionsalt"]
    with pytest.raises(ConfigError, match="encryptionsalt"):
        config.parse_stack("ci", ci)


@pytest.mark.parametrize("salt", ["", "v2:abc", 7])
def test_ci_encryptionsalt_must_be_well_formed(salt: object, documents: dict) -> None:
    ci = ci_document(documents)
    ci["encryptionsalt"] = salt
    with pytest.raises(ConfigError, match="encryptionsalt"):
        config.parse_stack("ci", ci)


def test_ci_rejects_a_kms_secretsprovider(documents: dict) -> None:
    ci = ci_document(documents)
    ci["secretsprovider"] = documents["test"]["secretsprovider"]
    with pytest.raises(ConfigError, match="secretsprovider"):
        config.parse_stack("ci", ci)


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_shared_stack_shaped_like_ci_fails(stack: str, documents: dict) -> None:
    documents[stack] = ci_document(documents)
    with pytest.raises(ConfigError):
        check(stack, documents)


# --- closed shape ---------------------------------------------------------------------


def test_unknown_config_key_fails(documents: dict) -> None:
    documents["test"]["config"][key("debug")] = True
    with pytest.raises(ConfigError, match="debug"):
        config.parse_stack("test", documents["test"])


def test_unknown_provider_key_fails(documents: dict) -> None:
    documents["prod"]["config"]["aws:profile"] = "admin"
    with pytest.raises(ConfigError, match="aws:profile"):
        config.parse_stack("prod", documents["prod"])


def test_unknown_top_level_key_fails(documents: dict) -> None:
    documents["test"]["environment"] = ["imports"]
    with pytest.raises(ConfigError, match="environment"):
        config.parse_stack("test", documents["test"])


@pytest.mark.parametrize("stack", ["dev", "example", "staging"])
def test_unknown_stack_fails(stack: str, documents: dict) -> None:
    with pytest.raises(ConfigError, match=stack):
        config.parse_stack(stack, documents["test"])


@pytest.mark.parametrize("document", [None, [], "config"])
def test_document_must_be_a_mapping(document: object) -> None:
    with pytest.raises(ConfigError, match="mapping"):
        config.parse_stack("test", document)


def test_config_must_be_a_mapping(documents: dict) -> None:
    documents["test"]["config"] = ["aws:region"]
    with pytest.raises(ConfigError, match="mapping"):
        config.parse_stack("test", documents["test"])


def test_secure_values_are_rejected(documents: dict) -> None:
    documents["test"]["config"][key("pulumiBackendUrl")] = {"secure": "AAAA"}
    with pytest.raises(ConfigError, match="pulumiBackendUrl"):
        config.parse_stack("test", documents["test"])


# --- reading the program directory ----------------------------------------------------


def test_load_stack_rejects_an_unknown_stack_file(program_copy, documents) -> None:
    program_dir = program_copy("example", documents["test"])
    with pytest.raises(ConfigError, match="example"):
        config.load_stack("test", program_dir)


def test_load_stack_rejects_a_missing_selected_stack(program_copy) -> None:
    (program_copy.directory / "Pulumi.prod.yaml").unlink()
    with pytest.raises(ConfigError, match="prod"):
        config.load_stack("prod", program_copy.directory)


def test_load_stack_cross_checks_every_stack(program_copy, documents) -> None:
    account = documents["test"]["config"][key("awsAccountId")]
    documents["prod"]["config"][key("awsAccountId")] = account
    documents["prod"]["config"]["aws:allowedAccountIds"] = [account]
    program_dir = program_copy("prod", documents["prod"])
    with pytest.raises(ConfigError, match="account"):
        config.load_stack("test", program_dir)


def test_duplicate_yaml_keys_fail(program_copy) -> None:
    path = program_copy.directory / "Pulumi.test.yaml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "secretsprovider: passphrase\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="[Dd]uplicate"):
        config.load_stack("test", program_copy.directory)


def test_invalid_yaml_fails(program_copy) -> None:
    (program_copy.directory / "Pulumi.test.yaml").write_text(
        "config: [unclosed\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="YAML"):
        config.load_stack("test", program_copy.directory)


def test_symlinked_stack_file_fails(program_copy) -> None:
    path = program_copy.directory / "Pulumi.test.yaml"
    target = program_copy.directory / "real-test.yaml"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(ConfigError, match="symlink"):
        config.load_stack("test", program_copy.directory)


def test_wrong_project_name_fails(program_copy) -> None:
    manifest = program_copy.directory / "Pulumi.yaml"
    manifest.write_text("name: vilnacrm\nruntime: python\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="project"):
        config.load_stack("test", program_copy.directory)


def test_ci_stack_file_is_loaded_from_disk(program_copy, documents) -> None:
    program_dir = program_copy("ci", ci_document(documents))
    settings = config.load_stack("ci", program_dir)
    assert settings.is_offline is True


# --- Pulumi.yaml is closed (G31-F01) --------------------------------------------------

MANIFEST = "name: api-gateway-infrastructure\nruntime:\n  name: python\n"


def write_manifest(program_copy, text: str) -> Path:
    (program_copy.directory / "Pulumi.yaml").write_text(text, encoding="utf-8")
    return program_copy.directory


@pytest.mark.parametrize(
    "text",
    [
        MANIFEST,
        "name: api-gateway-infrastructure\nruntime: python\n",
        "name: api-gateway-infrastructure\ndescription: gateway\nruntime: python\n",
    ],
)
def test_manifest_minimal_forms_are_accepted(program_copy, text: str) -> None:
    program_dir = write_manifest(program_copy, text)
    assert config.load_stack("test", program_dir).stack == "test"


def test_fixture_a_stack_config_dir_fails(program_copy, documents) -> None:
    """(A) `stackConfigDir` points the engine at stack files nobody checks."""
    alt = program_copy.directory / "alt"
    alt.mkdir()
    bad = documents["test"]
    bad["encryptionsalt"] = ci_document(documents)["encryptionsalt"]
    bad["config"]["aws:skipCredentialsValidation"] = True
    (alt / "Pulumi.test.yaml").write_text(yaml.safe_dump(bad), encoding="utf-8")
    program_dir = write_manifest(program_copy, MANIFEST + "stackConfigDir: alt/\n")
    with pytest.raises(ConfigError, match="stackConfigDir"):
        config.load_stack("test", program_dir)


def test_fixture_b_main_elsewhere_fails(program_copy) -> None:
    """(B) `main` runs another entry point than the tested `__main__.py`."""
    other = program_copy.directory / "other"
    other.mkdir()
    (other / "__main__.py").write_text("print('unchecked')\n", encoding="utf-8")
    program_dir = write_manifest(program_copy, MANIFEST + "main: other/\n")
    with pytest.raises(ConfigError, match="main"):
        config.load_stack("test", program_dir)


def test_fixture_c_project_config_block_fails(program_copy) -> None:
    """(C) a project-level `config:` block merges into every stack unchecked."""
    text = MANIFEST + "config:\n  aws:skipCredentialsValidation:\n    value: true\n"
    program_dir = write_manifest(program_copy, text)
    with pytest.raises(ConfigError, match="config"):
        config.load_stack("test", program_dir)


@pytest.mark.parametrize(
    ("text", "match"),
    [
        (MANIFEST + "backend:\n  url: file:///tmp\n", "backend"),
        (MANIFEST + "options:\n  refresh: always\n", "options"),
        (MANIFEST + "plugins:\n  providers: []\n", "plugins"),
        (MANIFEST + "packages: {}\n", "packages"),
        (
            "name: api-gateway-infrastructure\nruntime:\n  name: python\n"
            "  options:\n    toolchain: pip\n",
            "runtime",
        ),
        (
            "name: api-gateway-infrastructure\nruntime:\n  name: python\n"
            "  options:\n    virtualenv: ../venv\n",
            "runtime",
        ),
        ("name: api-gateway-infrastructure\nruntime: nodejs\n", "runtime"),
        ("name: api-gateway-infrastructure\n", "runtime"),
        (
            "name: api-gateway-infrastructure\nruntime: python\ndescription: [x]\n",
            "description",
        ),
        ("- name\n", "mapping"),
    ],
)
def test_manifest_is_closed(program_copy, text: str, match: str) -> None:
    program_dir = write_manifest(program_copy, text)
    with pytest.raises(ConfigError, match=match):
        config.load_stack("test", program_dir)


def test_committed_manifest_is_minimal() -> None:
    manifest = yaml.safe_load((PULUMI_DIR / "Pulumi.yaml").read_text())
    assert set(manifest) <= {"name", "description", "runtime"}
    assert manifest["runtime"] in ("python", {"name": "python"})


# --- YAML 1.1 booleans are not booleans (G31-F04) -------------------------------------


@pytest.mark.parametrize(
    "word", ["yes", "no", "on", "off", "y", "n", "True", "FALSE", "Yes", "OFF"]
)
@pytest.mark.parametrize("stack", ["test", "prod", "ci"])
def test_yaml11_boolean_feature_flag_fails(program_copy, stack: str, word: str) -> None:
    path = program_copy.directory / f"Pulumi.{stack}.yaml"
    text = path.read_text(encoding="utf-8")
    assert "    certificate: false\n" in text
    path.write_text(
        text.replace("    certificate: false\n", f"    certificate: {word}\n")
    )
    with pytest.raises(ConfigError, match="features"):
        config.load_stack(stack, program_copy.directory)


@pytest.mark.parametrize("word", ["yes", "on", "y", "True", "TRUE"])
def test_yaml11_boolean_stub_live_invokes_fails(program_copy, word: str) -> None:
    path = program_copy.directory / "Pulumi.ci.yaml"
    text = path.read_text(encoding="utf-8")
    old = "api-gateway-infrastructure:stub_live_invokes: true\n"
    assert old in text
    path.write_text(
        text.replace(old, f"api-gateway-infrastructure:stub_live_invokes: {word}\n")
    )
    with pytest.raises(ConfigError, match="stub_live_invokes"):
        config.load_stack("ci", program_copy.directory)


@pytest.mark.parametrize("word", ["yes", "on", "1"])
def test_explicit_bool_tag_needs_a_literal(program_copy, word: str) -> None:
    path = program_copy.directory / "Pulumi.ci.yaml"
    text = path.read_text(encoding="utf-8")
    old = "api-gateway-infrastructure:stub_live_invokes: true\n"
    path.write_text(
        text.replace(
            old, f"api-gateway-infrastructure:stub_live_invokes: !!bool {word}\n"
        )
    )
    with pytest.raises(ConfigError, match="literal true/false"):
        config.load_stack("ci", program_copy.directory)


def test_literal_booleans_still_load(program_copy) -> None:
    path = program_copy.directory / "Pulumi.ci.yaml"
    text = path.read_text(encoding="utf-8")
    old = "api-gateway-infrastructure:stub_live_invokes: true\n"
    path.write_text(
        text.replace(old, "api-gateway-infrastructure:stub_live_invokes: !!bool true\n")
    )
    assert config.load_stack("ci", program_copy.directory).stub_live_invokes is True


# --- default providers are disabled in every stack (G31-F05) --------------------------


@pytest.mark.parametrize("stack", ["test", "prod", "ci"])
def test_committed_stacks_disable_default_providers(stack: str) -> None:
    values = committed_documents()[stack]["config"]
    assert values["pulumi:disable-default-providers"] == ["*"]


@pytest.mark.parametrize("stack", ["test", "prod", "ci"])
def test_missing_disable_default_providers_fails(stack: str, documents: dict) -> None:
    del documents[stack]["config"]["pulumi:disable-default-providers"]
    with pytest.raises(ConfigError, match="disable-default-providers"):
        config.parse_stack(stack, documents[stack])


@pytest.mark.parametrize("value", [["aws"], "*", [], ["*", "aws"], None, True])
@pytest.mark.parametrize("stack", ["test", "prod", "ci"])
def test_disable_default_providers_must_be_all(
    stack: str, value: object, documents: dict
) -> None:
    documents[stack]["config"]["pulumi:disable-default-providers"] = value
    with pytest.raises(ConfigError, match="disable-default-providers"):
        config.parse_stack(stack, documents[stack])


# --- stack files equal the plan's architecture §1 (G31-F03) ---------------------------

ARCHITECTURE = ROOT / "specs" / "gateway-wa-plan" / "architecture.md"


def plan_rows() -> dict[str, str]:
    """Return the `| Item | Value |` rows of architecture.md §1."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split("## 1. Target and engine discovery", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| ([^|]+?) \| (.+?) \|$", section, re.MULTILINE)
    return {item: value for item, value in rows}


def plan_pins() -> dict[str, dict[str, str]]:
    rows = plan_rows()
    accounts = dict(
        re.findall(r"`(test|prod)` \(account `([0-9]{12})`\)", rows["Stacks"])
    )
    (region,) = re.findall(r"both `([a-z0-9-]+)`", rows["Stacks"])
    (bucket,) = re.findall(r"`s3://([^`]+)`", rows["Backend"])
    (kms,) = re.findall(r"`(awskms://[^`]+)`", rows["Backend"])
    return {
        stack: {
            "account": accounts[stack],
            "region": region,
            "backend": "s3://" + bucket.replace("{env}", stack),
            "kms": kms.replace("{env}", stack),
        }
        for stack in SHARED_STACKS
    }


def test_plan_rows_parse() -> None:
    pins = plan_pins()
    assert set(pins) == set(SHARED_STACKS)
    assert pins["test"]["account"] != pins["prod"]["account"]


@pytest.mark.parametrize("stack", SHARED_STACKS)
def test_shared_stack_equals_architecture_section_1(stack: str) -> None:
    pins = plan_pins()[stack]
    doc = committed_documents()[stack]
    values = doc["config"]
    settings = config.load_stack(stack, PULUMI_DIR)
    assert settings.account_id == values[key("awsAccountId")] == pins["account"]
    assert values["aws:allowedAccountIds"] == [pins["account"]]
    assert settings.region == values["aws:region"] == pins["region"]
    assert settings.backend_url == values[key("pulumiBackendUrl")] == pins["backend"]
    assert settings.secrets_provider == pins["kms"]
    assert doc["secretsprovider"] == values[key("pulumiSecretsProvider")] == pins["kms"]
