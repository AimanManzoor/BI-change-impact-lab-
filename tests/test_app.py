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


if __name__ == '__main__':
    unittest.main()
