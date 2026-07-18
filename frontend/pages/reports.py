"""Reports & History - executive reports, LinkedIn drafts, run history,
and simple execution analytics.

A thin HTTP client of the FastAPI backend: history and content are fetched
as-is and rendered here; no aggregation beyond simple display-side counts
over already-fetched data.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Reports & History")
st.caption("Executive reports, LinkedIn drafts, run history, and execution analytics.")

try:
    response = requests.get(f"{BACKEND_URL}/workflow/history", timeout=10)
    response.raise_for_status()
    history = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    history = []

if not history:
    st.info("No workflow has been run yet. Run Scout from the Run Scout page first.")
else:
    latest = history[0]

    st.subheader("Latest Executive Report")
    content_output = latest.get("content_output")
    if content_output:
        st.write(f"**Target company:** {content_output.get('target_company', 'Unknown')}")
        st.write("**Executive Summary**")
        st.write(content_output.get("executive_summary", "N/A"))
        st.write("**Opportunity Summary**")
        st.write(content_output.get("opportunity_summary", "N/A"))
        st.write("**Recommended Next Steps**")
        st.write(content_output.get("recommended_next_steps", "N/A"))

        with st.expander("LinkedIn Post Draft"):
            st.write(content_output.get("linkedin_post", "N/A"))
        with st.expander("Infographic Prompt"):
            st.write(content_output.get("infographic_prompt", "N/A"))
    else:
        st.caption("No content was generated for the most recent run.")

    st.divider()
    st.subheader("Execution Analytics")

    total_runs = len(history)
    completed_runs = sum(1 for run in history if run["status"] == "completed")
    failed_runs = sum(1 for run in history if run["status"] == "failed")
    success_rate = f"{(completed_runs / total_runs) * 100:.0f}%" if total_runs else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recent Runs", total_runs)
    col2.metric("Completed", completed_runs)
    col3.metric("Failed", failed_runs)
    col4.metric("Success Rate", success_rate)

    st.divider()
    st.subheader("Workflow History")
    st.caption("Most recent runs first. Persisted in SQLite - survives backend restarts.")

    history_rows = [
        {
            "Workflow ID": run["workflow_id"][:8],
            "Status": run["status"],
            "Target Company": run.get("target_company") or "N/A",
            "Completed Stages": len(run["completed_stages"]),
            "Errors": len(run["errors"]),
            "Created At": run["created_at"],
        }
        for run in history
    ]
    st.dataframe(history_rows, use_container_width=True, hide_index=True)
