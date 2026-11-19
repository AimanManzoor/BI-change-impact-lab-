# Planner reference evaluation v1

## Research question

Does the offline change-review planner select the right object and scope, stop
unsupported requests, and use evidence tools only when the reference task permits?
The unit of evaluation is one complete run_review invocation, including its fixed
REA evidence checker. No provider, Node.js, network or model artifact is needed.

The versioned JSON dataset in evals/planner_cases.json contains 22 manually
specified questions and expected decisions. Its expected answers are not generated
from the planner's returned results. These are development/reference cases, not a
held-out statistical benchmark or a representative sample of user traffic.

## Two purposes

| Suite | Cases | Purpose | Initial result |
|---|---:|---|---|
| regression | 16 | Preserve established supported behavior | 16 matched, 0 mismatched |
| challenge | 6 | Measure desired behaviors the baseline lacks | 0 matched, 6 mismatched |

Regression includes routing, all/direct/indirect scope, leaf/empty scope,
case-normalised names, ambiguity, blank inputs, unknown objects and explicit
write requests. An empty consumer list is a valid result for a supported leaf
or empty scope; it is different from an invalid question or unavailable source.

Challenge cases deliberately express desired task semantics rather than current
keyword-policy behavior:

| Question pattern | Desired outcome | Current limitation |
|---|---|---|
| Views that rely on orders | Review orders | Paraphrase not recognised |
| Review without changing it | Read-only review | Benign assurance triggers clarification |
| Downstream effect if I rename orders | Review hypothetical change | Rename keyword causes rejection |
| Review orders and explain impact | Review one object | Conjunction triggers clarification |
| Review the number of rows in orders | Clarify unsupported task | Downstream review returned instead |
| Review upstream dependencies | Clarify unsupported direction | Downstream review returned instead |

Hypothetical change analysis does not authorise executing a rename. The reference
expects only the existing read-only dependency tool. These challenge labels are
reviewable product requirements; change them only for a justified specification
change, not merely to match existing output. More independent review and broader
examples are needed before treating them as ground truth for real-world usage.

## What the grader checks

Each case checks status, exact plan, expected consumers and hop depths, tool-call
count, zero model calls, rules mode, human-review marker, duplicate consumers,
integer tool counts, and presence/absence of a report. The report includes the
reference-file SHA-256, per-category agreement, status confusion counts, actual
and expected values, and failed-check names. The hash identifies reference bytes;
it does not authenticate the labels or establish correctness.

case_agreement is the fraction of these cases satisfying every check. It is not
model accuracy, a confidence interval, production reliability, or general SQL
lineage quality. The grader checks selected structured outcomes; it is not a
semantic judge or an independent proof of every source-evidence claim. The
existing checker and regression suite cover the evidence contracts separately.

## Run and interpret

```bash
.venv/bin/python -m evals.evaluate_planner
.venv/bin/python -m evals.evaluate_planner --suite challenge --measure
```

The default is a regression gate. Exit 0 means all selected cases matched;
exit 1 means at least one mismatch. --measure explicitly changes the exit policy:
mismatches remain visible in JSON, but do not fail the command. Invalid references,
unexpected runner failures, and planner/evidence operational errors still exit 2.
Therefore a zero exit in measurement mode does not mean all cases passed.

Without --measure, the challenge command currently exits 1 with six mismatches:

```bash
.venv/bin/python -m evals.evaluate_planner --suite challenge
```

To save reports locally, create reports/generated and redirect stdout there.
Graphify diagnostics go to stderr; JSON stdout remains parseable. Reports are
not automatically committed. The GitHub workflow runs the existing GraphRAG
references, the planner regression gate, and challenge measurement separately.
Challenge behavior mismatches are non-gating; infrastructure errors are gating.

## Verification of the evaluator

Eight additional test methods bring the repository to 94 tests. They cover case
aggregation, changed reference hashes, deliberately incorrect expectations,
corrupted consumers/call budgets, unexpected runner failures, missing evidence,
invalid/duplicate/inconsistent reference data, and CLI gating/measurement exit
codes. Negative controls demonstrate the checker can fail. No planner production
logic changed in this milestone and no live model evaluation was performed.

## Next experiment

Choose one observed failure class, propose a small intent-gate change and compare
before/after on both suites. Freeze a separately authored set of new questions
before further tuning and use it only for final evaluation. Add repeated trials
and usage/latency reporting when evaluating a stochastic model.

The current live planner inherits the same conservative intent gate. It cannot
recover questions stopped before the model is called. Comparing only the existing
live adapter against these early-gate failures would not measure improved language
understanding; the gate design must be addressed explicitly first.
