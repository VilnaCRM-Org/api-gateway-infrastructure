#!/usr/bin/env python3
"""Compute the next release tag from conventional commits (PD-11).

Stdlib only. Reads git history, never writes to the repository. Writes
``skipped``, ``tag`` and ``previous`` to ``$GITHUB_OUTPUT`` when it is set
and prints the same lines to stdout.

Rules:
- the previous release is the highest tag reachable from HEAD that is exactly ``vMAJOR.MINOR.PATCH``
  (tags such as ``v1.0.0-rc1`` or ``v1.2.3foo`` are ignored);
- ``type!:`` or a ``BREAKING CHANGE:`` body line is major, ``feat`` is minor,
  ``fix`` is patch, anything else is not releasable;
- below 1.0.0 a breaking change bumps the minor version.
"""

import os
import re
import shutil
import subprocess  # nosec B404
import sys

TAG_RE = re.compile(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$", re.ASCII)
BREAKING_SUBJECT_RE = re.compile(r"^[a-z]+(\([^)]*\))?!:", re.IGNORECASE)
BREAKING_BODY_RE = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)
FEAT_RE = re.compile(r"^feat(\([^)]*\))?:", re.IGNORECASE)
FIX_RE = re.compile(r"^fix(\([^)]*\))?:", re.IGNORECASE)
RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"


def git(args, cwd):
    exe = shutil.which("git")
    if exe is None:
        raise RuntimeError("git executable not found")
    cmd = [exe, *args]
    result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)  # nosec B603
    return result.stdout


def latest_release_tag(cwd):
    """Return (tag, (major, minor, patch)) or (None, (0, 0, 0))."""
    best = None
    out = git(
        ["for-each-ref", "--merged=HEAD", "--format=%(refname:lstrip=2)", "refs/tags"],
        cwd,
    )
    for name in out.splitlines():
        match = TAG_RE.match(name)
        if match:
            version = tuple(int(part) for part in match.groups())
            if best is None or version > best[1]:
                best = (name, version)
    return best if best else (None, (0, 0, 0))


def commits_since(tag, cwd):
    """Return a list of (subject, body) since ``tag`` (all history if None)."""
    fmt = f"--format=%s{FIELD_SEP}%b{RECORD_SEP}"
    args = ["log", fmt] + ([f"{tag}..HEAD"] if tag else ["HEAD"])
    out = git(args, cwd)
    commits = []
    for record in out.split(RECORD_SEP):
        if not record.strip():
            continue
        subject, _, body = record.strip("\n").partition(FIELD_SEP)
        commits.append((subject.strip(), body))
    return commits


def classify(commits):
    bump = None
    for subject, body in commits:
        if BREAKING_SUBJECT_RE.match(subject) or BREAKING_BODY_RE.search(body):
            return "major"
        if FEAT_RE.match(subject):
            bump = "minor"
        elif FIX_RE.match(subject) and bump is None:
            bump = "patch"
    return bump


def next_release(cwd="."):
    """Return a dict with ``skipped``, ``tag`` and ``previous``."""
    previous, (major, minor, patch) = latest_release_tag(cwd)
    bump = classify(commits_since(previous, cwd))
    if bump == "major" and major == 0:
        bump = "minor"
    if bump is None:
        return {"skipped": "true", "tag": "", "previous": previous or ""}
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return {
        "skipped": "false",
        "tag": f"v{major}.{minor}.{patch}",
        "previous": previous or "",
    }


def main():
    result = next_release()
    lines = [f"{key}={value}" for key, value in result.items()]
    print("\n".join(lines))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
