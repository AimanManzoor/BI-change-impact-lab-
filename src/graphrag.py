"""Fixture-scoped graph retrieval, optional structured generation, and claim checks."""
import argparse
from contextlib import redirect_stdout
import copy
import getpass
import json
import os
import sys
from src.harness import run_harness, _unique_object
from src.impact import ROOT

QUESTION_KINDS = ('all', 'direct', 'indirect')


class RetrievalFailure(ValueError):
    def __init__(self, tool_calls):
        super().__init__('Graph retrieval did not produce usable context.')
        self.tool_calls = tool_calls


def parse_claims(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > 8192:
        raise ValueError('Answer must be bounded JSON text.')
    return json.loads(text, object_pairs_hook=_unique_object)


def retrieve_context(object_name, kind='all', result=None):
    if kind not in QUESTION_KINDS:
        raise ValueError('Unsupported question kind.')
    receipt = run_harness(object_name, json.dumps(
        {'tool': 'trace_downstream', 'object': object_name}), result)
    if receipt['status'] not in {'completed', 'no_consumers_in_fixture'}:
        raise RetrievalFailure(receipt['tool_calls'])
    try:
        return _package_context(object_name, kind, receipt)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise RetrievalFailure(receipt['tool_calls']) from exc


def _package_context(object_name, kind, receipt):
    hits = receipt['report']['potentially_affected']
    selected = [h for h in hits if kind == 'all' or
                (kind == 'direct' and h['depth'] == 1) or
                (kind == 'indirect' and h['depth'] > 1)]
    evidence, claims, identities = [], [], {}
    lines = (ROOT/'examples/retail.sql').read_text().splitlines()
    for hit in selected:
        refs = []
        for hop in hit['evidence_path']:
            identity = tuple(hop[k] for k in
                             ('consumer', 'dependency', 'source_file', 'source_location', 'confidence'))
            if identity not in identities:
                ref = f'E{len(evidence)+1}'
                identities[identity] = ref
                if hop['source_file'] != 'examples/retail.sql':
                    raise ValueError('Evidence source is outside the supported fixture.')
                line = int(hop['source_location'].removeprefix('L'))
                if not 1 <= line <= len(lines):
                    raise ValueError('Source location is outside the SQL fixture.')
                evidence.append({'id': ref, **hop, 'sql_excerpt': lines[line-1]})
            refs.append(identities[identity])
        claims.append({'object': hit['object'], 'depth': hit['depth'], 'evidence_ids': refs})
    package = {'object': object_name, 'question_kind': kind,
               'question': f'Which {kind} downstream views could be affected if {object_name} changes?',
               'scope': receipt['report']['scope'], 'source_sha256': receipt['source_sha256'],
               'claims_to_cover': claims, 'evidence': evidence}
    if len(json.dumps(package).encode('utf-8')) > 16000:
        raise ValueError('Graph context exceeds the supported byte budget.')
    return package, receipt


def verify_claims(candidate, context):
    if not isinstance(candidate, dict) or set(candidate) != {'claims'}:
        raise ValueError('Only structured claims are allowed; free-form text is not accepted.')
    claims = candidate['claims']
    expected = {c['object']: c for c in context['claims_to_cover']}
    if not isinstance(claims, list) or len(claims) != len(expected):
        raise ValueError('Answer must cover exactly the retrieved consumers.')
    seen = set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'object', 'depth', 'evidence_ids'}:
            raise ValueError('Unexpected claim fields.')
        name = claim['object']
        if not isinstance(name, str) or name not in expected or name in seen:
            raise ValueError('Unknown or duplicate consumer.')
        seen.add(name)
        target = expected[name]
        if (type(claim['depth']) is not int or claim['depth'] != target['depth'] or
                claim['evidence_ids'] != target['evidence_ids']):
            raise ValueError('Claim depth or complete ordered citation path is unsupported.')
    return copy.deepcopy(context['claims_to_cover'])


def render_answer(claims, context):
    if not claims:
        return ('No matching downstream consumers were found for this question in the bundled fixture. '
                'This is not proof of no impact outside this example.')
    lines = []
    for claim in claims:
        relation = 'directly' if claim['depth'] == 1 else 'indirectly'
        citations = ' '.join(f'[{ref}]' for ref in claim['evidence_ids'])
        lines.append(f"- `{claim['object']}` could be affected {relation} "
                     f"({claim['depth']} hop(s) from `{context['object']}`). {citations}")
    lines.append('\nThese paths indicate potential dependency impact, not a confirmed break. Human review is required.')
    return '\n'.join(lines)


def answer_question(object_name, kind='all', *, generator=None, result=None):
    answer = {'status': 'retrieval_error', 'mode': 'model' if generator else 'template',
              'model_calls': 0, 'retrieval_tool_calls': 0, 'answer': None,
              'context': None, 'human_review_required': True}
    try:
        context, receipt = retrieve_context(object_name, kind, result)
    except (ValueError, OSError, ImportError, KeyError, TypeError) as exc:
        answer['error_type'] = type(exc).__name__
        answer['retrieval_tool_calls'] = getattr(exc, 'tool_calls', 0)
        return answer
    answer.update(context=context, retrieval_tool_calls=receipt['tool_calls'])
    if not context['claims_to_cover']:
        answer.update(status='no_context', answer=render_answer([], context))
        return answer  # No evidence to explain: no generation attempt.
    if generator is None:
        candidate = {'claims': copy.deepcopy(context['claims_to_cover'])}
    else:
        answer['model_calls'] = 1
        try:
            candidate = parse_claims(generator(copy.deepcopy(context)))
        except Exception as exc:
            answer.update(status='generation_error', error_type=type(exc).__name__)
            return answer
    try:
        claims = verify_claims(candidate, context)
    except (ValueError, KeyError, TypeError) as exc:
        answer.update(status='verification_failed', error_type=type(exc).__name__)
        return answer
    answer.update(status='completed', answer=render_answer(claims, context))
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', default='orders')
    parser.add_argument('--kind', choices=QUESTION_KINDS, default='all')
    parser.add_argument('--live', action='store_true', help='Opt in to one potentially billable model request.')
    parser.add_argument('--model', default=os.getenv('ANTHROPIC_MODEL'))
    args = parser.parse_args()
    generator = None
    if args.live:
        from src.graph_generator import AnthropicGenerator
        key = os.getenv('ANTHROPIC_API_KEY') or getpass.getpass('Anthropic API key (hidden): ')
        try:
            generator = AnthropicGenerator(model=args.model, api_key=key)
        except ValueError as exc:
            parser.error(str(exc))
    with redirect_stdout(sys.stderr):
        answer = answer_question(args.object, args.kind, generator=generator)
    if generator is not None:
        answer['provider'] = generator.metadata
    print(json.dumps(answer, indent=2))
    return 0 if answer['status'] in {'completed', 'no_context'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
