"""Independent reference checks for a fixed synthetic multi-file SQL corpus."""
import argparse
from contextlib import redirect_stdout
import hashlib
import json
import re
import sys
from src.impact import ROOT, dependencies, downstream

DIRECTORY = ROOT/'examples/education'
SQL_FILES = tuple(DIRECTORY/name for name in
                  ('00_tables.sql', '10_summaries.sql', '20_reports.sql'))
OBJECTS = ('attendance_events', 'attendance_summary', 'attendance_report',
           'behavior_events', 'behavior_summary', 'enrollment',
           'review_candidates', 'regional_review')


def source_fingerprint():
    digest = hashlib.sha256()
    for path in (*SQL_FILES, DIRECTORY/'expected.json'):
        digest.update(path.name.encode('utf-8')+b'\0'+path.read_bytes()+b'\0')
    return digest.hexdigest()


def extract_education():
    from graphify.extract import extract
    if any(not path.is_file() for path in SQL_FILES):
        raise FileNotFoundError('An education SQL source is missing.')
    return extract(list(SQL_FILES), root=ROOT)


def verify_education(result):
    expected = json.loads((DIRECTORY/'expected.json').read_text())
    successful = {str(path) for path in result.get('extracted_sources', [])}
    if result.get('failed_sources') or successful != {str(p) for p in SQL_FILES}:
        raise ValueError('All three SQL sources must extract successfully.')
    nodes, edges = dependencies(result)
    actual = {(nodes[e['source']]['label'], nodes[e['target']]['label']) for e in edges}
    wanted = {tuple(pair) for pair in expected['dependencies']}
    if actual != wanted or len(edges) != len(wanted):
        raise ValueError('Cross-file dependency pairs differ from the independent reference.')
    allowed_sources = {str(p.relative_to(ROOT)): p.read_text().splitlines() for p in SQL_FILES}
    for edge in edges:
        location = edge['source_location']
        if (edge['source_file'] not in allowed_sources or
                not isinstance(location, str) or not re.fullmatch(r'L[1-9][0-9]*', location) or
                int(location[1:]) > len(allowed_sources[edge['source_file']])):
            raise ValueError('Dependency has an unsupported source location.')
    object_ids = {e[k] for e in edges for k in ('source', 'target')}
    if {nodes[i]['label'] for i in object_ids} != set(OBJECTS):
        raise ValueError('Unexpected SQL object set.')
    cases = []
    for name, expected_depths in expected['impacts'].items():
        hits = downstream(result, name)
        actual_depths = {hit['object']: hit['depth'] for hit in hits}
        if len(hits) != len(actual_depths) or actual_depths != expected_depths:
            raise ValueError(f'Downstream reference case failed for {name}.')
        cases.append({'object': name, 'passed': True})
    if {case['object'] for case in cases} != set(OBJECTS):
        raise ValueError('Reference cases must cover every supported object.')
    return nodes, edges, cases


def check_education(object_name='attendance_events', *, result=None):
    if object_name not in OBJECTS:
        raise ValueError('Select an object from the education example.')
    if result is None:
        result = extract_education()
    nodes, edges, cases = verify_education(result)
    relationships = [{
        'consumer': nodes[e['source']]['label'], 'dependency': nodes[e['target']]['label'],
        'source_file': e['source_file'], 'source_location': e['source_location'],
        'confidence': e['confidence'],
    } for e in edges]
    return {'status': 'reference_verified', 'corpus': 'synthetic_education',
            'sql_files': [str(p.relative_to(ROOT)) for p in SQL_FILES],
            'source_and_reference_sha256': source_fingerprint(),
            'dependency_pairs': len(edges), 'reference_cases': len(cases),
            'reference_cases_passed': sum(case['passed'] for case in cases),
            'changed_object': object_name,
            'potentially_affected': downstream(result, object_name),
            'relationships': relationships, 'model_calls': 0,
            'scope': 'Three bundled synthetic SQL files; one shortest path per consumer.',
            'human_review_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', choices=OBJECTS, default='attendance_events')
    args = parser.parse_args()
    try:
        with redirect_stdout(sys.stderr):
            report = check_education(args.object)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Education reference check stopped: {type(exc).__name__}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
