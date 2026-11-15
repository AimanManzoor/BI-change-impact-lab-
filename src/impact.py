"""Verified, fixture-scoped SQL dependency exploration. No model or SQL execution."""
from collections import deque
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]


def extract_fixture():
    from graphify.extract import extract
    result = extract([ROOT / 'examples/retail.sql'], root=ROOT)
    if result.get('failed_sources') or not result.get('extracted_sources'):
        raise ValueError('SQL extraction was incomplete; do not report impact.')
    return result


def dependencies(result):
    nodes = {n['id']: n for n in result['nodes']}
    edges = [e for e in result['edges'] if e['relation'] == 'reads_from']
    if not edges:
        raise ValueError('No SQL dependencies extracted.')
    for e in edges:
        if e['source'] not in nodes or e['target'] not in nodes:
            raise ValueError('Dependency endpoint is missing.')
        if not e.get('source_file') or not e.get('source_location'):
            raise ValueError('Dependency source evidence is missing.')
        if e.get('confidence') not in {'EXTRACTED', 'INFERRED', 'AMBIGUOUS'}:
            raise ValueError('Dependency confidence is missing or unsupported.')
    return nodes, edges


def verify_fixture(result):
    nodes, edges = dependencies(result)
    actual = {(nodes[e['source']]['label'], nodes[e['target']]['label']) for e in edges}
    expected = {tuple(pair) for pair in json.loads(
        (ROOT / 'examples/expected_dependencies.json').read_text())}
    if actual != expected:
        raise ValueError(f'Fixture mismatch: missing={sorted(expected-actual)}, unexpected={sorted(actual-expected)}')
    return nodes, edges


def downstream(result, object_name):
    nodes, edges = dependencies(result)
    object_ids = {e[k] for e in edges for k in ('source', 'target')}
    matches = [i for i in object_ids if nodes[i]['label'] == object_name]
    if len(matches) != 1:
        raise ValueError('Object name must identify exactly one dependency object.')
    seed = matches[0]
    queue = deque([(seed, [])])
    visited = {seed}
    hits = []
    while queue:
        current, path = queue.popleft()
        for edge in sorted(edges, key=lambda e: (e['source'], e['target'])):
            if edge['target'] != current or edge['source'] in visited:
                continue
            caller = edge['source']
            visited.add(caller)
            hop = {
                'consumer': nodes[caller]['label'],
                'dependency': nodes[current]['label'],
                'source_file': edge['source_file'],
                'source_location': edge['source_location'],
                'confidence': edge['confidence'],
            }
            next_path = path + [hop]
            hits.append({'object': nodes[caller]['label'], 'depth': len(next_path),
                         'evidence_path': next_path})
            queue.append((caller, next_path))
    return sorted(hits, key=lambda h: (h['depth'], h['object']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', default='orders')
    args = parser.parse_args()
    try:
        result = extract_fixture()
        _, edges = verify_fixture(result)
        report = {'status': 'fixture_verified', 'changed_object': args.object,
                  'verified_dependencies': len(edges),
                  'potentially_affected': downstream(result, args.object),
                  'scope': 'examples/retail.sql only; one shortest evidence path per object',
                  'human_review_required': True, 'model_calls': 0}
    except ValueError as exc:
        parser.exit(1, f'Stopped: {exc}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
