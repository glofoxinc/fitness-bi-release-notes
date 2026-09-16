"""Build the SHIPIT Change Request payload from Fix Version tickets.

Prints JSON for Deployment Bot to pass to Atlassian MCP createJiraIssue.
Does not create the Jira issue itself.

  py -3 scripts/build_shipit_change_request.py --jira-json jira_<VERSION>.json --fix-version <VERSION> --config config.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from normalize_tickets import normalize_issues
from upload_to_sharepoint import month_folder_from_version


def calendar_parts(fix_version: str) -> tuple[int, int, int]:
    parts = fix_version.strip().split(".")
    if len(parts) >= 4:
        return int(parts[0]), int(parts[2]), int(parts[3])
    raise ValueError(f"Unexpected fix version format: {fix_version}")


def planned_window(fix_version: str, shipit: dict) -> dict[str, str]:
    year, month, day = calendar_parts(fix_version)
    start = shipit.get("planned_start_local") or "10:30"
    end = shipit.get("planned_end_local") or "12:30"
    tz = shipit.get("timezone_offset") or "+0530"
    sh, sm = start.split(":")
    eh, em = end.split(":")
    start_iso = f"{year:04d}-{month:02d}-{day:02d}T{int(sh):02d}:{int(sm):02d}:00.000{tz}"
    end_iso = f"{year:04d}-{month:02d}-{day:02d}T{int(eh):02d}:{int(em):02d}:00.000{tz}"
    window_label = f"{day} {month_name(month)} {year} {start}AM–{end}PM IST"
    return {
        "start_iso": start_iso,
        "end_iso": end_iso,
        "label": window_label,
    }


def month_name(month: int) -> str:
    names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    return names[month]


def sharepoint_docx_url(sharepoint: dict, fix_version: str) -> str:
    site = (sharepoint.get("site_url") or "").rstrip("/")
    month = month_folder_from_version(fix_version)
    root = sharepoint.get("folder_name") or "deployment bot release notes"
    filename = f"Release Notes {fix_version}.docx"
    path = (
        "/Shared%20Documents/Glofox%20-%20Customize/Release%20Notes/"
        f"{root.replace(' ', '%20')}/{month}/{filename.replace(' ', '%20')}"
    )
    return f"{site}{path}"


def adf_text(text: str, *, strong: bool = False) -> dict:
    node: dict = {"type": "text", "text": text}
    if strong:
        node["marks"] = [{"type": "strong"}]
    return node


def adf_link(text: str, href: str) -> dict:
    return {
        "type": "text",
        "text": text,
        "marks": [{"type": "link", "attrs": {"href": href}}],
    }


def adf_para(*nodes: dict) -> dict:
    return {"type": "paragraph", "content": list(nodes) if nodes else []}


def adf_doc(*blocks: dict) -> dict:
    return {"type": "doc", "version": 1, "content": list(blocks)}


def adf_ordered(*items: str) -> dict:
    return {
        "type": "orderedList",
        "attrs": {"order": 1},
        "content": [
            {
                "type": "listItem",
                "content": [adf_para(adf_text(item))],
            }
            for item in items
        ],
    }


def build_payload(
    issues: list[dict],
    fix_version: str,
    config: dict,
    *,
    test_ticket: bool = False,
) -> dict:
    shipit = config.get("shipit") or {}
    sharepoint = config.get("sharepoint") or {}
    site = config.get("jira_site") or "https://abcfinancial.atlassian.net"
    rows = normalize_issues(issues, categories=config.get("summary_categories"))
    if not rows:
        raise ValueError("No tickets to put on the Change Request.")

    window = planned_window(fix_version, shipit)
    notes_url = sharepoint_docx_url(sharepoint, fix_version)
    notes_name = f"Release Notes {fix_version}.docx"
    clients = list(dict.fromkeys(r["client"] for r in rows))
    reports = list(dict.fromkeys(r["report"] for r in rows))
    keys = [r["key"] for r in rows]

    prefix = "TEST TICKET - DO NOT ACTION - " if test_ticket else ""
    summary = (
        f"{prefix}Glofox Insights Customize BI - Prod Deployment - "
        f"Release Version {fix_version}"
    )

    change_bullets = []
    for row in rows:
        change_bullets.append(
            f"* {row['client']} — change **{row['report']}** {row['description']} "
            f"([{row['key']}]({row['link']}))."
        )
    client_phrase = ", ".join(clients)
    report_phrase = ", ".join(reports)
    ticket_lines = "\n".join(
        f"* [{row['key']}]({row['link']}) — {row['client']} {row['report']} "
        f"(Jira status: {row['status'] or 'unknown'})"
        for row in rows
    )
    test_banner = ""
    if test_ticket:
        test_banner = (
            "**THIS IS A TEST TICKET created by Deployment Bot. "
            "Do not deploy, approve, or action anything from this ticket.**\n\n"
        )

    description = (
        f"{test_banner}"
        "**What is changing, in business terms**\n\n"
        + "\n".join(change_bullets)
        + "\n\n**Who is affected**\n\n"
        f"Entitled {client_phrase} users of {report_phrase}. "
        "The tickets do not document an affected-user count.\n\n"
        "**Not included in this change**\n\n"
        "* Production RLS, workspace access, and capacity settings.\n"
        "* Any reports other than those listed above.\n\n"
        "**How it is deployed**\n\n"
        f"Back up the current Production version of {report_phrase}. "
        "Publish the updated report(s) to the customer-facing V2 Fitness BI workspace. "
        "Do not change RLS, access, or capacity.\n\n"
        "**Supporting records**\n\n"
        f"{ticket_lines}\n"
        f"* Planned window on this request: {window['label']}\n"
        f"* Release notes: [{notes_name}]({notes_url})\n"
    )
    if test_ticket:
        description += (
            "\n**Note on ownership**\n\n"
            "Assignee is intentionally left blank. The deployment owner is assigned per deployment.\n"
        )

    warn = "TEST TICKET - do not execute. " if test_ticket else ""
    impl_blocks = [
        adf_para(adf_text(f"{warn}Pre-deployment backups", strong=True))
        if test_ticket
        else adf_para(adf_text("Pre-deployment backups", strong=True)),
        adf_para(
            adf_text(
                f"Take backups of the current Production {report_phrase} before deployment."
            )
        ),
        adf_para(
            adf_text(
                "Deploy updated reports to the customer-facing V2 Fitness BI workspace."
            )
        ),
    ]
    for row in rows:
        impl_blocks.append(
            adf_para(
                adf_text(
                    f"{row['client']} ({row['key']}): publish the updated {row['report']} "
                    f"({row['description']})."
                )
            )
        )
    impl_blocks.append(
        adf_para(
            adf_text(
                "Do not change Production RLS, workspace access, or capacity settings "
                "unless explicitly required by a ticket in this release."
            )
        )
    )

    verify_items = [
        f"{row['client']} ({row['key']}): verify {row['report']} matches "
        f"{row['description']}."
        for row in rows
    ]
    verify_items.append(
        "Smoke-test one other existing customer-facing report in the same workspace is unaffected."
    )
    verify_items.append(
        "Record validator, timestamp, screenshots, expected vs observed, pass/fail. "
        "Roll back on mismatch or smoke-test failure."
    )

    comms = adf_doc(
        adf_para(adf_text(f"{warn}Pre-deployment", strong=True)),
        adf_para(
            adf_text(
                "Notify the insights-customize-squad channel for the production window. "
                "Confirm Pass QA on the linked tickets."
            )
        ),
        adf_para(adf_text("During deployment", strong=True)),
        adf_para(
            adf_text(
                "Post start and completion status and capture Deployment ID and time. "
                "Stop further publishes if the deploy fails and alert the Release Owner immediately."
            )
        ),
        adf_para(adf_text("After success", strong=True)),
        adf_para(
            adf_text(
                "Notify stakeholders when verification checklist passes. "
                "Then share Product/CSM release notes."
            )
        ),
        adf_para(adf_text("After rollback", strong=True)),
        adf_para(
            adf_text(
                "Notify the same channel: change is not in Production, previous report "
                "version is restored, and the failed artifact stays out of Production until retested."
            )
        ),
    )
    if test_ticket:
        comms["content"].insert(
            0, adf_para(adf_text("TEST TICKET - do not send any of these communications.", strong=True))
        )

    impact_blocks = []
    if test_ticket:
        impact_blocks.append(
            adf_para(adf_text("TEST TICKET - for automation validation only.", strong=True))
        )
    impact_blocks.extend(
        [
            adf_para(
                adf_text(
                    f"This release deploys Insights Customize report change(s) for {client_phrase}: "
                    f"{report_phrase}."
                )
            ),
            adf_para(
                adf_text("Audience and boundary: ", strong=True),
                adf_text(
                    f"Entitled {client_phrase} users of {report_phrase}. "
                    "Other reports, RLS, workspace access, and capacity are unchanged."
                ),
            ),
            adf_para(
                adf_text("Measured impact: ", strong=True),
                adf_text(
                    "No affected-user count supplied on the ticket; no numerical impact claim."
                ),
            ),
        ]
    )
    for row in rows:
        impact_blocks.append(
            adf_para(
                adf_text("Ticket: ", strong=True),
                adf_link(row["key"], row["link"]),
            )
        )

    risk_blocks = []
    if test_ticket:
        risk_blocks.append(
            adf_para(
                adf_text(
                    "TEST TICKET - risk content included only to validate field mapping.",
                    strong=True,
                )
            )
        )
    risk_blocks.extend(
        [
            adf_para(adf_text("Overall", strong=True)),
            adf_para(
                adf_text(
                    "This change is limited to the listed customer-facing Fitness BI reports. "
                    "Primary failure modes are incorrect report results and publish to the wrong "
                    "workspace. Controls: pre-deploy backup, verification steps, stop on first "
                    "failure, restore only the failed report."
                )
            ),
            adf_para(adf_text("Shared controls", strong=True)),
            adf_para(
                adf_text(
                    "Do not change Production RLS, workspace access, or capacity. "
                    "Stop further publishes on first failure and alert the Release Owner."
                )
            ),
        ]
    )

    test_plan_nodes = []
    if test_ticket:
        test_plan_nodes.append(
            adf_para(adf_text("TEST TICKET - do not action.", strong=True))
        )
    for row in rows:
        test_plan_nodes.append(
            adf_para(
                adf_link(row["key"], row["link"]),
                adf_text(
                    f": {row['client']} {row['report']} — Jira status {row['status'] or 'unknown'}."
                ),
            )
        )
    test_plan_nodes.append(
        adf_para(
            adf_text("Release notes: "),
            adf_link(notes_name, notes_url),
        )
    )

    reason = "Production Deployment"
    if test_ticket:
        reason = "Production Deployment (TEST TICKET - not a real change request)"

    no_opt = {"value": "No"}
    additional_fields = {
        "priority": {"name": shipit.get("priority") or "Medium"},
        "customfield_11715": reason,
        "customfield_11757": {"value": shipit.get("change_type") or "Normal"},
        "customfield_11758": {"value": shipit.get("change_risk") or "Medium"},
        "customfield_11763": window["start_iso"],
        "customfield_11764": window["end_iso"],
        "customfield_11765": window["start_iso"],
        "customfield_11794": [
            {"groupId": shipit.get("approver_group_id") or "7e6deb19-8ce4-46c8-88cd-a695a554e5f8"}
        ],
        "customfield_16101": no_opt,
        "customfield_15908": {"value": shipit.get("new_update_app") or "New app"},
        "customfield_15727": no_opt,
        "customfield_15837": no_opt,
        "customfield_15845": no_opt,
        "customfield_15896": no_opt,
        "customfield_15971": no_opt,
        "customfield_15993": no_opt,
        "customfield_11717": comms,
        "customfield_11720": adf_doc(*impl_blocks),
        "customfield_11721": adf_doc(
            *([adf_para(adf_text(warn.strip(), strong=True))] if test_ticket else []),
            adf_ordered(*verify_items),
        ),
        "customfield_11722": adf_doc(
            *([adf_para(adf_text(warn.strip(), strong=True))] if test_ticket else []),
            adf_para(
                adf_text(
                    "If verification fails, halt the deploy and restore from the pre-deployment backup."
                )
            ),
            adf_para(
                adf_text(
                    f"Republish the previous {report_phrase}. Smoke-test the restored report "
                    "and one other existing customer-facing report."
                )
            ),
            adf_para(
                adf_text(
                    "Notify stakeholders, set deployment status to Rolled back, comment on the "
                    "linked tickets, and keep the failed package out of Production until a "
                    "retested build is ready. No data migration or deletion is in scope. "
                    "No RLS or access rollback is expected."
                )
            ),
        ),
        "customfield_14549": adf_doc(*impact_blocks),
        "customfield_17225": adf_doc(*risk_blocks),
        "customfield_11762": adf_doc(*test_plan_nodes),
    }

    return {
        "projectKey": shipit.get("project_key") or "SHIPIT",
        "issueTypeName": shipit.get("issue_type") or "Change Request",
        "summary": summary,
        "description": description,
        "assignee_account_id": None,
        "leave_assignee_blank": True,
        "leave_request_type_blank": True,
        "additional_fields": additional_fields,
        "link": {
            "type": shipit.get("link_type") or "Discovery - Connected",
            "inward_keys": keys,
            "note": "For each key: inwardIssue=work ticket, outwardIssue=new SHIPIT key.",
        },
        "sharepoint_url": notes_url,
        "jira_site": site,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SHIPIT Change Request payload JSON.")
    parser.add_argument("--jira-json", required=True)
    parser.add_argument("--fix-version", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--test-ticket", action="store_true")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    raw = json.loads(Path(args.jira_json).read_text(encoding="utf-8"))
    issues = raw.get("issues") if isinstance(raw, dict) else raw
    try:
        payload = build_payload(
            issues or [],
            args.fix_version,
            config,
            test_ticket=args.test_ticket,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    text = json.dumps(payload, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
