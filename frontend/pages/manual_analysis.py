"""Manual Analysis - run the full V2 intelligence pipeline for any
monitored company on demand (V2 Phase 9, FR-003).

A thin HTTP client of the FastAPI backend: no pipeline logic lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Manual Analysis")
st.caption("Run Research, Capability Matching, Opportunity Analysis, and Reporting for any company on demand.")

try:
    response = requests.get(f"{BACKEND_URL}/companies", timeout=10)
    response.raise_for_status()
    companies = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    companies = []

if not companies:
    st.info("No companies to analyze yet. Add one on the Companies page first.")
else:
    options = {company["name"]: company["id"] for company in companies}
    selected_name = st.selectbox("Company", options.keys())
    selected_id = options[selected_name]

    if st.button("Run Analysis", type="primary"):
        with st.spinner(f"Analyzing {selected_name} - this can take a minute..."):
            try:
                analyze_response = requests.post(
                    f"{BACKEND_URL}/companies/{selected_id}/analyze", timeout=300
                )
                analyze_response.raise_for_status()
            except requests.RequestException as exc:
                detail = None
                if exc.response is not None:
                    try:
                        detail = exc.response.json().get("detail")
                    except ValueError:
                        detail = exc.response.text
                st.session_state["manual_analysis_error"] = detail or str(exc)
                st.session_state.pop("manual_analysis_report", None)
            else:
                st.session_state["manual_analysis_report"] = analyze_response.json()
                st.session_state.pop("manual_analysis_error", None)

st.divider()

error = st.session_state.get("manual_analysis_error")
report = st.session_state.get("manual_analysis_report")

if error:
    st.error(f"Analysis failed: {error}")
elif report:
    st.subheader("Executive Summary")
    st.write(report.get("executive_summary", "N/A"))
    st.write("**Company Overview**")
    st.write(report.get("company_overview", "N/A"))
    st.write("**Key Findings**")
    st.write(report.get("key_findings", "N/A"))
    st.write("**Technology Analysis**")
    st.write(report.get("technology_analysis", "N/A"))
    st.write("**Capability Alignment**")
    st.write(report.get("capability_alignment", "N/A"))
    st.write("**Opportunities**")
    st.write(report.get("opportunities_section", "N/A"))
    st.write("**Recommendations**")
    st.write(report.get("recommendations", "N/A"))
    st.write("**Talking Points**")
    st.write(report.get("talking_points", "N/A"))
else:
    st.caption("No analysis run yet.")
