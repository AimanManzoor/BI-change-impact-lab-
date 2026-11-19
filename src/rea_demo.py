"""Browser demo over a bundled synthetic schema; no live REA process."""
import json
import streamlit as st
from src.impact import ROOT
from src.rea_check import check_evidence

DEMO = ROOT / "examples/rea/retail_schema.json"
OBJECTS = [
    "customers", "orders", "order_summary",
    "regional_sales", "customer_directory",
]


def render_rea_demo():
    with st.expander("REA: explore a recovered database schema"):
        st.caption(
            "Bundled synthetic schema exported from a local REA inspection. "
            "No Node.js, live database connection, uploads, or model calls. "
            "This section is independent of the selectors above."
        )

        if not st.checkbox(
            "Explore the bundled REA example", key="rea_enabled"
        ):
            return

        selected = st.selectbox(
            "Which recovered object might change?",
            OBJECTS, index=1, key="rea_object",
        )

        try:
            report = check_evidence(DEMO, object_name=selected)
        except (ValueError, OSError, KeyError, TypeError):
            st.error(
                "REA demo verification failed. No impact report is displayed."
            )
            return

        st.success(
            "Verified 5 objects and 4 dependency pairs against the retail reference."
        )

        total, direct, indirect = st.columns(3)
        total.metric(
            "REA: potentially affected views",
            len(report["potentially_affected"]),
        )
        direct.metric("REA: direct consumers", report["direct_count"])
        indirect.metric("REA: indirect consumers", report["indirect_count"])

        st.caption(
            "Potential impact is not confirmed breakage. Human review is required."
        )

        for hit in report["potentially_affected"]:
            st.write(f"{hit['object']} — {hit['depth']} hop(s)")
            st.dataframe(
                hit["evidence_path"], hide_index=True, width="stretch"
            )

        if not report["potentially_affected"]:
            st.info(
                "No downstream consumers exist for this object "
                "in the bundled REA fixture."
            )

        st.code(report["recovered_sql"], language="sql", line_numbers=True)
        st.caption(
            "Evidence locations refer to the recovered SQL shown above."
        )

        st.download_button(
            "Download REA demo report",
            json.dumps(report, indent=2),
            file_name=f"rea_impact_{selected}.json",
            mime="application/json",
            key="rea_download",
        )
