"""Versioned offline planner evaluation; challenge measurement is not a CI quality gate."""
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import sys

from src.harness import _unique_object
from src.review_agent import run_review

REFERENCE = Path(__file__).with_name("planner_cases.json")
SUITES = {"regression", "challenge"}
STATUSES = {"completed", "no_consumers", "clarification_required", "rejected"}


def load_reference(path=REFERENCE):
    raw = Path(path).read_bytes()
    reference = json.loads(raw, object_pairs_hook=_unique_object)
    if (not isinstance(reference, dict) or reference.get("schema_version") != 1
            or reference.get("dataset_id") != "planner_reference_v1"
            or not isinstance(reference.get("cases"), list) or not reference["cases"]):
        raise ValueError("Expected a nonempty planner_reference_v1 dataset")
    ids = set()
    for case in reference["cases"]:
        if (not isinstance(case, dict) or set(case) != {"id", "suite", "category", "question", "expected"}
                or not isinstance(case["id"], str) or not case["id"] or case["id"] in ids
                or not isinstance(case["suite"], str) or case["suite"] not in SUITES
                or not isinstance(case["category"], str) or not case["category"]
                or not isinstance(case["question"], str)):
            raise ValueError("Invalid or duplicate reference case")
        ids.add(case["id"])
        expected = case["expected"]
        if (not isinstance(expected, dict) or set(expected) != {"status", "plan", "consumers", "tool_calls"}
                or not isinstance(expected["status"], str) or expected["status"] not in STATUSES
                or type(expected["tool_calls"]) is not int or expected["tool_calls"] not in (0, 1)
                or not isinstance(expected["consumers"], dict)
                or any(not isinstance(k, str) or type(v) is not int or v < 1
                       for k, v in expected["consumers"].items())):
            raise ValueError("Invalid expected result")
        if expected["status"] in {"completed", "no_consumers"}:
            plan = expected["plan"]
            if (not isinstance(plan, dict) or set(plan) != {"tool", "object", "scope"}
                    or plan["tool"] != "trace_recovered_impacts"
                    or not isinstance(plan["object"], str) or not plan["object"]
                    or plan["scope"] not in ("all", "direct", "indirect")
                    or expected["tool_calls"] != 1
                    or bool(expected["consumers"]) != (expected["status"] == "completed")):
                raise ValueError("Inconsistent accepted reference")
        elif expected["plan"] is not None or expected["tool_calls"] != 0 or expected["consumers"]:
            raise ValueError("Stopped requests must have no plan or tool results")
    return reference, hashlib.sha256(raw).hexdigest()


def evaluate(suite="regression", reference_path=REFERENCE, *, runner=None):
    if suite not in SUITES:
        raise ValueError("Select regression or challenge")
    reference, fingerprint = load_reference(reference_path)
    cases = [case for case in reference["cases"] if case["suite"] == suite]
    if not cases:
        raise ValueError("Selected suite contains no cases")
    runner = runner or run_review
    outcomes, confusion, categories = [], Counter(), {}
    model_attempts = 0
    for case in cases:
        infrastructure_error = False
        try:
            receipt = runner(case["question"])
            if not isinstance(receipt.get("status"), str):
                raise ValueError("Runner status must be text")
            if type(receipt.get("model_calls")) is int and receipt["model_calls"] >= 0:
                model_attempts += receipt["model_calls"]
            report = receipt.get("report")
            hits = (report or {}).get("potentially_affected", [])
            consumers = {hit["object"]: hit["depth"] for hit in hits}
            actual = {"status": receipt["status"], "plan": receipt.get("plan"),
                      "consumers": consumers, "tool_calls": receipt["tool_calls"]}
            infrastructure_error = receipt["status"] in {"evidence_error", "planner_error"}
            checks = {key: actual[key] == value for key, value in case["expected"].items()}
            checks.update(zero_model_calls=type(receipt.get("model_calls")) is int and receipt["model_calls"] == 0,
                          integer_tool_count=type(receipt.get("tool_calls")) is int,
                          rule_mode=receipt.get("planner_mode") == "rules",
                          human_review=receipt.get("human_review_required") is True,
                          no_duplicate_consumers=len(hits) == len(consumers),
                          integer_depths=all(type(hit["depth"]) is int and hit["depth"] > 0 for hit in hits),
                          report_presence=(report is not None) == (case["expected"]["tool_calls"] == 1))
        except Exception as error:
            actual = {"status": "execution_error", "error_type": type(error).__name__}
            checks, infrastructure_error = {"execution": False}, True
        passed = all(checks.values()) and not infrastructure_error
        confusion[(case["expected"]["status"], actual["status"])] += 1
        category = categories.setdefault(case["category"], {"cases": 0, "passed": 0})
        category["cases"] += 1
        category["passed"] += int(passed)
        outcomes.append({"id": case["id"], "category": case["category"], "question": case["question"],
                         "passed": passed, "expected": case["expected"], "actual": actual,
                         "failed_checks": [key for key, value in checks.items() if not value],
                         "infrastructure_error": infrastructure_error})
    passed = sum(outcome["passed"] for outcome in outcomes)
    return {"schema_version": 1, "dataset_id": reference["dataset_id"], "suite": suite,
            "reference_sha256": fingerprint, "planner_mode": "rules", "model_calls": model_attempts,
            "cases": len(cases), "passed": passed, "failed": len(cases) - passed,
            "infrastructure_errors": sum(o["infrastructure_error"] for o in outcomes),
            "case_agreement": passed / len(cases), "categories": categories,
            "status_confusion": [{"expected": a, "actual": b, "cases": count}
                                 for (a, b), count in sorted(confusion.items())], "outcomes": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=sorted(SUITES), default="regression")
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--measure", action="store_true", help="Report mismatches without failing the gate")
    args = parser.parse_args()
    try:
        with redirect_stdout(sys.stderr):
            report = evaluate(args.suite, args.reference)
    except (ValueError, OSError, RecursionError) as error:
        print(json.dumps({"status": "invalid_reference", "error_type": type(error).__name__}))
        return 2
    report["mode"] = "measurement" if args.measure else "regression_gate"
    print(json.dumps(report, indent=2))
    if report["infrastructure_errors"]:
        return 2
    return 0 if args.measure or report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
