"""No-cost rule-based preview of the same guarded workflow used by the live CLI."""
import hashlib
import json
import streamlit as st
from src.impact import ROOT
from src.review_agent import DEMO, run_review


def render_review():
    with st.expander("BI Change Review Agent — offline planning baseline"):
        st.caption("Rule-based intent recognition; no model call. One verified analysis attempt. "
                   "Optional model planning is available only through the local CLI.")
        question = st.text_input("Your change-review question",
            value="Which downstream views depend on orders?", max_chars=1000,
            key="review_question")
        st.caption("Use one exact retail object name. Include direct or indirect to narrow the review.")
        try:
            inputs = [DEMO, ROOT / "examples/expected_dependencies.json",
                      ROOT / "examples/expected_impacts.json"]
            fingerprint = hashlib.sha256(b"".join(path.read_bytes() for path in inputs)).hexdigest()
            identity = (question, fingerprint)
        except OSError:
            identity = None
            st.error("Review evidence or references are unavailable.")
        if st.button("Plan and verify review", key="review_run", disabled=identity is None):
            st.session_state.pop("review_result", None)
            st.session_state["review_result"] = (identity, run_review(question))
        stored = st.session_state.get("review_result")
        if identity is None or stored is None or stored[0] != identity:
            return
        receipt = stored[1]
        if receipt["status"] not in {"completed", "no_consumers"}:
            st.warning("Review stopped: " + receipt["status"] +
                       ". Ask a read-only impact question about one supported object.")
            return
        st.json(receipt["plan"])
        report = receipt["report"]
        if report["potentially_affected"]:
            for hit in report["potentially_affected"]:
                st.write(f"Review {hit['object']} ({hit['depth']} hop(s)).")
                st.dataframe(hit["evidence_path"], hide_index=True, width="stretch")
        else:
            st.info("No consumers match this scope in the fixture; this is not proof of no external impact.")
        st.code(report["recovered_sql"], language="sql", line_numbers=True)
        st.caption("Source locations refer to this recovered SQL. Potential impact requires human review.")
        st.download_button("Download change-review receipt", json.dumps(receipt, indent=2),
            file_name="change_review.json", mime="application/json", key="review_download")
