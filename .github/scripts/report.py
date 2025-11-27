#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
import urllib.request


def decode_summary(value: str) -> dict:
    data = base64.b64decode(value.encode("utf-8")).decode("utf-8")
    return json.loads(data)


def create_comment(owner: str, repo: str, issue_number: str, body: str, token: str) -> None:
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    url = f"{api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
    payload = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as response:
        response.read()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy-summary-b64", required=True)
    parser.add_argument("--trigger-user", required=True)
    parser.add_argument("--stack", default="unknown stack")
    parser.add_argument("--comment-url", default="")
    parser.add_argument("--issue-number", required=True)
    args = parser.parse_args()

    try:
        summary = decode_summary(args.deploy_summary_b64)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Unable to decode deployment summary: {exc}\n")
        sys.exit(1)

    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repository:
        sys.stderr.write("GITHUB_REPOSITORY is unavailable.\n")
        sys.exit(1)
    owner, repo = repository.split("/", 1)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.stderr.write("GITHUB_TOKEN is required to post comments.\n")
        sys.exit(1)

    run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repository}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
    status = summary.get("status", "failure").lower()
    success = status == "success"
    icon = ":white_check_mark:" if success else ":x:"
    duration = summary.get("duration_seconds", "n/a")

    lines = [
        f"{icon} **Manual Pulumi Deploy – {status.upper()}**",
        "",
        f"Request: [source comment]({args.comment_url})" if args.comment_url else "Request: manual dispatch",
        f"Trigger: @{args.trigger_user}",
        f"Stack: `{args.stack}`",
        f"Duration: {duration}s" if isinstance(duration, int) else f"Duration: {duration}",
        "",
        "Pulumi summary:",
        f"- Added: {summary.get('added', 0)}",
        f"- Updated: {summary.get('updated', 0)}",
        f"- Replaced: {summary.get('replaced', 0)}",
        f"- Deleted: {summary.get('deleted', 0)}",
        "",
        f"[View workflow run]({run_url})",
    ]

    if not success:
        error_line = summary.get("first_error") or "See workflow logs for details."
        lines.extend(["", "Failure detail:", f"> {error_line}"])

    body = "\n".join(lines)

    try:
        create_comment(owner, repo, args.issue_number, body, token)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Failed to post deployment summary comment: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
