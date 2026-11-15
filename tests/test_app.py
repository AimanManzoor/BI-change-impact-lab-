import json
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.impact import ROOT


class AppTests(unittest.TestCase):
    def launch(self):
        return AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()

    def test_default_orders_and_evidence(self):
        app = self.launch()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['2', '1', '1'])
        self.assertEqual(list(app.dataframe[0].value['view']), ['order_summary', 'regional_sales'])
        app.selectbox(key='evidence_target').select('regional_sales').run()
        self.assertFalse(app.exception)
        self.assertEqual(list(app.dataframe[1].value['source_location']), ['L5', 'L9'])

    def test_customers_changes_results(self):
        app = self.launch()
        app.selectbox(key='changed_object').select('customers').run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['2', '2', '0'])
        self.assertEqual(set(app.dataframe[0].value['view']),
                         {'customer_directory', 'regional_sales'})

    def test_leaf_clears_previous_results(self):
        app = self.launch()
        app.selectbox(key='changed_object').select('regional_sales').run()
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['0', '0', '0'])
        self.assertFalse(app.dataframe)
        self.assertEqual(len(app.selectbox), 1)
        self.assertIn('verified fixture', app.info[0].value)

    def test_invalid_fixture_stops_before_showing_impact(self):
        with patch('src.impact.verify_fixture', side_effect=ValueError('Fixture mismatch')):
            app = self.launch()
        self.assertFalse(app.exception)
        self.assertIn('unavailable', app.error[0].value)
        self.assertFalse(app.metric)
        self.assertFalse(app.dataframe)

    def test_missing_source_stops_before_showing_impact(self):
        with patch('src.impact.extract_fixture', side_effect=FileNotFoundError('Missing SQL')):
            app = self.launch()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertFalse(app.selectbox)

    def test_receipt_tracks_current_object(self):
        app = self.launch()
        receipt = json.loads(app.json[0].value)
        self.assertEqual(receipt['requested_object'], 'orders')
        self.assertEqual(receipt['tool_calls'], 1)
        app.selectbox(key='changed_object').select('regional_sales').run()
        receipt = json.loads(app.json[0].value)
        self.assertEqual(receipt['requested_object'], 'regional_sales')
        self.assertEqual(receipt['status'], 'no_consumers_in_fixture')
        self.assertEqual(receipt['report']['potentially_affected'], [])

    def test_harness_failure_does_not_display_unverified_results(self):
        with patch('src.harness.run_harness', return_value={'status': 'verification_failed'}):
            app = self.launch()
        self.assertFalse(app.exception)
        self.assertIn('verification_failed', app.error[0].value)
        self.assertFalse(app.metric)
        self.assertFalse(app.dataframe)


if __name__ == '__main__':
    unittest.main()
