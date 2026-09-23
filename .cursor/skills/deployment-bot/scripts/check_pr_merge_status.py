"""Validate that every Jira ticket has only merged pull requests.

Jira exposes GitHub development status in customfield_10500. The canonical
deployment-notes builder calls this check before writing any output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEVELOPMENT_FIELD = "customfield_10500"
MERGED_STATE = "MERGED"


def gate_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge config.json -> pull_request_gate over the built-in defaults."""
    gate = (config or {}).get("pull_request_gate") or {}
    return {
        "enabled": gate.get("enabled", True),
        "field": gate.get("jira_development_field") or DEVELOPMENT_FIELD,
        "require_attached_pr": gate.get("require_attached_pr", True),
        "require_all_merged": gate.get("require_all_merged", True),
        "merged_state": (gate.get("merged_state") or MERGED_STATE).upper(),
    }


def _from_mapping(value: dict[str, Any]) -> tuple[int, int, str]:
    overall = (
        value.get("cachedValue", {})
        .get("summary", {})
        .get("pullrequest", {})
        .get("overall", {})
    )
    if not overall and "pullrequest" in value:
        overall = value.get("pullrequest") or {}
    count = int(overall.get("count") or 0)
    state_count = int(overall.get("stateCount") or 0)
    state = str(overall.get("state") or "").upper()
    return count, state_count, state


def parse_pr_status(value: Any, merged_state: str = MERGED_STATE) -> dict[str, Any]:
    """Return normalized Jira development status for one issue."""
    if isinstance(value, dict):
        count, state_count, state = _from_mapping(value)
    elif isinstance(value, str):
        count_match = re.search(
            r'"overall"\s*:\s*\{\s*"count"\s*:\s*(\d+)', value
        )
        summary_match = re.search(
            r"pullrequest=\{dataType=pullrequest,\s*"
            r"state=([^,}]+),\s*stateCount=(\d+)",
            value,
            flags=re.IGNORECASE,
        )
        count = int(count_match.group(1)) if count_match else 0
        state = summary_match.group(1).strip().upper() if summary_match else ""
        state_count = int(summary_match.group(2)) if summary_match else 0
    else:
        count, state_count, state = 0, 0, ""

    wanted = (merged_state or MERGED_STATE).upper()
    if count == 0:
        status = "missing"
    elif state == wanted and state_count == count:
        status = "merged"
    else:
        status = "not_merged"

    return {
        "status": status,
        "count": count,
        "merged_count": state_count if state == wanted else 0,
        "jira_state": state or "UNKNOWN",
    }


def check_issues(
    issues: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return tickets that cannot pass the merged-PR gate."""
    gate = gate_settings(config)
    blockers = []
    for issue in issues:
        result = parse_pr_status(
            (issue.get("fields") or {}).get(gate["field"]),
            merged_state=gate["merged_state"],
        )
        if result["status"] == "missing" and not gate["require_attached_pr"]:
            continue
        if result["status"] == "not_merged" and not gate["require_all_merged"]:
            continue
        if result["status"] != "merged":
            blockers.append(
                {
                    "key": issue.get("key") or "UNKNOWN",
                    **result,
                }
            )
    return blockers


def assert_all_prs_merged(
    issues: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> None:
    if not gate_settings(config)["enabled"]:
        return
    blockers = check_issues(issues, config)
    if not blockers:
        return

    details = []
    for row in blockers:
        if row["status"] == "missing":
            details.append(f"{row['key']}: no attached PR found")
        else:
            details.append(
                f"{row['key']}: aggregate PR state {row['jira_state']} "
                f"across {row['count']} PR(s)"
            )
    raise ValueError(
        "Deployment notes paused because PR verification failed: "
        + "; ".join(details)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Require all Jira-ticket pull requests to be merged."
    )
    parser.add_argument("--jira-json", required=True)
    parser.add_argument("--config", default="")
    args = parser.parse_args(argv)

    raw = json.loads(Path(args.jira_json).read_text(encoding="utf-8"))
    issues = raw.get("issues", []) if isinstance(raw, dict) else raw
    config = (
        json.loads(Path(args.config).read_text(encoding="utf-8"))
        if args.config
        else {}
    )
    try:
        assert_all_prs_merged(issues or [], config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"PR gate passed: {len(issues)} ticket(s), all PRs merged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
