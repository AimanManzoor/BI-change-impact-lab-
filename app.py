"""Local interactive explorer for the verified synthetic SQL fixture."""
import json
import streamlit as st
from src.impact import ROOT, extract_fixture, verify_fixture
from src.harness import run_harness
from src.graphrag import answer_question


st.set_page_config(page_title='BI Change Impact Lab', layout='wide')
st.title('BI Change Impact Lab')
st.write('Explore how a SQL change could flow into dependent views.')
st.caption('Synthetic retail example only. Powered by Graphify. No AI calls or live database access.')

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
question_labels = {'All downstream views': 'all', 'Direct downstream views': 'direct',
                   'Indirect downstream views': 'indirect'}
question_label = st.radio('Which impacts should the answer cover?', list(question_labels), key='gr_kind')
question_kind = question_labels[question_label]
answer_key = (selected, question_kind, receipt['source_sha256'])
if st.button('Retrieve graph-grounded answer', key='gr_answer'):
    st.session_state['gr_result'] = (answer_key, answer_question(selected, question_kind, result=result))
stored = st.session_state.get('gr_result')
if stored is not None and stored[0] == answer_key:
    grounded = stored[1]
    if grounded['status'] in {'completed', 'no_context'}:
        st.markdown(grounded['answer'])
        if grounded['context']['evidence']:
            st.dataframe(grounded['context']['evidence'], hide_index=True, width='stretch')
        st.download_button('Download graph-grounded answer', json.dumps(grounded, indent=2),
                           file_name=f'graph_answer_{selected}_{question_kind}.json', mime='application/json')
    else:
        st.error('The graph-grounded answer could not be verified. No answer is displayed.')
