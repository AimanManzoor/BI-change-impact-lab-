"""Local interactive explorer for the verified synthetic SQL fixture."""
import json
import streamlit as st
from src.impact import ROOT, extract_fixture, verify_fixture, build_report


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
try:
    report = build_report(result, selected)
except ValueError as exc:
    st.error(f'Could not verify the impact report. {exc}')
    st.stop()

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
st.caption('Four dependency pairs checked against a manually specified reference. No column-level lineage, DAX, or Power BI report mapping yet.')
