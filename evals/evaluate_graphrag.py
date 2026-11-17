"""Offline reference checks for template retrieval; not an LLM quality benchmark."""
from contextlib import redirect_stdout
import json
import sys
from src.graphrag import answer_question
from src.impact import ROOT


def evaluate():
    cases = json.loads((ROOT/'evals/graphrag_cases.json').read_text())
    outcomes = []
    for case in cases:
        actual = answer_question(case['object'], case['kind'], corpus=case['corpus'])
        consumers = [c['object'] for c in (actual.get('context') or {}).get('claims_to_cover', [])]
        depths = [c['depth'] for c in (actual.get('context') or {}).get('claims_to_cover', [])]
        matching_corpus = actual.get('context') is None or actual['context']['corpus'] == case['corpus']
        passed = (actual['status'] == case['status'] and consumers == case['consumers']
                  and depths == case['depths'] and matching_corpus and actual['model_calls'] == 0)
        outcomes.append({'corpus': case['corpus'], 'object': case['object'], 'kind': case['kind'], 'passed': passed})
    return {'mode': 'template_reference_checks', 'cases': len(cases),
            'passed': sum(o['passed'] for o in outcomes), 'model_calls': 0, 'outcomes': outcomes}


if __name__ == '__main__':
    with redirect_stdout(sys.stderr):
        report = evaluate()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] == report['cases'] else 1)
