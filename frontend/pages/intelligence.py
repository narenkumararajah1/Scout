"""Intelligence - research summaries and scored opportunities from the
most recent Scout run.

A thin HTTP client of the FastAPI backend: no analysis logic lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Intelligence")
st.caption("Research summaries and business opportunities from the most recent Scout run.")

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
    st.caption(f"Showing results from run `{latest['workflow_id']}` ({latest['status']}).")

    research_output = latest.get("research_output")
    st.subheader("Research Summary")
    if research_output:
        st.write(f"**Target company:** {research_output.get('target_company', 'Unknown')}")
        st.write(research_output.get("unified_research", "No unified research available."))
        with st.expander("Raw research sources"):
            sources = research_output.get("sources", {})
            st.write("**Business Research**")
            st.write(sources.get("business_research", "N/A"))
            st.write("**Social Intelligence**")
            st.write(sources.get("social_intelligence", "N/A"))
    else:
        st.caption("No research available for this run.")

    st.divider()
    st.subheader("Opportunities")
    opportunity_output = latest.get("opportunity_output")
    opportunities = (opportunity_output or {}).get("opportunities") or []
    if not opportunities:
        st.caption("No opportunities available for this run.")
    else:
        for opportunity in opportunities:
            title = f"{opportunity.get('name', 'Untitled')} — score {opportunity.get('score', '?')}/10"
            with st.expander(title, expanded=True):
                st.write(opportunity.get("description", ""))

                matched_services = opportunity.get("matched_services") or []
                if matched_services:
                    st.write("**Matched services:**")
                    for service in matched_services:
                        st.write(f"- {service}")
                else:
                    st.caption("No matched services.")

                if opportunity.get("reasoning"):
                    st.write(f"**Reasoning:** {opportunity['reasoning']}")

                if opportunity.get("recommendation"):
                    st.write(f"**Recommendation:** {opportunity['recommendation']}")

                talking_points = opportunity.get("talking_points") or []
                if talking_points:
                    st.write("**Talking points:**")
                    for point in talking_points:
                        st.write(f"- {point}")
