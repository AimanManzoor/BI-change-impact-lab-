# Bounded BI Change Review Agent

## Behavior and boundaries

The workflow turns a short impact question into a proposed plan, checks its
permissions, makes at most one verified analysis-tool attempt, and returns a
review receipt. It never executes model-supplied SQL, changes a database, chooses
an evidence path, or performs remediation. The caller's evidence is always the
bundled synthetic retail schema. This is a single bounded workflow, not a
multi-agent or autonomous investigation system.

The offline planner uses conservative keyword rules. It recognises one of five
retail object names and all/direct/indirect impact scope. Names are recognised
case-insensitively and normalised. Empty/oversized inputs, unknown or multiple
recognised names, compound/negative requests, or questions without impact intent
stop for clarification. Action verbs such as drop, update, execute, modify and run
are rejected conservatively, even in some harmless contexts. This is not general
natural-language understanding or a comprehensive intent/security classifier.
Unknown concepts and paraphrases may not be classified correctly. Read-only tools
and the Python allowlist remain the effective capability boundary.

Example plan:

```json
{"tool":"trace_recovered_impacts","object":"orders","scope":"indirect"}
```

Python independently derives the permitted object/scope from the same conservative
gate. A model proposal must match that complete plan exactly. Duplicate JSON keys,
extra fields, alternate tools, object changes or scope changes stop the run.
Successful planning authorises exactly one call to the existing check_evidence
function. That function compares recovered objects and edges with the independent
retail references before returning results. Scope filtering then narrows the
verified consumer list; intermediate evidence hops remain intact.

An accepted request can therefore finish with zero matching consumers. That is
separate from an unavailable source, failed planning, rejected proposal or invalid
question. Receipts preserve those statuses and count planner/tool attempts, not
SQL statements or every internal function invocation. A failed evidence attempt
counts as one tool call. model_calls counts attempts to invoke the trusted model
adapter, not guaranteed successful HTTP responses.

## Run locally without a model

From the repository root with requirements installed:

```bash
.venv/bin/python -m src.review_agent --question "Which indirect views depend on orders?"
```

Expected: completed, rules mode, zero model calls, one tool call, and only
regional_sales as a returned consumer with its complete two-hop path. This CLI
needs no Node.js, REA process or API key. Exit 0 means completed/no_consumers;
other statuses exit 1. JSON is emitted on stdout; extraction diagnostics go to
stderr. Machine-readable results are not a production reliability estimate.

## Optional live model planner

```bash
.venv/bin/python -m src.review_agent --live --model YOUR_AVAILABLE_MODEL_ID --question "Which indirect views depend on orders?"
```

Replace YOUR_AVAILABLE_MODEL_ID with a model ID available to your account.
The command reads ANTHROPIC_API_KEY or prompts with hidden input. Model IDs can
also come from ANTHROPIC_MODEL. Never put a key in a command argument, committed
file, receipt or public Streamlit widget.

An accepted request sends the question and permitted object/scope to Claude.
It does not send database rows, recovered SQL or local paths. The shared adapter
allows one provider attempt, no redirects or retry, a 512-token output setting,
a 64 KiB response limit, and a 30-second urllib/socket timeout. This is not a
strict total wall-clock deadline. The proposal is limited to 2048 UTF-8 bytes.
Invalid questions stop before credential prompting/provider setup. A model may
refuse or return invalid JSON; that produces no tool call, not a fabricated plan.
This is a potentially billable action, invoked only with --live.

The existing graph-generation adapter now accepts an internal system prompt and
output-validator callback. Its previous defaults remain the same. The planner
uses a different prompt/validator through composition; no model output can set
either callback or the provider URL. API reference:
https://platform.claude.com/docs/en/api/messages/create

## Browser behavior

The new expander is explicitly labelled an offline planning baseline. It runs
only after clicking Plan and verify review. Results and downloads are hidden when
the question or bundled evidence/reference fingerprint changes. The downloadable
receipt includes the checked plan, selected evidence paths, source SQL/fingerprints,
attempt counts, and a human-review marker. The UI's report is deterministic Python
output, not an unverified model narrative. No public model credentials are used.

## Validation and research interpretation

Eleven added test methods bring the suite to 86 tests. They include twelve
manually specified reference questions, invalid input and compound/negative
requests, forged tool/object/scope proposals, malformed/duplicate-key plans,
provider failure without retry, evidence failure, simulated model transport,
CLI JSON/exit behavior, UI rejection, and stale-result hiding. The existing
20 GraphRAG reference cases still pass independently.

The reference questions are known regression cases, not a held-out language
benchmark. The model path is tested with a simulated provider response only.
No live model call, model-quality comparison, latency benchmark or production
trial was run for this milestone. Passing these tests establishes covered
software contracts, not reliable interpretation of arbitrary questions.

A useful next research experiment is to freeze a new set of independently
labelled paraphrases and unsupported requests, then compare this rule baseline
with one selected live model over repeated trials. Measure correct object/scope,
appropriate abstention, tool misuse, evidence verification, latency and usage
separately. Do not tune on the final held-out questions.
