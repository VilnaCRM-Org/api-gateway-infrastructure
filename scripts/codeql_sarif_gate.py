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


def first(items: object) -> dict:
    """Return the first element of a SARIF list when it is an object."""
    head = items[0] if isinstance(items, list) and items else None
    return head if isinstance(head, dict) else {}


def place(location: dict) -> str:
    """Return `uri:line` of one SARIF location (`?` for a missing part)."""
    physical = location.get("physicalLocation") or {}
    uri = (physical.get("artifactLocation") or {}).get("uri", "?")
    line = (physical.get("region") or {}).get("startLine", "?")
    return f"{uri}:{line}"


def label(location: dict) -> str:
    """Return `uri:line: message` for a related location or a flow step."""
    text = (location.get("message") or {}).get("text")
    return f"{place(location)}: {text}" if text else place(location)


def sources(result: dict) -> str:
    """Return the first related location and the first code-flow step.

    Both come straight from the SARIF result, so CI shows where a
    taint-tracking result starts (the `[1]` in its message) and nothing else.
    """
    parts = []
    related = first(result.get("relatedLocations"))
    if related:
        parts.append(f"related: {label(related)}")
    thread = first(first(result.get("codeFlows")).get("threadFlows"))
    step = first(thread.get("locations")).get("location")
    if isinstance(step, dict) and step:
        parts.append(f"flow source: {label(step)}")
    return "".join(f" [{part}]" for part in parts)


def describe(result: dict) -> str:
    rule = result.get("ruleId", "<no rule id>")
    message = (result.get("message") or {}).get("text", "")
    where = "<no location>"
    locations = result.get("locations")
    if isinstance(locations, list) and locations:
        where = place(first(locations))
    return f"{where}: {rule}: {message}{sources(result)}"


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
