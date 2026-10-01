"""Workflow-shape and repository-hygiene tests (G2.1).

Stdlib only; run with ``python3 -m unittest discover -s tests -v``.
The checks live in ``workflow_checks.py`` and fail closed.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_checks as wc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WF_DIR.glob("*.y*ml"))
ACTIONS = sorted((ROOT / ".github" / "actions").glob("**/action.y*ml"))
SHA = "a" * 40
PR_OK = (
    "on:\n  pull_request:\n    branches: [main]\n"
    "permissions:\n  contents: read\n"
    "jobs:\n  lint:  # trailing comment\n    runs-on: ubuntu-latest\n"
    f"    steps:\n      - uses: actions/checkout@{SHA}  # v1\n"
)


class RealWorkflowsTest(unittest.TestCase):
    def test_workflows_exist(self):
        self.assertTrue(WORKFLOWS)

    def test_every_workflow_passes_check_workflow(self):
        for wf in WORKFLOWS:
            self.assertEqual(wc.check_workflow(wf.read_text()), [], wf.name)

    def test_every_composite_action_is_pinned(self):
        for act in ACTIONS:
            self.assertEqual(wc.check_action(act.read_text()), [], str(act))

    def test_autorelease_shape(self):
        text = (WF_DIR / "autorelease.yml").read_text()
        self.assertEqual(wc.check_autorelease(text), [])


class FailClosedFixtureTest(unittest.TestCase):
    """Each fixture must be reported; the good fixture must pass."""

    def assertViolation(self, text, needle=""):
        found = wc.check_workflow(text)
        self.assertTrue(found, "fixture was not rejected")
        self.assertTrue(any(needle in f for f in found), found)

    def test_good_fixture_passes_with_trailing_comments(self):
        self.assertEqual(wc.check_workflow(PR_OK), [])

    def test_a_quoted_on_key(self):
        self.assertViolation(PR_OK.replace("on:", '"on":', 1), "quoted")

    def test_b_list_form_on(self):
        text = PR_OK.replace(
            "on:\n  pull_request:\n    branches: [main]\n",
            "on: [push, pull_request]\n",
        )
        self.assertViolation(text, "not supported")

    def test_c_four_space_indentation(self):
        text = PR_OK.replace("on:\n  pull_request:", "on:\n    pull_request:")
        self.assertViolation(text, "2 spaces")

    def test_d_unrecognised_job_line(self):
        text = PR_OK.replace("  lint:  # trailing comment", '  "lint": ')
        self.assertViolation(text, "unrecognised job line")
        flow = PR_OK.replace("  lint:  # trailing comment", "  lint: {runs-on: x}")
        self.assertViolation(flow, "unrecognised job line")

    def test_e_flow_style_uses_step(self):
        text = PR_OK.replace(
            f"      - uses: actions/checkout@{SHA}  # v1\n",
            "      - {uses: actions/checkout@v4}\n",
        )
        self.assertViolation(text, "not SHA-pinned")

    def test_pull_request_job_write_permission(self):
        self.assertViolation(PR_OK.replace("contents: read", "contents: write"))

    def test_pull_request_job_without_permissions(self):
        self.assertViolation(PR_OK.replace("permissions:\n  contents: read\n", ""))

    def test_missing_on_is_a_failure(self):
        self.assertViolation(PR_OK.replace("on:", "when:", 1), "on:")

    def test_pull_request_target_rejected(self):
        self.assertViolation(PR_OK.replace("pull_request:", "pull_request_target:"))

    def test_secrets_in_pull_request_workflow(self):
        for snippet in (
            "      - run: echo ${{ secrets.X }}\n",
            "      - run: echo ${{ secrets['X'] }}\n",
            "      - run: echo ${{ toJSON(secrets) }}\n",
        ):
            self.assertViolation(PR_OK + snippet, "secrets")
        inherit = PR_OK.replace(
            "    runs-on: ubuntu-latest\n",
            "    uses: ./.github/workflows/x.yml\n    secrets: inherit\n",
        )
        self.assertViolation(inherit, "secrets")


class AutoreleaseFixtureTest(unittest.TestCase):
    def setUp(self):
        self.good = (WF_DIR / "autorelease.yml").read_text()

    def assertRejected(self, text):
        self.assertTrue(wc.check_autorelease(text))

    def test_tags_filter_rejected(self):
        self.assertRejected(self.good.replace(
            "    branches:\n      - main\n",
            "    branches:\n      - main\n    tags:\n      - 'v*'\n"))

    def test_paths_filter_rejected(self):
        self.assertRejected(self.good.replace(
            "    branches:\n      - main\n",
            "    branches:\n      - main\n    paths:\n      - 'x'\n"))

    def test_extra_branch_rejected(self):
        self.assertRejected(self.good.replace("      - main\n", "      - main\n      - dev\n"))

    def test_forbidden_commands_rejected(self):
        for cmd in ("gh api x", "curl http://x", "wget x", "git push origin", "git commit -m x"):
            self.assertRejected(self.good + f"      - run: {cmd}\n")

    def test_unlisted_command_rejected(self):
        self.assertRejected(self.good + "      - run: echo hi\n")

    def test_extra_secret_rejected(self):
        self.assertRejected(self.good + "      - run: gh release create ${{ secrets.X }}\n")


class RepositoryGrepTest(unittest.TestCase):
    def test_real_tree_has_no_forbidden_strings(self):
        self.assertEqual(wc.scan_repo(ROOT), [])

    def test_hit_in_unlisted_folder_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "docs" / "deep").mkdir(parents=True)
            (tmp / "docs" / "deep" / "note.md").write_text("uses VILNACRM_APP_ID")
            (tmp / "specs").mkdir()
            (tmp / "specs" / "ok.md").write_text("PERSONAL_ACCESS_TOKEN")
            (tmp / ".github").mkdir()
            (tmp / ".github" / "w.yml").write_text("aws-secret-access-key: x")
            hits = wc.scan_repo(tmp)
        self.assertEqual(
            sorted(hits),
            [".github/w.yml: aws-secret-access-key",
             "docs/deep/note.md: VILNACRM_APP_"],
        )

    def test_removed_files_stay_removed(self):
        for name in ("tempate-sync-pat.yml", "template-sync-app.yml", "super-linter.yml"):
            self.assertFalse((WF_DIR / name).exists(), name)
        self.assertFalse((ROOT / "super-linter-output").exists())
        self.assertFalse((ROOT / ".github" / "linters").exists())

    def test_compose_has_no_static_aws_keys(self):
        text = (ROOT / "docker-compose.yml").read_text()
        for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            self.assertNotIn(key, text)

    def test_codeowners(self):
        co = (ROOT / ".github" / "CODEOWNERS").read_text().split()
        self.assertEqual(co, ["*", "@Kravalg"])

    def test_dependabot_ecosystems_and_directories(self):
        dep = (ROOT / ".github" / "dependabot.yml").read_text()
        entries = re.findall(
            r"package-ecosystem:\s*['\"]([^'\"]+)['\"]\s*\n\s*directory:\s*['\"]([^'\"]+)['\"]",
            dep,
        )
        self.assertEqual(sorted(entries), [("github-actions", "/"), ("uv", "/")])


def make_repo(tmp, tags_and_commits):
    """tags_and_commits: list of ('commit', msg) or ('tag', name)."""
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp, check=True, env=env,
                       capture_output=True)

    git("init", "-q")
    for kind, value in tags_and_commits:
        if kind == "commit":
            git("commit", "-q", "--allow-empty", "-m", value)
        else:
            git("tag", value)


class NextReleaseVersionTest(unittest.TestCase):
    script = ROOT / "scripts" / "next_release_version.py"

    def run_helper(self, steps):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, steps)
            out = Path(tmp) / "gh_output"
            env = dict(os.environ, GITHUB_OUTPUT=str(out))
            res = subprocess.run([sys.executable, str(self.script)], cwd=tmp,
                                 env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            data = dict(line.split("=", 1) for line in out.read_text().split())
        return data

    def test_no_tag_feat_is_v0_1_0(self):
        r = self.run_helper([("commit", "feat: init")])
        self.assertEqual((r["skipped"], r["tag"]), ("false", "v0.1.0"))

    def test_chore_only_is_skipped(self):
        r = self.run_helper([("commit", "feat: a"), ("tag", "v0.2.0"),
                             ("commit", "chore: deps")])
        self.assertEqual(r["skipped"], "true")
        self.assertEqual(r["previous"], "v0.2.0")

    def test_fix_is_patch(self):
        r = self.run_helper([("commit", "feat: a"), ("tag", "v0.2.0"),
                             ("commit", "chore: x"), ("commit", "fix(core): y")])
        self.assertEqual(r["tag"], "v0.2.1")

    def test_breaking_below_one_is_minor(self):
        r = self.run_helper([("commit", "a"), ("tag", "v0.2.0"),
                             ("commit", "feat!: drop")])
        self.assertEqual(r["tag"], "v0.3.0")

    def test_breaking_body_below_one_is_minor(self):
        r = self.run_helper([("commit", "a"), ("tag", "v0.2.0"),
                             ("commit", "fix: x\n\nBREAKING CHANGE: gone")])
        self.assertEqual(r["tag"], "v0.3.0")

    def test_breaking_from_one_is_major(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.2.3"),
                             ("commit", "feat!: drop")])
        self.assertEqual(r["tag"], "v2.0.0")

    def test_feat_from_one_is_minor(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.2.3"),
                             ("commit", "feat: more")])
        self.assertEqual(r["tag"], "v1.3.0")

    def test_non_matching_tags_are_ignored(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.2.3"),
                             ("commit", "b"), ("tag", "v1.0.0-rc1"),
                             ("tag", "v9.9.9foo"), ("tag", "v1.10.0"),
                             ("commit", "fix: z")])
        self.assertEqual((r["previous"], r["tag"]), ("v1.10.0", "v1.10.1"))

    def test_many_commits_no_sigpipe(self):
        steps = [("commit", "chore: n")] * 300 + [("commit", "feat: last")]
        r = self.run_helper(steps)
        self.assertEqual(r["tag"], "v0.1.0")

    def test_helper_only_reads_git(self):
        src = self.script.read_text()
        used = set(re.findall(r'git\(\s*\[\s*"([a-z-]+)"', src))
        self.assertEqual(used, {"for-each-ref"})
        self.assertIn('"log"', src)


if __name__ == "__main__":
    unittest.main()
