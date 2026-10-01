"""In-process tests of `scripts/next_release_version.py` (G3.2, NFR-A09).

`tests/test_workflow_hygiene.py` runs the script as the workflow does, in a
subprocess, which coverage does not measure. These tests import it, so the
100% branch-coverage gate covers `scripts/` too.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import pytest

import next_release_version as nrv
from test_workflow_hygiene import git_env, make_repo

SCRIPT = Path(nrv.__file__)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch):
    """Build a throwaway git repository; git sees no inherited GIT_* state."""
    for name in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(name)
    for name in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"):
        monkeypatch.setenv(name, git_env()[name])

    def build(steps):
        make_repo(str(tmp_path), steps)
        return str(tmp_path)

    return build


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        ([("commit", "chore: x")], ("true", "", "")),
        ([("commit", "feat: x")], ("false", "v0.1.0", "")),
        ([("commit", "fix: x")], ("false", "v0.0.1", "")),
        (
            [("commit", "a"), ("tag", "v0.2.0"), ("commit", "feat!: x")],
            ("false", "v0.3.0", "v0.2.0"),
        ),
        (
            [
                ("commit", "a"),
                ("tag", "v1.2.3"),
                ("commit", "fix: a"),
                ("commit", "feat: b"),
            ],
            ("false", "v1.3.0", "v1.2.3"),
        ),
        (
            [
                ("commit", "a"),
                ("tag", "v1.2.3"),
                ("commit", "feat: a"),
                ("commit", "fix: b"),
            ],
            ("false", "v1.3.0", "v1.2.3"),
        ),
        (
            [("commit", "a"), ("tag", "v1.2.3"), ("commit", "x\n\nBREAKING CHANGE: y")],
            ("false", "v2.0.0", "v1.2.3"),
        ),
        (
            [("commit", "a"), ("tag", "v1.2.3"), ("commit", "fix: z")],
            ("false", "v1.2.4", "v1.2.3"),
        ),
        (
            [
                ("commit", "a"),
                # for-each-ref lists v1.10.0 before the lower v1.9.0.
                ("tag", "v1.10.0"),
                ("tag", "v1.9.0"),
                ("tag", "v1.0.0-rc1"),
                ("commit", "fix: z"),
            ],
            ("false", "v1.10.1", "v1.10.0"),
        ),
    ],
)
def test_next_release_in_process(repo, steps, expected) -> None:
    result = nrv.next_release(repo(steps))
    assert (result["skipped"], result["tag"], result["previous"]) == expected


def test_missing_git_raises(monkeypatch) -> None:
    monkeypatch.setattr(nrv.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="git executable not found"):
        nrv.git(["status"], ".")


def test_main_writes_github_output(repo, tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(repo([("commit", "feat: x")]))
    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert nrv.main() == 0
    assert output.read_text(encoding="utf-8").split() == [
        "skipped=false",
        "tag=v0.1.0",
        "previous=",
    ]
    assert "tag=v0.1.0" in capsys.readouterr().out


def test_main_without_github_output_prints_only(repo, monkeypatch, capsys) -> None:
    monkeypatch.chdir(repo([("commit", "chore: x")]))
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    assert nrv.main() == 0
    assert "skipped=true" in capsys.readouterr().out


def test_script_entry_point_exits_with_main(repo, monkeypatch) -> None:
    monkeypatch.chdir(repo([("commit", "fix: x")]))
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert stop.value.code == 0
