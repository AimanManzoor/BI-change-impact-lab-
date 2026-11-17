"""Local interactive explorer for the verified synthetic SQL fixture."""
import json
import streamlit as st
from src.impact import ROOT, extract_fixture, verify_fixture
from src.harness import run_harness
from src.graphrag import answer_question
from src.education_check import OBJECTS as EDUCATION_OBJECTS, check_education, source_fingerprint


st.set_page_config(page_title='BI Change Impact Lab', layout='wide')
st.title('BI Change Impact Lab')
st.write('Explore how a SQL change could flow into dependent views.')
st.caption('Synthetic SQL examples powered by Graphify. Retail analysis, plus retail/education graph-grounded questions. No AI calls or live database access.')

try:
    result = extract_fixture()
    nodes, edges = verify_fixture(result)
    sql_text = (ROOT / 'examples/retail.sql').read_text()
except (ValueError, OSError, ImportError) as exc:
    st.error(f'Could not verify the SQL fixture. Impact results are unavailable. {exc}')
    st.stop()

object_ids = {edge[key] for edge in edges for key in ('source', 'target')}
names = sorted({nodes[node_id]['label'] for node_id in object_ids})
selected = st.selectbox('Which SQL object might change?', names,
                        index=names.index('orders'), key='changed_object')
proposal = json.dumps({'tool': 'trace_downstream', 'object': selected})
receipt = run_harness(selected, proposal, result)
if receipt['status'] not in {'completed', 'no_consumers_in_fixture'}:
    st.error(f"Impact checks stopped the run: {receipt['status']}. Results are unavailable.")
    st.stop()
report = receipt['report']

hits = report['potentially_affected']
direct = sum(hit['depth'] == 1 for hit in hits)
first, second, third = st.columns(3)
first.metric('Potentially affected views', len(hits))
second.metric('Direct dependencies', direct)
third.metric('Indirect dependencies', len(hits) - direct)
st.warning('A dependency path indicates potential impact. It does not prove a breaking change or a correct KPI. Human review is required.')

st.subheader('Dependency map')
st.caption('Arrows point from a dependency to its consumer. Blue: selected object. Orange: downstream views. Gray: other objects in this fixture.')
affected_names = {hit['object'] for hit in hits}
dot = ['digraph dependencies {', 'rankdir=LR;', 'bgcolor="transparent";',
       'node [shape=box, style="rounded,filled", fontcolor="#172033", color="#94a3b8"];',
       'edge [color="#94a3b8", fontcolor="#64748b"];']
for name in names:
    color = '#93c5fd' if name == selected else '#fdba74' if name in affected_names else '#e2e8f0'
    dot.append(f'{json.dumps(name)} [fillcolor="{color}"];')
for edge in edges:
    dependency = json.dumps(nodes[edge['target']]['label'])
    consumer = json.dumps(nodes[edge['source']]['label'])
    dot.append(f'{dependency} -> {consumer} [label="feeds"];')
dot.append('}')
st.graphviz_chart('\n'.join(dot), width='stretch')

st.subheader('Potentially affected views')
if hits:
    st.dataframe([{'view': h['object'],
                   'relationship': 'Direct' if h['depth'] == 1 else 'Indirect',
                   'hops': h['depth']} for h in hits], hide_index=True, width='stretch')
    target = st.selectbox('Inspect the evidence path', [h['object'] for h in hits], key='evidence_target')
    hit = next(h for h in hits if h['object'] == target)
    st.dataframe(hit['evidence_path'], hide_index=True, width='stretch')
    st.caption('One shortest path per view. Confidence labels are preserved from Graphify; they are not probabilities or guarantees.')
else:
    st.info('No downstream consumers were found in this verified fixture. This says nothing about objects outside the example.')

with st.expander('Read the SQL source', expanded=False):
    st.caption('examples/retail.sql — line numbers correspond to the evidence table.')
    st.code(sql_text, language='sql', line_numbers=True)

st.download_button('Download this impact report', json.dumps(report, indent=2),
                   file_name=f'impact_{selected}.json', mime='application/json')
with st.expander('Inspect the execution receipt'):
    st.caption('The dropdown creates a deterministic proposal. Python checks permissions, limits the impact tool to one attempt, and verifies the returned evidence. This dashboard makes no model calls; optional structured model generation is available through the local GraphRAG CLI.')
    st.code(proposal, language='json')
    st.json(receipt)
    st.download_button('Download execution receipt', json.dumps(receipt, indent=2),
                       file_name=f'receipt_{selected}.json', mime='application/json')
st.caption('Four dependency pairs checked against a manually specified reference. No column-level lineage, DAX, or Power BI report mapping yet.')

st.subheader('Graph-grounded question preview')
st.caption('Template mode: retrieve relevant graph paths and show checked citations. No LLM call or API key. Optional model generation is available through the local CLI.')
question_corpus = st.radio('Question corpus', ('retail', 'education'), key='gr_corpus')
st.caption('This choice controls only the question section. The retail dependency map above and the education reference checker below keep their own scopes.')
query_object = selected if question_corpus == 'retail' else st.selectbox(
    'Education object for this question', EDUCATION_OBJECTS, key='gr_education_object')
question_labels = {'All downstream views': 'all', 'Direct downstream views': 'direct',
                   'Indirect downstream views': 'indirect'}
question_label = st.radio('Which impacts should the answer cover?', list(question_labels), key='gr_kind')
question_kind = question_labels[question_label]
try:
    question_hash = receipt['source_sha256'] if question_corpus == 'retail' else source_fingerprint()
    answer_key = (question_corpus, query_object, question_kind, question_hash)
except OSError:
    answer_key = None
    st.error('The selected question corpus is unavailable.')
if st.button('Retrieve graph-grounded answer', key='gr_answer', disabled=answer_key is None):
    st.session_state['gr_result'] = (answer_key, answer_question(
        query_object, question_kind, corpus=question_corpus,
        result=result if question_corpus == 'retail' else None))
stored = st.session_state.get('gr_result')
if answer_key is not None and stored is not None and stored[0] == answer_key:
    grounded = stored[1]
    if grounded['status'] in {'completed', 'no_context'}:
        st.markdown(grounded['answer'])
        if grounded['context']['evidence']:
            st.dataframe(grounded['context']['evidence'], hide_index=True, width='stretch')
        st.download_button('Download graph-grounded answer', json.dumps(grounded, indent=2),
                           file_name=f'graph_answer_{question_corpus}_{query_object}_{question_kind}.json', mime='application/json')
    else:
        st.error('The graph-grounded answer could not be verified. No answer is displayed.')

st.subheader('Cross-file SQL validation: education example')
st.caption('A separate reference-check view: three files, eight SQL objects, and eight independently specified dependency pairs. To ask cited questions about these objects, select education in the Graph-grounded question preview above.')
education_object = st.radio('Which education object might change?', EDUCATION_OBJECTS,
                            key='education_object')
try:
    education_key = (education_object, source_fingerprint())
except OSError:
    education_key = None
    st.error('Education sources are unavailable.')
if st.button('Verify cross-file example', key='education_verify', disabled=education_key is None):
    st.session_state.pop('education_result', None)
    try:
        st.session_state['education_result'] = (education_key, check_education(education_object))
    except (ValueError, OSError, KeyError, TypeError):
        st.error('Cross-file verification failed. No education impact report is displayed.')
education_stored = st.session_state.get('education_result')
if education_key is not None and education_stored is not None and education_stored[0] == education_key:
    education = education_stored[1]
    st.success(f"Verified {education['dependency_pairs']} dependency pairs and {education['reference_cases_passed']} reference scenarios across three files.")
    st.caption('This does not establish runtime breakage, correct educational decisions, DAX lineage, or support for arbitrary repositories. No real student data is included.')
    if education['potentially_affected']:
        st.dataframe([{'view': h['object'], 'hops': h['depth']} for h in education['potentially_affected']],
                     hide_index=True, width='stretch')
        for h in education['potentially_affected']:
            with st.expander(f"Evidence for {h['object']} ({h['depth']} hops)"):
                st.dataframe(h['evidence_path'], hide_index=True, width='stretch')
    else:
        st.info('No downstream consumer exists for this object in the education fixture.')
    with st.expander('All checked education dependencies'):
        st.dataframe(education['relationships'], hide_index=True, width='stretch')
    st.download_button('Download cross-file validation report', json.dumps(education, indent=2),
                       file_name=f'education_impact_{education_object}.json', mime='application/json')
