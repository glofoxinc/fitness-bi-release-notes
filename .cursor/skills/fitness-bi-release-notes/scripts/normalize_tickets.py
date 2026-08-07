#!/usr/bin/env python3
"""Normalize Jira issue dicts into release-notes ticket rows."""

from __future__ import annotations

import re
from typing import Any


CLIENT_SPLIT = re.compile(r"\s+[-–:]\s+")

# Extend via config / skill updates as new clients appear
KNOWN_CUSTOM_CLIENTS = [
    "FIT4MOM",
    "Jazzercise",
    "Jetts",
    "FWBC",
]


def classify_type(project_key: str) -> str:
    key = (project_key or "").upper()
    if key == "AN":
        return "Analyze"
    if key == "PIC":
        return "Custom"
    return "Other"


def split_segments(text: str) -> list[str]:
    """Split on spaced delimiters first; only fall back to bare hyphens
    when no spaced delimiter exists (keeps names like 'E-agreements' intact)."""
    text = (text or "").strip()
    parts = [p.strip() for p in re.split(r"\s+[-–—:]\s+", text) if p.strip()]
    if len(parts) == 1:
        parts = [p.strip() for p in re.split(r"\s*[-–—]\s*", text) if p.strip()]
    return parts


def split_client_report_desc(summary: str, typ: str) -> tuple[str, str, str]:
    """Return (client, report_name, description).

    report_name = the short report title only (no explanation).
    description = the remaining explanation text.
    """
    summary = (summary or "").strip()

    if typ == "Analyze":
        if summary.lower().startswith("analyze"):
            summary = summary[len("analyze") :].lstrip(" -–—:\t")
        segs = split_segments(summary)
        report = segs[0] if segs else summary
        desc = " - ".join(segs[1:]) if len(segs) > 1 else report
        return "Standard", report, desc

    # Custom: try known client name at start
    client = None
    for kc in sorted(KNOWN_CUSTOM_CLIENTS, key=len, reverse=True):
        if summary.lower().startswith(kc.lower()):
            client = kc
            summary = summary[len(kc) :].lstrip(" -–—:\t")
            break

    segs = split_segments(summary)
    if client is None:
        if segs and len(segs[0].split()) <= 3:
            client = segs[0]
            segs = segs[1:]
        else:
            client = "Unknown"

    report = segs[0] if segs else summary
    desc = " - ".join(segs[1:]) if len(segs) > 1 else report
    return client, report, desc


def normalize_issue(issue: dict[str, Any], site: str = "https://abcfinancial.atlassian.net") -> dict[str, Any]:
    fields = issue.get("fields") or {}
    key = issue.get("key") or ""
    project = (fields.get("project") or {}).get("key") or key.split("-")[0]
    typ = classify_type(project)
    summary = fields.get("summary") or ""
    client, report, desc = split_client_report_desc(summary, typ)
    parent = ((fields.get("parent") or {}).get("key")) or ""
    return {
        "key": key,
        "parent": parent,
        "link": f"{site}/browse/{key}",
        "type": typ if typ != "Other" else project,
        "client": client,
        "report": report,
        "description": desc if desc else report,
        "test_by": "",
        "comments": "",
        "testing_status": "",
        "status": ((fields.get("status") or {}).get("name")) or "",
        "assignee": ((fields.get("assignee") or {}).get("displayName")) or "",
    }


def normalize_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_issue(i) for i in issues]
