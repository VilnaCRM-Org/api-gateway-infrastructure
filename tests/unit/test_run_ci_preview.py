"""The offline `ci` Structural Preview runner (G3.3, AD-A15, G3.1 F02).

The preview runs on a fresh local file backend with an allow-listed
environment: no AWS variable, no Pulumi token, no per-key config override,
the `ci` stack's empty passphrase, and plugin downloads disabled.
"""

from __future__ import annotations

import runpy
import subprocess  # nosec B404
from pathlib import Path

import pytest

import run_ci_preview as rp

PULUMI = "/opt/pulumi/pulumi"
# Host variables that must never reach the preview; their values are
# placeholders, not credentials.
PLACEHOLDER = "host-only"
LEAKS = (
    "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "PULUMI_ACCESS_TOKEN",
    "PULUMI_BACKEND_URL",
    "PULUMI_CONFIG_PASSPHRASE",
    "PULUMI_CONFIG_api-gateway-infrastructure:features",
    "GITHUB_TOKEN",
)
HOST_ENV = {
    "PATH": "/usr/bin",
    "HOME": "/home/dev",
    "PULUMI_HOME": "/home/dev/.pulumi",
    "PULUMI_PYTHON_CMD": "/venv/bin/python",
} | {name: PLACEHOLDER for name in LEAKS}


class Runner:
    """Records subprocess.run calls and returns scripted results."""

    def __init__(self, *codes: int, stdout: str = '{"steps": []}') -> None:
        self.codes = list(codes)
        self.stdout = stdout
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        assert kwargs["env"]["PULUMI_BACKEND_URL"].startswith("file://")
        backend = Path(kwargs["env"]["PULUMI_BACKEND_URL"][len("file://") :])
        assert backend.is_dir()
        return subprocess.CompletedProcess(argv, self.codes.pop(0), self.stdout)


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch):
    def install(*codes: int, stdout: str = '{"steps": []}') -> Runner:
        fake = Runner(*codes, stdout=stdout)
        monkeypatch.setattr(rp.subprocess, "run", fake)
        monkeypatch.setattr(rp.shutil, "which", lambda name: PULUMI)
        return fake

    return install


def test_environment_is_allow_listed(tmp_path: Path) -> None:
    env = rp.preview_env(tmp_path, HOST_ENV)
    assert (
        env
        == {
            "PATH": "/usr/bin",
            "HOME": "/home/dev",
            "PULUMI_HOME": "/home/dev/.pulumi",
            "PULUMI_PYTHON_CMD": "/venv/bin/python",
            "PULUMI_BACKEND_URL": tmp_path.as_uri(),
        }
        | rp.FIXED_ENV
    )
    assert rp.FIXED_ENV == {
        "PULUMI_CONFIG_PASSPHRASE": rp.FIXED_ENV["PULUMI_CONFIG_PASSPHRASE"],
        "PULUMI_DISABLE_AUTOMATIC_PLUGIN_ACQUISITION": "true",
        "PULUMI_SKIP_UPDATE_CHECK": "true",
    }
    assert not env["PULUMI_CONFIG_PASSPHRASE"]  # the ci stack's empty passphrase
    assert PLACEHOLDER not in env.values()
    assert not any(name.startswith("AWS_") for name in env)


def test_json_mode_commands() -> None:
    init, preview = rp.preview_commands(PULUMI, None)
    assert init == [PULUMI, "stack", "init", "ci", "--non-interactive"]
    assert preview == [
        PULUMI,
        "preview",
        "--stack",
        "ci",
        "--non-interactive",
        "--json",
        "--show-sames",
        "--show-replacement-steps",
    ]


def test_policy_mode_commands(tmp_path: Path) -> None:
    _, preview = rp.preview_commands(PULUMI, tmp_path / "policy")
    assert preview[-2:] == ["--policy-pack", str((tmp_path / "policy").resolve())]
    assert "--json" not in preview


def test_json_mode_writes_the_document(
    runner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = runner(0, 0)
    output = tmp_path / "out" / "ci.json"
    code = rp.run_preview(json_output=output, program_dir=tmp_path, environ=HOST_ENV)
    assert code == 0
    assert output.read_text(encoding="utf-8") == '{"steps": []}'
    (init, init_kw), (preview, preview_kw) = fake.calls
    assert init[1:3] == ["stack", "init"] and preview[1] == "preview"
    assert init_kw["cwd"] == preview_kw["cwd"] == tmp_path
    assert init_kw["env"] == preview_kw["env"]
    assert init_kw["text"] is preview_kw["text"] is True
    assert "check" not in preview_kw  # subprocess.run's default: check=False
    assert init_kw["stdout"] is None
    assert preview_kw["stdout"] == subprocess.PIPE
    assert "stderr" not in preview_kw  # the engine's stderr streams to the log
    assert "AWS_PROFILE" not in preview_kw["env"]
    assert "exit 0" in capsys.readouterr().out


def test_json_mode_returns_the_engine_failure(runner, tmp_path: Path) -> None:
    runner(0, 255, stdout='{"diagnostics": []}')
    output = tmp_path / "ci.json"
    assert rp.run_preview(json_output=output, environ=HOST_ENV) == 255
    assert output.read_text(encoding="utf-8") == '{"diagnostics": []}'


def test_policy_mode_streams_and_returns_the_exit_code(runner, tmp_path: Path) -> None:
    fake = runner(0, 255)
    assert rp.run_preview(policy_pack=tmp_path, environ=HOST_ENV) == 255
    _, preview_kw = fake.calls[1]
    assert preview_kw["stdout"] is None


def test_stack_init_failure_stops(
    runner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = runner(3)
    assert rp.run_preview(json_output=tmp_path / "x.json", environ=HOST_ENV) == 3
    assert len(fake.calls) == 1
    assert not (tmp_path / "x.json").exists()
    assert "stack init ci failed" in capsys.readouterr().err


@pytest.mark.parametrize("both", [True, False])
def test_exactly_one_mode(both: bool, tmp_path: Path) -> None:
    kwargs = {"json_output": tmp_path, "policy_pack": tmp_path} if both else {}
    with pytest.raises(ValueError):
        rp.run_preview(**kwargs)


def test_missing_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rp.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        rp.pulumi_binary()


def test_cli_modes_are_exclusive_and_required(tmp_path: Path) -> None:
    for argv in ([], ["--json-output", "a", "--policy-pack", "b"]):
        with pytest.raises(SystemExit):
            rp.cli(argv)


def test_main_runs_the_cli(
    runner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner(0, 0)
    output = tmp_path / "ci.json"
    monkeypatch.setattr("sys.argv", ["run_ci_preview.py", "--json-output", str(output)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(rp.__file__, run_name="__main__")
    assert raised.value.code == 0
    assert output.exists()


def test_program_dir_is_the_pulumi_program() -> None:
    assert (rp.PROGRAM_DIR / "Pulumi.ci.yaml").is_file()
    assert rp.STACK == "ci"
