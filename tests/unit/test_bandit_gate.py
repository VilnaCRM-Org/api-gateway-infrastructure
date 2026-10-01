"""Tests of `scripts/bandit_gate.py`, the G3.2 `Bandit` check.

The G2.1 hand-off: the Bandit job must fail on bandit's "Test in comment"
and "nosec encountered ... but no failed test" warnings, with no global
skips. The fixture tests run the real bandit; the unit tests feed canned
bandit output to cover every branch.
"""

from __future__ import annotations

import json
import runpy
import subprocess  # nosec B404
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import bandit_gate

CLEAN = (
    "import subprocess  # nosec B404\n\nsubprocess.run(['/bin/true'])  # nosec B603\n"
)


@pytest.fixture
def project(tmp_path: Path, monkeypatch) -> Path:
    """A directory with an empty bandit config, used as the working dir."""
    (tmp_path / "pyproject.toml").write_text("[tool.bandit]\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def write(project: Path, source: str) -> None:
    (project / "src" / "mod.py").write_text(source, encoding="utf-8")


# --- real bandit -----------------------------------------------------------


def test_clean_rule_specific_nosec_passes(project: Path) -> None:
    write(project, CLEAN)
    assert bandit_gate.gate(["src"], None) == []


def test_test_in_comment_warning_fails(project: Path) -> None:
    write(project, "import subprocess  # nosec B404 - reason in the same comment\n")
    problems = bandit_gate.gate(["src"], None)
    assert any("Test in comment" in p for p in problems), problems
    assert any("rule ids only" in p for p in problems), problems


def test_nosec_encountered_warning_fails(project: Path) -> None:
    write(project, CLEAN + "subprocess.run(['/bin/true'], shell=True)  # nosec B603\n")
    problems = bandit_gate.gate(["src"], None)
    assert any("nosec encountered (B603)" in p for p in problems), problems
    assert any("bandit exited 1" in p for p in problems), problems


def test_unused_nosec_without_a_bandit_warning_fails(project: Path) -> None:
    write(project, CLEAN + "VALUE = 1  # nosec B603\n")
    problems = bandit_gate.gate(["src"], None)
    assert problems == ["src/mod.py:4: nosec B603 suppresses nothing"]


def test_blanket_nosec_fails(project: Path) -> None:
    write(project, "import subprocess  # nosec\n")
    problems = bandit_gate.gate(["src"], None)
    assert problems == ["src/mod.py:1: nosec must name rule ids only: '# nosec'"]


def test_nosec_on_a_multi_line_statement_fails(project: Path) -> None:
    write(project, CLEAN + "subprocess.run(\n    ['/bin/true'],\n)  # nosec B603\n")
    problems = bandit_gate.gate(["src"], None)
    assert "src/mod.py:6: nosec must sit on a one-line statement" in problems


def test_an_unsuppressed_finding_fails(project: Path) -> None:
    write(project, "import subprocess\n")
    problems = bandit_gate.gate(["src"], None)
    assert problems == ["bandit exited 1"]


def test_skip_is_passed_to_bandit(project: Path) -> None:
    write(project, "assert True\n")
    assert bandit_gate.gate(["src"], None) == ["bandit exited 1"]
    assert bandit_gate.gate(["src"], "B101") == []


def test_justification_after_the_rule_ids_is_allowed(project: Path) -> None:
    write(project, "import subprocess  # nosec B404  # only argv lists are run\n")
    assert bandit_gate.gate(["src"], None) == []


def test_main_and_entry_point(project: Path, monkeypatch, capsys) -> None:
    write(project, CLEAN)
    assert bandit_gate.main(["src"]) == 0
    assert "bandit-gate: OK (src)" in capsys.readouterr().out
    write(project, "import subprocess\n")
    assert bandit_gate.main(["src"]) == 1
    assert "bandit-gate: bandit exited 1" in capsys.readouterr().err
    write(project, CLEAN)
    monkeypatch.setattr(sys, "argv", ["bandit_gate.py", "src"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(bandit_gate.__file__, run_name="__main__")
    assert stop.value.code == 0


# --- canned bandit output --------------------------------------------------


def runner_with(first, second):
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return first if len(calls) == 1 else second

    runner.calls = calls
    return runner


def done(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def report(files, results=()):
    metrics = {name: {} for name in files}
    metrics["_totals"] = {}
    return json.dumps({"metrics": metrics, "results": list(results)})


def test_unreadable_second_report_fails_closed() -> None:
    for stdout in ("not json", "{}", '{"metrics": [], "results": 1}'):
        runner = runner_with(done(), done(stdout=stdout))
        problems = bandit_gate.gate(["src"], None, runner)
        assert len(problems) == 1
        assert problems[0].startswith("unreadable bandit --ignore-nosec report")


def test_no_scanned_file_fails() -> None:
    runner = runner_with(done(), done(stdout=report([])))
    assert bandit_gate.gate(["src"], None, runner) == ["bandit scanned no files"]


def test_any_bandit_warning_fails() -> None:
    first = done(stderr="[manager]\tWARNING\tsomething new\n[main]\tINFO\tfine\n")
    runner = runner_with(first, done(stdout=report([])))
    problems = bandit_gate.gate(["src"], None, runner)
    assert problems[0] == "bandit warning: [manager]\tWARNING\tsomething new"


def test_command_shape() -> None:
    runner = runner_with(done(), done(stdout=report([])))
    bandit_gate.gate(["a", "b"], "B101", runner)
    head = [sys.executable, "-m", "bandit", "-q", "-c", "pyproject.toml"]
    assert runner.calls == [
        [*head, "--skip", "B101", "-r", "a", "b"],
        [*head, "--skip", "B101", "--ignore-nosec", "-f", "json", "-r", "a", "b"],
    ]


def test_nosec_inside_a_string_is_not_a_comment() -> None:
    assert bandit_gate.nosec_comments("X = '# nosec'\n") == []


def test_default_runner_is_subprocess_run() -> None:
    result = bandit_gate.run([sys.executable, "-c", "print('ok')"])
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.stdout == "ok\n"


def test_repository_nosec_comments_are_well_formed() -> None:
    """Fast form check of rules 3 and 4 over every Python file (no bandit)."""
    root = Path(bandit_gate.__file__).resolve().parents[1]
    problems = []
    for top in ("pulumi", "scripts", "tests", "policy"):
        for path in sorted((root / top).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            statements = bandit_gate.single_line_statements(source)
            for line, comment in bandit_gate.nosec_comments(source):
                if not bandit_gate.STRICT_NOSEC_RE.fullmatch(comment):
                    problems.append(f"{path}:{line}: {comment!r}")
                elif line not in statements:
                    problems.append(f"{path}:{line}: not a one-line statement")
    assert problems == []
