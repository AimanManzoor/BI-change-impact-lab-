import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from src.impact import ROOT
from src.review_agent import run_review


class ReadonlyAssuranceTests(unittest.TestCase):
    def test_exact_assurance_preserves_object_scope_and_results(self):
        cases = [
            (
                "Review downstream impacts for orders without changing it",
                "orders", "all", "completed",
                ["order_summary", "regional_sales"],
            ),
            (
                "Review direct impacts for orders without changing it.",
                "orders", "direct", "completed", ["order_summary"],
            ),
            (
                "Review indirect impacts for orders without changing it?",
                "orders", "indirect", "completed", ["regional_sales"],
            ),
            (
                "Which views rely on customers without changing it!",
                "customers", "all", "completed",
                ["customer_directory", "regional_sales"],
            ),
            (
                "Review downstream impacts for regional_sales without changing it",
                "regional_sales", "all", "no_consumers", [],
            ),
            (
                "Review orders WITHOUT CHANGING IT   ",
                "orders", "all", "completed",
                ["order_summary", "regional_sales"],
            ),
        ]

        for question, name, scope, status, consumers in cases:
            with self.subTest(question=question):
                receipt = run_review(question)
                self.assertEqual(receipt["status"], status)
                self.assertEqual(receipt["plan"]["object"], name)
                self.assertEqual(receipt["plan"]["scope"], scope)
                self.assertEqual(
                    (receipt["model_calls"], receipt["tool_calls"]),
                    (0, 1),
                )
                self.assertEqual(
                    [
                        hit["object"]
                        for hit in receipt["report"]["potentially_affected"]
                    ],
                    consumers,
                )

    def test_ambiguous_write_and_unsupported_requests_do_not_call_tools(self):
        cases = [
            ("Review orders without customers", "clarification_required"),
            ("Review orders without changing customers", "clarification_required"),
            ("Review orders without changing it and customers", "clarification_required"),
            ("Review orders without changing it without changing it", "clarification_required"),
            ("Review orders without changing it DELETE rows", "rejected"),
            ("DELETE orders without changing it", "rejected"),
            ("Review upstream dependencies for orders without changing it", "clarification_required"),
            ("Review row counts for orders without changing it", "clarification_required"),
            ("Review orders and customers without changing it", "clarification_required"),
            ("Review without changing it", "clarification_required"),
            ("Review orders except customers without changing it", "clarification_required"),
        ]

        for question, status in cases:
            with self.subTest(question=question):
                planner = Mock()
                with patch("src.review_agent.check_evidence") as tool:
                    receipt = run_review(question, planner=planner)

                self.assertEqual(receipt["status"], status)
                self.assertEqual(
                    (receipt["model_calls"], receipt["tool_calls"]),
                    (0, 0),
                )
                self.assertIsNone(receipt["report"])
                planner.assert_not_called()
                tool.assert_not_called()

    def test_ui_accepts_assurance_then_hides_report_for_ambiguity(self):
        app = AppTest.from_file(
            str(ROOT / "app.py"), default_timeout=20
        ).run()

        app.text_input(key="review_question").set_value(
            "Review orders without changing it"
        ).run()
        app.button(key="review_run").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any(
            item.proto.label == "Download change-review receipt"
            for item in app.get("download_button")
        ))

        app.text_input(key="review_question").set_value(
            "Review orders without customers"
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
