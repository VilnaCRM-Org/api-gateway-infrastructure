#!/usr/bin/env python3
"""Fail the CodeQL job on any result (G3.2, NFR-A11: CodeQL is blocking).

Every PR job runs with ``contents: read`` only (FR-A08, FR-A10), so the
CodeQL job cannot upload to code scanning (that needs
``security-events: write``) and cannot rely on the code-scanning check run.
``codeql-action/analyze`` therefore runs with ``upload: never`` and writes
SARIF files; this gate fails the job on every result in them, suppressed or
not. It also fails closed when the directory holds no SARIF file or a file it
cannot read.

Usage: ``codeql_sarif_gate.py SARIF_DIR``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


class GateError(Exception):
    """The SARIF output is missing or malformed."""


def describe(result: dict) -> str:
    rule = result.get("ruleId", "<no rule id>")
    message = (result.get("message") or {}).get("text", "")
    where = "<no location>"
    for location in result.get("locations") or []:
        physical = location.get("physicalLocation") or {}
        uri = (physical.get("artifactLocation") or {}).get("uri", "?")
        line = (physical.get("region") or {}).get("startLine", "?")
        where = f"{uri}:{line}"
        break
    return f"{where}: {rule}: {message}"


def file_results(path: Path) -> list[dict]:
    """Return every result of one SARIF file; raise on a malformed file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise GateError(f"{path.name}: not JSON: {error}") from None
    runs = document.get("runs") if isinstance(document, dict) else None
    if not isinstance(runs, list) or not runs:
        raise GateError(f"{path.name}: no runs")
    results = []
    for run in runs:
        found = run.get("results") if isinstance(run, dict) else None
        if not isinstance(found, list):
            raise GateError(f"{path.name}: a run has no results list")
        if not all(isinstance(result, dict) for result in found):
            raise GateError(f"{path.name}: a result is not an object")
        results += found
    return results


def findings(sarif_dir: Path) -> list[str]:
    files = sorted(sarif_dir.glob("*.sarif"))
    if not files:
        raise GateError(f"no SARIF file in {sarif_dir}")
    return [
        f"{path.name}: {describe(result)}"
        for path in files
        for result in file_results(path)
    ]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: codeql_sarif_gate.py SARIF_DIR", file=sys.stderr)
        return 2
    try:
        found = findings(Path(args[0]))
    except GateError as error:
        print(f"codeql-sarif-gate: {error}", file=sys.stderr)
        return 1
    for line in found:
        print(f"codeql-sarif-gate: {line}", file=sys.stderr)
    if found:
        print(f"codeql-sarif-gate: {len(found)} result(s)", file=sys.stderr)
        return 1
    print("codeql-sarif-gate: OK (no results)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
