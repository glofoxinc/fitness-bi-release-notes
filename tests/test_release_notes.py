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
from normalize_tickets import split_client_report_desc  # noqa: E402


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
