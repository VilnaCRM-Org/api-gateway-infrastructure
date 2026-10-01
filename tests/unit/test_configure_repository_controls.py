"""The controls CLI: dry-run, `--check` and the apply sequence (G2.2).

Nothing here calls GitHub: `gh` is replaced by a recording fake, so no write
ever leaves the test (the apply path runs against the fake only).
"""

from __future__ import annotations

import copy
import json
import runpy
import subprocess  # nosec B404
from pathlib import Path

import pytest

import _github_repository_controls as rc
import configure_github_repository_controls as cli
from stack_fixtures import ROOT, committed_documents, key

FIXTURES = ROOT / "tests" / "fixtures" / "repository-controls"
REPO = "VilnaCRM-Org/api-gateway-infrastructure"
REVIEWER_ID = 9444106
LISTED_NAME = "AWS_SECRET_ACCESS_KEY"


def fixture_text(name: str) -> str:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    for stack, document in committed_documents().items():
        text = text.replace(
            "{account:%s}" % stack, document["config"][key("awsAccountId")]
        )
    return text


def readback() -> dict:
    return json.loads(fixture_text("readback.json"))


# --- the gh wrapper ----------------------------------------------------------


class Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def fake_subprocess(monkeypatch: pytest.MonkeyPatch, *results: Completed) -> list:
    calls: list = []
    queue = list(results)

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return queue.pop(0)

    monkeypatch.setattr(cli.subprocess, "run", run)
    return calls


def test_run_gh_api_parses_json_and_sends_input(monkeypatch) -> None:
    calls = fake_subprocess(monkeypatch, Completed(stdout='{"a": 1}'))
    assert cli._run_gh_api(["x", "--method", "PUT"], input_payload={"b": 2}) == {"a": 1}
    command, kwargs = calls[0]
    assert command == ["gh", "api", "x", "--method", "PUT", "--input", "-"]
    assert kwargs["input"] == '{"b": 2}'
    assert kwargs["capture_output"] is True


def test_run_gh_api_response_forms(monkeypatch) -> None:
    calls = fake_subprocess(
        monkeypatch,
        Completed(stdout=""),
        Completed(stdout="[1]"),
        Completed(stdout="3"),
    )
    assert cli._run_gh_api(["x"]) == {}
    assert cli._run_gh_api(["x"]) == [1]
    assert cli._run_gh_api(["x"]) == {}
    assert calls[0][1]["input"] is None


def test_run_gh_api_errors(monkeypatch) -> None:
    fake_subprocess(
        monkeypatch,
        Completed(1, stderr=" boom "),
        Completed(1, stdout="out"),
        Completed(1),
    )
    for detail in ("boom", "out", "gh api failed"):
        with pytest.raises(RuntimeError, match=detail):
            cli._run_gh_api(["x"])


# --- a fake GitHub -----------------------------------------------------------


class FakeGitHub:
    """Serves reads from a readback and records every write.

    `first` holds responses served once, before the readback takes over, to
    model a repository that differs from the definition until applied.
    """

    def __init__(self, data: dict, *, admin: bool = True, first=None) -> None:
        self.data = data
        self.admin = admin
        self.first = dict(first or {})
        self.writes: list = []

    def __call__(self, args, *, input_payload=None):
        endpoint = args[0]
        method = args[2] if len(args) > 2 and args[1] == "--method" else "GET"
        if method != "GET":
            self.writes.append((method, endpoint, input_payload))
            return {}
        if endpoint in self.first:
            return self.first.pop(endpoint)
        return self.read(endpoint)

    def read(self, endpoint: str):
        if endpoint == f"repos/{REPO}":
            return {"permissions": {"admin": self.admin}}
        if endpoint == "users/Kravalg":
            return {"id": REVIEWER_ID}
        if endpoint == f"repos/{REPO}/rulesets":
            return [{"id": 101, "name": "main", "target": "branch"}, "x"]
        if endpoint == f"repos/{REPO}/rulesets/101":
            return self.data["ruleset"]
        parts = endpoint.removeprefix(f"repos/{REPO}/environments/").split("/")
        name = parts[0]
        if self.data["environments"].get(name) is None:
            raise RuntimeError("Not Found")
        env = copy.deepcopy(self.data["environments"][name])
        if len(parts) == 1:
            return env
        if parts[1] == "deployment-branch-policies":
            return listing(env["deployment_branch_policies"])
        if parts[1].startswith("secrets"):
            rows = [{"name": LISTED_NAME}] * self.data["secrets"][name]
            return {"total_count": len(rows), "secrets": rows}
        rows = [
            {"name": k, "value": v} for k, v in self.data["variables"][name].items()
        ]
        return {"total_count": len(rows), "variables": rows}


def listing(policies: list) -> dict:
    return {"total_count": len(policies), "branch_policies": policies}


def install(monkeypatch, data=None, **kwargs) -> FakeGitHub:
    fake = FakeGitHub(data if data is not None else readback(), **kwargs)
    monkeypatch.setattr(cli, "_run_gh_api", fake)
    return fake


# --- reads -------------------------------------------------------------------


def test_read_live_matches_the_fixture_readback(monkeypatch) -> None:
    install(monkeypatch)
    live = cli.read_live(REPO)
    expected = readback()
    assert live["ruleset"] == expected["ruleset"]
    assert live["variables"] == expected["variables"]
    assert live["secrets"] == expected["secrets"]
    for name in rc.ENVIRONMENTS:
        assert (
            live["environments"][name]["deployment_branch_policies"]
            == (expected["environments"][name]["deployment_branch_policies"])
        )


def test_main_ruleset_edge_forms(monkeypatch) -> None:
    responses = iter(
        [
            {},
            [{"id": "x", "name": "main", "target": "branch"}],
            [{"id": 5, "name": "main", "target": "branch"}],
            [],
        ]
    )
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: next(responses))
    assert cli._main_ruleset(REPO) is None
    assert cli._main_ruleset(REPO) is None
    assert cli._main_ruleset(REPO) is None
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: [])
    assert cli._main_ruleset(REPO) is None


def test_main_ruleset_skips_other_entries(monkeypatch) -> None:
    fake = install(monkeypatch)
    fake.read_rulesets = [
        "x",
        {"id": 1, "name": "other", "target": "branch"},
        {"id": 101, "name": "main", "target": "branch"},
    ]
    original = fake.read
    fake.read = lambda e: (
        fake.read_rulesets if e == f"repos/{REPO}/rulesets" else original(e)
    )
    assert cli._main_ruleset(REPO) == fake.data["ruleset"]


def test_user_and_admin_lookups(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: {"id": 3})
    assert cli._github_user_id("x") == 3
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: [])
    with pytest.raises(ValueError, match="Could not resolve"):
        cli._github_user_id("x")
    assert cli._repo_admin_allowed(REPO) is False
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: {"permissions": 1})
    assert cli._repo_admin_allowed(REPO) is False
    monkeypatch.setattr(
        cli, "_run_gh_api", lambda args, **_: {"permissions": {"admin": True}}
    )
    assert cli._repo_admin_allowed(REPO) is True


def test_read_environment_and_variable_failures(monkeypatch) -> None:
    def failing(args, **_):
        raise RuntimeError("no")

    monkeypatch.setattr(cli, "_run_gh_api", failing)
    assert cli._read_environment(REPO, "test") is None
    assert cli._read_variables(REPO, "test") is None
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: [])
    assert cli._read_environment(REPO, "test") is None
    assert cli._read_variables(REPO, "test") is None


@pytest.mark.parametrize(
    "response",
    [
        {"total_count": 2, "variables": [{"name": "A", "value": "1"}]},
        {"total_count": 1, "variables": ["x"]},
        {"total_count": 1, "variables": [{"name": "A", "value": 1}]},
        {"total_count": 2, "variables": [{"name": "A", "value": "1"}] * 2},
        {"total_count": True, "variables": []},
    ],
)
def test_incomplete_variable_pages_are_unreadable(monkeypatch, response) -> None:
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: response)
    assert cli._read_variables(REPO, "test") is None


# --- dry run -----------------------------------------------------------------


def test_dry_run_is_offline_and_equals_the_fixture(monkeypatch, capsys) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not call gh")

    monkeypatch.setattr(cli.subprocess, "run", forbidden)
    assert (
        cli.main(["--repo", REPO, "--reviewer-id", str(REVIEWER_ID), "--dry-run"]) == 0
    )
    assert json.loads(capsys.readouterr().out) == json.loads(
        fixture_text("dry-run.json")
    )
    assert cli.main(["--repo", REPO, "--reviewer-id", str(REVIEWER_ID)]) == 0


def test_dry_run_resolves_the_reviewer_with_a_read(monkeypatch, capsys) -> None:
    fake = install(monkeypatch)
    assert cli.main(["--repo", REPO]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(
        fixture_text("dry-run.json")
    )
    assert fake.writes == []


# --- check -------------------------------------------------------------------


def test_check_live_passes_on_the_fixture(monkeypatch, capsys) -> None:
    fake = install(monkeypatch)
    assert cli.main(["--repo", REPO, "--check"]) == 0
    assert json.loads(capsys.readouterr().out) == {"check": {"differences": []}}
    assert fake.writes == []


def write_readback(tmp_path: Path, mutate) -> Path:
    data = readback()
    mutate(data)
    path = tmp_path / "readback.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def check_file(path: Path) -> list[str]:
    return cli.check(REPO, "Kravalg", reviewer_id=REVIEWER_ID, readback_file=path)


def test_check_file_passes_without_gh(monkeypatch, tmp_path, capsys) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("a readback file must not call gh")

    monkeypatch.setattr(cli.subprocess, "run", forbidden)
    path = write_readback(tmp_path, lambda d: None)
    argv = ["--repo", REPO, "--reviewer-id", str(REVIEWER_ID), "--check"]
    assert cli.main([*argv, "--readback-file", str(path)]) == 0


def test_check_fails_on_an_extra_bypass_actor(tmp_path, capsys) -> None:
    actor = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
    path = write_readback(
        tmp_path, lambda d: d["ruleset"]["bypass_actors"].append(actor)
    )
    argv = ["--repo", REPO, "--reviewer-id", str(REVIEWER_ID), "--check"]
    assert cli.main([*argv, "--readback-file", str(path)]) == 1
    differences = json.loads(capsys.readouterr().out)["check"]["differences"]
    assert differences == ["Ruleset has 1 bypass actor(s)."]


def test_check_fails_on_a_wrong_role_arn(tmp_path, capsys) -> None:
    def wrong(data: dict) -> None:
        data["variables"]["test-preview"]["AWS_PREVIEW_ROLE_ARN"] = data["variables"][
            "prod-preview"
        ]["AWS_PREVIEW_ROLE_ARN"]

    path = write_readback(tmp_path, wrong)
    argv = ["--repo", REPO, "--reviewer-id", str(REVIEWER_ID), "--check"]
    assert cli.main([*argv, "--readback-file", str(path)]) == 1
    differences = json.loads(capsys.readouterr().out)["check"]["differences"]
    assert differences == [
        "test-preview variable AWS_PREVIEW_ROLE_ARN has the wrong value."
    ]


def test_check_file_errors(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.json"
    argv = ["--repo", REPO, "--reviewer-id", "1", "--check", "--readback-file"]
    assert cli.main([*argv, str(missing)]) == 1
    assert "error:" in capsys.readouterr().err
    listing = tmp_path / "list.json"
    listing.write_text("[]", encoding="utf-8")
    assert cli.main([*argv, str(listing)]) == 1
    assert "must be a JSON object" in capsys.readouterr().err
    assert cli.main(["--repo", REPO, "--readback-file", str(listing)]) == 1
    assert "only valid with --check" in capsys.readouterr().err


# --- apply (against the fake only) -------------------------------------------


def test_apply_requires_admin(monkeypatch, capsys) -> None:
    fake = install(monkeypatch, admin=False)
    assert cli.main(["--repo", REPO, "--apply"]) == 1
    assert "admin rights" in capsys.readouterr().err
    assert fake.writes == []


ENV = f"repos/{REPO}/environments"
VARS = "variables?per_page=100"


def test_apply_converges_in_order_and_verifies(monkeypatch, capsys) -> None:
    stale_vars = {
        "total_count": 1,
        "variables": [{"name": "AWS_APPLY_ROLE_ARN", "value": "old"}],
    }
    first = {
        f"repos/{REPO}/rulesets": [],
        f"{ENV}/test/deployment-branch-policies": listing(
            [
                {"id": 9, "name": "other", "type": "branch"},
                {"id": 8, "name": "main", "type": "branch"},
                {"id": 7, "name": "main", "type": "branch"},
            ]
        ),
        f"{ENV}/prod/deployment-branch-policies": listing([]),
        f"{ENV}/test-preview/{VARS}": {"total_count": 0, "variables": []},
        f"{ENV}/test/{VARS}": stale_vars,
    }
    fake = install(monkeypatch, first=first)
    assert cli.main(["--repo", REPO, "--apply"]) == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True
    writes = [(m, e.removeprefix(f"repos/{REPO}/"), p) for m, e, p in fake.writes]
    assert writes[0] == ("POST", "rulesets", rc.ruleset_payload())
    assert writes[1] == (
        "PUT",
        "environments/test-preview",
        rc.environment_payload("test-preview", REVIEWER_ID),
    )
    steps = [(m, e) for m, e, _ in writes]
    assert ("DELETE", "environments/test/deployment-branch-policies/9") in steps
    assert ("DELETE", "environments/test/deployment-branch-policies/8") in steps
    assert ("DELETE", "environments/test/deployment-branch-policies/7") not in steps
    assert ("POST", "environments/prod/deployment-branch-policies") in steps
    assert ("PATCH", "environments/test/variables/AWS_APPLY_ROLE_ARN") in steps
    assert ("POST", "environments/test/variables") in steps
    assert ("POST", "environments/test-preview/variables") in steps
    assert not any(m == "DELETE" and "variables" in e for m, e in steps)


def differing_ruleset() -> dict:
    data = readback()
    data["ruleset"]["bypass_actors"].append({"actor_id": 1})
    data["ruleset"]["rules"].append({"type": "update"})
    return data


def test_apply_refuses_to_replace_a_differing_ruleset(monkeypatch, capsys) -> None:
    fake = install(monkeypatch, differing_ruleset())
    assert cli.main(["--repo", REPO, "--apply"]) == 1
    err = capsys.readouterr().err
    assert "would replace it" in err
    assert "1 bypass actor(s)" in err and "unexpected update rule" in err
    assert "pass --replace" in err
    assert fake.writes == []


def test_apply_replace_proceeds_and_still_verifies(monkeypatch, capsys) -> None:
    fake = install(monkeypatch, differing_ruleset())
    assert cli.main(["--repo", REPO, "--apply", "--replace"]) == 1
    captured = capsys.readouterr()
    assert "1 bypass actor(s)" in captured.err
    assert (fake.writes[0][0], fake.writes[0][1]) == (
        "PUT",
        f"repos/{REPO}/rulesets/101",
    )


def test_apply_of_a_matching_ruleset_needs_no_replace(monkeypatch, capsys) -> None:
    fake = install(monkeypatch)
    assert cli.main(["--repo", REPO, "--apply"]) == 0
    assert "would replace" not in capsys.readouterr().err
    assert fake.writes[0][1] == f"repos/{REPO}/rulesets/101"


def test_replace_needs_apply(capsys) -> None:
    assert cli.main(["--repo", REPO, "--replace", "--reviewer-id", "1"]) == 1
    assert "only valid with --apply" in capsys.readouterr().err


def test_check_counts_secrets_and_never_prints_a_name(monkeypatch, capsys) -> None:
    data = readback()
    data["secrets"]["prod"] = 1
    install(monkeypatch, data)
    assert cli.main(["--repo", REPO, "--check"]) == 1
    captured = capsys.readouterr()
    differences = json.loads(captured.out)["check"]["differences"]
    assert differences == ["prod has 1 environment secret(s); expected none."]
    assert LISTED_NAME not in captured.out + captured.err


@pytest.mark.parametrize(
    "response",
    [
        [],
        {"total_count": 2, "secrets": [{"name": "A"}]},
        {"total_count": True, "secrets": []},
        {"total_count": 1, "secrets": ["x"]},
    ],
)
def test_incomplete_secret_listings_are_unreadable(monkeypatch, response) -> None:
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: response)
    assert cli._count_environment_entries(REPO, "test", "secrets") is None


def test_the_count_is_an_int_and_keeps_no_name(monkeypatch) -> None:
    page = {"total_count": 2, "secrets": [{"name": LISTED_NAME}, {"name": "B"}]}
    monkeypatch.setattr(cli, "_run_gh_api", lambda args, **_: page)
    assert cli._count_environment_entries(REPO, "test", "secrets") == 2


def test_secret_listing_failure_is_unreadable(monkeypatch) -> None:
    def failing(args, **_):
        raise RuntimeError("no")

    monkeypatch.setattr(cli, "_run_gh_api", failing)
    assert cli._count_environment_entries(REPO, "test", "secrets") is None


def test_apply_refuses_unreadable_variables(monkeypatch) -> None:
    fake = install(monkeypatch)
    original = fake.read

    def read(endpoint: str):
        if "variables" in endpoint:
            raise RuntimeError("no")
        return original(endpoint)

    fake.read = read
    with pytest.raises(RuntimeError, match="not readable before apply"):
        cli.configure(REPO, "Kravalg", apply=True, reviewer_id=REVIEWER_ID)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ([], "incomplete"),
        ({"total_count": 1, "branch_policies": ["x"]}, "malformed"),
        ({"total_count": 1, "branch_policies": [{"id": 0}]}, "malformed"),
        (
            {"total_count": 2, "branch_policies": [{"id": 1}, {"id": 1}]},
            "unique",
        ),
    ],
)
def test_branch_policy_listing_is_validated(response, message) -> None:
    with pytest.raises(ValueError, match=message):
        cli._validated_branch_policies(response)


# --- entry point -------------------------------------------------------------


def test_script_runs_as_main(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["x", "--repo", REPO, "--reviewer-id", "1", "--dry-run"],
    )
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(
            str(ROOT / "scripts" / "configure_github_repository_controls.py"),
            run_name="__main__",
        )
    assert exit_info.value.code == 0
    assert json.loads(capsys.readouterr().out)["reviewerLogin"] == "Kravalg"


def test_subprocess_is_the_only_process_api() -> None:
    assert cli.subprocess is subprocess
