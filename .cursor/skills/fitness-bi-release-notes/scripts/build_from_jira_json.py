#!/usr/bin/env python3
"""Build tickets JSON from a saved Jira search payload and generate DOCX."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from normalize_tickets import normalize_issues  # noqa: E402
from generate_release_notes import build_document, MONTHS  # noqa: E402


def find_release_date(fix_version: str, issues: list) -> str:
    for issue in issues:
        for fv in (issue.get("fields", {}).get("fixVersions") or []):
            if fv.get("name") == fix_version and fv.get("releaseDate"):
                y, m, d = fv["releaseDate"].split("-")
                return f"{int(d):02d}-{MONTHS[int(m)]}-{y}"
    return ""


def build_payload(fix_version: str, issues: list, config: dict) -> dict:
    tickets = normalize_issues(issues)
    has_analyze = any(t["type"] == "Analyze" for t in tickets)
    has_custom = any(t["type"] == "Custom" for t in tickets)
    customs = []
    for t in tickets:
        if t["type"] == "Custom" and t["client"] not in customs and t["client"] != "Unknown":
            customs.append(t["client"])

    bits = []
    if has_analyze:
        bits.append("reporting enhancements")
    if has_custom:
        bits.append("custom client updates")
    bits.append("semantic model improvements")
    release_summary = "This release includes " + ", ".join(bits[:-1])
    if len(bits) > 1:
        release_summary += f", and {bits[-1]}."
    else:
        release_summary = f"This release includes {bits[0]}."

    custom_summary = (
        "This release includes updates to existing functionality, semantic model changes, "
        "column additions, and new report creation for custom clients."
        if has_custom
        else "No custom client changes in this release."
    )
    std_summary = (
        "This release improves reporting usability through dashboard restructuring, clearer "
        "report metrics, and standardized paginated report formatting alongside custom client enhancements."
    )

    return {
        "fix_version": fix_version,
        "release_date": find_release_date(fix_version, issues),
        "mode": "pre",
        "meta": config.get("defaults", {}),
        "narratives": {
            "release_summary": release_summary,
            "custom_clients_summary": custom_summary,
            "standard_custom_summary": std_summary,
        },
        "tickets": tickets,
        "excluded": [],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--jira-json", required=True, help="Raw MCP/Jira search JSON with issues[]")
    parser.add_argument("--fix-version", required=True)
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-docx", required=True)
    args = parser.parse_args()

    raw = json.loads(Path(args.jira_json).read_text(encoding="utf-8"))
    issues = raw["issues"] if isinstance(raw, dict) else raw
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    payload = build_payload(args.fix_version, issues, config)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    out_docx = Path(args.output_docx)
    out_docx.parent.mkdir(parents=True, exist_ok=True)
    build_document(payload).save(str(out_docx))

    unknowns = [t["key"] for t in payload["tickets"] if t.get("client") == "Unknown"]
    print(f"Tickets: {len(payload['tickets'])}")
    print(f"Wrote JSON: {out_json}")
    print(f"Wrote DOCX: {out_docx}")
    if unknowns:
        print("WARNING Unknown clients:", ", ".join(unknowns))


if __name__ == "__main__":
    main()
