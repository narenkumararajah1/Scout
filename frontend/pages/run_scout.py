"""Run Scout - trigger a workflow run and view its status.

A thin HTTP client of the FastAPI backend: no workflow logic lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Scout")
st.caption("AI-powered sales intelligence platform")

st.subheader("Backend Status")
try:
    health = requests.get(f"{BACKEND_URL}/health", timeout=5)
    health.raise_for_status()
    st.success(f"Connected to FastAPI backend at {BACKEND_URL}")
    st.json(health.json())
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))

st.divider()
st.subheader("Run Scout")

if st.button("Run Scout", type="primary"):
    with st.spinner("Running the Scout workflow..."):
        try:
            response = requests.post(f"{BACKEND_URL}/workflow/run", timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            st.session_state["last_workflow_run_error"] = str(exc)
            st.session_state.pop("last_workflow_state", None)
        else:
            st.session_state["last_workflow_state"] = response.json()
            st.session_state.pop("last_workflow_run_error", None)

st.subheader("Workflow Status")

run_error = st.session_state.get("last_workflow_run_error")
state = st.session_state.get("last_workflow_state")

if run_error:
    st.error(f"Could not reach the backend to run the workflow: {run_error}")
elif state:
    status = state["status"]
    if status == "completed":
        st.success(f"Status: {status}")
    elif status == "failed":
        st.error(f"Status: {status}")
    else:
        st.info(f"Status: {status}")

    st.write("**Completed stages:**")
    for stage in state["completed_stages"]:
        st.write(f"- {stage}")

    if state["errors"]:
        st.warning("**Errors:**")
        for error in state["errors"]:
            st.write(f"- {error}")

    with st.expander("Full workflow state"):
        st.json(state)
else:
    st.caption("No workflow has been run yet.")
