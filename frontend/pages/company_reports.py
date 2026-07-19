"""Reports - browse historical V2 executive reports per company
(V2 Phase 9, FR-014).

A thin HTTP client of the FastAPI backend: no aggregation logic lives
here. Distinct from V1's "Reports & History" page (frontend/pages/reports.py),
which still shows V1's single-run workflow history unchanged.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Reports")
st.caption("Historical executive reports generated for monitored companies.")

try:
    response = requests.get(f"{BACKEND_URL}/companies", timeout=10)
    response.raise_for_status()
    companies = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    companies = []

if not companies:
    st.info("No companies added yet. Add one on the Companies page first.")
else:
    options = {company["name"]: company["id"] for company in companies}
    selected_name = st.selectbox("Company", options.keys())
    selected_id = options[selected_name]

    try:
        reports_response = requests.get(f"{BACKEND_URL}/companies/{selected_id}/reports", timeout=10)
        reports_response.raise_for_status()
        reports = reports_response.json()
    except requests.RequestException as exc:
        st.error(f"Could not load reports for {selected_name}")
        st.caption(str(exc))
        reports = []

    if not reports:
        st.info(f"No reports yet for {selected_name}. Run Manual Analysis to generate one.")
    else:
        labels = [report["created_at"] for report in reports]
        selected_index = st.selectbox("Report", range(len(reports)), format_func=lambda i: labels[i])
        report = reports[selected_index]

        st.subheader("Executive Summary")
        st.write(report.get("executive_summary", "N/A"))
        with st.expander("Company Overview"):
            st.write(report.get("company_overview", "N/A"))
        with st.expander("Key Findings"):
            st.write(report.get("key_findings", "N/A"))
        with st.expander("Technology Analysis"):
            st.write(report.get("technology_analysis", "N/A"))
        with st.expander("Capability Alignment"):
            st.write(report.get("capability_alignment", "N/A"))
        with st.expander("Opportunities"):
            st.write(report.get("opportunities_section", "N/A"))
        with st.expander("Recommendations"):
            st.write(report.get("recommendations", "N/A"))
        with st.expander("Talking Points"):
            st.write(report.get("talking_points", "N/A"))

        st.divider()
        st.subheader("Distribution")

        if st.button("Distribute Report", type="primary"):
            with st.spinner("Sending to eligible recipients..."):
                try:
                    distribute_response = requests.post(
                        f"{BACKEND_URL}/reports/{report['id']}/distribute", timeout=30
                    )
                    distribute_response.raise_for_status()
                except requests.RequestException as exc:
                    st.error(f"Could not distribute report: {exc}")
                else:
                    st.session_state["last_distribution"] = distribute_response.json()

        try:
            deliveries_response = requests.get(
                f"{BACKEND_URL}/reports/{report['id']}/deliveries", timeout=10
            )
            deliveries_response.raise_for_status()
            deliveries = deliveries_response.json()
        except requests.RequestException as exc:
            st.error("Could not load delivery history for this report.")
            st.caption(str(exc))
            deliveries = []

        if not deliveries:
            st.caption("No deliveries yet for this report.")
        else:
            status_icon = {"sent": "✅", "skipped": "⚠️", "failed": "❌"}
            rows = [
                {
                    "Recipient ID": delivery["recipient_id"][:8],
                    "Channel": delivery["channel"],
                    "Status": f"{status_icon.get(delivery['status'], '')} {delivery['status']}",
                    "Delivery Time": delivery["delivery_time"],
                }
                for delivery in deliveries
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
