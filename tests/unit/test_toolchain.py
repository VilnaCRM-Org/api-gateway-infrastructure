"""Toolchain tests (G3.1, FR-A09, PD-2, NFR-A11).

uv with a hash-pinned frozen lockfile at the root, Python 3.11,
`pulumi-aws` 7.23.0, PyYAML in the dev group, the Poetry files gone, and a
Dockerfile whose downloaded tools are version-pinned and checksum-verified.
"""

from __future__ import annotations

import re
import tomllib

from stack_fixtures import PULUMI_DIR, ROOT

PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
LOCK = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")


def locked(name: str) -> dict:
    (package,) = [p for p in LOCK["package"] if p["name"] == name]
    return package


def test_poetry_files_are_gone() -> None:
    assert not (PULUMI_DIR / "pyproject.toml").exists()
    assert not (PULUMI_DIR / "poetry.lock").exists()


def test_project_metadata() -> None:
    project = PYPROJECT["project"]
    assert project["name"] == "api-gateway-infrastructure"
    assert project["requires-python"] == ">=3.11,<3.12"


def test_pulumi_aws_is_pinned_exactly() -> None:
    assert "pulumi-aws==7.23.0" in PYPROJECT["project"]["dependencies"]
    assert locked("pulumi-aws")["version"] == "7.23.0"


def test_pyyaml_is_in_the_dev_group() -> None:
    dev = PYPROJECT["dependency-groups"]["dev"]
    assert any(re.match(r"pyyaml\b", spec, re.IGNORECASE) for spec in dev)
    assert any(re.match(r"pytest\b", spec) for spec in dev)


def test_every_locked_registry_package_is_hash_pinned() -> None:
    registry = [p for p in LOCK["package"] if "registry" in p.get("source", {})]
    assert registry
    for package in registry:
        artifacts = package.get("wheels", []) + (
            [package["sdist"]] if "sdist" in package else []
        )
        assert artifacts, package["name"]
        for artifact in artifacts:
            assert re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["hash"]), package[
                "name"
            ]


def test_lock_requires_python_311() -> None:
    assert LOCK["requires-python"] == "==3.11.*"


def test_pulumi_manifest_uses_the_uv_environment() -> None:
    text = (PULUMI_DIR / "Pulumi.yaml").read_text(encoding="utf-8")
    assert "poetry" not in text
    assert "name: api-gateway-infrastructure" in text


# --- Dockerfile ---------------------------------------------------------------------


def test_base_image_is_digest_pinned() -> None:
    match = re.search(r"^ARG BASE_IMAGE=(\S+)$", DOCKERFILE, re.MULTILINE)
    assert match
    assert re.fullmatch(r"python:3\.11\.\d+-slim-\w+@sha256:[0-9a-f]{64}", match[1])


def test_every_downloaded_tool_is_pinned_with_checksums() -> None:
    versions = dict(re.findall(r"^ARG (\w+)_VERSION=(\S+)$", DOCKERFILE, re.MULTILINE))
    assert {"PULUMI", "UV", "AWSCLI"} <= set(versions)
    for tool, version in versions.items():
        assert re.fullmatch(r"[0-9]+(\.[0-9]+)+", version), tool
        for arch in ("AMD64", "ARM64"):
            assert re.search(
                rf"^ARG {tool}_SHA256_{arch}=[0-9a-f]{{64}}$", DOCKERFILE, re.MULTILINE
            ), f"{tool} {arch}"
    downloads = DOCKERFILE.count("--output ")
    verifications = DOCKERFILE.count("| sha256sum -c -")
    assert downloads == verifications == len(versions)


def test_no_unverified_installers() -> None:
    assert not re.search(r"curl[^\n]*\|\s*(ba)?sh", DOCKERFILE)
    assert "install.python-poetry.org" not in DOCKERFILE
    assert "get.pulumi.com | " not in DOCKERFILE


def test_pulumi_cli_matches_the_locked_sdk() -> None:
    version = re.search(r"^ARG PULUMI_VERSION=(\S+)$", DOCKERFILE, re.MULTILINE)[1]
    assert locked("pulumi")["version"] == version


def test_image_syncs_the_frozen_lock() -> None:
    assert "uv sync --frozen" in DOCKERFILE
    assert "COPY --chown=${USERNAME}:${GID} pyproject.toml uv.lock /workspace/" in (
        DOCKERFILE
    )


# --- Makefile -----------------------------------------------------------------------


def recipe(target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:.*?\n((?:[ \t]+.*\n?)+)", MAKEFILE, re.MULTILINE
    )
    assert match, target
    return match[1]


def test_make_test_runs_pytest_on_the_frozen_lock() -> None:
    assert "uv run --frozen pytest" in recipe("test")


def test_make_test_lockfile_checks_the_lock() -> None:
    assert "uv lock --check" in recipe("test-lockfile")
