import copy
import sqlite3
import unittest
from src.impact import ROOT, extract_fixture, verify_fixture, downstream


class ImpactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = extract_fixture()

    def test_all_expected_dependencies_and_source_evidence(self):
        _, edges = verify_fixture(self.result)
        self.assertEqual(len(edges), 4)

    def test_orders_direct_and_transitive_consumers(self):
        hits = downstream(self.result, 'orders')
        self.assertEqual([(h['object'], h['depth']) for h in hits],
                         [('order_summary', 1), ('regional_sales', 2)])
        self.assertEqual(hits[1]['evidence_path'][1]['dependency'], 'order_summary')

    def test_customers_consumers_and_leaf(self):
        self.assertEqual({h['object'] for h in downstream(self.result, 'customers')},
                         {'customer_directory', 'regional_sales'})
        self.assertEqual(downstream(self.result, 'regional_sales'), [])

    def test_unknown_object_is_not_reported_as_no_impact(self):
        with self.assertRaises(ValueError):
            downstream(self.result, 'typo_orders')

    def test_missing_extra_and_unproven_edges_are_rejected(self):
        r = copy.deepcopy(self.result)
        edge = next(e for e in r['edges'] if e['relation'] == 'reads_from')
        r['edges'].remove(edge)
        with self.assertRaises(ValueError):
            verify_fixture(r)
        r = copy.deepcopy(self.result)
        edge = next(e for e in r['edges'] if e['relation'] == 'reads_from')
        edge['source'], edge['target'] = edge['target'], edge['source']
        with self.assertRaises(ValueError):
            verify_fixture(r)
        edge['source_location'] = None
        with self.assertRaises(ValueError):
            verify_fixture(r)

    def test_cycles_terminate_and_do_not_return_seed(self):
        r = copy.deepcopy(self.result)
        edge = copy.deepcopy(next(e for e in r['edges'] if e['relation'] == 'reads_from'))
        edge['source'], edge['target'] = edge['target'], edge['source']
        r['edges'].append(edge)
        self.assertEqual({h['object'] for h in downstream(r, 'orders')},
                         {'order_summary', 'regional_sales'})

    def test_sql_fixture_executes_in_isolated_database(self):
        with sqlite3.connect(':memory:') as connection:
            connection.executescript((ROOT/'examples/retail.sql').read_text())
            connection.execute("INSERT INTO customers VALUES (1, 'North')")
            connection.execute('INSERT INTO orders VALUES (10, 1, 25)')
            self.assertEqual(connection.execute('SELECT * FROM regional_sales').fetchall(),
                             [('North', 25)])


if __name__ == '__main__':
    unittest.main()
