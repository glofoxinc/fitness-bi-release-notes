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

EXPLANATION_SUFFIXES = re.compile(
    r"\s*\((?:new\s+)?(?:paginated\s+)?report\)\s*$",
    re.IGNORECASE,
)
LEADING_ACTIONS = re.compile(
    r"^(?:remove|delete|update|updates?\s+to|fix|add|change|modify|optimi[sz]e|"
    r"enhance|create|replace|migrate|clean\s+up)\b[\s:–—-]*",
    re.IGNORECASE,
)
NAMED_ASSET = re.compile(
    r"\b(?:dashboard|reports?|semantic\s+model|data\s+model|dataset)\b",
    re.IGNORECASE,
)
INLINE_EXPLANATION = re.compile(
    r"^(.*?\b(?:dashboard|reports?|semantic\s+model|data\s+model|dataset))"
    r"\s+((?:change|replac(?:e|ing)|pointing|updates?|fix(?:es)?|add(?:ing)?|"
    r"remov(?:e|ing)|optimization|optimisation|enhancements?)\b.*)$",
    re.IGNORECASE,
)

# Product/tooling context words that appear before the real report content
# (e.g. "ABC Insights - Analyse - Course bookings"). Stripped from the front so
# both Key Highlights and the Report column start at the meaningful text.
CONTEXT_PREFIXES = re.compile(
    r"^(?:\s*(?:abc\s+insights|insights\s+customi[sz]e|insights\s+analy[sz]e|"
    r"abc\s+customi[sz]e|customi[sz]e|insights|analy[sz]e)\s*[-–—:]?\s*)+",
    re.IGNORECASE,
)


def strip_context_prefixes(text: str) -> str:
    return CONTEXT_PREFIXES.sub("", (text or "").strip()).strip(" -–—:")


def tidy_spacing(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    # "Medallia reports(New Paginated Report)" -> "... (New Paginated Report)"
    text = re.sub(r"(\S)\(", r"\1 (", text)
    return text


def classify_type(project_key: str) -> str:
    key = (project_key or "").upper()
    if key == "AN":
        return "Analyze"
    if key == "PIC":
        return "Custom"
    return "Other"


def split_segments(text: str) -> list[str]:
    """Split explanations on spaced delimiters, preserving hyphenated names."""
    text = (text or "").strip()
    parts = [p.strip() for p in re.split(r"\s+[-–—:]\s+", text) if p.strip()]
    return parts


def clean_asset_name(text: str) -> str:
    """Remove change wording while preserving a named report/dashboard/model."""
    value = EXPLANATION_SUFFIXES.sub("", (text or "").strip()).strip(" -–—:")
    value = LEADING_ACTIONS.sub("", value).strip(" -–—:")

    # "older class utilization dashboard" describes the age of the asset, not its name.
    value = re.sub(r"^(?:the\s+)?older\s+", "", value, flags=re.IGNORECASE)

    # An action title such as "Remove Jetts ... from Fitness BI Reporting" does
    # not identify a particular report/dashboard/model.
    if re.search(r"\bfrom\s+fitness\s+bi\s+reporting\b", value, re.IGNORECASE):
        return ""
    return value


def report_name_and_description(text: str, typ: str) -> tuple[str, str]:
    """Extract only the report/dashboard/model name plus separate explanation."""
    segs = split_segments(text)
    first = segs[0] if segs else (text or "").strip()
    inline = INLINE_EXPLANATION.match(EXPLANATION_SUFFIXES.sub("", first).strip())
    inline_desc = ""
    if inline:
        first, inline_desc = inline.group(1), inline.group(2)
    report = clean_asset_name(first)
    desc_parts = [inline_desc, *segs[1:]]
    desc = " - ".join(part.strip() for part in desc_parts if part.strip())

    if not report:
        return ("All Reports" if typ == "Analyze" else ""), desc or first

    # If an Analyze title starts as a change instruction and names no report,
    # dashboard, model, or dataset, use the agreed fallback.
    starts_with_action = bool(LEADING_ACTIONS.match(first))
    if typ == "Analyze" and starts_with_action and not NAMED_ASSET.search(first):
        return "All Reports", desc or first

    return report, desc or report


def client_and_core(summary: str, typ: str) -> tuple[str, str]:
    """Return (client, core_text).

    core_text is the meaningful part of the summary with the client name and
    product/context prefixes removed. It is the shared basis for both the
    Key Highlights line and the Report column.
    """
    summary = (summary or "").strip()

    if typ == "Analyze":
        return "Standard", strip_context_prefixes(summary)

    # Custom: try known client name at start
    client = None
    remaining = summary
    for kc in sorted(KNOWN_CUSTOM_CLIENTS, key=len, reverse=True):
        if summary.lower().startswith(kc.lower()):
            client = kc
            remaining = summary[len(kc) :].lstrip(" -–—:\t")
            break

    if client is None:
        compact_prefix = re.match(r"^([A-Za-z0-9&]+)[-–—](.+)$", summary)
        segs = split_segments(summary)
        if compact_prefix:
            client = compact_prefix.group(1).strip()
            remaining = compact_prefix.group(2).strip()
        elif segs and len(segs[0].split()) <= 3:
            client = segs[0]
            remaining = " - ".join(segs[1:])
        else:
            client = "Unknown"
            remaining = summary

    return client, strip_context_prefixes(remaining)


def highlight_line(summary: str, typ: str) -> str:
    """Concise 'Client: <minimal ticket info>' line for Key Highlights."""
    client, core = client_and_core(summary, typ)
    core = tidy_spacing(core)
    if client and core:
        return f"{client}: {core}"
    return core or client


def split_client_report_desc(summary: str, typ: str) -> tuple[str, str, str]:
    """Return (client, report_name, description).

    report_name = the report/dashboard/model name only (no explanation).
    description = the remaining explanation text.
    """
    client, core = client_and_core(summary, typ)
    report, desc = report_name_and_description(core, typ)
    if not report:
        report = clean_asset_name(core) or core
    return client, report, desc


def description_text(summary: str, typ: str) -> str:
    """Full concise change text for the Description column.

    Uses the whole meaningful summary so the cell always reads as a complete
    change (never a bare fragment like "optimization").
    """
    _, core = client_and_core(summary, typ)
    return tidy_spacing(core)


def normalize_issue(issue: dict[str, Any], site: str = "https://abcfinancial.atlassian.net") -> dict[str, Any]:
    fields = issue.get("fields") or {}
    key = issue.get("key") or ""
    project = (fields.get("project") or {}).get("key") or key.split("-")[0]
    typ = classify_type(project)
    summary = fields.get("summary") or ""
    client, report, _ = split_client_report_desc(summary, typ)
    desc = description_text(summary, typ)
    highlight = highlight_line(summary, typ)
    parent = ((fields.get("parent") or {}).get("key")) or ""
    return {
        "key": key,
        "parent": parent,
        "link": f"{site}/browse/{key}",
        "type": typ if typ != "Other" else project,
        "client": client,
        "report": report,
        "description": desc if desc else report,
        "highlight": highlight,
        "test_by": "",
        "comments": "",
        "testing_status": "",
        "status": ((fields.get("status") or {}).get("name")) or "",
        "assignee": ((fields.get("assignee") or {}).get("displayName")) or "",
    }


def normalize_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_issue(i) for i in issues]
