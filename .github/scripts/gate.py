#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict


def normalize_command(value: str) -> str:
    collapsed = " ".join(value.strip().split())
    return collapsed.lower()


def gate_event(event: Dict[str, Any], event_name: str, actor: str) -> Dict[str, Any]:
    result = {
        "should_run": False,
        "trigger_type": event_name,
        "trigger_user": actor or "",
        "issue_number": "",
        "comment_id": "",
        "comment_url": "",
        "command": "",
        "reason": "",
    }

    if event_name == "workflow_dispatch":
        result.update(
            {
                "should_run": True,
                "trigger_type": "workflow_dispatch",
                "command": "/deploy",
            }
        )
        return result

    if event_name != "issue_comment":
        result["reason"] = f"unsupported event {event_name}"
        return result

    if event.get("action") != "created":
        result["reason"] = 'comment action is not "created"'
        return result

    issue = event.get("issue")
    if not issue:
        result["reason"] = "comment is not attached to an issue or PR"
        return result

    comment = event.get("comment") or {}
    body = (comment.get("body") or "").strip()
    normalized = normalize_command(body)
    if normalized != "/deploy":
        result["reason"] = "comment does not match /deploy"
        return result

    result.update(
        {
            "should_run": True,
            "trigger_type": "issue_comment",
            "trigger_user": (comment.get("user") or {}).get("login", "") or actor or "",
            "issue_number": str(issue.get("number", "")),
            "comment_id": str(comment.get("id", "")),
            "comment_url": comment.get("html_url", ""),
            "command": "/deploy",
            "reason": "",
        }
    )
    return result


def write_outputs(data: Dict[str, Any]) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        return
    with open(output_file, "a", encoding="utf-8") as handle:
        for key in (
            "should_run",
            "trigger_type",
            "trigger_user",
            "issue_number",
            "comment_id",
            "comment_url",
            "command",
        ):
            value = data.get(key, "")
            if isinstance(value, bool):
                value = "true" if value else "false"
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH"), required=True)
    parser.add_argument("--output-json", default=".gha/gate.json")
    args = parser.parse_args()

    try:
        with open(args.event_path, "r", encoding="utf-8") as file:
            event = json.load(file)
    except FileNotFoundError:
        sys.stderr.write(f"Event payload not found at {args.event_path}\n")
        sys.exit(78)

    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    actor = os.environ.get("GITHUB_ACTOR", "")
    result = gate_event(event, event_name, actor)

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2, sort_keys=True)

    write_outputs(result)

    summary = json.dumps(result, indent=2)
    print(summary)

    if not result.get("should_run"):
        reason = result.get("reason") or "gate rejected event"
        print(f"Gate ignored event: {reason}")


if __name__ == "__main__":
    main()
