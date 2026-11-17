import copy
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from src.graphrag import answer_question, retrieve_context, parse_claims
from src.graph_generator import AnthropicGenerator, NoRedirect, API_VERSION
from src.impact import ROOT, extract_fixture
from evals.evaluate_graphrag import evaluate


class GraphRAGTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = extract_fixture()

    def test_indirect_context_retains_every_hop_and_source_excerpt(self):
        context, receipt = retrieve_context('orders', 'indirect', self.result)
        self.assertEqual([c['object'] for c in context['claims_to_cover']], ['regional_sales'])
        self.assertEqual(context['claims_to_cover'][0]['evidence_ids'], ['E1', 'E2'])
        self.assertEqual([e['source_location'] for e in context['evidence']], ['L5', 'L9'])
        self.assertIn('FROM orders', context['evidence'][0]['sql_excerpt'])
        self.assertNotIn('customer_directory', json.dumps(context))
        self.assertEqual(receipt['tool_calls'], 1)

    def test_direct_context_omits_unneeded_hops(self):
        context, _ = retrieve_context('orders', 'direct', self.result)
        self.assertEqual([c['object'] for c in context['claims_to_cover']], ['order_summary'])
        self.assertEqual(len(context['evidence']), 1)

    def test_template_is_explicit_and_cited(self):
        answer = answer_question('orders', result=self.result)
        self.assertEqual(answer['mode'], 'template')
        self.assertEqual(answer['model_calls'], 0)
        self.assertIn('[E1]', answer['answer'])
        self.assertIn('[E2]', answer['answer'])

    def test_no_context_never_calls_generator(self):
        generator = Mock()
        for obj, kind in [('regional_sales', 'all'), ('customers', 'indirect')]:
            answer = answer_question(obj, kind, generator=generator, result=self.result)
            self.assertEqual(answer['status'], 'no_context')
            self.assertEqual(answer['model_calls'], 0)
        generator.assert_not_called()

    def test_bad_scope_never_calls_generator(self):
        generator = Mock()
        for obj, kind in [('orders', 'root_cause'), ('missing', 'all')]:
            answer = answer_question(obj, kind, generator=generator, result=self.result)
            self.assertEqual(answer['status'], 'retrieval_error')
            self.assertIsNone(answer['answer'])
        generator.assert_not_called()

    def test_failed_harness_attempt_is_counted_without_model_call(self):
        with patch('src.graphrag.run_harness', return_value={
                'status': 'verification_failed', 'tool_calls': 1}):
            answer = answer_question('orders', generator=Mock(), result=self.result)
        self.assertEqual(answer['status'], 'retrieval_error')
        self.assertEqual(answer['retrieval_tool_calls'], 1)
        self.assertEqual(answer['model_calls'], 0)

    def test_valid_mocked_generation_and_private_context_copy(self):
        def generate(context):
            response = json.dumps({'claims': context['claims_to_cover']})
            context['evidence'].clear()
            return response
        answer = answer_question('orders', generator=generate, result=self.result)
        self.assertEqual(answer['status'], 'completed')
        self.assertEqual(answer['model_calls'], 1)
        self.assertTrue(answer['context']['evidence'])

    def test_unsupported_claims_citations_depths_and_omissions_are_blocked(self):
        context, _ = retrieve_context('orders', result=self.result)
        good = {'claims': context['claims_to_cover']}
        bad = [{'claims': []}, {'claims': good['claims'], 'answer': 'Everything is safe'}]
        for field, value in [('object', 'customer_directory'), ('depth', True),
                             ('depth', 20), ('evidence_ids', ['E999']),
                             ('evidence_ids', ['E2', 'E1'])]:
            candidate = copy.deepcopy(good)
            candidate['claims'][0][field] = value
            bad.append(candidate)
        candidate = copy.deepcopy(good)
        candidate['claims'][1]['evidence_ids'] = ['E2']
        bad.append(candidate)
        candidate = copy.deepcopy(good)
        candidate['claims'][1] = candidate['claims'][0]
        bad.append(candidate)
        for candidate in bad:
            with self.subTest(candidate=candidate):
                answer = answer_question('orders', generator=Mock(return_value=json.dumps(candidate)), result=self.result)
                self.assertEqual(answer['status'], 'verification_failed')
                self.assertIsNone(answer['answer'])

    def test_bad_json_and_provider_errors_withhold_answer_without_retry(self):
        for text in ['```json\n{}\n```', '{"claims":[],"claims":[]}', 'x'*8193]:
            generator = Mock(return_value=text)
            answer = answer_question('orders', generator=generator, result=self.result)
            self.assertEqual(answer['status'], 'generation_error')
            self.assertIsNone(answer['answer'])
            generator.assert_called_once()
        generator = Mock(side_effect=TimeoutError('secret request body'))
        answer = answer_question('orders', generator=generator, result=self.result)
        self.assertNotIn('secret', json.dumps(answer))
        generator.assert_called_once()

    def test_offline_reference_cases(self):
        report = evaluate()
        self.assertEqual((report['cases'], report['passed'], report['model_calls']), (20, 20, 0))

    def test_cli_default_is_json_template_without_credentials(self):
        proc = subprocess.run([sys.executable, '-m', 'src.graphrag', '--object', 'orders'],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['model_calls'], 0)


class ProviderTests(unittest.TestCase):
    def test_mocked_request_has_bounded_evidence_and_fixed_settings(self):
        body = {'stop_reason': 'end_turn', 'model': 'mock-model',
                'content': [{'type': 'text', 'text': '{"claims":[]}'}],
                'usage': {'input_tokens': 20, 'output_tokens': 5}}
        transport = Mock(return_value=io.BytesIO(json.dumps(body).encode()))
        generator = AnthropicGenerator(model='mock-model', api_key='fake-test-key', transport=transport)
        self.assertEqual(json.loads(generator({'evidence': []})), {'claims': []})
        req = transport.call_args.args[0]
        payload = json.loads(req.data)
        self.assertEqual(payload['max_tokens'], 512)
        self.assertFalse(payload['stream'])
        self.assertEqual(req.get_header('Anthropic-version'), API_VERSION)
        self.assertEqual(transport.call_args.kwargs['timeout'], 30)
        self.assertEqual(generator.metadata['usage']['output_tokens'], 5)
        self.assertNotIn('fake-test-key', json.dumps(generator.metadata))
        with self.assertRaises(ValueError):
            generator({})
        transport.assert_called_once()

    def test_provider_failure_and_truncation_do_not_retry(self):
        for body in [{'stop_reason': 'max_tokens', 'content': []},
                     {'stop_reason': 'end_turn', 'content': [{'type': 'tool_use'}]}]:
            transport = Mock(return_value=io.BytesIO(json.dumps(body).encode()))
            generator = AnthropicGenerator(model='mock', api_key='fake', transport=transport)
            with self.assertRaises(ValueError):
                generator({})
            transport.assert_called_once()
        transport = Mock(side_effect=HTTPError('fixed-url', 429, 'rate limit', {}, None))
        generator = AnthropicGenerator(model='mock', api_key='fake', transport=transport)
        with self.assertRaises(HTTPError):
            generator({})
        transport.assert_called_once()

    def test_oversized_body_duplicate_envelope_and_configuration(self):
        for raw in [b'x'*65537, b'{"stop_reason":"end_turn","stop_reason":"max_tokens"}']:
            generator = AnthropicGenerator(model='mock', api_key='fake',
                                           transport=Mock(return_value=io.BytesIO(raw)))
            with self.assertRaises(ValueError):
                generator({})
        for model, key in [(None, 'fake'), ('mock', ''), (' '*3, 'fake')]:
            with self.assertRaises(ValueError):
                AnthropicGenerator(model=model, api_key=key)

    def test_redirects_are_refused(self):
        handler = NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, 'redirect', {}, 'https://other.test'))


if __name__ == '__main__':
    unittest.main()
