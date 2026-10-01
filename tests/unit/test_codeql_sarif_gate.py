"""Tests of `scripts/codeql_sarif_gate.py` (G3.2, NFR-A11: CodeQL blocking).

P: SARIF with no result passes. N: any result fails, suppressed or not.
E: a missing directory, no SARIF file or a malformed file fails closed.
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

import codeql_sarif_gate as gate

RESULT = {
    "ruleId": "py/clear-text-logging",
    "message": {"text": "logs a secret"},
    "locations": [
        {
            "physicalLocation": {
                "artifactLocation": {"uri": "scripts/x.py"},
                "region": {"startLine": 7},
            }
        }
    ],
}


def sarif(directory: Path, results: list, name: str = "python.sarif") -> Path:
    directory.mkdir(exist_ok=True)
    document = {"version": "2.1.0", "runs": [{"results": results}]}
    (directory / name).write_text(json.dumps(document), encoding="utf-8")
    return directory


def test_no_results_passes(tmp_path: Path, capsys) -> None:
    assert gate.main([str(sarif(tmp_path / "out", []))]) == 0
    assert "OK (no results)" in capsys.readouterr().out


def test_any_result_fails(tmp_path: Path, capsys) -> None:
    directory = sarif(tmp_path / "out", [RESULT])
    assert gate.main([str(directory)]) == 1
    err = capsys.readouterr().err
    assert "python.sarif: scripts/x.py:7: py/clear-text-logging: logs a secret" in err
    assert "1 result(s)" in err


def test_a_suppressed_result_still_fails(tmp_path: Path) -> None:
    suppressed = dict(RESULT, suppressions=[{"kind": "inSource"}])
    assert gate.main([str(sarif(tmp_path / "out", [suppressed]))]) == 1


def test_results_in_every_file_and_run_count(tmp_path: Path) -> None:
    directory = sarif(tmp_path / "out", [RESULT], "actions.sarif")
    sarif(directory, [RESULT, {}], "python.sarif")
    assert gate.findings(directory) == [
        "actions.sarif: scripts/x.py:7: py/clear-text-logging: logs a secret",
        "python.sarif: scripts/x.py:7: py/clear-text-logging: logs a secret",
        "python.sarif: <no location>: <no rule id>: ",
    ]


def test_partial_location_is_described() -> None:
    result = {"ruleId": "r", "locations": [{}, {"physicalLocation": {}}]}
    assert gate.describe(result) == "?:?: r: "


def at(uri: str, line: int, text: str | None = None) -> dict:
    location: dict = {
        "physicalLocation": {
            "artifactLocation": {"uri": uri},
            "region": {"startLine": line},
        }
    }
    if text is not None:
        location["message"] = {"text": text}
    return location


def test_taint_sources_are_printed() -> None:
    result = dict(
        RESULT,
        relatedLocations=[at("scripts/a.py", 3, "sensitive data (secret)"), at("b", 4)],
        codeFlows=[
            {
                "threadFlows": [
                    {
                        "locations": [
                            {"location": at("scripts/a.py", 3, "call to f()")},
                            {"location": at("scripts/x.py", 7, "sink")},
                        ]
                    }
                ]
            }
        ],
    )
    assert gate.describe(result) == (
        "scripts/x.py:7: py/clear-text-logging: logs a secret"
        " [related: scripts/a.py:3: sensitive data (secret)]"
        " [flow source: scripts/a.py:3: call to f()]"
    )


def test_a_source_without_a_message_prints_its_place() -> None:
    result = dict(
        RESULT,
        relatedLocations=[at("a.py", 1)],
        codeFlows=[{"threadFlows": [{"locations": [{"location": at("b.py", 2)}]}]}],
    )
    assert gate.describe(result).endswith(" [related: a.py:1] [flow source: b.py:2]")


@pytest.mark.parametrize(
    "extra",
    [
        {"relatedLocations": []},
        {"relatedLocations": ["x"], "codeFlows": ["x"]},
        {"codeFlows": [{"threadFlows": []}]},
        {"codeFlows": [{"threadFlows": [{"locations": [{"location": []}]}]}]},
        {"codeFlows": [{"threadFlows": [{"locations": ["x"]}]}]},
    ],
)
def test_missing_or_malformed_sources_are_skipped(extra: dict) -> None:
    assert gate.describe(dict(RESULT, **extra)) == (
        "scripts/x.py:7: py/clear-text-logging: logs a secret"
    )


def test_sources_reach_the_gate_output(tmp_path: Path, capsys) -> None:
    result = dict(RESULT, relatedLocations=[at("scripts/a.py", 3, "src")])
    assert gate.main([str(sarif(tmp_path / "out", [result]))]) == 1
    assert "[related: scripts/a.py:3: src]" in capsys.readouterr().err


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        json.dumps({"runs": []}),
        json.dumps({"runs": [{}]}),
        json.dumps({"runs": ["x"]}),
        json.dumps({"runs": [{"results": ["x"]}]}),
    ],
)
def test_malformed_sarif_fails_closed(tmp_path: Path, content: str, capsys) -> None:
    (tmp_path / "python.sarif").write_text(content, encoding="utf-8")
    assert gate.main([str(tmp_path)]) == 1
    assert "codeql-sarif-gate: python.sarif" in capsys.readouterr().err


def test_no_sarif_file_fails_closed(tmp_path: Path, capsys) -> None:
    assert gate.main([str(tmp_path / "missing")]) == 1
    assert "no SARIF file" in capsys.readouterr().err


def test_usage(capsys) -> None:
    assert gate.main([]) == 2
    assert gate.main(["a", "b"]) == 2
    assert "usage" in capsys.readouterr().err


def test_entry_point_reads_argv(tmp_path: Path, monkeypatch) -> None:
    directory = sarif(tmp_path / "out", [])
    monkeypatch.setattr(sys, "argv", ["codeql_sarif_gate.py", str(directory)])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(gate.__file__, run_name="__main__")
    assert stop.value.code == 0
