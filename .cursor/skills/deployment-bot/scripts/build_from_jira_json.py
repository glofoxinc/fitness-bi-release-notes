#!/usr/bin/env python3
"""Build tickets JSON from a saved Jira search payload and generate DOCX."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from normalize_tickets import ANALYZE_CLIENT, DEFAULT_CATEGORIES, normalize_issues  # noqa: E402
from generate_release_notes import build_document, MONTHS  # noqa: E402


def find_release_date(fix_version: str, issues: list) -> str:
    for issue in issues:
        for fv in (issue.get("fields", {}).get("fixVersions") or []):
            if fv.get("name") == fix_version and fv.get("releaseDate"):
                y, m, d = fv["releaseDate"].split("-")
                return f"{int(d):02d}-{MONTHS[int(m)]}-{y}"
    return ""


def count_categories(tickets: list, categories: dict) -> list[dict]:
    order = categories.get("order") or DEFAULT_CATEGORIES["order"]
    display = categories.get("display") or DEFAULT_CATEGORIES["display"]
    counts = {key: 0 for key in order}
    for t in tickets:
        key = t.get("category") or (categories.get("fallback") or "customizations")
        counts[key] = counts.get(key, 0) + 1
    return [
        {"key": key, "label": display.get(key, key), "count": counts.get(key, 0)}
        for key in order
    ]


def size_sentence(
    category_counts: list[dict],
    categories: dict,
    has_analyze: bool = False,
    custom_clients: list[str] | None = None,
) -> str:
    """The single Release Summary: brief description plus the delivery counts."""
    forms = categories.get("sentence") or DEFAULT_CATEGORIES["sentence"]
    parts = []
    for row in category_counts:
        count = row["count"]
        if not count:
            continue
        singular, plural = forms.get(row["key"], (row["label"], row["label"]))
        parts.append(f"{count} {singular if count == 1 else plural}")

    if not parts:
        return "This release contains no deliverables in the tracked categories."
    if len(parts) == 1:
        counts_text = parts[0]
    else:
        counts_text = ", ".join(parts[:-1]) + f", and {parts[-1]}"

    scope = []
    if has_analyze:
        scope.append(ANALYZE_CLIENT)
    scope.extend(custom_clients or [])
    if not scope:
        return f"This release delivers {counts_text}."
    if len(scope) == 1:
        scope_text = scope[0]
    else:
        scope_text = ", ".join(scope[:-1]) + f", and {scope[-1]}"
    return f"This release delivers {counts_text} for {scope_text}."


def build_payload(fix_version: str, issues: list, config: dict) -> dict:
    categories = config.get("summary_categories") or DEFAULT_CATEGORIES
    tickets = normalize_issues(issues, categories)
    category_counts = count_categories(tickets, categories)
    has_analyze = any(t["type"] == "Analyze" for t in tickets)
    customs = []
    for t in tickets:
        if t["type"] == "Custom" and t["client"] not in customs and t["client"] != "Unknown":
            customs.append(t["client"])

    release_summary = size_sentence(category_counts, categories, has_analyze, customs)

    return {
        "fix_version": fix_version,
        "release_date": find_release_date(fix_version, issues),
        "mode": "pre",
        "meta": config.get("defaults", {}),
        "narratives": {
            "release_summary": release_summary,
        },
        "category_counts": category_counts,
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
    unlabeled = [t["key"] for t in payload["tickets"] if not t.get("category_from_label")]
    print(f"Tickets: {len(payload['tickets'])}")
    for row in payload["category_counts"]:
        print(f"  {row['label']}: {row['count']}")
    print(f"Wrote JSON: {out_json}")
    print(f"Wrote DOCX: {out_docx}")
    if unknowns:
        print("WARNING Unknown clients:", ", ".join(unknowns))
    if unlabeled:
        print("WARNING Category from summary (no category label):", ", ".join(unlabeled))


if __name__ == "__main__":
    main()
