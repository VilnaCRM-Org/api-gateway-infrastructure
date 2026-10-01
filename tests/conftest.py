"""Shared pytest fixtures for the G3.1 program and stack-config tests."""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest
import yaml

from stack_fixtures import PULUMI_DIR, committed_documents


@pytest.fixture
def documents() -> dict[str, dict]:
    """A deep copy of the committed stack documents, safe to mutate."""
    return copy.deepcopy(committed_documents())


@pytest.fixture
def program_copy(tmp_path: Path):
    """Copy the program's manifest and stack files to tmp_path.

    The returned writer replaces one stack file with a given document.
    """
    for path in PULUMI_DIR.glob("Pulumi*.yaml"):
        shutil.copy2(path, tmp_path / path.name)

    def write(stack: str, document: dict) -> Path:
        (tmp_path / f"Pulumi.{stack}.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )
        return tmp_path

    write.directory = tmp_path
    return write
