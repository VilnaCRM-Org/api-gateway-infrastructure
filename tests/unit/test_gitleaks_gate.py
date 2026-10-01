"""The fail-closed Secrets Scan (G3.3 gate G33-F02).

P: gitleaks succeeds and reports scanned commits. N: git cannot read the
repository (a worktree without its main .git), gitleaks reports 0 or no
scanned commits, or gitleaks fails; each fails the gate.
"""

from __future__ import annotations

import runpy
import subprocess  # nosec B404
from pathlib import Path

import pytest

import gitleaks_gate as gate


def git(cwd: Path, *args: str) -> None:
    env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
    argv = [gate._binary("git"), *args]
    subprocess.run(argv, cwd=cwd, check=True, capture_output=True, env=env)  # nosec B603


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    git(tmp_path, "add", "a.txt")
    git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-qm",
        "a",
    )
    return tmp_path


class FakeGitleaks:
    """Replace only the gitleaks call; git runs for real."""

    def __init__(self, code: int, output: str) -> None:
        self.code, self.output, self.argv = code, output, None
        self.real = subprocess.run

    def __call__(self, argv, **kwargs):
        if Path(argv[0]).name != "gitleaks":
            return self.real(argv, **kwargs)
        self.argv = argv
        return subprocess.CompletedProcess(argv, self.code, "", self.output)


def install(monkeypatch, code: int, output: str) -> FakeGitleaks:
    fake = FakeGitleaks(code, output)
    monkeypatch.setattr(gate.subprocess, "run", fake)
    real_which = gate.shutil.which
    monkeypatch.setattr(
        gate.shutil,
        "which",
        lambda name: "/usr/bin/gitleaks" if name == "gitleaks" else real_which(name),
    )
    return fake


def test_p_scanned_commits_pass(repo: Path, monkeypatch, capsys) -> None:
    fake = install(monkeypatch, 0, "\x1b[32mINF\x1b[0m 1 commits scanned.\n")
    assert gate.main([str(repo)]) == 0
    assert fake.argv[1:] == [*gate.GITLEAKS_ARGS, "."]
    assert "OK (1 commit(s) scanned, 1 reachable)" in capsys.readouterr().out


def test_n_unreadable_repository_fails_before_gitleaks(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A worktree whose `.git` points at a main repository that is absent."""
    (tmp_path / ".git").write_text("gitdir: /nonexistent/.git/worktrees/x\n")
    fake = install(monkeypatch, 0, "INF 0 commits scanned.\n")
    assert gate.main([str(tmp_path)]) == 1
    assert fake.argv is None
    assert "git cannot resolve HEAD" in capsys.readouterr().err


@pytest.mark.parametrize("output", ["INF 0 commits scanned.\n", "no count\n"])
def test_n_empty_scan_fails(repo: Path, monkeypatch, capsys, output: str) -> None:
    install(monkeypatch, 0, output)
    assert gate.main([str(repo)]) == 1
    assert "refusing an empty scan" in capsys.readouterr().err


def test_n_gitleaks_failure_fails(repo: Path, monkeypatch) -> None:
    install(monkeypatch, 1, "WRN leaks found: 1\n1 commits scanned.\n")
    assert gate.main([str(repo)]) == 1


def test_n_uncountable_history_fails(repo: Path, monkeypatch, capsys) -> None:
    real = subprocess.run

    def fake(argv, **kwargs):
        if argv[1:3] == ["rev-list", "--count"]:
            return subprocess.CompletedProcess(argv, 0, "x\n", "")
        return real(argv, **kwargs)

    monkeypatch.setattr(gate.subprocess, "run", fake)
    assert gate.main([str(repo)]) == 1
    assert "cannot count commits" in capsys.readouterr().err


def test_n_missing_binary_fails(repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(gate.shutil, "which", lambda name: None)
    assert gate.main([str(repo)]) == 1
    assert "git is not on PATH" in capsys.readouterr().err


def test_scanned_commits_parsing() -> None:
    assert gate.scanned_commits("\x1b[1m48 commits scanned.\x1b[0m") == 48
    assert gate.scanned_commits("1 commit scanned") == 1
    assert gate.scanned_commits("nothing") is None


def test_main_defaults_to_the_current_directory(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, 0, "2 commits scanned\n")
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["gitleaks_gate.py"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(gate.__file__, run_name="__main__")
    assert raised.value.code == 0
