# Controlled impact plans

## Purpose and status

This is the deterministic control layer for a future AI planner. It is implemented
in `src/harness.py`. The dashboard creates its proposal from the selected object;
no language model is connected, and all runs record `model_calls: 0`.

Permitted proposal:

```json
{"tool": "trace_downstream", "object": "orders"}
```

The caller's selected object is the authority. A proposal cannot change that
object, introduce extra arguments, execute SQL or code, or select another file.
Only the five objects in the bundled fixture are supported. Input is capped at
2,048 UTF-8 bytes. Duplicate keys, code fences, extra text, and malformed JSON
are rejected rather than repaired.

## Execution boundary

1. Validate the caller's object and the proposal before loading a source or running the tool.
2. Load the fixture extraction; record a SHA-256 of the current SQL source.
3. Attempt the fixed impact tool once, with no retry.
4. Check result metadata, expected fixture consumers/depths, and each source-backed evidence hop.
5. Return a receipt. An unsuccessful run contains no displayable impact report.

The existing expected dependency pairs are checked inside the impact tool.
`examples/expected_impacts.json` additionally records manually specified downstream
objects and shortest depths for the five example objects. It is not generated
from extraction output. Evidence must connect the requested object to the
reported consumer through actual extracted edges, preserving file, line, and
confidence. Extra report fields are rejected.

## Receipt and outcomes

Receipts contain a run ID, selected object, status, stage list, impact-tool
attempt count, model-call count, elapsed milliseconds, source hash when available,
and a verified report on success. Human review remains required. The source hash
identifies bytes; it does not establish truth or freshness of every cached record.

| Status | Meaning |
|---|---|
| `completed` | Allowed plan; impact report passed implemented fixture checks |
| `no_consumers_in_fixture` | Verified result has no downstream consumers in this example |
| `rejected` | Invalid or unauthorized plan; zero impact-tool attempts |
| `source_error` | Source loading failed; zero impact-tool attempts |
| `tool_error` | The one impact-tool attempt failed; no retry |
| `verification_failed` | Returned evidence or metadata failed checks; report withheld |

One impact-tool attempt is not one total Python function call. The graph
extraction and validation stages are separate. This is not a sandbox, query
timeout, CPU/memory limit, fixed dollar budget, or crash-recovery system.
Receipts are not written to the server's filesystem; users can download them.

## Try locally

```bash
.venv/bin/python -m src.harness --object orders
```

The CLI constructs the same deterministic proposal as the dashboard unless
`--plan-json` supplies another JSON string. A rejected or failed run exits with
status 1; verified completed/no-consumer runs exit with status 0.

In Streamlit, select an object and expand **Inspect the execution receipt**.
The existing impact-report download remains available; a separate receipt
download includes execution checks and outcomes.

## Verification and limits

The full suite has 25 tests: seven analysis tests, seven app tests, and eleven
harness tests with multiple rejection and corrupted-result cases. Tests cover
zero-call rejection, one-attempt execution, error handling, invalid evidence,
wrong scope, missing/duplicate consumers, all five reference outcomes, and UI
suppression of failed results, plus CLI JSON output and exit codes. These cases are not a benchmark of general SQL
support or model behavior.

An extracted edge is not proof of runtime impact or correct business logic.
The reference checks apply only to the tiny bundled fixture. They do not prove
completeness for arbitrary repositories. A permitted plan is not proof that a
natural-language question was understood: there is no natural-language parser
or explanation-quality gate in this milestone.

Next: connect an explicitly enabled model planner without giving it permission
to edit these checks, choose file paths, execute SQL, or replace reference answers.
Evaluate held-out questions and failure cases separately from software tests.
