import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.impact import ROOT
from src.review_agent import run_review


class RelianceQuestionTests(unittest.TestCase):
    def test_supported_phrasings_preserve_object_scope_and_consumers(self):
        cases = [
            (
                "Which views rely on orders?",
                "orders", "all", ["order_summary", "regional_sales"],
            ),
            (
                "Which direct views rely on orders?",
                "orders", "direct", ["order_summary"],
            ),
            (
                "Which indirect views rely on orders?",
                "orders", "indirect", ["regional_sales"],
            ),
            (
                "Which views rely on customers?",
                "customers", "all", ["customer_directory", "regional_sales"],
            ),
            (
                "Which view relies on order_summary?",
                "order_summary", "all", ["regional_sales"],
            ),
            (
                "Which views are relying on orders?",
                "orders", "all", ["order_summary", "regional_sales"],
            ),
        ]

        for question, name, scope, consumers in cases:
            with self.subTest(question=question):
                receipt = run_review(question)
                self.assertEqual(receipt["status"], "completed")
                self.assertEqual(receipt["plan"]["object"], name)
                self.assertEqual(receipt["plan"]["scope"], scope)
                self.assertEqual(
                    (receipt["model_calls"], receipt["tool_calls"]), (0, 1)
                )
                self.assertEqual(
                    [
                        hit["object"]
                        for hit in receipt["report"]["potentially_affected"]
                    ],
                    consumers,
                )

    def test_unrelated_reverse_unknown_and_destructive_requests_do_not_use_tools(self):
        questions = [
            ("I rely on orders", "clarification_required"),
            ("Which views do orders rely on?", "clarification_required"),
            ("How many rows rely on orders?", "clarification_required"),
            ("Which views rely on payments?", "clarification_required"),
            ("Which views rely on orders_backup?", "clarification_required"),
            (
                "Which views rely on orders and customers?",
                "clarification_required",
            ),
            ("Which views rely on orders? DELETE orders", "rejected"),
        ]

        for question, status in questions:
            with self.subTest(question=question):
                with patch("src.review_agent.check_evidence") as tool:
                    receipt = run_review(question)
                self.assertEqual(receipt["status"], status)
                self.assertEqual(receipt["tool_calls"], 0)
                tool.assert_not_called()

    def test_streamlit_accepts_the_new_phrase(self):
        app = AppTest.from_file(
            str(ROOT / "app.py"), default_timeout=20
        ).run()
        app.text_input(key="review_question").set_value(
            "Which views rely on orders?"
        ).run()
        app.button(key="review_run").click().run()

        self.assertFalse(app.exception)
        self.assertTrue(any(
            "Review order_summary" in item.value
            for item in app.markdown
        ))
        self.assertTrue(any(
            "Review regional_sales" in item.value
            for item in app.markdown
        ))
        self.assertTrue(any(
            item.proto.label == "Download change-review receipt"
            for item in app.get("download_button")
        ))
