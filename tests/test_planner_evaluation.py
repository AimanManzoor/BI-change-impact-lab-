import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.evaluate_planner import REFERENCE, evaluate, load_reference
from src.impact import ROOT
from src.review_agent import run_review


class PlannerEvaluationTests(unittest.TestCase):
    def test_regression_reference_and_challenge_reporting(self):
        regression = evaluate()
        self.assertEqual((regression["cases"], regression["passed"], regression["failed"]), (16, 16, 0))
        self.assertEqual(regression["model_calls"], 0)
        challenge = evaluate("challenge")
        self.assertEqual(challenge["cases"], 6)
        self.assertEqual(challenge["passed"] + challenge["failed"], 6)
        self.assertEqual(sum(group["cases"] for group in challenge["categories"].values()), 6)
        self.assertEqual(sum(item["cases"] for item in challenge["status_confusion"]), 6)

    def test_wrong_reference_is_detected_and_fingerprint_changes(self):
        reference, original_hash = load_reference()
        reference["cases"][0]["expected"]["plan"]["scope"] = "indirect"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reference.json"
            path.write_text(json.dumps(reference))
            report = evaluate(reference_path=path)
        self.assertEqual(report["failed"], 1)
        self.assertIn("plan", report["outcomes"][0]["failed_checks"])
        self.assertNotEqual(report["reference_sha256"], original_hash)

    def test_checker_detects_wrong_consumers_tool_budget_and_model_calls(self):
        def broken(question):
            receipt = run_review(question)
            receipt["tool_calls"] = 99
            receipt["model_calls"] = 1
            if receipt["report"]:
                receipt["report"]["potentially_affected"].append({"object": "invented", "depth": 1})
            return receipt

        report = evaluate(runner=broken)
        self.assertEqual(report["failed"], 16)
        self.assertEqual(report["model_calls"], 16)
        self.assertIn("consumers", report["outcomes"][0]["failed_checks"])
        self.assertIn("tool_calls", report["outcomes"][0]["failed_checks"])
        self.assertIn("zero_model_calls", report["outcomes"][0]["failed_checks"])

    def test_missing_evidence_is_an_infrastructure_error(self):
        with patch("src.review_agent.check_evidence", side_effect=FileNotFoundError("PRIVATE_PATH")):
            report = evaluate()
        self.assertGreater(report["infrastructure_errors"], 0)
        self.assertNotIn("PRIVATE_PATH", json.dumps(report))

    def test_unexpected_runner_errors_do_not_disappear_as_measurements(self):
        def broken(question):
            raise RuntimeError("PRIVATE_DETAIL")

        report = evaluate(runner=broken)
        self.assertEqual(report["infrastructure_errors"], 16)
        self.assertEqual(report["failed"], 16)
        self.assertNotIn("PRIVATE_DETAIL", json.dumps(report))

    def test_empty_duplicate_and_inconsistent_references_are_rejected(self):
        reference = load_reference()[0]
        inconsistent = copy.deepcopy(reference)
        inconsistent["cases"][0]["expected"]["tool_calls"] = 0
        malformed = copy.deepcopy(reference)
        del malformed["cases"][0]["expected"]["plan"]
        variants = [dict(reference, cases=[]),
                    dict(reference, cases=[reference["cases"][0]] * 2), inconsistent, malformed]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reference.json"
            for variant in variants:
                path.write_text(json.dumps(variant))
                with self.subTest(variant=variant), self.assertRaises(ValueError):
                    load_reference(path)

    def test_cli_gate_measurement_and_invalid_reference_exit_codes(self):
        reference = load_reference()[0]
        reference["cases"][0]["expected"]["plan"]["scope"] = "indirect"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reference.json"
            path.write_text(json.dumps(reference))
            for options, expected_code in (([], 1), (["--measure"], 0)):
                process = subprocess.run([sys.executable, "-m", "evals.evaluate_planner",
                    "--reference", str(path), *options], cwd=ROOT, capture_output=True,
                    text=True, timeout=30)
                self.assertEqual(process.returncode, expected_code, process.stderr)
                self.assertEqual(json.loads(process.stdout)["failed"], 1)
            path.write_text('{"cases":[]}')
            process = subprocess.run([sys.executable, "-m", "evals.evaluate_planner",
                "--reference", str(path), "--measure"], cwd=ROOT, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(process.returncode, 2)

    def test_measurement_mode_still_fails_on_infrastructure_error(self):
        from evals.evaluate_planner import main
        report = evaluate()
        report["infrastructure_errors"] = 1
        with patch("evals.evaluate_planner.evaluate", return_value=report), \
             patch("sys.argv", ["evaluate_planner", "--measure"]), \
             patch("builtins.print"):
            self.assertEqual(main(), 2)
