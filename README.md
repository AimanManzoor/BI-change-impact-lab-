# BI Change Impact Lab

An end-to-end BI engineering project combining SQL dependency analysis, GraphRAG, change-impact evaluation, and interactive retail analytics. The change-impact explorer retrieves source-backed graph context and checks structured dependency claims; an optional local GraphRAG CLI adds model generation behind the same evidence boundary.

## Live Demos

Explore both applications directly in your browser — no local installation required.

### 1. SQL Change Impact Analyzer (Streamlit)

[**Launch Streamlit App**](https://5h6ugidjyitkpvyqj4mjss.streamlit.app/)

- SQL dependency and lineage analysis
- Downstream change-impact investigation
- Source-backed evidence retrieval
- Downloadable impact reports

### 2. Retail Intelligence Dashboard (HTML)

[**Launch Interactive HTML Dashboard**](https://bi-change-impact-lab.onrender.com/dashboard)

- Dynamic SQL-driven KPI cards
- Regional revenue analysis and interactive cross-filtering
- Revenue distribution charts and customer performance analysis
- FastAPI, HTML, CSS, JavaScript, Plotly.js, and read-only SQLite connectivity

**Dataset:** 500 synthetic customers and 5,000 synthetic orders across five regions. All demo data is synthetic.

**Note:** Free hosting services may take a moment to wake up.

## Run Locally

### SQL Change Impact Analyzer (Streamlit)

Requires Git, Python 3.12, and an internet connection to install dependencies.
The bundled synthetic example needs no dataset download, API key, or database server.

**macOS / Linux** — paste this entire block into Terminal:

```bash
git clone https://github.com/AimanManzoor/BI-change-impact-lab-.git &&
cd BI-change-impact-lab- &&
python3 -m venv .venv &&
.venv/bin/python -m pip install -r requirements.txt &&
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

**Windows PowerShell** — run each line in order; stop if a command reports an error:

```powershell
git clone https://github.com/AimanManzoor/BI-change-impact-lab-.git
cd BI-change-impact-lab-
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open the URL printed in Terminal, normally [http://127.0.0.1:8501](http://127.0.0.1:8501).
Keep Terminal running while using the app. Press **Control+C** to stop it.
This address works on the computer running the app; it is not a public demo link.

Already cloned? Enter your existing checkout, run `git pull --ff-only`, reinstall
requirements, and launch Streamlit with the command above.

### Retail Intelligence Dashboard (FastAPI)

From the cloned repository directory, with your Python 3.12 virtual environment activated:

```bash
python -m pip install -r dashboard/requirements.txt
python dashboard/seed_data.py
python -m uvicorn dashboard.api:app --port 8000
```

Open [Local Dashboard](http://127.0.0.1:8000/dashboard). Keep the server running while exploring; press **Control+C** to stop it.

The seed script initializes the synthetic SQLite database if needed. An internet connection is required to load Plotly.js.

### Your first exploration

| Select | What you should see |
|---|---|
| `orders` | `order_summary` directly affected; `regional_sales` indirectly affected |
| `customers` | `customer_directory` and `regional_sales` directly affected |
| `regional_sales` | No downstream consumers in the bundled fixture |

Use **Inspect the evidence path** to check source lines, expand **Read the SQL source**,
and download a JSON report for your selection. These are potential dependency impacts,
not confirmed breaking changes. The app currently supports only this bundled example.

### Sharing

Share this repository: https://github.com/AimanManzoor/BI-change-impact-lab-

Use the [SQL Change Impact Analyzer](https://5h6ugidjyitkpvyqj4mjss.streamlit.app/) or [Retail Intelligence Dashboard](https://bi-change-impact-lab.onrender.com/dashboard) for browser access. GitHub hosts the source; Streamlit and Render host the applications. Visitors can also reproduce them locally.

## Milestone 1: verified SQL dependency baseline

Implemented: local Graphify AST extraction of a synthetic retail SQL fixture, comparison against independently specified dependency pairs, downstream traversal, and source evidence for each path. No API key, model call, assistant installation, or running database is required by the CLI.

The fixture contains two tables and three views. Graphify extracts four `reads_from` relationships. Changing `orders` potentially affects `order_summary` directly and `regional_sales` transitively. `customer_directory` is not downstream of `orders`.

## Run tests and the terminal report

After completing the installation above, run from the repository folder:

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
.venv/bin/python -m src.impact --object orders
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
Object names are exact and case-sensitive. An unknown name is an error rather than a report of no impact.

## Milestone 2: local Streamlit explorer

After installing requirements, run from the repository folder:

```bash
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Open the local URL printed by Streamlit (normally http://127.0.0.1:8501).
Keep that terminal running; press Control+C when finished. GitHub stores the
application source and does not run this local Python server.

- Select the object that might change; results update immediately.
- Inspect counts of direct and indirect downstream views.
- The dependency map shows all five example objects. Arrows point from a
  dependency to its consumer; blue marks the selected object, orange its
  downstream views, and gray the remaining objects.
- Choose a potentially affected view to inspect one shortest evidence path.
  Graphify's source file, line, and confidence labels are retained.
- Expand the SQL source to compare evidence locations with actual statements.
- Download the current selection's JSON impact report for review.

Try `orders`: two downstream views, one direct and one indirect. Try `customers`:
two direct views. Try `regional_sales`: no downstream consumer within this fixture.
The app stops on fixture verification failures instead of showing impact numbers.
The same `build_report()` function supplies the CLI and the dashboard's controlled impact tool.

The interface is a synthetic demo available locally and through the linked Streamlit deployment. No SQL uploads, database connection,
provider calls, model costs, or automatic business decisions are involved.
Automated UI checks use Streamlit AppTest; browser rendering and public hosting
are separate checks and have not been validated in this milestone.

## Milestone 3: AI harness foundation

The dashboard now passes a structured proposal through a Python-controlled harness.
It accepts only `trace_downstream` for the selected object, permits one impact-tool
attempt without retries, and checks result scope, expected consumers/depths, and
source evidence before displaying results. Failed runs expose no impact report.

Expand **Inspect the execution receipt** to see the proposed action, validation
stages, outcome, call count, and source hash, or download the receipt.

Run the harness locally:

```bash
.venv/bin/python -m src.harness --object orders
```

This impact-harness milestone uses a deterministic proposal, with **zero model calls**.
The later GraphRAG adapter below can optionally generate claims after retrieval;
the impact tool remains deterministic and does not interpret natural-language intent.

Read [the harness technical guide](docs/harness.md) for permitted inputs, statuses,
test coverage, and limitations.

## Milestone 4: graph retrieval and optional structured generation

The dashboard now includes **Graph-grounded question preview**. Select all,
direct, or indirect downstream impacts and click **Retrieve graph-grounded answer**.
Relevant paths are retrieved through the impact harness, with citation IDs,
SQL source lines, and excerpts. Indirect questions retain every intermediate hop.

The hosted preview uses deterministic templates: **no model calls or API key**.
An optional local Anthropic adapter generates structured claims from the same
context. Python rejects unsupported consumers, depths or citation paths before
rendering fixed explanatory sentences. No arbitrary model prose is displayed.

```bash
.venv/bin/python -m src.graphrag --object orders --kind indirect
.venv/bin/python -m evals.evaluate_graphrag
```

See [the GraphRAG technical guide](docs/graphrag.md) for optional live setup,
budgets, validation, and limitations. Live model requests and model-quality
evaluation remain unverified. This applies the graph-based RAG pattern to our
small fixture; it does not install Microsoft's GraphRAG framework, implement
free-form question understanding, or establish improvements over vector RAG.

## Milestone 5: cross-file SQL validation

A second synthetic education-reporting example spans **three SQL files, eight
objects, and eight dependency pairs**. A separate dashboard section checks
every dependency and eight independently specified downstream scenarios.

Try `attendance_events`: the verified path reaches `attendance_summary`,
`attendance_report`, `review_candidates`, then `regional_review` at four hops.
The checker also tests unrelated branches, shorter alternative paths and leaf
objects. Missing or unexpected dependencies stop the report.

In the app, scroll to **Cross-file SQL validation: education example**, select
an object, and click **Verify cross-file example**. Expand an evidence path or
download the report. Previous results are hidden when the object or source
fingerprint changes.

```bash
.venv/bin/python -m src.education_check --object attendance_events
```

All **52 tests** passed locally. No API calls or real student data are involved.
This milestone broadened extraction/traversal validation. The later selected-corpus
milestone below extends retrieval/generation support to education; neither establishes
performance on arbitrary SQL.

See [cross-file validation guide](docs/cross_file_validation.md).

## Milestone 6: GraphRAG across two validated corpora

In **Graph-grounded question preview**, choose **retail** or **education**.
Retail uses the selected object from the main explorer. Education has its own
object selector. Both support all, direct, and indirect downstream questions.

The selected corpus is a caller-controlled allowlist. Only its registered SQL
files may supply evidence. Education citations use IDs such as
`[education:E1]`; retail retains `[E1]`. Every claim must retain its complete
ordered evidence path. Unknown corpora and other-corpus objects stop retrieval
before generation. Switching corpus, object, question kind or fingerprint hides
the previous answer.

```bash
.venv/bin/python -m src.graphrag --corpus education --object attendance_events --kind indirect
.venv/bin/python -m evals.evaluate_graphrag
```

All **60 tests** and **20 offline template reference cases** passed locally.
The public dashboard makes zero model calls. The optional local model adapter
accepts either corpus, with simulated-response tests for both; live provider
verification and model-quality evaluation remain pending. The corpus selector
is not a multi-user access-control system, free-form query parser, or arbitrary
repository upload feature.

See [the GraphRAG guide](docs/graphrag.md) for context scope and optional live setup.

## How it works

1. `examples/retail.sql` supplies the synthetic source. It contains no organization data.
2. `graphify.extract.extract()` parses it locally and returns nodes and edges.
3. `examples/expected_dependencies.json` supplies the manually specified expected pairs; expected answers are not generated from extraction output.
4. `src/impact.py` checks exact pair agreement and edge evidence before reporting fixture impact.
5. Breadth-first traversal follows dependencies in reverse: from a changed object to consumers. One shortest evidence path is returned per consumer, with source locations and original confidence labels.

The CLI reads SQL as source text; it does not execute SQL. One test separately executes the fixture in an isolated in-memory SQLite database to confirm the example is valid.

## Verification

Sixty tests passed locally on Python 3.12, covering analysis, Streamlit interactions, the impact harness, graph retrieval, and simulated provider responses. Twenty offline template reference cases across both corpora and eight education object/depth reference scenarios pass; no live model quality benchmark has been run. Checks cover the four expected dependencies, direct/transitive impact, unrelated objects, leaf objects, unknown names, changed/missing edges, missing evidence, cycle handling, executable SQL, object selection, evidence-path inspection, clearing stale results, and stopping on invalid or missing fixtures. This is a small fixture validation, not a general SQL parser benchmark. GitHub Actions also passed for the Streamlit milestone ([run](https://github.com/AimanManzoor/BI-change-impact-lab-/actions/runs/43686739869)). The workflow runs the suite on subsequent pushes; check Actions for the latest outcome.

## Scope and limitations

- Two fixed synthetic examples are included. GraphRAG can select retail or education; the retail impact harness and the standalone education reference checker supply validated context. Neither accepts arbitrary-corpus input.
- Potential impact indicates a dependency path, not a demonstrated breaking change.
- Source locations and confidence labels do not prove business correctness.
- No column-level lineage, dynamic SQL, DAX, TMDL, Power BI report mapping, or live database integration is implemented.
- A Streamlit interface is implemented, with the owner-provided hosted app linked above. Graph-grounded template answers and an optional local structured model-generation adapter are implemented; live provider verification is pending.
- The pinned published Graphify package is used; this application does not require modifying the Graphify fork. Indirect dependencies are not fully locked.

## Roadmap

- [x] Synthetic SQL fixture, Graphify extraction, independent expected dependencies and source-backed traversal.
- [x] A second, multi-file synthetic education fixture with independent dependency and impact references.
- [x] A selected-corpus GraphRAG interface for retail and education, with scoped citations and reference cases.
- [ ] Broader SQL dialect/repository coverage.
- [x] Streamlit interface for selecting an object and inspecting evidence paths.
- [x] Deterministic harness foundation: strict plan permissions, one impact-tool attempt, fixture evidence checks, and downloadable receipts.
- [x] Scoped graph retrieval, cited template answers, and an opt-in structured model-generation adapter with mocked-provider tests.
- [ ] Live provider verification, broader SQL fixtures, natural-language intent checks, and held-out model task evaluation.

## Attribution

Built using [Graphify](https://github.com/Graphify-Labs/graphify), an Apache-2.0 project. Graphify supplies extraction; this repository supplies the synthetic example, expected-dependency checks, impact traversal, and tests. This project is independent and is not affiliated with or endorsed by Graphify Labs.

## REA SQLite schema verification

This optional local experiment connects REA database inspection with
Graphify dependency extraction. It is limited to the bundled synthetic
retail fixture: two tables, three views, and four expected dependencies.

REA recovers stored SQL declarations. The Python checker validates the
recovered objects, analyses the SQL without executing it, compares
dependencies with the existing reference, and verifies downstream
impacts from `orders`.

### Reproduce

Use Python dependencies from requirements.txt. REA is an optional
external CLI; this experiment uses rea-agents 6.9.0. That release requires
Node.js ^22.23.4, ^24.22.1, or >=26.12.1; SQLite inspection additionally
requires the supported native SQLite capability in Node 24/26.

Create the synthetic database once, from the repository root:

```bash
.venv/bin/python - <<'PYTHON'
import sqlite3
from pathlib import Path

database = Path("reports/generated/retail_demo.sqlite")
if database.exists():
    raise SystemExit("Database exists; inspect it before replacing it.")
database.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(database) as connection:
    connection.executescript(
        Path("examples/retail.sql").read_text(encoding="utf-8")
    )
print(database)
PYTHON
```

Inspect the database and verify the recovered definitions:

```bash
npx --package=rea-agents@6.9.0 rea inspect-sqlite-database ./reports/generated/retail_demo.sqlite --schema-scope database --json > reports/generated/rea_schema.json
.venv/bin/python -m src.rea_check --evidence reports/generated/rea_schema.json
```

Expected result: `reference_verified`, five objects and four dependencies.
Changing `orders` potentially affects `order_summary` directly and
`regional_sales` indirectly.

The report embeds the recovered SQL and its line references, plus SHA-256
fingerprints of the evidence file and recovered SQL. Fingerprints identify
content; they do not authenticate the inspection or prove correctness.

### Tests and limitations

Six additional regression tests cover valid recovery, missing or multiple
schemas, missing/duplicate/misclassified objects, missing SQL, incorrect
dependencies, and missing evidence files. The tests construct a minimal
evidence envelope; they do not invoke REA, Node.js, or a model.

This is fixture-scoped integration validation, not support for arbitrary
databases, column-level lineage, DAX/TMDL analysis, or confirmed breaking
changes. REA inspection and graph extraction are separate stages.
Human review remains required. See the bundled Streamlit demo below.

Generated databases and inspection reports remain local under the ignored
reports/generated/ directory.

External tools:
- REA: https://github.com/morluto/rea
- Project owner's REA fork: https://github.com/AimanManzoor/rea

## REA impact selection

The REA checker supports selecting any object in the fixed retail fixture:

- `orders`
- `customers`
- `order_summary`
- `regional_sales`
- `customer_directory`

Example, after creating the REA evidence file using the instructions above:

```bash
.venv/bin/python -m src.rea_check --evidence reports/generated/rea_schema.json --object customers
```

The default remains `orders`. Reports include direct and indirect consumer
counts and source-backed paths. Selecting a leaf view returns an empty
impact list; an unknown or incorrectly capitalized name is rejected.

All selections are checked against examples/expected_impacts.json.
This remains a synthetic, fixture-scoped experiment rather than arbitrary
database support or proof that a downstream report will break.

The CLI reserves stdout for JSON and sends extraction diagnostics to stderr.
This lets other programs reliably parse its output.

Three additional regression tests cover all five objects, invalid selections,
and CLI behavior. The complete suite now contains 103 tests.
The existing 20 offline GraphRAG reference cases remain separate checks.
The Streamlit interface now includes a separate bundled REA demo.

## Explore recovered schema evidence in Streamlit

Open the application, expand **REA: explore a recovered database schema**,
and enable **Explore the bundled REA example**.

Select a retail table or view to see:
- Direct and indirect downstream consumer counts.
- Reference-verified dependency paths.
- Recovered SQL with matching line references.
- A downloadable report for the current selection.

Try `customers`: two direct consumers, customer_directory and regional_sales.
Try `regional_sales`: no downstream consumers in this fixture.

The bundled examples/rea/retail_schema.json contains only synthetic object
names and SQL definitions projected from a local REA inspection. Original
machine paths, database files, row data, and the full inspection envelope
are not bundled. This projection is not a signed REA attestation.

The browser does not run REA, require Node.js, connect to a database,
accept uploads, or call a model. Python reuses src/rea_check.py to verify
the stored schema against the fixed retail reference. Results recompute
on selection; failed verification displays no REA report or download.

The six new interface tests bring the suite to 75 tests. They cover the
default interface, evidence display, selection-specific downloads, leaf
objects, missing/invalid evidence, and failed rechecks.

This remains a synthetic demonstration of potential dependency impact,
not arbitrary-database support or proof of runtime breakage.


## Bounded change-review planning

The Streamlit app now includes **BI Change Review Agent — offline planning
baseline**. Ask a short question about one retail object, such as
"Which indirect views depend on orders?", then click **Plan and verify review**.
The rule-based planner proposes an object/scope; Python checks the plan and
permits one reference-verified evidence-tool attempt. Completed receipts include
SQL evidence and can be downloaded. Changing the question or source/reference
fingerprint hides the previous result.

The browser makes zero model calls. An optional local `--live` CLI uses the
shared Claude adapter for one bounded model-planning attempt. The model can
propose only the permitted tool/object/scope and cannot choose files, execute
SQL, modify data or supply final factual claims. Live model verification is
pending; the provider path was tested with a simulated response.

```bash
.venv/bin/python -m src.review_agent --question "Which indirect views depend on orders?"
```

Local validation: **86 tests passed**, including 11 added methods and 12 known
reference questions; all **20 existing GraphRAG reference cases** also passed.
The narrow intent gate is a conservative keyword baseline, not general language
understanding. See [change-review methodology](docs/change_review_agent.md) for
permissions, failure statuses, CLI setup, source handling and evaluation limits.


## Planner evaluation dataset v1

A versioned set of **22 manually specified questions** now evaluates the complete
offline planner workflow. **16 regression cases pass**. **Two challenge cases
currently fail**: hypothetical rename analysis and compound explanations reveal limits in the keyword baseline. These are development results, not a held-out
model benchmark or a general language-understanding score.

```bash
.venv/bin/python -m evals.evaluate_planner
.venv/bin/python -m evals.evaluate_planner --suite challenge --measure
```

Reports include expected/actual plans, consumer depths, tool-use checks, category
results, status-confusion counts, and a reference fingerprint. The challenge
measurement command returns success for completed measurements even when cases
mismatch; read its failed count. Invalid references or infrastructure errors still
fail. CI gates the supported regression cases and separately measures challenges.

Initial evaluation milestone: **94 tests passed**, all **20 existing GraphRAG reference cases
passed**, the planner regression suite matched **16/16**, and the challenge suite
matched **0/6**. No planner logic, live provider call, or model-quality benchmark
was introduced in this milestone. The existing live planner shares the same
pre-model intent gate and cannot fix questions rejected before a model call.

See [planner evaluation methodology](docs/planner_evaluation.md). The next step is
to address a measured failure class and check that supported behavior is preserved.


## Reliance-question refinement

The offline planner now recognises constrained questions such as
"Which views rely on orders?", "Which direct views rely on orders?",
and "Which views are relying on orders?".

Recognition requires a view-oriented question naming one supported
dependency object. A bare use of "rely" does not permit a tool call.
Existing ambiguity and action checks still run first.

Local validation: 97 tests passed, all 16 supported planner cases passed,
and all 20 GraphRAG reference cases passed. On the unchanged development
dataset, challenge agreement improved from 0/6 to 1/6. Five cases remain
unresolved.

This is a targeted rule refinement, not a held-out model evaluation or
evidence of general language understanding. No model call is required.




## Unsupported-analysis guard

The change-review planner now asks for clarification on requests for upstream
dependencies or explicit row counts. Its tool supports downstream dependency
impact only, so these requests make zero model calls and zero analysis-tool calls.
Explicit write requests remain rejected by the earlier action guard.

Local validation: 100 regression tests passed, all 16 supported planner reference
cases passed, and all 20 GraphRAG cases passed. On the unchanged development
reference dataset, challenge agreement improved from 1/6 to 3/6. The remaining
three cases concern benign assurances, hypothetical renames and compound
explanations. This is a targeted development-set improvement, not a held-out
language benchmark. No model call is required.


## Read-only assurance refinement

The planner accepts the trailing phrase "without changing it" as a read-only
assurance, with optional final punctuation. The phrase is ignored only for the
ambiguity check. The original full question still passes through the earlier
action guard and the existing object, scope and unsupported-analysis checks.

Other uses of "without", multiple-object requests, and write requests remain
stopped. This is a narrow phrase rule rather than general negation handling.

Local validation: 103 tests passed; all 16 supported planner cases and all 20
GraphRAG cases passed. On the unchanged development dataset, challenge agreement
improved from 3/6 to 4/6. Hypothetical renames and compound explanations remain
unresolved. No live model was evaluated.

## Downstream explanation-request refinement

The planner recognises the trailing phrase "and explain the downstream impact"
for an otherwise supported single-object review. It preserves the selected
object and direct/indirect scope.

The original question still passes through action, ambiguity, object and
unsupported-analysis checks. Write requests and multiple-object requests
remain stopped before model or analysis-tool calls.

This is a narrow rule refinement, not general language understanding.
The offline workflow uses zero model calls and returns reference-verified
potential dependency impacts, not proof of runtime breakage.

Run the targeted checks:
`python -m unittest tests.test_explanation_request -v`.
