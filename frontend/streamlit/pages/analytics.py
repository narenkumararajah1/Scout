"""Analytics - company trends and cross-company opportunity rankings
(V2 Phase 9, FR-017).

A thin HTTP client of the FastAPI backend: no aggregation logic lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Analytics")
st.caption("Opportunity rankings and per-company historical trends.")

st.subheader("Top Opportunities")
try:
    response = requests.get(f"{BACKEND_URL}/analytics/opportunities", timeout=10)
    response.raise_for_status()
    opportunities = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    opportunities = []

if not opportunities:
    st.caption("No opportunities generated yet.")
else:
    rows = [
        {
            "Title": opportunity["title"],
            "Priority": opportunity.get("priority"),
            "Confidence": opportunity.get("confidence_score"),
            "Company ID": opportunity["company_id"][:8],
        }
        for opportunity in opportunities
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Company Trends")

try:
    companies_response = requests.get(f"{BACKEND_URL}/companies", timeout=10)
    companies_response.raise_for_status()
    companies = companies_response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    companies = []

if not companies:
    st.info("No companies added yet.")
else:
    options = {company["name"]: company["id"] for company in companies}
    selected_name = st.selectbox("Company", options.keys())
    selected_id = options[selected_name]

    try:
        trends_response = requests.get(
            f"{BACKEND_URL}/analytics/companies/{selected_id}/trends", timeout=10
        )
        trends_response.raise_for_status()
        trends = trends_response.json()
    except requests.RequestException as exc:
        st.error(f"Could not load trends for {selected_name}")
        st.caption(str(exc))
        trends = None

    if trends:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Research Sessions", trends["research_session_count"])
        col2.metric("Opportunities", trends["opportunity_count"])
        col3.metric("Reports", trends["report_count"])
        avg_confidence = trends.get("average_opportunity_confidence")
        col4.metric("Avg. Confidence", f"{avg_confidence:.2f}" if avg_confidence is not None else "N/A")

        st.write("**Top Opportunities**")
        top_opportunities = trends.get("top_opportunities") or []
        if not top_opportunities:
            st.caption("No opportunities yet.")
        else:
            for opportunity in top_opportunities:
                st.write(
                    f"- {opportunity['title']} (priority {opportunity.get('priority')}, "
                    f"confidence {opportunity.get('confidence_score')})"
                )
