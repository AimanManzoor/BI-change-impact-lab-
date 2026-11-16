# Graph-grounded retrieval and optional generation

## Implemented scope

This milestone applies the graph-based retrieval-augmented generation pattern
to the existing Graphify SQL fixture. It is not Microsoft's GraphRAG package or
its global/community-summary pipeline. No embeddings, vector store, new database,
or additional Python dependency is introduced.

The selected SQL object is the retrieval seed. Three predefined question kinds
cover all, direct, or indirect downstream impacts. There is no free-form question
understanding, entity-linking model, upstream-impact query, causal diagnosis,
or general SQL repository ingestion in this version.

The public dashboard uses template mode and makes no model requests. An opt-in
local CLI can send the retrieved context to Anthropic for structured generation.
The provider integration is implemented and tested with simulated responses;
no live provider request or LLM task-quality benchmark has been run.

## Retrieval and evidence

`src/graphrag.py` first invokes the existing controlled impact harness. The
verified downstream paths are filtered by question kind. An indirect question
retains the intermediate hops needed to justify the connection.

Each retrieved edge receives a context-local ID such as E1, its consumer and
dependency, source file, source line, Graphify confidence label, and that line's
SQL excerpt. The context includes the source hash and scope. It contains only
the selected paths, not the whole graph or all SQL files. IDs identify evidence
within one answer package; they are not globally persistent citations.

The fixed context budget is 16,000 serialized UTF-8 bytes. The underlying harness
permits one impact-tool attempt per question. An app rerun also performs its
existing dashboard analysis separately; the per-question budget does not bound
all work in an entire browser session. There is no query or pipeline deadline.

No matching context produces a scoped no-context response without a generation
attempt. Retrieval failures withhold the answer and preserve the tool-attempt
count when available. Absence from this small graph is not proof of no impact
outside the bundled fixture.

## Structured generation and checks

The local model receives the question kind, object, scoped claims to cover,
and evidence package. It proposes only this structure:

```json
{"claims":[{"object":"regional_sales","depth":2,"evidence_ids":["E1","E2"]}]}
```

Python requires exactly the retrieved consumers, their exact depths, and each
complete ordered evidence-ID path. Unknown or duplicate consumers, changed
depths, extra fields, missing citations, and unsupported citations are rejected.
Malformed, duplicated-key, fenced, truncated, or oversized responses do not
produce a displayed answer. There is no repair or retry.

After verification, Python renders fixed explanatory sentences and citations.
Arbitrary model-written prose is not displayed. This deliberately narrow
generation task mostly reproduces supplied structured claims; it does not show
that a model independently inferred multi-hop impact. Template mode supplies
the same structure deterministically without an LLM, providing a baseline.

These checks ground the displayed structural claims in the retrieved fixture
paths. They do not verify business semantics, a breaking change, the truth of
SQL runtime behavior, or natural-language explanation quality.

## Use the dashboard

Select a SQL object, scroll to **Graph-grounded question preview**, choose all,
direct, or indirect downstream views, then click **Retrieve graph-grounded
answer**. The evidence table maps each citation to its SQL source. Download the
answer package for review. Changing the selected object, question kind, or
source hash hides the previous answer until a fresh retrieval is submitted.

## Run offline

From the repository root after the normal installation:

```bash
.venv/bin/python -m src.graphrag --object orders --kind indirect
.venv/bin/python -m evals.evaluate_graphrag
.venv/bin/python -m unittest discover -s tests -t . -v
```

The CLI prints JSON to stdout; extraction diagnostics go to stderr. Offline mode
does not use credentials even if provider environment variables are set.

## Optional live generation (local CLI only)

Choose a model ID available to your own Anthropic account and replace MODEL_ID:

```bash
.venv/bin/python -m src.graphrag --object orders --kind indirect --live --model MODEL_ID
```

The API key is read from ANTHROPIC_API_KEY or a hidden terminal prompt. Never
put keys into chat, screenshots, command arguments, or tracked files. No .env
file is automatically loaded. ANTHROPIC_MODEL can supply the model ID.

`src/graph_generator.py` uses the fixed HTTPS Messages endpoint, API version
2026-10-21, a 512-output-token cap, a 30-second socket timeout, a 64-KiB response
cap, and one request attempt. Redirects are refused. The claim text is limited
to 8,192 bytes. These are not a fixed-cost budget or a total deadline; failed
requests can still incur charges. Provider usage is recorded when available,
but is not a complete billing report. Raw keys and provider responses are not
included in the result. Selected synthetic SQL evidence is sent to the provider
only in explicit live mode. The public app cannot enable provider calls.

## Validation and next work

The full suite has 42 tests, including graph retrieval, complete multi-hop
citations, wrong claims/citations, no-context behavior, provider error and size
handling, CLI JSON, and dashboard selection invalidation. Provider tests use
simulated responses and make no live calls.

Ten manually specified reference cases pass in template mode. They exercise
the known fixture and are not held-out research tasks or a comparison against
vector RAG. No retrieval-performance, token-saving, or model-quality gain has
been established. The reference evaluator reports exactly what it checked.

Next work: verify one live request, expand independently checked SQL fixtures,
define held-out natural-language tasks before adding question parsing, and
compare template and model-assisted modes on both failures and successes.

## Primary references

- [GraphRAG local-search concept](https://microsoft.github.io/graphrag/query/local_search/)
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)
- [Anthropic API versioning](https://platform.claude.com/docs/en/api/versioning)
