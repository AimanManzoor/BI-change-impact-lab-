import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from src.impact import ROOT
from src.review_agent import run_review


class ReviewScopeTests(unittest.TestCase):
    def test_unsupported_analysis_calls_neither_planner_nor_tool(self):
        questions = [
            "Review upstream dependencies for orders",
            "Review the number of rows in orders",
            "Review row counts for customers",
            "Review the count of rows in orders",
            "How many rows are in orders?",
            "Count rows in orders",
        ]

        for question in questions:
            with self.subTest(question=question):
                planner = Mock()
                with patch("src.review_agent.check_evidence") as tool:
                    receipt = run_review(question, planner=planner)

                self.assertEqual(
                    receipt["status"], "clarification_required"
                )
                self.assertEqual(
                    (receipt["model_calls"], receipt["tool_calls"]),
                    (0, 0),
                )
                self.assertIsNone(receipt["plan"])
                self.assertIsNone(receipt["report"])
                planner.assert_not_called()
                tool.assert_not_called()

    def test_downstream_analysis_and_write_rejection_are_preserved(self):
        cases = [
            ("Which downstream views depend on orders?", "all"),
            ("Which direct views rely on orders?", "direct"),
            ("Which indirect views rely on orders?", "indirect"),
        ]

        for question, scope in cases:
            with self.subTest(question=question):
                receipt = run_review(question)
                self.assertEqual(receipt["status"], "completed")
                self.assertEqual(receipt["plan"]["scope"], scope)
                self.assertEqual(receipt["tool_calls"], 1)

        with patch("src.review_agent.check_evidence") as tool:
            receipt = run_review("DELETE rows from orders")
        self.assertEqual(receipt["status"], "rejected")
        tool.assert_not_called()

    def test_ui_hides_previous_report_for_upstream_request(self):
        app = AppTest.from_file(
            str(ROOT / "app.py"), default_timeout=20
        ).run()

        app.button(key="review_run").click().run()
        app.text_input(key="review_question").set_value(
            "Review upstream dependencies for orders"
        ).run()
        app.button(key="review_run").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any(
            "Review stopped: clarification_required" in item.value
            for item in app.warning
        ))
        self.assertFalse(any(
            item.proto.label == "Download change-review receipt"
            for item in app.get("download_button")
        ))
