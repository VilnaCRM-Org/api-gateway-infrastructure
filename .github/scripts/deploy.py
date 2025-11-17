#!/usr/bin/env python3
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict


def request_id_token(audience: str) -> str:
    request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not request_url or not request_token:
        raise RuntimeError("GitHub OIDC environment variables are unavailable.")

    if "audience=" not in request_url:
        delimiter = "&" if "?" in request_url else "?"
        request_url = f"{request_url}{delimiter}audience={urllib.parse.quote(audience)}"

    req = urllib.request.Request(request_url)
    req.add_header("Authorization", f"Bearer {request_token}")
    with urllib.request.urlopen(req, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("value")
    if not token:
        raise RuntimeError("Failed to retrieve OIDC token value.")
    return token


def assume_role(role_arn: str, session_name: str, duration: int, token: str) -> Dict[str, str]:
    params = {
        "Action": "AssumeRoleWithWebIdentity",
        "RoleArn": role_arn,
        "RoleSessionName": session_name,
        "Version": "2011-06-15",
        "DurationSeconds": str(duration),
        "WebIdentityToken": token,
    }
    body = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        "https://sts.amazonaws.com/",
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        xml_body = response.read().decode("utf-8")

    root = ET.fromstring(xml_body)

    def find_text(tag: str) -> str:
        element = root.find(f".//{{*}}{tag}")
        return element.text if element is not None else ""

    credentials = {
        "AWS_ACCESS_KEY_ID": find_text("AccessKeyId"),
        "AWS_SECRET_ACCESS_KEY": find_text("SecretAccessKey"),
        "AWS_SESSION_TOKEN": find_text("SessionToken"),
    }
    if not all(credentials.values()):
        raise RuntimeError("Failed to parse credentials from STS response.")
    return credentials


def run_command(cmd: list[str], cwd: str, env: Dict[str, str], capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=capture_output,
        check=False,
    )


def to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def summarize_pulumi(json_output: str) -> Dict[str, Any]:
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError:
        return {}
    summary = data.get("changeSummary") or {}
    diagnostics = data.get("diagnostics") or []
    first_error = ""
    for diag in diagnostics:
        if str(diag.get("severity")).lower() == "error" and diag.get("detail"):
            first_error = diag["detail"]
            break
    return {
        "added": to_int(summary.get("create", 0)),
        "updated": to_int(summary.get("update", 0)),
        "replaced": to_int(summary.get("replace", 0)),
        "deleted": to_int(summary.get("delete", 0)),
        "first_error": first_error,
    }


def write_outputs(data: Dict[str, Any], summary_json: str) -> None:
    outputs = {
        "added": str(data.get("added", 0)),
        "updated": str(data.get("updated", 0)),
        "replaced": str(data.get("replaced", 0)),
        "deleted": str(data.get("deleted", 0)),
        "first_error": data.get("first_error", ""),
        "duration_seconds": str(data.get("duration_seconds", 0)),
        "status": data.get("status", "failure"),
        "deploy_summary_b64": base64.b64encode(summary_json.encode("utf-8")).decode("utf-8"),
    }
    outputs_path = os.environ.get("GITHUB_OUTPUT")
    if not outputs_path:
        return
    with open(outputs_path, "a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            safe_value = str(value).replace("\n", " ")
            handle.write(f"{key}={safe_value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=os.environ.get("PULUMI_PROJECT_DIR", "pulumi"))
    parser.add_argument("--stack", default=os.environ.get("PULUMI_STACK"))
    parser.add_argument("--aws-region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument("--role-arn", default=os.environ.get("AWS_ROLE_TO_ASSUME"))
    parser.add_argument("--session-name", default="ManualPulumiDeploy")
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--output-json", default=".gha/deploy-summary.json")
    args = parser.parse_args()

    if not args.stack:
        raise ValueError("PULUMI_STACK is not defined.")
    if not args.role_arn:
        raise ValueError("AWS_ROLE_TO_ASSUME secret is required.")

    project_dir = args.project_dir
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)

    summary = {
        "added": 0,
        "updated": 0,
        "replaced": 0,
        "deleted": 0,
        "first_error": "",
        "duration_seconds": 0,
        "status": "failure",
    }
    exit_code = 1
    start_time = time.time()

    try:
        oidc_token = request_id_token("sts.amazonaws.com")
        temp_credentials = assume_role(args.role_arn, args.session_name, min(args.duration_seconds, 3600), oidc_token)

        base_env = os.environ.copy()
        base_env.update(
            {
                **temp_credentials,
                "AWS_REGION": args.aws_region,
                "AWS_DEFAULT_REGION": args.aws_region,
            }
        )

        login = run_command(["pulumi", "login"], cwd=project_dir, env=base_env, capture_output=True)
        if login.returncode != 0:
            error = login.stderr or login.stdout or "pulumi login failed"
            raise RuntimeError(error.strip())

        stack_select = run_command(["pulumi", "stack", "select", args.stack], cwd=project_dir, env=base_env, capture_output=True)
        if stack_select.returncode != 0:
            error = stack_select.stderr or stack_select.stdout or "pulumi stack select failed"
            raise RuntimeError(error.strip())

        pulumi_cmd = [
            "pulumi",
            "up",
            "--yes",
            "--non-interactive",
            "--suppress-outputs",
            "--stack",
            args.stack,
            "--json",
        ]
        proc = run_command(pulumi_cmd, cwd=project_dir, env=base_env, capture_output=True)
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
        summary.update(summarize_pulumi(stdout_text))
        summary["status"] = "success" if proc.returncode == 0 else "failure"
        if not summary.get("first_error") and stderr_text:
            summary["first_error"] = stderr_text.splitlines()[0]
        exit_code = proc.returncode
    except Exception as exc:  # noqa: BLE001
        if not summary.get("first_error"):
            summary["first_error"] = str(exc)
    finally:
        summary["duration_seconds"] = max(0, int(time.time() - start_time))
        with open(args.output_json, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=2, sort_keys=True)
        write_outputs(summary, json.dumps(summary, separators=(",", ":")))
        print(json.dumps(summary, indent=2))
        if exit_code != 0:
            sys.exit(exit_code)
        sys.exit(0)


if __name__ == "__main__":
    main()
