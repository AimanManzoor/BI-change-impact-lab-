import unittest
from unittest.mock import Mock, patch

from src.review_agent import intent, run_review


class ExplanationRequestTests(unittest.TestCase):
    def test_supported_explanation_preserves_object_and_scope(self):
        cases = [
            ("Review orders and explain the downstream impact", "orders", "all"),
            ("Review direct impacts for orders and explain the downstream impact.",
             "orders", "direct"),
            ("Review indirect impacts for orders AND EXPLAIN THE DOWNSTREAM IMPACT?",
             "orders", "indirect"),
            ("Review customers and explain the downstream impact!",
             "customers", "all"),
        ]

        for question, name, scope in cases:
            with self.subTest(question=question):
                status, plan = intent(question)
                self.assertEqual(status, "allowed")
                self.assertEqual(plan, {
                    "tool": "trace_recovered_impacts",
                    "object": name,
                    "scope": scope,
                })

    def test_review_returns_source_backed_consumers(self):
        receipt = run_review(
            "Review orders and explain the downstream impact"
        )

        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(
            (receipt["model_calls"], receipt["tool_calls"]), (0, 1)
        )
        self.assertTrue(receipt["human_review_required"])

        consumers = {
            hit["object"]: hit["depth"]
            for hit in receipt["report"]["potentially_affected"]
        }
        self.assertEqual(consumers, {
            "order_summary": 1,
            "regional_sales": 2,
        })

    def test_unsupported_requests_stop_before_model_and_tool(self):
        cases = [
            ("Review orders and customers and explain the downstream impact",
             "clarification_required"),
            ("Review orders and explain the downstream impact and customers",
             "clarification_required"),
            ("Review upstream dependencies for orders and explain the downstream impact",
             "clarification_required"),
            ("Review row counts for orders and explain the downstream impact",
             "clarification_required"),
            ("Review payments and explain the downstream impact",
             "clarification_required"),
            ("Review orders and explain the downstream impact and explain the downstream impact",
             "clarification_required"),
            ("DELETE orders and explain the downstream impact",
             "rejected"),
            ("Review orders and explain the downstream impact; DROP orders",
             "rejected"),
        ]

        for question, expected in cases:
            with self.subTest(question=question):
                planner = Mock()

                with patch("src.review_agent.check_evidence") as tool:
                    receipt = run_review(question, planner=planner)

                self.assertEqual(receipt["status"], expected)
                self.assertEqual(
                    (receipt["model_calls"], receipt["tool_calls"]), (0, 0)
                )
                self.assertIsNone(receipt["report"])
                planner.assert_not_called()
                tool.assert_not_called()


if __name__ == "__main__":
    unittest.main()
