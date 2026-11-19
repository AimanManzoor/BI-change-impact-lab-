import io
import json
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from src.impact import ROOT
from src.review_agent import intent, model_planner, parse_proposal, run_review


class ReviewAgentTests(unittest.TestCase):
    def test_reference_questions(self):
        cases = [
            ("Which downstream views depend on orders?", "completed", "orders", "all", ["order_summary", "regional_sales"]),
            ("Which direct views depend on orders?", "completed", "orders", "direct", ["order_summary"]),
            ("Which indirect views depend on orders?", "completed", "orders", "indirect", ["regional_sales"]),
            ("Review downstream impacts for customers", "completed", "customers", "all", ["customer_directory", "regional_sales"]),
            ("Review downstream impacts for order_summary", "completed", "order_summary", "all", ["regional_sales"]),
            ("Review downstream impacts for regional_sales", "no_consumers", "regional_sales", "all", []),
            ("Review downstream impacts for customer_directory", "no_consumers", "customer_directory", "all", []),
            ("Review payments", "clarification_required", None, None, []),
            ("Review orders and customers", "clarification_required", None, None, []),
            ("DROP orders and review impact", "rejected", None, None, []),
            ("What color is orders?", "clarification_required", None, None, []),
            ("Review direct and indirect impacts for orders", "clarification_required", None, None, []),
        ]
        for question, status, name, scope, consumers in cases:
            with self.subTest(question=question):
                result = run_review(question)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["model_calls"], 0)
                self.assertEqual(result["tool_calls"], 1 if name else 0)
                if name:
                    self.assertEqual(result["plan"]["object"], name)
                    self.assertEqual(result["plan"]["scope"], scope)
                    self.assertEqual([hit["object"] for hit in result["report"]["potentially_affected"]], consumers)

    def test_unsupported_requests_call_neither_planner_nor_tool(self):
        for question in (None, "", "x" * 1001, "Review orders and customers", "DELETE FROM orders",
                         "Review orders and payments", "Review everything except orders",
                         "Run SQL to review orders", "Modify orders and review impacts"):
            planner = Mock()
            with patch("src.review_agent.check_evidence") as tool:
                run_review(question, planner=planner)
            planner.assert_not_called()
            tool.assert_not_called()

    def test_model_cannot_change_tool_object_or_scope(self):
        valid = intent("Review direct impacts for orders")[1]
        for changes in ({"tool": "execute_sql"}, {"object": "customers"}, {"scope": "all"}):
            planner = Mock(return_value=json.dumps({**valid, **changes}))
            with patch("src.review_agent.check_evidence") as tool:
                result = run_review("Review direct impacts for orders", planner=planner)
            self.assertEqual(result["status"], "plan_rejected")
            planner.assert_called_once()
            tool.assert_not_called()

    def test_malformed_plans_and_duplicate_keys_are_rejected(self):
        for text in ('{}', '[]', '{"tool":"a","tool":"b"}', 'x' * 2049):
            with self.subTest(text=text[:50]), self.assertRaises(ValueError):
                parse_proposal(text)

    def test_planner_error_has_no_retry_or_tool_call(self):
        planner = Mock(side_effect=TimeoutError("PRIVATE_API_DETAIL"))
        result = run_review("Review orders impacts", planner=planner)
        self.assertEqual(result["status"], "planner_error")
        self.assertEqual((result["model_calls"], result["tool_calls"]), (1, 0))
        self.assertNotIn("PRIVATE_API_DETAIL", json.dumps(result))
        planner.assert_called_once()

    def test_evidence_failure_produces_no_report(self):
        with patch("src.review_agent.check_evidence", side_effect=ValueError("bad evidence")) as tool:
            result = run_review("Review orders impacts")
        tool.assert_called_once()
        self.assertEqual(result["status"], "evidence_error")
        self.assertIsNone(result["report"])

    def test_optional_provider_adapter_with_simulated_response(self):
        plan = intent("Review orders impacts")[1]
        body = json.dumps({"stop_reason": "end_turn", "content": [
            {"type": "text", "text": json.dumps(plan)}]}).encode()
        transport = Mock(side_effect=lambda *args, **kwargs: io.BytesIO(body))
        planner = model_planner(model="test-model", api_key="test-key", transport=transport)
        result = run_review("Review orders impacts", planner=planner)
        self.assertEqual(result["status"], "completed")
        self.assertEqual((result["model_calls"], result["tool_calls"]), (1, 1))
        sent = json.loads(transport.call_args.args[0].data)
        self.assertIn("read-only BI review plan", sent["system"])
        self.assertNotIn("recovered_sql", sent["messages"][0]["content"])
        transport.assert_called_once()

    def test_cli_json_and_rejected_live_request_needs_no_credentials(self):
        for question, options, expected_code in (
            ("Review orders impacts", [], 0),
            ("Review payments", [], 1),
            ("DROP orders", ["--live", "--model", "test-model"], 1),
        ):
            process = subprocess.run(
                [sys.executable, "-m", "src.review_agent", "--question", question, *options],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, expected_code, process.stderr)
            receipt = json.loads(process.stdout)
            self.assertEqual(receipt["model_calls"], 0)


class ReviewUiTests(unittest.TestCase):
    def launch(self):
        return AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()

    def test_success_then_question_change_hides_old_receipt(self):
        app = self.launch().button(key="review_run").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Review order_summary" in item.value for item in app.markdown))
        app.text_input(key="review_question").set_value("Review customers impacts").run()
        self.assertFalse(any(item.proto.label == "Download change-review receipt"
                             for item in app.get("download_button")))

    def test_rejected_question_displays_no_receipt(self):
        app = self.launch()
        app.text_input(key="review_question").set_value("DROP orders").run()
        app.button(key="review_run").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Review stopped: rejected" in item.value for item in app.warning))
        self.assertFalse(any(item.proto.label == "Download change-review receipt"
                             for item in app.get("download_button")))

    def test_changed_fingerprint_hides_previous_receipt(self):
        app = self.launch().button(key="review_run").click().run()
        digest = Mock()
        digest.hexdigest.return_value = "changed-source-fingerprint"
        with patch("src.review_ui.hashlib.sha256", return_value=digest):
            app.run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.proto.label == "Download change-review receipt"
                             for item in app.get("download_button")))
