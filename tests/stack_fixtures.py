"""Stack-document helpers for the G3.1 program and stack-config tests.

Account ids never appear here as literals (FR-A09): every fixture document
is derived from the committed stack files, so the values stay in stack
config only.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PULUMI_DIR = ROOT / "pulumi"
PROJECT = "api-gateway-infrastructure"
SHARED_STACKS = ("test", "prod")


def key(name: str) -> str:
    """Return the project-namespaced stack-config key."""
    return f"{PROJECT}:{name}"


def read_document(stack: str, program_dir: Path = PULUMI_DIR) -> dict:
    """Read one committed stack file as plain data."""
    path = program_dir / f"Pulumi.{stack}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def committed_documents() -> dict[str, dict]:
    """Return every committed stack file, keyed by stack name."""
    return {
        path.name[len("Pulumi.") : -len(".yaml")]: yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
        for path in sorted(PULUMI_DIR.glob("Pulumi.*.yaml"))
    }


def fixture_account(documents: dict[str, dict]) -> str:
    """Derive a 12-digit account id that no committed stack pins."""
    used = {doc["config"][key("awsAccountId")] for doc in documents.values()}
    candidate = 10**11
    while str(candidate) in used:
        candidate += 1
    return str(candidate)


def ci_document(documents: dict[str, dict]) -> dict:
    """Build an offline `ci` stack document in the AD-A15 shape.

    The encryption salt is a syntactic placeholder: the loader checks only
    its presence and `v1:` form, never decrypts it.
    """
    region = documents["test"]["config"]["aws:region"]
    return {
        "encryptionsalt": "v1:AAAAAAAAAAA=:v1:AAAAAAAAAAAAAAAA:AAAAAAAAAAAAAAAAAAAA==",
        "config": {
            "aws:region": region,
            key("awsAccountId"): fixture_account(documents),
            key("stub_live_invokes"): True,
            key("features"): {"certificate": False, "front_door": False},
            "pulumi:disable-default-providers": ["*"],
        },
    }


def engine_view(values: dict) -> dict[str, str]:
    """Encode a stack file's config the way `pulumi preview` passes it.

    Observed with pulumi 3.223.0 (evidence log 20): strings as-is; booleans,
    lists and maps JSON-encoded with Go's compact separators.
    """
    return {
        name: value
        if isinstance(value, str)
        else json.dumps(value, separators=(",", ":"))
        for name, value in values.items()
    }
