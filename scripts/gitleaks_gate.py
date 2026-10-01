#!/usr/bin/env python3
"""The `Secrets Scan` check, fail-closed (G3.2 FR-A10; G3.3 gate G33-F02).

`gitleaks git` exits 0 when it cannot read the repository: in a git worktree
mounted without its main `.git`, git fails, gitleaks logs "0 commits
scanned" and reports success. This gate runs gitleaks only after git can
resolve `HEAD` in the same container, and it fails unless gitleaks
succeeded and reports at least one scanned commit.

Usage: ``gitleaks_gate.py [REPOSITORY]`` (default: the current directory).
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Sequence
from pathlib import Path

GITLEAKS_ARGS = ("git", "--no-banner", "--redact", "--verbose", "--log-opts=HEAD")
SCANNED_RE = re.compile(r"\b(\d+) commits? scanned")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class GateError(Exception):
    """The repository cannot be scanned."""


def _binary(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise GateError(f"{name} is not on PATH")
    return found


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)  # nosec B603


def commit_count(repository: Path) -> int:
    """Commits reachable from HEAD; raise when git cannot read the repository."""
    git = _binary("git")
    head = _run([git, "rev-parse", "--verify", "HEAD"], repository)
    if head.returncode != 0:
        raise GateError(f"git cannot resolve HEAD: {head.stderr.strip()}")
    count = _run([git, "rev-list", "--count", "HEAD"], repository)
    if count.returncode != 0 or not count.stdout.strip().isdigit():
        raise GateError(f"git cannot count commits: {count.stderr.strip()}")
    return int(count.stdout)


def scanned_commits(output: str) -> int | None:
    """The commit count gitleaks reports, or None when it reports none."""
    match = SCANNED_RE.search(ANSI_RE.sub("", output))
    return int(match[1]) if match else None


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fail-closed secrets scan; return its exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    repository = Path(args[0] if args else ".")
    try:
        reachable = commit_count(repository)
        result = _run([_binary("gitleaks"), *GITLEAKS_ARGS, "."], repository)
    except GateError as error:
        print(f"gitleaks-gate: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        print(f"gitleaks-gate: gitleaks exited {result.returncode}", file=sys.stderr)
        return result.returncode
    scanned = scanned_commits(result.stdout + result.stderr)
    if not scanned:
        print(
            f"gitleaks-gate: gitleaks scanned {scanned or 0} of {reachable} "
            "reachable commit(s); refusing an empty scan",
            file=sys.stderr,
        )
        return 1
    print(f"gitleaks-gate: OK ({scanned} commit(s) scanned, {reachable} reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
