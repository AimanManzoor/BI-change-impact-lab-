import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from graphify.extract import extract
from streamlit.testing.v1 import AppTest
from src.impact import ROOT
from src.education_check import (SQL_FILES, OBJECTS, DIRECTORY, extract_education,
                                 verify_education, check_education, source_fingerprint)


class EducationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = extract_education()

    def test_cross_file_pairs_and_all_eight_reference_cases(self):
        nodes, edges, cases = verify_education(self.result)
        self.assertEqual(len(edges), 8)
        self.assertEqual(len(cases), 8)
        self.assertEqual({c['object'] for c in cases}, set(OBJECTS))
        self.assertTrue(all(c['passed'] for c in cases))

    def test_four_hop_path_and_unrelated_branch_exclusion(self):
        report = check_education(result=self.result)
        self.assertEqual([(h['object'], h['depth']) for h in report['potentially_affected']],
                         [('attendance_summary', 1), ('attendance_report', 2),
                          ('review_candidates', 3), ('regional_review', 4)])
        chain = report['potentially_affected'][-1]['evidence_path']
        self.assertEqual([h['source_location'] for h in chain], ['L3', 'L3', 'L7', 'L11'])
        self.assertEqual(len({h['source_file'] for h in chain}), 2)
        self.assertNotIn('behavior_summary', [h['object'] for h in report['potentially_affected']])

    def test_shortest_path_wins_and_leaf_has_no_consumers(self):
        report = check_education('enrollment', result=self.result)
        self.assertEqual({h['object']: h['depth'] for h in report['potentially_affected']},
                         {'attendance_report': 1, 'regional_review': 1, 'review_candidates': 2})
        self.assertEqual(check_education('regional_review', result=self.result)['potentially_affected'], [])

    def test_missing_extra_or_unproven_edges_fail_reference_check(self):
        variants = []
        missing = copy.deepcopy(self.result)
        missing['edges'].remove(next(e for e in missing['edges'] if e['relation'] == 'reads_from'))
        variants.append(missing)
        duplicate = copy.deepcopy(self.result)
        duplicate['edges'].append(copy.deepcopy(next(e for e in duplicate['edges'] if e['relation'] == 'reads_from')))
        variants.append(duplicate)
        bad_source = copy.deepcopy(self.result)
        next(e for e in bad_source['edges'] if e['relation'] == 'reads_from')['source_file'] = 'elsewhere.sql'
        variants.append(bad_source)
        for result in variants:
            with self.assertRaises(ValueError):
                verify_education(result)

    def test_partial_extraction_and_unknown_objects_are_not_zero_impact(self):
        for field, value in [('failed_sources', ['missing.sql']), ('extracted_sources', [])]:
            result = copy.deepcopy(self.result)
            result[field] = value
            with self.assertRaises(ValueError):
                verify_education(result)
        with patch('src.education_check.extract_education') as extractor:
            with self.assertRaises(ValueError):
                check_education('unknown')
        extractor.assert_not_called()

    def test_file_order_and_source_bytes_are_preserved(self):
        before = {p: p.read_bytes() for p in SQL_FILES}
        reversed_result = extract(list(reversed(SQL_FILES)), root=ROOT)
        report = check_education(result=reversed_result)
        self.assertEqual(report['reference_cases_passed'], 8)
        self.assertEqual(before, {p: p.read_bytes() for p in SQL_FILES})

    def test_source_and_reference_changes_invalidate_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            files = tuple(temp/p.name for p in SQL_FILES)
            for src, dest in zip(SQL_FILES, files):
                dest.write_bytes(src.read_bytes())
            reference = temp/'expected.json'
            reference.write_bytes((DIRECTORY/'expected.json').read_bytes())
            with patch('src.education_check.SQL_FILES', files), patch('src.education_check.DIRECTORY', temp):
                original = source_fingerprint()
                files[0].write_text(files[0].read_text()+'\n')
                self.assertNotEqual(source_fingerprint(), original)
                after_sql = source_fingerprint()
                reference.write_text(reference.read_text()+'\n')
                self.assertNotEqual(source_fingerprint(), after_sql)

    def test_synthetic_sql_executes_and_cli_emits_verified_json(self):
        with sqlite3.connect(':memory:') as conn:
            for path in SQL_FILES:
                conn.executescript(path.read_text())
            conn.executemany('INSERT INTO enrollment VALUES (?,?)', [(1, 'North'), (2, 'North')])
            conn.executemany('INSERT INTO attendance_events VALUES (?,?)', [(1, 2), (1, 3), (2, 1)])
            conn.execute('INSERT INTO behavior_events VALUES (1,1)')
            self.assertEqual(conn.execute('SELECT * FROM regional_review').fetchall(), [('North', 2)])
            self.assertEqual(conn.execute('SELECT absent_days FROM attendance_summary WHERE student_id=1').fetchone()[0], 5)
        proc = subprocess.run([sys.executable, '-m', 'src.education_check'], cwd=ROOT,
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['reference_cases_passed'], 8)


class EducationAppTests(unittest.TestCase):
    def launch(self):
        return AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()

    def test_education_path_and_stale_result_invalidation(self):
        app = self.launch()
        app.button(key='education_verify').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('8 dependency pairs' in x.value for x in app.success))
        self.assertTrue(any('regional_review (4 hops)' == x.label.replace('Evidence for ', '') for x in app.expander))
        app.radio(key='education_object').set_value('regional_review').run()
        self.assertFalse(app.success)
        app.button(key='education_verify').click().run()
        self.assertTrue(any('No downstream consumer' in x.value for x in app.info))

    def test_education_failure_withholds_report(self):
        with patch('src.education_check.check_education', side_effect=ValueError('reference mismatch')):
            app = self.launch()
            app.button(key='education_verify').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('verification failed' in x.value for x in app.error))
        self.assertFalse(app.success)


if __name__ == '__main__':
    unittest.main()
