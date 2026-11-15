"""Control structured impact proposals. This milestone makes no model calls."""
import argparse
from contextlib import redirect_stdout
import hashlib
import json
import time
import sys
import uuid
from src.impact import ROOT, extract_fixture, build_report, dependencies

SUPPORTED_OBJECTS = frozenset({'orders', 'customers', 'order_summary',
                               'regional_sales', 'customer_directory'})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are not allowed.')
        result[key] = value
    return result


def validate_plan(requested_object, proposal_json):
    if not isinstance(requested_object, str) or requested_object not in SUPPORTED_OBJECTS:
        raise ValueError('Select one supported object from the bundled fixture.')
    if not isinstance(proposal_json, str) or len(proposal_json.encode('utf-8')) > 2048:
        raise ValueError('Plan must be a JSON string of at most 2048 bytes.')
    try:
        plan = json.loads(proposal_json, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError) as exc:
        raise ValueError('Plan must be valid JSON without duplicate keys.') from exc
    if not isinstance(plan, dict) or set(plan) != {'tool', 'object'}:
        raise ValueError('Only tool and object fields are permitted.')
    if plan['tool'] != 'trace_downstream' or plan['object'] != requested_object:
        raise ValueError('Only trace_downstream for the requested object is permitted.')
    return plan


def verify_report(report, result, requested_object):
    """Check shape, fixed-fixture impact expectations, and every returned hop."""
    allowed_fields = {'status', 'changed_object', 'verified_dependencies',
                      'potentially_affected', 'scope', 'human_review_required', 'model_calls'}
    if (not isinstance(report, dict) or set(report) != allowed_fields or
            report.get('changed_object') != requested_object):
        raise ValueError('Report object does not match the requested object.')
    if (report.get('status') != 'fixture_verified' or
            report.get('human_review_required') is not True or
            type(report.get('model_calls')) is not int or report['model_calls'] != 0 or
            type(report.get('verified_dependencies')) is not int or
            report['verified_dependencies'] != 4 or
            report.get('scope') != 'examples/retail.sql only; one shortest evidence path per object'):
        raise ValueError('Report scope or validation metadata is invalid.')
    expected = json.loads((ROOT/'examples/expected_impacts.json').read_text())[requested_object]
    hits = report.get('potentially_affected')
    if not isinstance(hits, list) or len(hits) != len(expected):
        raise ValueError('Report must contain exactly the expected fixture consumers.')
    nodes, edges = dependencies(result)
    evidence_keys = ('consumer', 'dependency', 'source_file', 'source_location', 'confidence')
    valid_edges = {
        (nodes[e['source']]['label'], nodes[e['target']]['label'], e['source_file'],
         e['source_location'], e['confidence']) for e in edges
    }
    seen = set()
    for hit in hits:
        if not isinstance(hit, dict) or set(hit) != {'object', 'depth', 'evidence_path'}:
            raise ValueError('Unexpected impact result fields.')
        name, depth, path = hit['object'], hit['depth'], hit['evidence_path']
        if (not isinstance(name, str) or name not in expected or name in seen or
                type(depth) is not int or depth != expected[name] or
                not isinstance(path, list) or len(path) != depth):
            raise ValueError('Incorrect consumers or path length.')
        seen.add(name)
        previous = requested_object
        for hop in path:
            if (not isinstance(hop, dict) or set(hop) != set(evidence_keys) or
                    any(not isinstance(hop[k], str) for k in evidence_keys) or
                    hop['dependency'] != previous or
                    tuple(hop[k] for k in evidence_keys) not in valid_edges):
                raise ValueError('Evidence hop is disconnected or unsupported by the extraction.')
            previous = hop['consumer']
        if previous != name:
            raise ValueError('Evidence path ends at another object.')


def run_harness(requested_object, proposal_json, result=None):
    start = time.perf_counter()
    receipt = {'run_id': str(uuid.uuid4()), 'requested_object': requested_object,
               'status': 'rejected', 'tool_calls': 0, 'model_calls': 0,
               'max_tool_calls': 1, 'human_review_required': True, 'report': None,
               'steps': []}
    def finish():
        receipt['duration_ms'] = round((time.perf_counter()-start)*1000, 3)
        return receipt
    try:
        validate_plan(requested_object, proposal_json)
    except ValueError as exc:
        receipt['reason'] = str(exc)
        receipt['steps'].append('plan_rejected')
        return finish()
    receipt['steps'].append('plan_allowed')
    try:
        if result is None:
            result = extract_fixture()
        receipt['source_sha256'] = hashlib.sha256((ROOT/'examples/retail.sql').read_bytes()).hexdigest()
        receipt['steps'].append('source_loaded')
    except (ValueError, OSError, ImportError) as exc:
        receipt['status'] = 'source_error'
        receipt['error_type'] = type(exc).__name__
        return finish()
    # Exactly one impact-tool attempt; extraction is a separate preflight stage.
    receipt['tool_calls'] = 1
    try:
        report = build_report(result, requested_object)
        receipt['steps'].append('impact_tool_returned')
    except Exception as exc:
        receipt['status'] = 'tool_error'
        receipt['error_type'] = type(exc).__name__
        return finish()
    try:
        verify_report(report, result, requested_object)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        receipt['status'] = 'verification_failed'
        receipt['error_type'] = type(exc).__name__
        return finish()
    receipt['steps'].append('evidence_verified')
    receipt['status'] = 'completed' if report['potentially_affected'] else 'no_consumers_in_fixture'
    receipt['report'] = report
    return finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object', default='orders')
    parser.add_argument('--plan-json', help='Optional structured proposal; no code is executed.')
    args = parser.parse_args()
    plan = args.plan_json if args.plan_json is not None else json.dumps(
        {'tool': 'trace_downstream', 'object': args.object})
    # Keep Graphify cache/progress messages out of the machine-readable receipt.
    with redirect_stdout(sys.stderr):
        receipt = run_harness(args.object, plan)
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['status'] in {'completed', 'no_consumers_in_fixture'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
