"""Workflow-shape and repository-hygiene tests (G2.1).

Needs PyYAML (a G3.1 dev dependency; tests fail without it) and the
standard library only; run with ``python3 -m unittest discover -s tests -v``.
The checks live in ``workflow_checks.py`` and fail closed.
"""

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workflow_checks as wc  # noqa: E402

GIT = shutil.which("git")
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


class PyYamlRequiredTest(unittest.TestCase):
    def test_pyyaml_importable(self):
        self.assertIsNotNone(wc.yaml, "PyYAML is required (G3.1 dev dependency)")


PR_WRITE = PR_OK.replace("contents: read", "contents: write")


class FailClosedFixtureTest(unittest.TestCase):
    """Every fixture is a pull_request workflow that must be rejected."""

    def assertViolation(self, text, needle=""):
        found = wc.check_workflow(text)
        self.assertTrue(found, "fixture was not rejected")
        self.assertTrue(any(needle in f for f in found), found)

    def test_good_fixture_passes_with_trailing_comments(self):
        self.assertEqual(wc.check_workflow(PR_OK), [])

    def test_a_quoted_on_key(self):
        self.assertViolation(PR_WRITE.replace("on:", '"on":', 1), "contents")

    def test_b_list_form_on(self):
        text = PR_WRITE.replace(
            "on:\n  pull_request:\n    branches: [main]\n",
            "on: [push, pull_request]\n",
        )
        self.assertViolation(text, "contents")

    def test_c_four_space_indentation(self):
        text = PR_WRITE.replace("on:\n  pull_request:", "on:\n    pull_request:")
        self.assertViolation(text, "contents")

    def test_d_quoted_and_flow_job_lines(self):
        self.assertViolation(PR_WRITE.replace("  lint:  # trailing comment", '  "lint": '))
        flow = (
            "on: pull_request\npermissions: {contents: read}\n"
            "jobs: {lint: {runs-on: x, permissions: {contents: write}}}\n"
        )
        self.assertViolation(flow, "contents")

    def test_e_flow_style_uses_step(self):
        text = PR_OK.replace(
            f"      - uses: actions/checkout@{SHA}  # v1\n",
            "      - {uses: actions/checkout@v4}\n",
        )
        self.assertViolation(text, "not SHA-pinned")

    def test_1_jobs_indented_four_spaces(self):
        text = (
            "on: pull_request\npermissions:\n    contents: read\n"
            "jobs:\n    lint:\n        runs-on: x\n"
            "        permissions:\n            contents: write\n"
        )
        self.assertViolation(text, "contents")

    def test_2_quoted_permissions_key(self):
        text = PR_OK.replace(
            "    runs-on: ubuntu-latest\n",
            '    runs-on: ubuntu-latest\n    "permissions": {contents: write}\n',
        )
        self.assertViolation(text, "contents")

    def test_3_quoted_uses_key_and_next_line_value(self):
        quoted = PR_OK.replace(
            f"      - uses: actions/checkout@{SHA}  # v1\n",
            '      - "uses": actions/checkout@v4\n',
        )
        self.assertViolation(quoted, "not SHA-pinned")
        nextline = PR_OK.replace(
            f"      - uses: actions/checkout@{SHA}  # v1\n",
            "      - uses:\n          actions/checkout@v4\n",
        )
        self.assertViolation(nextline, "not SHA-pinned")

    def test_reusable_workflow_job_uses_is_checked(self):
        text = PR_OK.replace(
            "    runs-on: ubuntu-latest\n",
            "    uses: org/repo/.github/workflows/x.yml@main\n",
        ).replace(
            f"    steps:\n      - uses: actions/checkout@{SHA}  # v1\n", ""
        )
        self.assertViolation(text, "not SHA-pinned")

    def test_scalar_permissions_rejected(self):
        for scalar in ("read-all", "write-all"):
            self.assertViolation(
                PR_OK.replace("permissions:\n  contents: read\n", f"permissions: {scalar}\n"),
                "contents",
            )

    def test_unparseable_and_duplicate_keys_fail(self):
        self.assertViolation("on: [\n", "unparseable")
        self.assertViolation(PR_OK + "permissions:\n  contents: write\n", "duplicate")

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


class DeliberateBypassFixtureTest(unittest.TestCase):
    def test_secret_after_hash_inside_string_is_found(self):
        text = PR_OK.replace(
            "    runs-on: ubuntu-latest\n",
            '    runs-on: ubuntu-latest\n    env: {T: "x #${{ secrets.K }}"}\n',
        )
        self.assertTrue(any("secrets" in x for x in wc.check_workflow(text)))

    def test_secrets_key_is_found(self):
        text = PR_OK.replace(
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    secrets: inherit\n",
        )
        self.assertTrue(any("secrets" in x for x in wc.check_workflow(text)))

    def test_merge_key_rejected(self):
        text = (
            "on: pull_request\npermissions: &p {contents: read}\n"
            "jobs:\n  a:\n    runs-on: x\n    <<: {permissions: {contents: write}}\n"
        )
        self.assertTrue(any("merge" in x for x in wc.check_workflow(text)))

    def test_multi_document_rejected(self):
        found = wc.check_workflow(PR_OK + "---\n" + PR_WRITE)
        self.assertTrue(any("unparseable" in x for x in found), found)


class CompositeActionTest(unittest.TestCase):
    def test_unpinned_composite_step_rejected(self):
        text = "runs:\n  using: composite\n  steps:\n    - uses: a/b@v1\n      shell: bash\n"
        self.assertTrue(wc.check_action(text))
        self.assertEqual(wc.check_action(text.replace("v1", SHA)), [])


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

    def test_unpinned_or_other_action_rejected(self):
        self.assertRejected(self.good.replace("@" + self.good.split("checkout@")[1][:40], "@v7"))
        self.assertRejected(self.good.replace("actions/checkout@", "evil/other@"))

    def test_shell_chaining_rejected(self):
        for tail in ("; echo x", " && echo x", " || true", " | cat", " `id`", " $(id)"):
            self.assertRejected(self.good + f"      - run: gh release create{tail}\n")

    def test_any_secrets_reference_rejected(self):
        self.assertRejected(self.good.replace("github.token", "secrets.GITHUB_TOKEN"))

    def test_hash_hides_chained_command(self):
        block = "      - run: |\n          gh release create x"
        self.assertRejected(self.good + block + ' " #"; curl evil\n')
        self.assertRejected(self.good + block + ' " #" curl evil\n')
        self.assertRejected(self.good + block + " # comment\n")

    def test_extra_step_job_and_top_keys_rejected(self):
        marker = "    runs-on: ubuntu-latest\n"
        for extra in ("    container: alpine\n", "    services: {a: {image: x}}\n",
                      "    env: {BASH_ENV: x}\n", "    defaults: {run: {shell: bash}}\n"):
            self.assertRejected(self.good.replace(marker, marker + extra))
        step = "        run: python3 scripts/next_release_version.py\n"
        self.assertRejected(self.good.replace(step, step + "        shell: bash -c 'x'\n"))
        self.assertRejected(self.good.replace(step, step + "        working-directory: /tmp\n"))
        self.assertRejected("env:\n  BASH_ENV: x\n" + self.good)

    def test_step_env_keys_are_limited(self):
        marker = "          TAG: ${{ steps.version.outputs.tag }}\n"
        self.assertRejected(self.good.replace(marker, marker + "          BASH_ENV: /x\n"))

    def test_token_only_as_gh_token(self):
        marker = "          TAG: ${{ steps.version.outputs.tag }}\n"
        self.assertRejected(self.good.replace(marker, "          TAG: ${{ github.token }}\n"))
        self.assertRejected(self.good.replace(
            "          persist-credentials: false\n",
            "          persist-credentials: false\n          token: ${{ github.token }}\n"))
        self.assertRejected(self.good.replace("GH_TOKEN: ${{ github.token }}", "GH_TOKEN: abc"))

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


def git_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t.invalid",
    )
    return env


def make_repo(tmp, steps):
    """steps: ('commit', msg), ('tag', name) or ('git', *args)."""
    env = git_env()

    def git(*args):
        cmd = [GIT, *args]
        subprocess.run(cmd, cwd=tmp, check=True, env=env, capture_output=True)  # nosec B603

    git("init", "-q", "-b", "main")
    for kind, *rest in steps:
        if kind == "commit":
            git("commit", "-q", "--allow-empty", "-m", rest[0])
        elif kind == "tag":
            git("tag", rest[0])
        else:
            git(*rest)


class MakeRepoIsolationTest(unittest.TestCase):
    def test_git_is_resolved(self):
        self.assertTrue(GIT and os.path.isabs(GIT))

    def test_make_repo_raises_on_failing_git_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(subprocess.CalledProcessError):
                make_repo(tmp, [("commit", "a"), ("git", "checkout", "-q", "no-such-ref")])

    def test_commits_use_the_isolated_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, [("commit", "a")])
            cmd = [GIT, "log", "--format=%ae|%ce"]
            env = git_env()
            res = subprocess.run(cmd, cwd=tmp, check=True, env=env, capture_output=True, text=True)  # nosec B603
            out = res.stdout.strip()
        self.assertEqual(out, "t@t.invalid|t@t.invalid")


class NextReleaseVersionTest(unittest.TestCase):
    script = ROOT / "scripts" / "next_release_version.py"

    def run_helper(self, steps):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, steps)
            out = Path(tmp) / "gh_output"
            env = dict(git_env(), GITHUB_OUTPUT=str(out))
            cmd = [sys.executable, str(self.script)]
            res = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True)  # nosec B603
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

    def test_mixed_case_and_scoped_breaking_types(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.0.0"), ("commit", "Feat: x")])
        self.assertEqual(r["tag"], "v1.1.0")
        r = self.run_helper([("commit", "a"), ("tag", "v1.0.0"), ("commit", "FIX: x")])
        self.assertEqual(r["tag"], "v1.0.1")
        r = self.run_helper([("commit", "a"), ("tag", "v1.0.0"),
                             ("commit", "fix(scope)!: x")])
        self.assertEqual(r["tag"], "v2.0.0")

    def test_breaking_change_footer_stays_uppercase(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.0.0"),
                             ("commit", "chore: x\n\nbreaking change: no")])
        self.assertEqual(r["skipped"], "true")

    def test_unreachable_tag_is_ignored(self):
        r = self.run_helper([
            ("commit", "feat: base"), ("tag", "v1.0.0"),
            ("git", "checkout", "-q", "-b", "side"),
            ("commit", "chore: side"), ("tag", "v5.0.0"),
            ("git", "checkout", "-q", "main"),
            ("commit", "fix: on main"),
        ])
        self.assertEqual((r["previous"], r["tag"]), ("v1.0.0", "v1.0.1"))

    def test_annotated_tags_are_selected(self):
        r = self.run_helper([("commit", "a"),
                             ("git", "tag", "-a", "v1.2.3", "-m", "release"),
                             ("commit", "feat: z")])
        self.assertEqual((r["previous"], r["tag"]), ("v1.2.3", "v1.3.0"))

    def test_non_ascii_digit_tag_is_ignored(self):
        r = self.run_helper([("commit", "a"), ("tag", "v1.0.0"),
                             ("tag", "v\u0663.0.0"), ("commit", "fix: z")])
        self.assertEqual(r["tag"], "v1.0.1")

    def test_main_without_github_output_prints_only(self):
        spec = importlib.util.spec_from_file_location("nrv", self.script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(tmp, [("commit", "feat: x")])
            old_cwd, old_env = os.getcwd(), dict(os.environ)
            os.environ.pop("GITHUB_OUTPUT", None)
            buf = io.StringIO()
            try:
                os.chdir(tmp)
                with contextlib.redirect_stdout(buf):
                    self.assertEqual(mod.main(), 0)
            finally:
                os.chdir(old_cwd)
                os.environ.clear()
                os.environ.update(old_env)
        self.assertIn("tag=v0.1.0", buf.getvalue())

    def test_helper_only_reads_git(self):
        src = self.script.read_text()
        used = set(re.findall(r'git\(\s*\[\s*"([a-z-]+)"', src))
        self.assertEqual(used, {"for-each-ref"})
        self.assertIn('"log"', src)


if __name__ == "__main__":
    unittest.main()
