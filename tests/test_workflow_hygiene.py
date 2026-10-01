"""Workflow-shape and repository-hygiene checks (G2.1).

Stdlib only; run with ``python3 -m unittest discover -s tests -v``.
G3.1/G3.2 may adopt this module into the pytest battery unchanged.
No YAML parser is available in the stdlib, so the checks use line-based
scanning that matches the plain block-style YAML used by our workflows.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)")
FORBIDDEN = (
    "PERSONAL_ACCESS_TOKEN",
    "VILNACRM_APP_",
    "git-auto-commit-action",
    "pull_request_target",
)
# Scanned for forbidden strings. specs/ documents the removed names and
# tests/ holds the names themselves, so both are excluded.
SCAN_ROOTS = (".github", "docker-compose.yml", "Makefile", "README.md",
              "CONTRIBUTING.md", "AGENTS.md", "pulumi", "Dockerfile")


def strip_comment(line):
    return re.sub(r"\s+#.*$", "", line)


def triggers(text):
    """Return the set of top-level `on:` event names (block or inline form)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^on:\s*(.*)$", line)
        if not m:
            continue
        rest = strip_comment(m.group(1)).strip()
        if rest:
            return set(re.findall(r"[A-Za-z_]+", rest.strip("[]{}")))
        events = set()
        for nxt in lines[i + 1:]:
            if nxt.strip() and not nxt.startswith(" "):
                break
            em = re.match(r"^  ([A-Za-z_]+):", nxt)
            if em:
                events.add(em.group(1))
        return events
    return set()


def jobs_blocks(text):
    """Map job id -> its text block (jobs are indented two spaces)."""
    lines = text.splitlines()
    out, cur, in_jobs = {}, None, False
    for line in lines:
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs and line and not line.startswith(" "):
            in_jobs = False
        if not in_jobs:
            continue
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def permissions(block):
    """Return the permissions mapping of a text block, or None if absent."""
    lines = block.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)permissions:\s*(.*)$", line)
        if not m:
            continue
        indent, rest = len(m.group(1)), strip_comment(m.group(2)).strip()
        if rest:
            return {"*": rest}
        perms = {}
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            if len(nxt) - len(nxt.lstrip()) <= indent:
                break
            pm = re.match(r"^\s+([a-z-]+):\s*(\S+)", strip_comment(nxt))
            if pm:
                perms[pm.group(1)] = pm.group(2)
        return perms
    return None


class WorkflowShapeTest(unittest.TestCase):
    def test_workflows_exist(self):
        self.assertTrue(WORKFLOWS, "no workflow files found")

    def test_every_uses_is_pinned_to_a_40_hex_sha(self):
        for wf in WORKFLOWS:
            for n, line in enumerate(wf.read_text().splitlines(), 1):
                m = USES_RE.match(strip_comment(line))
                if not m or m.group(1).startswith("./"):
                    continue
                ref = m.group(1).rpartition("@")[2]
                self.assertRegex(
                    ref, SHA_RE, f"{wf.name}:{n} not SHA-pinned: {m.group(1)}"
                )
                self.assertIn("#", line, f"{wf.name}:{n} lacks a tag comment")

    def test_pull_request_jobs_are_contents_read(self):
        for wf in WORKFLOWS:
            text = wf.read_text()
            if "pull_request" not in triggers(text):
                continue
            top = permissions(text.split("\njobs:")[0])
            for job, block in jobs_blocks(text).items():
                perms = permissions(block)
                if perms is None:
                    perms = top
                self.assertIsNotNone(
                    perms, f"{wf.name}:{job} has no permissions block"
                )
                self.assertEqual(
                    perms.get("contents"), "read",
                    f"{wf.name}:{job} must be contents: read",
                )
                writes = {k: v for k, v in perms.items() if v == "write"}
                self.assertFalse(writes, f"{wf.name}:{job} writes {writes}")


class ShapeHelperSelfTest(unittest.TestCase):
    """Prove the checkers can fail: a pull_request job without read-only."""

    BAD = (
        "on:\n  pull_request:\n    branches: [main]\n"
        "jobs:\n  lint:\n    runs-on: ubuntu-latest\n"
        "    permissions:\n      contents: write\n"
    )

    def test_detects_pull_request_trigger_and_write(self):
        self.assertIn("pull_request", triggers(self.BAD))
        block = jobs_blocks(self.BAD)["lint"]
        self.assertEqual(permissions(block), {"contents": "write"})

    def test_unpinned_ref_is_not_a_sha(self):
        self.assertIsNone(SHA_RE.match("v4"))
        self.assertIsNotNone(SHA_RE.match("a" * 40))


class AutoreleaseShapeTest(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / ".github" / "workflows" / "autorelease.yml"
        self.text = self.path.read_text()

    def test_runs_on_main_push_only(self):
        self.assertEqual(triggers(self.text), {"push"})
        self.assertRegex(self.text, r"(?m)^\s+branches:\s*\[?\s*-?\s*\"?main\"?")

    def test_pushes_no_commit(self):
        body = "\n".join(strip_comment(x) for x in self.text.splitlines())
        for needle in ("git push", "git commit", "git add",
                       "conventional-changelog-action", "create-release"):
            self.assertNotIn(needle, body)

    def test_uses_github_token_only(self):
        for tok in re.findall(r"secrets\.([A-Za-z0-9_]+)", self.text):
            self.assertEqual(tok, "GITHUB_TOKEN")

    def test_release_job_may_write_contents_only(self):
        for block in jobs_blocks(self.text).values():
            perms = permissions(block)
            self.assertEqual(perms, {"contents": "write"})


class RepositoryGrepTest(unittest.TestCase):
    def test_no_forbidden_strings(self):
        hits = []
        for entry in SCAN_ROOTS:
            base = ROOT / entry
            files = [base] if base.is_file() else (
                [p for p in base.rglob("*") if p.is_file()] if base.exists() else []
            )
            for f in files:
                try:
                    text = f.read_text()
                except UnicodeDecodeError:
                    continue
                for s in FORBIDDEN:
                    if s in text:
                        hits.append(f"{f.relative_to(ROOT)}: {s}")
        self.assertEqual(hits, [])

    def test_removed_files_stay_removed(self):
        wf = ROOT / ".github" / "workflows"
        for name in ("tempate-sync-pat.yml", "template-sync-app.yml",
                     "super-linter.yml"):
            self.assertFalse((wf / name).exists(), name)

    def test_compose_has_no_static_aws_keys(self):
        text = (ROOT / "docker-compose.yml").read_text()
        for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
                    "AWS_SESSION_TOKEN"):
            self.assertNotIn(key, text)

    def test_codeowners_and_dependabot(self):
        co = (ROOT / ".github" / "CODEOWNERS").read_text().split()
        self.assertEqual(co, ["*", "@Kravalg"])
        dep = (ROOT / ".github" / "dependabot.yml").read_text()
        for eco in ("uv", "github-actions"):
            self.assertRegex(dep, rf"package-ecosystem:\s*['\"]{eco}['\"]")


if __name__ == "__main__":
    unittest.main()
