# Cross-file SQL validation: synthetic education example

## Purpose

The first retail example has one SQL file and five objects. This milestone
checks extraction and downstream traversal on a second example spread across
three files. It is an explicit reference fixture, not an arbitrary-repository
scanner or a benchmark of general SQL coverage.

No real student data, agency schema, school identifiers, or production measures
are included. Names and relationships are synthetic. These views do not define
a validated educational intervention policy or demonstrate correct KPI formulas.

## Files and independent expectations

- `examples/education/00_tables.sql`: three table definitions.
- `examples/education/10_summaries.sql`: attendance and behavior summary views.
- `examples/education/20_reports.sql`: attendance report, candidate-review view,
  and regional-review view.
- `examples/education/expected.json`: eight manually specified dependency pairs
  and expected consumer/depth mappings for all eight objects. These are written
  as reference answers, not generated from Graphify output.

The example has three tables, five views, and eight `reads_from` relationships.
The selected source is fixed by the application; users cannot choose file paths.

## Useful cases

| Changed object | Expected downstream result |
|---|---|
| `attendance_events` | attendance_summary (1 hop), attendance_report (2), review_candidates (3), regional_review (4) |
| `behavior_events` | behavior_summary (1), review_candidates (2), regional_review (3) |
| `enrollment` | attendance_report (1), regional_review (1), review_candidates (2) |
| `regional_review` | No downstream consumers inside this fixture |

Attendance changes do not make `behavior_summary` downstream merely because
both branches eventually join. Enrollment has both a short direct route and
a longer route to regional_review; the tool returns one shortest path per
consumer, not every possible dependency path.

## Verification behavior

`src/education_check.py` checks that all three files extracted successfully,
that the exact expected dependency pairs appear without duplicates, that source
locations refer to allowed files and valid line ranges, and that downstream
consumer/depth results match every reference case. Unknown objects or failed
reference checks stop execution rather than returning a no-impact result.

The report retains source file, line and confidence for each hop. A fingerprint
covers all source files and the reference JSON to identify the bytes used. It
is not an authenticity signature or proof that extraction is complete on
unseen SQL. A valid location also does not independently prove semantics.

The command analyzes source text. SQL is not executed by the app or CLI. One
test separately executes the fixture in an isolated in-memory SQLite database
with made-up rows to confirm that the example is usable SQL.

## Run locally

```bash
.venv/bin/python -m src.education_check --object attendance_events
.venv/bin/python -m unittest discover -s tests -t . -v
```

The CLI prints JSON to stdout and Graphify diagnostics to stderr. A handled
source or reference failure exits nonzero. No model call or API key is needed.

## Dashboard

Scroll to **Cross-file SQL validation: education example**. Choose an object
and click **Verify cross-file example**. Inspect the affected views and expand
their evidence paths. The report can be downloaded. Changing the education
object or any source/reference bytes hides the old report until rerun.

This section is separate from the retail impact harness and GraphRAG preview.
The new education example is not yet supported by model-backed generation.

## Observed validation and limits

All eight reference scenarios pass. Ten new test methods bring the full suite
to 52 tests. They cover cross-file edges, the four-hop chain, negative cases,
shortest paths, leaf objects, missing/duplicate edges, incomplete extraction,
file-order independence, source preservation, fingerprint changes, executable
SQL, CLI JSON, and dashboard failure/invalidation behavior.

These results establish behavior on two known fixtures, not a held-out model
evaluation, general SQL accuracy, column-level lineage, DAX/TMDL support,
runtime breakage detection, or correctness of educational decisions.

Next: extend the retrieval/harness interface to select a validated corpus,
then evaluate cited generation on both corpora. Keep the expected results
independent of the extractor and model when adding further cases.
