#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Dict, Optional


def read_allowlist(value: str) -> set[str]:
    entries = {item.strip().lower() for item in value.split(",") if item.strip()}
    # Support whitespace/newline separated secrets as well
    extra = {item.strip().lower() for item in value.split() if item.strip()}
    return {entry for entry in entries.union(extra) if entry}


def github_request(url: str, token: str) -> Dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_comment(owner: str, repo: str, issue_number: str, body: str, token: str) -> None:
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}/repos/{owner}/{repo}/issues/{issue_number}/comments"
    payload = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as response:
        response.read()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger-user", required=True)
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--comment-url", default="")
    parser.add_argument("--deny-comments", action="store_true")
    args = parser.parse_args()

    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        sys.stderr.write("GITHUB_REPOSITORY is unavailable.\n")
        sys.exit(1)
    owner, repo = repository.split("/", 1)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.stderr.write("GITHUB_TOKEN is required for authorization checks.\n")
        sys.exit(1)

    allowlist = read_allowlist(os.environ.get("ALLOWED_DEPLOYERS", ""))
    trigger = (args.trigger_user or "").lower()
    result: Dict[str, Optional[str]] = {
        "authorized": "false",
        "via": "",
        "denial_reason": "",
        "permission": "",
    }

    if not trigger:
        result["denial_reason"] = "unable to determine triggering GitHub user"
    elif trigger in allowlist:
        result["authorized"] = "true"
        result["via"] = "allowlist"
    else:
        api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        url = f"{api_url}/repos/{owner}/{repo}/collaborators/{trigger}/permission"
        try:
            data = github_request(url, token)
            permission = (data.get("permission") or "").lower()
            result["permission"] = permission
            if permission in {"admin", "maintain"}:
                result["authorized"] = "true"
                result["via"] = "repo-permission"
            else:
                result["denial_reason"] = f"requires admin or maintain rights (current: {permission or 'none'})"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                result["denial_reason"] = "user is not a collaborator with sufficient permissions"
            else:
                result["denial_reason"] = f"failed to verify collaborator permissions (HTTP {exc.code})"
        except urllib.error.URLError as exc:
            result["denial_reason"] = f"network error while checking permissions: {exc.reason}"

    outputs_path = os.environ.get("GITHUB_OUTPUT")
    if outputs_path:
        with open(outputs_path, "a", encoding="utf-8") as handle:
            for key, value in result.items():
                handle.write(f"{key}={value or ''}\n")

    print(json.dumps(result, indent=2))

    if result["authorized"] == "true":
        return

    if args.deny_comments and args.issue_number:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        run_url = f"{server}/{repository}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
        denial = result["denial_reason"] or "You are not allowed to run this command."
        body = (
            f":no_entry: @{args.trigger_user} this deploy request cannot proceed.\n\n"
            f"Reason: {denial}\n\n"
            f"[Workflow logs]({run_url})"
        )
        try:
            post_comment(owner, repo, args.issue_number, body, token)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"Failed to post denial comment: {exc}\n")


if __name__ == "__main__":
    main()
