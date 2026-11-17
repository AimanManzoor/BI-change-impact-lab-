import copy
import json
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
from src.graphrag import answer_question, retrieve_context
from src.impact import ROOT


class CorpusGraphRAGTests(unittest.TestCase):
    def test_education_four_hop_context_is_scoped_and_complete(self):
        context, receipt = retrieve_context('attendance_events', 'indirect', corpus='education')
        self.assertEqual(context['corpus'], 'education')
        self.assertEqual(context['fingerprint_kind'], 'sources_and_reference')
        self.assertEqual([c['depth'] for c in context['claims_to_cover']], [2, 3, 4])
        self.assertEqual(context['claims_to_cover'][-1]['evidence_ids'],
                         ['education:E1','education:E2','education:E3','education:E4'])
        self.assertTrue(all(e['source_file'].startswith('examples/education/') for e in context['evidence']))
        self.assertNotIn('examples/retail.sql', json.dumps(context))
        self.assertEqual(receipt['tool_calls'], 1)

    def test_valid_mocked_model_generation_in_both_corpora(self):
        for corpus, obj in [('retail', 'orders'), ('education', 'attendance_events')]:
            seen = []
            def generate(context):
                seen.append(context['corpus'])
                return json.dumps({'claims': context['claims_to_cover']})
            answer = answer_question(obj, corpus=corpus, generator=generate)
            self.assertEqual(answer['status'], 'completed')
            self.assertEqual(answer['model_calls'], 1)
            self.assertEqual(seen, [corpus])

    def test_other_corpus_object_cannot_reach_generation(self):
        generator = Mock()
        for corpus, obj in [('retail', 'attendance_events'), ('education', 'orders'), ('unknown', 'orders')]:
            with self.subTest(corpus=corpus):
                answer = answer_question(obj, corpus=corpus, generator=generator)
                self.assertEqual(answer['status'], 'retrieval_error')
                self.assertEqual(answer['model_calls'], 0)
                self.assertIsNone(answer['answer'])
        generator.assert_not_called()

    def test_wrong_corpus_citations_and_incomplete_long_path_are_rejected(self):
        def wrong_prefix(context):
            claims = copy.deepcopy(context['claims_to_cover'])
            for claim in claims:
                claim['evidence_ids'] = [ref.removeprefix('education:') for ref in claim['evidence_ids']]
            return json.dumps({'claims': claims})
        def missing_hop(context):
            claims = copy.deepcopy(context['claims_to_cover'])
            claims[-1]['evidence_ids'].pop(0)
            return json.dumps({'claims': claims})
        for generate in [wrong_prefix, missing_hop]:
            answer = answer_question('attendance_events', corpus='education', generator=generate)
            self.assertEqual(answer['status'], 'verification_failed')
            self.assertIsNone(answer['answer'])

    def test_leaf_and_invalid_education_evidence_skip_model(self):
        generator = Mock()
        answer = answer_question('regional_review', corpus='education', generator=generator)
        self.assertEqual(answer['status'], 'no_context')
        with patch('src.graphrag.check_education', side_effect=ValueError('mismatch')):
            answer = answer_question('attendance_events', corpus='education', generator=generator)
        self.assertEqual(answer['retrieval_tool_calls'], 1)
        self.assertEqual(answer['status'], 'retrieval_error')
        generator.assert_not_called()

    def test_education_cli_emits_corpus_and_checked_citations(self):
        proc = subprocess.run([sys.executable, '-m', 'src.graphrag', '--corpus', 'education',
                               '--object', 'attendance_events', '--kind', 'indirect'],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        answer = json.loads(proc.stdout)
        self.assertEqual(answer['context']['corpus'], 'education')
        self.assertIn('[education:E4]', answer['answer'])
        self.assertEqual(answer['model_calls'], 0)


class CorpusAppTests(unittest.TestCase):
    def test_switching_corpora_and_objects_hides_previous_answer(self):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()
        app.button(key='gr_answer').click().run()
        self.assertTrue(any('`order_summary` could' in x.value for x in app.markdown))
        app.radio(key='gr_corpus').set_value('education').run()
        self.assertFalse(any('`order_summary` could' in x.value for x in app.markdown))
        app.button(key='gr_answer').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('[education:E4]' in x.value for x in app.markdown))
        app.selectbox(key='gr_education_object').select('regional_review').run()
        self.assertFalse(any('[education:E4]' in x.value for x in app.markdown))
        app.button(key='gr_answer').click().run()
        self.assertTrue(any('No matching downstream consumers' in x.value for x in app.markdown))
        app.radio(key='gr_corpus').set_value('retail').run()
        self.assertFalse(any('No matching downstream consumers' in x.value for x in app.markdown))

    def test_education_retrieval_failure_displays_no_answer(self):
        with patch('src.graphrag.check_education', side_effect=ValueError('bad reference')):
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()
            app.radio(key='gr_corpus').set_value('education').run()
            app.button(key='gr_answer').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('could not be verified' in x.value for x in app.error))
        self.assertFalse(any('[education:E' in x.value for x in app.markdown))


if __name__ == '__main__':
    unittest.main()
