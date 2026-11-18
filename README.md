# BI Change Impact Lab

[![Launch interactive app](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://5h6ugidjyitkpvyqj4mjss.streamlit.app/)

**[Launch interactive app →](https://5h6ugidjyitkpvyqj4mjss.streamlit.app/)** — explore the bundled SQL dependencies in your browser.

A learning project using Graphify to trace SQL dependencies, retrieve source-backed graph context, and check structured dependency claims. The dashboard offers a template preview; an optional local GraphRAG CLI adds model generation behind the same evidence boundary.

## Try the interactive app

Open **[the hosted Streamlit app](https://5h6ugidjyitkpvyqj4mjss.streamlit.app/)** to explore the example without a local installation.
Choose an object, inspect its downstream views and source evidence, and download the impact report.

### Run a local copy instead

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

Share this repository URL: https://github.com/AimanManzoor/BI-change-impact-lab-

Share the app URL for browser access: https://5h6ugidjyitkpvyqj4mjss.streamlit.app/

The README launch button opens the Streamlit deployment. GitHub hosts the source;
Streamlit runs the application. Visitors can also follow the local setup instructions.
The deployment URL was supplied by the project owner; public access and browser
interactions should be checked in a signed-out or private browser window.

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
Human review remains required. The hosted dashboard is unchanged.

Generated databases and inspection reports remain local under the ignored
reports/generated/ directory.

External tools:
- REA: https://github.com/morluto/rea
- Project owner's REA fork: https://github.com/AimanManzoor/rea
