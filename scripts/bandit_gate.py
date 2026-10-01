#!/usr/bin/env python3
"""Bandit with no silent suppressions (G3.2 ``Bandit`` check, AD-A11).

Bandit exits 0 even when a ``# nosec`` comment is wrong or stale. This gate
runs bandit and fails when:

1. bandit reports an issue or exits non-zero;
2. bandit logs any WARNING, among them "Test in comment: ... is not a test
   name or id, ignoring" and "nosec encountered (...), but no failed test";
3. a ``# nosec`` comment is not exactly ``# nosec`` followed by bandit rule
   ids (``# nosec B603``, ``# nosec B404 B603``), optionally followed by a
   separate ``# reason`` comment;
4. a ``# nosec`` comment is not on a statement that starts and ends on its
   own line (a mid-statement ``nosec`` once commented out real arguments);
5. a ``# nosec`` rule id suppresses nothing: a second run with
   ``--ignore-nosec`` reports no finding of that rule on that line.

Usage: ``bandit_gate.py [--skip B101[,...]] PATH...``. Bandit reads its
configuration from ``pyproject.toml``; the gate adds no skips of its own.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess  # nosec B404
import sys
import tokenize
from pathlib import Path

NOSEC_RE = re.compile(r"#\s*nosec\b", re.IGNORECASE)
STRICT_NOSEC_RE = re.compile(r"# nosec (?P<ids>B[0-9]{3}(?: B[0-9]{3})*)(?:\s+#.*)?")
WARNING_RE = re.compile(r"^\[[\w.]+\]\s+WARNING\b.*$", re.MULTILINE)


def single_line_statements(source: str) -> set[int]:
    """Lines that hold at least one statement starting and ending there."""
    return {
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.stmt) and node.lineno == node.end_lineno
    }


def nosec_comments(source: str) -> list[tuple[int, str]]:
    """Return ``(line, comment)`` for every comment bandit reads as nosec."""
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [
        (tok.start[0], tok.string)
        for tok in tokens
        if tok.type == tokenize.COMMENT and NOSEC_RE.search(tok.string)
    ]


def nosec_problems(name: str, source: str, used: set[tuple[str, int, str]]):
    """Check every nosec comment of one file against rules 3-5."""
    problems = []
    statements = single_line_statements(source)
    for line, comment in nosec_comments(source):
        where = f"{name}:{line}"
        match = STRICT_NOSEC_RE.fullmatch(comment)
        if not match:
            problems.append(f"{where}: nosec must name rule ids only: {comment!r}")
            continue
        if line not in statements:
            problems.append(f"{where}: nosec must sit on a one-line statement")
        for rule in match["ids"].split():
            if (name, line, rule) not in used:
                problems.append(f"{where}: nosec {rule} suppresses nothing")
    return problems


def bandit_command(paths: list[str], skip: str | None, *extra: str) -> list[str]:
    command = [sys.executable, "-m", "bandit", "-q", "-c", "pyproject.toml"]
    if skip:
        command += ["--skip", skip]
    return [*command, *extra, "-r", *paths]


def run(command: list[str], runner=subprocess.run):
    return runner(command, check=False, capture_output=True, text=True)


def used_suppressions(report: dict) -> set[tuple[str, int, str]]:
    return {
        (result["filename"], line, result["test_id"])
        for result in report["results"]
        for line in result["line_range"]
    }


def gate(paths: list[str], skip: str | None, runner=subprocess.run) -> list[str]:
    first = run(bandit_command(paths, skip), runner)
    print(first.stdout + first.stderr, end="")
    problems = [f"bandit warning: {w}" for w in WARNING_RE.findall(first.stderr)]
    if first.returncode != 0:
        problems.append(f"bandit exited {first.returncode}")
    second = run(bandit_command(paths, skip, "--ignore-nosec", "-f", "json"), runner)
    try:
        report = json.loads(second.stdout)
        files = sorted(name for name in report["metrics"] if name != "_totals")
        used = used_suppressions(report)
    except (ValueError, KeyError, TypeError) as error:
        return [*problems, f"unreadable bandit --ignore-nosec report: {error!r}"]
    if not files:
        problems.append("bandit scanned no files")
    for name in files:
        source = Path(name).read_text(encoding="utf-8")
        problems += nosec_problems(name, source, used)
    return problems


def main(argv: list[str] | None = None, runner=subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip", help="bandit rule ids to skip, comma-separated")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    problems = gate(args.paths, args.skip, runner)
    for problem in problems:
        print(f"bandit-gate: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"bandit-gate: OK ({' '.join(args.paths)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
