import copy
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from src.impact import ROOT, extract_fixture, build_report
from src.harness import run_harness, validate_plan


def plan(name='orders', **extra):
    return json.dumps({'tool': 'trace_downstream', 'object': name, **extra})


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = extract_fixture()

    def test_allowed_plan_calls_tool_once_and_returns_evidence(self):
        with patch('src.harness.build_report', wraps=build_report) as tool:
            receipt = run_harness('orders', plan(), self.result)
        self.assertEqual(receipt['status'], 'completed')
        self.assertEqual(receipt['tool_calls'], 1)
        tool.assert_called_once_with(self.result, 'orders')
        self.assertEqual(receipt['model_calls'], 0)
        self.assertTrue(receipt['human_review_required'])
        self.assertEqual(len(receipt['source_sha256']), 64)
        self.assertEqual(receipt['steps'][-1], 'evidence_verified')

    def test_all_fixture_objects_match_manual_impact_expectations(self):
        expected = {'orders': [('order_summary', 1), ('regional_sales', 2)],
                    'customers': [('customer_directory', 1), ('regional_sales', 1)],
                    'order_summary': [('regional_sales', 1)],
                    'regional_sales': [], 'customer_directory': []}
        for name, hits in expected.items():
            with self.subTest(name=name):
                r = run_harness(name, plan(name), self.result)
                self.assertEqual(r['status'], 'completed' if hits else 'no_consumers_in_fixture')
                self.assertEqual([(h['object'], h['depth']) for h in r['report']['potentially_affected']], hits)

    def test_rejected_plans_never_load_source_or_run_tool(self):
        bad = ['not JSON', '[]', '{}', 'null',
               '{"tool":"trace_downstream","object":"orders","object":"customers"}',
               json.dumps({'tool': 'execute_sql', 'object': 'orders'}),
               plan('customers'), plan(sql='DROP TABLE orders'),
               plan(path='/etc/passwd'), plan(max_tool_calls=20),
               'x'*2049, plan(False)]
        for proposal in bad:
            with self.subTest(proposal=proposal[:80]):
                with patch('src.harness.extract_fixture') as extract, patch('src.harness.build_report') as tool:
                    r = run_harness('orders', proposal)
                self.assertEqual(r['status'], 'rejected')
                self.assertEqual(r['tool_calls'], 0)
                self.assertIsNone(r['report'])
                extract.assert_not_called()
                tool.assert_not_called()

    def test_unknown_requested_object_is_rejected(self):
        self.assertEqual(run_harness('typo_orders', plan('typo_orders'))['status'], 'rejected')

    def test_source_error_returns_no_report_and_zero_tool_calls(self):
        with patch('src.harness.extract_fixture', side_effect=FileNotFoundError):
            r = run_harness('orders', plan())
        self.assertEqual(r['status'], 'source_error')
        self.assertEqual(r['tool_calls'], 0)
        self.assertIsNone(r['report'])

    def test_tool_failure_is_not_retried(self):
        with patch('src.harness.build_report', side_effect=RuntimeError('example')) as tool:
            r = run_harness('orders', plan(), self.result)
        tool.assert_called_once()
        self.assertEqual(r['status'], 'tool_error')
        self.assertEqual(r['tool_calls'], 1)
        self.assertIsNone(r['report'])

    def test_missing_consumer_cannot_be_silently_accepted(self):
        report = build_report(self.result, 'orders')
        report['potentially_affected'].pop()
        with patch('src.harness.build_report', return_value=report):
            r = run_harness('orders', plan(), self.result)
        self.assertEqual(r['status'], 'verification_failed')
        self.assertIsNone(r['report'])

    def test_fabricated_or_disconnected_evidence_is_blocked(self):
        for field, value in [('source_location', 'L999'), ('confidence', 'GUARANTEED'),
                             ('source_file', 'missing.sql'), ('dependency', 'customers')]:
            with self.subTest(field=field):
                report = build_report(self.result, 'orders')
                report['potentially_affected'][0]['evidence_path'][0][field] = value
                with patch('src.harness.build_report', return_value=report):
                    r = run_harness('orders', plan(), self.result)
                self.assertEqual(r['status'], 'verification_failed')
                self.assertIsNone(r['report'])

    def test_wrong_object_depth_metadata_or_extra_fields_are_blocked(self):
        baseline = build_report(self.result, 'orders')
        alternatives = []
        for key, value in [('changed_object', 'customers'), ('human_review_required', False),
                           ('model_calls', True), ('scope', 'All databases'),
                           ('verified_dependencies', 99), ('sql', 'arbitrary text')]:
            r = copy.deepcopy(baseline)
            r[key] = value
            alternatives.append(r)
        wrong_depth = copy.deepcopy(baseline)
        wrong_depth['potentially_affected'][0]['depth'] = True
        alternatives.append(wrong_depth)
        duplicate = copy.deepcopy(baseline)
        duplicate['potentially_affected'][1] = duplicate['potentially_affected'][0]
        alternatives.append(duplicate)
        for report in alternatives:
            with self.subTest(report=report):
                with patch('src.harness.build_report', return_value=report):
                    r = run_harness('orders', plan(), self.result)
                self.assertEqual(r['status'], 'verification_failed')
                self.assertIsNone(r['report'])

    def test_input_plan_is_data_and_not_repaired(self):
        for proposal in ['```json\n'+plan()+'\n```', ' '+plan()+' trailing']:
            with self.assertRaises(ValueError):
                validate_plan('orders', proposal)

    def test_cli_emits_json_and_correct_exit_status(self):
        for proposal, exit_code, status, calls in [
                (plan(), 0, 'completed', 1),
                (json.dumps({'tool': 'execute_sql', 'object': 'orders'}), 1, 'rejected', 0)]:
            with self.subTest(status=status):
                proc = subprocess.run([sys.executable, '-m', 'src.harness', '--object',
                                       'orders', '--plan-json', proposal],
                                      cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(proc.returncode, exit_code)
                receipt = json.loads(proc.stdout)
                self.assertEqual(receipt['status'], status)
                self.assertEqual(receipt['tool_calls'], calls)


if __name__ == '__main__':
    unittest.main()
