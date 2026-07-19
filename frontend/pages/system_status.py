"""System Status - scheduler, health, and recent workflow runs
(V2 Phase 9, FR-017).

A thin HTTP client of the FastAPI backend: no monitoring logic lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("System Status")
st.caption("Scheduler, health, and recent workflow run history.")

try:
    response = requests.get(f"{BACKEND_URL}/system/status", timeout=10)
    response.raise_for_status()
    status = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    status = None

if status:
    st.subheader("Health")
    health = status["health"]
    if health["status"] == "ok":
        st.success(f"Status: {health['status']}")
    else:
        st.warning(f"Status: {health['status']}")
    col1, col2 = st.columns(2)
    col1.metric("Database", "Connected" if health["database_connected"] else "Disconnected")
    col2.metric("ChromaDB", "Connected" if health["chroma_connected"] else "Disconnected")

    st.divider()
    st.subheader("Scheduler")
    scheduler = status["scheduler"]
    if scheduler["running"]:
        st.success("Scheduler is running.")
    else:
        st.warning("Scheduler is not running.")
    st.write(f"**Interval:** every {scheduler['interval_hours']} hour(s)")
    st.write(f"**Next run:** {scheduler.get('next_run_time') or 'unknown'}")

st.divider()
st.subheader("Recent Workflow Runs")

try:
    history_response = requests.get(f"{BACKEND_URL}/workflow/history", timeout=10)
    history_response.raise_for_status()
    history = history_response.json()
except requests.RequestException as exc:
    st.error("Could not load workflow history.")
    st.caption(str(exc))
    history = []

if not history:
    st.caption("No workflow runs yet.")
else:
    rows = [
        {
            "Workflow ID": run["workflow_id"][:8],
            "Status": run["status"],
            "Target Company": run.get("target_company") or "N/A",
            "Created At": run["created_at"],
        }
        for run in history[:10]
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
