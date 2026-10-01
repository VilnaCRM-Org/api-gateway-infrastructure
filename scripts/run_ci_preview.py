"""The offline `ci` Structural Preview (AD-A15, AD-A11, FR-A11; G3.3).

Runs `pulumi preview --stack ci` on a fresh local file backend, so the plan
is create-only. Two modes:

- `--json-output PATH` writes the `--json` document the gates read. It adds
  `--show-sames`, so every resource of the plan is listed, and
  `--show-replacement-steps`, so a replacement shows its
  `create-replacement` / `replace` / `delete-replaced` steps in engine order
  (the Deployment allowance of the destructive gate needs that order);
- `--policy-pack DIR` enforces the CrossGuard pack. CrossGuard reports
  violations only in the text output, so this mode streams it and returns
  the engine's exit code.

The child process gets an allow-listed environment: no `AWS_*` variable, no
Pulumi access token, no `PULUMI_CONFIG_<KEY>` override, the `ci` stack's
fixed empty passphrase (the stack holds no secret), and automatic plugin
acquisition disabled, so only the image's preinstalled, checksum-verified
`aws` plugin can run (G3.1 hand-off F02). The make targets run it in the
`app-offline` compose service, which has no network at all.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

STACK = "ci"
ROOT = Path(__file__).resolve().parents[1]
PROGRAM_DIR = ROOT / "pulumi"
# Variables the Pulumi CLI and the Python language host need; nothing else
# reaches the preview.
PASSTHROUGH_ENV = (
    "HOME",
    "LANG",
    "PATH",
    "PULUMI_HOME",
    "PULUMI_PYTHON_CMD",
    "UV_PROJECT_ENVIRONMENT",
)
# AD-A15: the `ci` stack's passphrase is intentionally empty and not a secret;
# the stack holds no secret (pulumi/Pulumi.ci.yaml).
EMPTY_PASSPHRASE_ENV = "PULUMI_CONFIG_PASSPHRASE"  # nosec B105  # a variable name
FIXED_ENV = dict.fromkeys((EMPTY_PASSPHRASE_ENV,), "") | {
    "PULUMI_DISABLE_AUTOMATIC_PLUGIN_ACQUISITION": "true",
    "PULUMI_SKIP_UPDATE_CHECK": "true",
}
JSON_FLAGS = ("--json", "--show-sames", "--show-replacement-steps")


def preview_env(backend: Path, environ: Mapping[str, str]) -> dict[str, str]:
    """The child environment: the allow-list, the backend and FIXED_ENV."""
    env = {name: environ[name] for name in PASSTHROUGH_ENV if name in environ}
    env.update(FIXED_ENV)
    env["PULUMI_BACKEND_URL"] = backend.as_uri()
    return env


def pulumi_binary() -> str:
    """The absolute path of the Pulumi CLI."""
    found = shutil.which("pulumi")
    if found is None:
        raise RuntimeError("The pulumi CLI is not on PATH.")
    return found


def preview_commands(
    pulumi: str, policy_pack: Path | None
) -> tuple[list[str], list[str]]:
    """The `stack init` and `preview` argv lists for one mode."""
    init = [pulumi, "stack", "init", STACK, "--non-interactive"]
    preview = [pulumi, "preview", "--stack", STACK, "--non-interactive"]
    if policy_pack is None:
        preview += JSON_FLAGS
    else:
        preview += ["--policy-pack", str(policy_pack.resolve())]
    return init, preview


def _run(
    argv: list[str], cwd: Path, env: dict[str, str], out: int | None
) -> subprocess.CompletedProcess[str]:
    """Run one Pulumi command; `out` is `subprocess.PIPE` to capture stdout."""
    return subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=out)  # nosec B603


def run_preview(
    *,
    json_output: Path | None = None,
    policy_pack: Path | None = None,
    program_dir: Path = PROGRAM_DIR,
    environ: Mapping[str, str] = os.environ,
) -> int:
    """Run one offline preview and return the engine's exit code."""
    if (json_output is None) == (policy_pack is None):
        raise ValueError("Give exactly one of json_output and policy_pack.")
    init, preview = preview_commands(pulumi_binary(), policy_pack)
    with tempfile.TemporaryDirectory(prefix="pulumi-ci-backend-") as backend:
        env = preview_env(Path(backend), environ)
        created = _run(init, program_dir, env, None)
        if created.returncode != 0:
            print(f"pulumi stack init {STACK} failed", file=sys.stderr)
            return created.returncode
        if json_output is None:
            return _run(preview, program_dir, env, None).returncode
        result = _run(preview, program_dir, env, subprocess.PIPE)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(result.stdout, encoding="utf-8")
    print(f"pulumi preview --stack {STACK}: exit {result.returncode}; {json_output}")
    return result.returncode


def cli(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and run the offline preview."""
    parser = argparse.ArgumentParser(
        description="Offline `ci` Structural Preview (AD-A15)."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--json-output", type=Path)
    mode.add_argument("--policy-pack", type=Path)
    args = parser.parse_args(argv)
    return run_preview(json_output=args.json_output, policy_pack=args.policy_pack)


if __name__ == "__main__":
    raise SystemExit(cli())
