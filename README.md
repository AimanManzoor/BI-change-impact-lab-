# BI Change Impact Lab

A learning project using Graphify to trace SQL dependencies and support evidence-based change review. Planned AI explanations will sit behind a Python-controlled harness.

## Milestone 1: verified SQL dependency baseline

Implemented: local Graphify AST extraction of a synthetic retail SQL fixture, comparison against independently specified dependency pairs, downstream traversal, and source evidence for each path. No API key, model call, assistant installation, or running database is required by the CLI.

The fixture contains two tables and three views. Graphify extracts four `reads_from` relationships. Changing `orders` potentially affects `order_summary` directly and `regional_sales` transitively. `customer_directory` is not downstream of `orders`.

## Run locally (Python 3.12 recommended)

```bash
git clone https://github.com/AimanManzoor/BI-change-impact-lab-.git
cd BI-change-impact-lab-
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -v
.venv/bin/python -m src.impact --object orders
```

On Windows use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.
If already cloned, enter that checkout and use `git pull --ff-only` before running the setup commands.

Try `--object customers` or `--object regional_sales` as well. Object names are exact and case-sensitive. An unknown name is an error; it is never presented as proof of no impact.

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
The same `build_report()` function supplies both the CLI and app results.

The interface is a local synthetic demo. No SQL uploads, database connection,
provider calls, model costs, or automatic business decisions are involved.
Automated UI checks use Streamlit AppTest; browser rendering and public hosting
are separate checks and have not been validated in this milestone.

## How it works

1. `examples/retail.sql` supplies the synthetic source. It contains no organization data.
2. `graphify.extract.extract()` parses it locally and returns nodes and edges.
3. `examples/expected_dependencies.json` supplies the manually specified expected pairs; expected answers are not generated from extraction output.
4. `src/impact.py` checks exact pair agreement and edge evidence before reporting fixture impact.
5. Breadth-first traversal follows dependencies in reverse: from a changed object to consumers. One shortest evidence path is returned per consumer, with source locations and original confidence labels.

The CLI reads SQL as source text; it does not execute SQL. One test separately executes the fixture in an isolated in-memory SQLite database to confirm the example is valid.

## Verification

Twelve tests passed locally on Python 3.12 (seven analysis tests and five Streamlit interaction/error tests). Checks cover the four expected dependencies, direct/transitive impact, unrelated objects, leaf objects, unknown names, changed/missing edges, missing evidence, cycle handling, executable SQL, object selection, evidence-path inspection, clearing stale results, and stopping on invalid or missing fixtures. This is a small fixture validation, not a general SQL parser benchmark. A GitHub Actions workflow runs the same suite; its hosted outcome must be checked in Actions.

## Scope and limitations

- Only the bundled SQL fixture is supported in this milestone. The CLI has no arbitrary-corpus input.
- Potential impact indicates a dependency path, not a demonstrated breaking change.
- Source locations and confidence labels do not prove business correctness.
- No column-level lineage, dynamic SQL, DAX, TMDL, Power BI report mapping, or live database integration is implemented.
- A local Streamlit interface is implemented. No AI explanation or public hosted deployment is implemented yet.
- The pinned published Graphify package is used; this application does not require modifying the Graphify fork. Indirect dependencies are not fully locked.

## Roadmap

- [x] Synthetic SQL fixture, Graphify extraction, independent expected dependencies and source-backed traversal.
- [ ] Additional SQL fixtures and measured coverage of supported/unsupported cases.
- [x] Streamlit interface for selecting an object and inspecting evidence paths.
- [ ] Optional AI explanation harness: allowlisted inputs, bounded calls, source-reference checks, abstention when evidence is missing, and evaluation against held-out examples.

## Attribution

Built using [Graphify](https://github.com/Graphify-Labs/graphify), an Apache-2.0 project. Graphify supplies extraction; this repository supplies the synthetic example, expected-dependency checks, impact traversal, and tests. This project is independent and is not affiliated with or endorsed by Graphify Labs.
