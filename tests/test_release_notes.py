import sys
import unittest
import zipfile
from pathlib import Path


SCRIPTS = (
    Path(__file__).parents[1]
    / ".cursor"
    / "skills"
    / "notebot"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from generate_release_notes import build_document  # noqa: E402
from normalize_tickets import (  # noqa: E402
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
        "Standard: Course bookings",
        "Course bookings",
        "Course bookings",
    ),
    (
        _issue("AN-5396", "AN", "Analyze - Remove older class utilization dashboard"),
        "Standard: Remove older class utilization dashboard",
        "class utilization dashboard",
        "Remove older class utilization dashboard",
    ),
    (
        _issue(
            "AN-5468",
            "AN",
            "Insights Analyze- Remove Jetts Vasant Square Mall from Fitness BI Reporting",
        ),
        "Standard: Remove Jetts Vasant Square Mall from Fitness BI Reporting",
        "All Reports",
        "Remove Jetts Vasant Square Mall from Fitness BI Reporting",
    ),
    (
        _issue("PIC-5407", "PIC", "XtremeFitness - Custom semantic model optimization"),
        "XtremeFitness: Custom semantic model optimization",
        "Custom semantic model",
        "Custom semantic model optimization",
    ),
    (
        _issue(
            "PIC-5673", "PIC", "Lift - ABC Customize - Medallia reports(New Paginated Report)"
        ),
        "Lift: Medallia reports (New Paginated Report)",
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
        "Jazzercise: Class Participation Report - Event Details tab - "
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
        self.assertEqual(line, "Standard: Remove older class utilization dashboard")


class ReportNameExtractionTests(unittest.TestCase):
    def test_analyze_report_name(self):
        self.assertEqual(
            split_client_report_desc(
                "Course bookings - Create a paginated report", "Analyze"
            ),
            ("Standard", "Course bookings", "Create a paginated report"),
        )

    def test_hyphenated_report_name_is_preserved(self):
        client, report, _ = split_client_report_desc(
            "E-agreements by Member", "Analyze"
        )
        self.assertEqual(client, "Standard")
        self.assertEqual(report, "E-agreements by Member")

    def test_analyze_dashboard_name_removes_change_wording(self):
        client, report, _ = split_client_report_desc(
            "Remove older class utilization dashboard", "Analyze"
        )
        self.assertEqual(client, "Standard")
        self.assertEqual(report.lower(), "class utilization dashboard")

    def test_analyze_without_named_report_uses_all_reports(self):
        client, report, _ = split_client_report_desc(
            "Remove Jetts Vasant Square Mall from Fitness BI Reporting", "Analyze"
        )
        self.assertEqual(client, "Standard")
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


class HyperlinkTests(unittest.TestCase):
    def test_change_detail_link_is_a_real_docx_hyperlink(self):
        url = "https://abcfinancial.atlassian.net/browse/AN-5359"
        payload = {
            "fix_version": "2026.3.08.05",
            "tickets": [
                {
                    "key": "AN-5359",
                    "parent": "AN-5356",
                    "link": url,
                    "type": "Analyze",
                    "client": "Standard",
                    "report": "Course bookings",
                    "description": "Create a paginated report",
                }
            ],
        }
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


if __name__ == "__main__":
    unittest.main()
