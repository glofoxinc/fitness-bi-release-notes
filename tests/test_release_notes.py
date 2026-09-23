import json
import sys
import unittest
import zipfile
from pathlib import Path


SCRIPTS = (
    Path(__file__).parents[1]
    / ".cursor"
    / "skills"
    / "deployment-bot"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from generate_release_notes import build_document  # noqa: E402
from check_pr_merge_status import (  # noqa: E402
    assert_all_prs_merged,
    check_issues,
    parse_pr_status,
)
from normalize_tickets import (  # noqa: E402
    assert_supported_projects,
    configured_project_types,
    highlight_line,
    normalize_issue,
    split_client_report_desc,
)


def _issue(key, project, summary, parent=""):
    fields = {"summary": summary, "project": {"key": project}}
    if parent:
        fields["parent"] = {"key": parent}
    return {"key": key, "fields": fields}


# Real fixVersion 2026.3.08.12 summaries
# -> (expected highlight, expected report, expected description)
LIVE_TICKETS = [
    (
        _issue("AN-5359", "AN", "ABC Insights - Analyse - Course bookings"),
        "Course bookings",
        "Course bookings",
        "Course bookings",
    ),
    (
        _issue("AN-5396", "AN", "Analyze - Remove older class utilization dashboard"),
        "class utilization dashboard - Remove older class utilization dashboard",
        "class utilization dashboard",
        "Remove older class utilization dashboard",
    ),
    (
        _issue(
            "AN-5468",
            "AN",
            "Insights Analyze- Remove Jetts Vasant Square Mall from Fitness BI Reporting",
        ),
        "All Reports - Remove Jetts Vasant Square Mall from Fitness BI Reporting",
        "All Reports",
        "Remove Jetts Vasant Square Mall from Fitness BI Reporting",
    ),
    (
        _issue("PIC-5407", "PIC", "XtremeFitness - Custom semantic model optimization"),
        "Custom semantic model - optimization",
        "Custom semantic model",
        "Custom semantic model optimization",
    ),
    (
        _issue(
            "PIC-5673", "PIC", "Lift - ABC Customize - Medallia reports(New Paginated Report)"
        ),
        "Medallia reports - (New Paginated Report)",
        "Medallia reports",
        "Medallia reports (New Paginated Report)",
    ),
    (
        _issue(
            "PIC-5924",
            "PIC",
            "Jazzercise - Class Participation Report - Event Details tab - "
            "Weekly Class Counts updates needed",
        ),
        "Class Participation Report - Event Details tab - "
        "Weekly Class Counts updates needed",
        "Class Participation Report",
        "Class Participation Report - Event Details tab - "
        "Weekly Class Counts updates needed",
    ),
]


class KeyHighlightVsReportSeparationTests(unittest.TestCase):
    def test_highlight_report_and_description_match_live_expectations(self):
        for issue, expected_highlight, expected_report, expected_desc in LIVE_TICKETS:
            row = normalize_issue(issue)
            self.assertEqual(
                row["highlight"], expected_highlight, msg=issue["key"]
            )
            self.assertEqual(row["report"], expected_report, msg=issue["key"])
            self.assertEqual(row["description"], expected_desc, msg=issue["key"])

    def test_description_is_never_a_bare_fragment(self):
        row = normalize_issue(
            _issue("PIC-5407", "PIC", "XtremeFitness - Custom semantic model optimization")
        )
        self.assertEqual(row["description"], "Custom semantic model optimization")
        self.assertNotEqual(row["description"], "optimization")

    def test_highlight_is_independent_of_report(self):
        # Key Highlights keeps the fuller ticket info even when Report is name-only.
        line = highlight_line(
            "Analyze - Remove older class utilization dashboard", "Analyze"
        )
        self.assertEqual(
            line,
            "class utilization dashboard - Remove older class utilization dashboard",
        )


class ReportNameExtractionTests(unittest.TestCase):
    def test_analyze_report_name(self):
        self.assertEqual(
            split_client_report_desc(
                "Course bookings - Create a paginated report", "Analyze"
            ),
            ("Glofox Analyze", "Course bookings", "Create a paginated report"),
        )

    def test_hyphenated_report_name_is_preserved(self):
        client, report, _ = split_client_report_desc(
            "E-agreements by Member", "Analyze"
        )
        self.assertEqual(client, "Glofox Analyze")
        self.assertEqual(report, "E-agreements by Member")

    def test_analyze_dashboard_name_removes_change_wording(self):
        client, report, _ = split_client_report_desc(
            "Remove older class utilization dashboard", "Analyze"
        )
        self.assertEqual(client, "Glofox Analyze")
        self.assertEqual(report.lower(), "class utilization dashboard")

    def test_analyze_without_named_report_uses_all_reports(self):
        client, report, _ = split_client_report_desc(
            "Remove Jetts Vasant Square Mall from Fitness BI Reporting", "Analyze"
        )
        self.assertEqual(client, "Glofox Analyze")
        self.assertEqual(report, "All Reports")

    def test_custom_report_excludes_explanation(self):
        self.assertEqual(
            split_client_report_desc(
                "Jazzercise - Class Participation Report - Event Details tab - "
                "Weekly Class Counts updates needed",
                "Custom",
            ),
            (
                "Jazzercise",
                "Class Participation Report",
                "Event Details tab - Weekly Class Counts updates needed",
            ),
        )

    def test_custom_parenthetical_explanation_removed(self):
        client, report, _ = split_client_report_desc(
            "Lift - Medallia reports (New Paginated Report)", "Custom"
        )
        self.assertEqual(client, "Lift")
        self.assertEqual(report, "Medallia reports")

    def test_semantic_model_name_excludes_action(self):
        client, report, description = split_client_report_desc(
            "XtremeFitness - Custom semantic model optimization", "Custom"
        )
        self.assertEqual(client, "XtremeFitness")
        self.assertEqual(report, "Custom semantic model")
        self.assertEqual(description, "optimization")


class JiraProjectScopeTests(unittest.TestCase):
    def test_live_scope_maps_glofox_boards(self):
        skill = Path(__file__).parents[1] / ".cursor" / "skills" / "deployment-bot"
        config = json.loads((skill / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(
            configured_project_types(config),
            {"AN": "Analyze", "PIC": "Custom"},
        )

    def test_unknown_project_stops_processing(self):
        with self.assertRaisesRegex(ValueError, "IGN"):
            assert_supported_projects(
                [_issue("IGN-1", "IGN", "Ignite - example")],
                {"AN": "Analyze", "PIC": "Custom"},
            )


class DocumentLayoutTests(unittest.TestCase):
    def _payload(self):
        url = "https://abcfinancial.atlassian.net/browse/AN-5359"
        return {
            "fix_version": "2026.3.08.05",
            "release_date": "05-August-2026",
            "meta": {
                "development_team": "Customize BI Team",
                "deployment_owner": "",
                "senior_manager": "Senior Manager",
                "director": "Must Not Render",
                "svp": "SVP",
                "environment": "Production",
            },
            "narratives": {
                "deployment_summary": "This deployment delivers 1 new report for Glofox Analyze."
            },
            "category_counts": [
                {"key": "new_reports", "label": "New Reports", "count": 1},
                {"key": "customizations", "label": "Customizations", "count": 0},
                {"key": "looker_exits", "label": "Looker Exits", "count": 0},
                {"key": "optimizations", "label": "Optimizations", "count": 0},
            ],
            "tickets": [
                {
                    "key": "AN-5359",
                    "parent": "AN-5356",
                    "link": url,
                    "type": "Analyze",
                    "client": "Glofox Analyze",
                    "report": "Course bookings",
                    "description": "Course bookings - Create a paginated report",
                }
            ],
            "excluded": [],
        }

    def test_ticket_link_is_a_real_docx_hyperlink(self):
        payload = self._payload()
        url = payload["tickets"][0]["link"]
        output = Path(__file__).with_name("_hyperlink_test.docx")
        try:
            build_document(payload).save(output)
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode()
                relationships_xml = archive.read(
                    "word/_rels/document.xml.rels"
                ).decode()
            self.assertIn("<w:hyperlink", document_xml)
            self.assertIn(url, relationships_xml)
        finally:
            output.unlink(missing_ok=True)

    def test_final_section_names_and_tables(self):
        doc = build_document(self._payload())
        headings_and_text = [p.text for p in doc.paragraphs if p.text]

        self.assertEqual(headings_and_text[0], "Deployment notes")
        self.assertNotIn("Release Notes", headings_and_text)
        self.assertIn("Deployment Summary:", headings_and_text)
        self.assertIn("Reports / Dashboards Delivered:", headings_and_text)
        self.assertIn("Affected Clients:", headings_and_text)
        self.assertIn("Deployment Details:", headings_and_text)
        self.assertIn("Ticket Details:", headings_and_text)
        self.assertIn("Testing Evidence:", headings_and_text)
        self.assertIn("Tickets Excluded from Deployment:", headings_and_text)

        all_text = " ".join(headings_and_text)
        all_table_text = " ".join(
            cell.text
            for table in doc.tables
            for row in table.rows
            for cell in row.cells
        )
        self.assertIn("Deployment Date", all_table_text)
        self.assertIn("Deployment Owner", all_table_text)
        self.assertNotIn("Release", f"{all_text} {all_table_text}")
        for removed in (
            "Key Highlights",
            "Dashboards / Reports:",
            "Change Details:",
            "Sanity Checklist",
            "Screenshots:",
            "Must Not Render",
            "Standard",
        ):
            self.assertNotIn(removed, all_text)

        # Header block + four visible content tables.
        self.assertEqual(len(doc.tables), 5)
        headers = [
            [cell.text for cell in table.rows[0].cells]
            for table in doc.tables[1:]
        ]
        self.assertEqual(headers[0], ["Category", "Count"])
        self.assertEqual(
            headers[1],
            ["Client", "Deployment Owner", "Status", "Deployment ID & Time"],
        )
        self.assertEqual(headers[2], ["Ticket", "Ticket Link", "Test", "Status"])
        self.assertEqual(
            headers[3],
            ["Ticket", "Ticket Link", "Client", "Report", "Notes"],
        )

    def test_delivered_report_includes_client_report_and_action(self):
        doc = build_document(self._payload())
        self.assertIn(
            "Glofox Analyze - Course bookings - Create a paginated report",
            [p.text for p in doc.paragraphs],
        )


class SharePointUploadTests(unittest.TestCase):
    def test_creates_folder_and_copies_docx(self):
        import tempfile

        from upload_to_sharepoint import upload_docx

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "Deployment Notes 2026.3.09.16.docx"
            src.write_bytes(b"docx-bytes")
            dest = upload_docx(
                src,
                {
                    "enabled": True,
                    "folder_name": "deployment bot release notes",
                    "local_sync_path": str(root / "library"),
                },
                fix_version="2026.3.09.16",
            )
            expected = (
                root
                / "library"
                / "deployment bot release notes"
                / "2026-09"
                / src.name
            )
            self.assertEqual(dest, expected)
            self.assertTrue(expected.is_file())
            self.assertEqual(expected.read_bytes(), b"docx-bytes")

    def test_month_folder_from_fix_version(self):
        from upload_to_sharepoint import month_folder_from_version

        self.assertEqual(month_folder_from_version("2026.3.09.16"), "2026-09")
        self.assertEqual(month_folder_from_version("2026.3.08.12"), "2026-08")

    def test_notes_docx_name(self):
        from upload_to_sharepoint import notes_docx_name

        self.assertEqual(
            notes_docx_name("2026.3.09.23", {"docx_prefix": "Deployment Notes"}),
            "Deployment Notes 2026.3.09.23.docx",
        )

    def test_slack_has_download_and_exact_folder_urls(self):
        from upload_to_sharepoint import (
            sharepoint_file_url,
            sharepoint_month_folder_url,
        )

        skill = Path(__file__).parents[1] / ".cursor" / "skills" / "deployment-bot"
        config = json.loads((skill / "config.json").read_text(encoding="utf-8"))
        sharepoint = config["sharepoint"]
        download = sharepoint_file_url(
            sharepoint,
            "2026.3.09.23",
            download=True,
        )
        folder = sharepoint_month_folder_url(sharepoint, "2026.3.09.23")

        self.assertIn("Deployment%20Notes%202026.3.09.23.docx", download)
        self.assertTrue(download.endswith("?download=1"))
        self.assertIn("Forms/AllItems.aspx?id=", folder)
        self.assertIn("2026-09", folder)


class PullRequestGateTests(unittest.TestCase):
    def _development_field(self, state, state_count, count):
        return (
            "{pullrequest={dataType=pullrequest, "
            f"state={state}, stateCount={state_count}"
            '}, json={"cachedValue":{"summary":{"pullrequest":{"overall":'
            f'{{"count":{count}'
        )

    def test_all_attached_prs_must_be_merged(self):
        value = self._development_field("MERGED", 2, 2)
        self.assertEqual(parse_pr_status(value)["status"], "merged")
        assert_all_prs_merged(
            [{"key": "PIC-1", "fields": {"customfield_10500": value}}]
        )

    def test_open_pr_blocks_generation(self):
        value = self._development_field("OPEN", 1, 2)
        blockers = check_issues(
            [{"key": "PIC-2", "fields": {"customfield_10500": value}}]
        )
        self.assertEqual(blockers[0]["status"], "not_merged")
        with self.assertRaisesRegex(ValueError, "PIC-2"):
            assert_all_prs_merged(
                [{"key": "PIC-2", "fields": {"customfield_10500": value}}]
            )

    def test_missing_pr_blocks_generation(self):
        blockers = check_issues([{"key": "AN-1", "fields": {}}])
        self.assertEqual(blockers[0]["status"], "missing")
        with self.assertRaisesRegex(ValueError, "no attached PR found"):
            assert_all_prs_merged([{"key": "AN-1", "fields": {}}])

    def test_live_config_enables_the_gate(self):
        skill = Path(__file__).parents[1] / ".cursor" / "skills" / "deployment-bot"
        config = json.loads((skill / "config.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "AN-2"):
            assert_all_prs_merged([{"key": "AN-2", "fields": {}}], config)

    def test_gate_can_be_disabled_by_config(self):
        assert_all_prs_merged(
            [{"key": "AN-3", "fields": {}}],
            {"pull_request_gate": {"enabled": False}},
        )


class ShipitChangeRequestTests(unittest.TestCase):
    def test_payload_for_2026_3_09_16(self):
        from build_shipit_change_request import build_payload

        skill = Path(__file__).parents[1] / ".cursor" / "skills" / "deployment-bot"
        config = json.loads((skill / "config.json").read_text(encoding="utf-8"))
        raw = json.loads((skill / "jira_2026.3.09.16.json").read_text(encoding="utf-8"))
        payload = build_payload(raw["issues"], "2026.3.09.16", config, test_ticket=True)
        self.assertTrue(payload["summary"].startswith("TEST TICKET - DO NOT ACTION -"))
        self.assertIn("2026.3.09.16", payload["summary"])
        self.assertTrue(payload["leave_assignee_blank"])
        self.assertTrue(payload["leave_request_type_blank"])
        self.assertIsNone(payload["assignee_account_id"])
        self.assertEqual(payload["link"]["inward_keys"], ["PIC-5966"])
        self.assertIn("PIC-5966", payload["description"])
        self.assertIn("Deployment Notes 2026.3.09.16.docx", payload["description"])
        self.assertIn("Deployment notes:", payload["description"])
        self.assertEqual(
            payload["transition_after_create"]["status_name"], "Review Ready"
        )
        self.assertEqual(payload["transition_after_create"]["status_id"], "14545")
        self.assertIn("deployment%20bot%20release%20notes/2026-09", payload["sharepoint_url"])
        self.assertTrue(payload["sharepoint_download_url"].endswith("?download=1"))
        self.assertIn("Forms/AllItems.aspx?id=", payload["sharepoint_folder_url"])
        fields = payload["additional_fields"]
        self.assertEqual(fields["customfield_11757"], {"value": "Normal"})
        self.assertEqual(fields["customfield_11758"], {"value": "Medium"})
        self.assertEqual(fields["priority"], {"name": "Medium"})
        self.assertEqual(
            fields["customfield_11794"],
            [{"groupId": "7e6deb19-8ce4-46c8-88cd-a695a554e5f8"}],
        )

    def test_optional_reporter_and_assignee_overrides(self):
        from build_shipit_change_request import build_payload

        skill = Path(__file__).parents[1] / ".cursor" / "skills" / "deployment-bot"
        config = json.loads((skill / "config.json").read_text(encoding="utf-8"))
        raw = json.loads((skill / "jira_2026.3.09.16.json").read_text(encoding="utf-8"))
        payload = build_payload(
            raw["issues"],
            "2026.3.09.16",
            config,
            reporter_account_id="reporter-id",
            reporter_name="Reporter Person",
            assignee_account_id="assignee-id",
            assignee_name="Deployment Owner",
        )

        self.assertEqual(payload["assignee_account_id"], "assignee-id")
        self.assertFalse(payload["leave_assignee_blank"])
        self.assertEqual(
            payload["additional_fields"]["reporter"],
            {"accountId": "reporter-id"},
        )
        self.assertEqual(payload["people"]["reporter"]["name"], "Reporter Person")
        self.assertEqual(payload["people"]["assignee"]["name"], "Deployment Owner")


if __name__ == "__main__":
    unittest.main()
