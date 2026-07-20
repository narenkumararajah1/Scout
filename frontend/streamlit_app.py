"""Streamlit dashboard entry point - defines navigation only.

Page content lives under frontend/pages/. No business logic lives here
or in any page: all state and processing belong to the FastAPI backend;
Streamlit only renders data returned by its API.
"""

import streamlit as st

st.set_page_config(page_title="Scout", layout="wide")

pages = {
    "Company Intelligence": [
        st.Page("pages/companies.py", title="Companies", icon=":material/apartment:"),
        st.Page("pages/manual_analysis.py", title="Manual Analysis", icon=":material/search:"),
        st.Page("pages/company_reports.py", title="Reports", icon=":material/summarize:"),
        st.Page("pages/analytics.py", title="Analytics", icon=":material/query_stats:"),
        st.Page("pages/ask_scout.py", title="Ask Scout", icon=":material/chat:"),
    ],
    "Administration": [
        st.Page("pages/recipients.py", title="Recipients", icon=":material/group:"),
        st.Page("pages/system_status.py", title="System Status", icon=":material/monitor_heart:"),
    ],
    "V1 Workflow": [
        st.Page("pages/run_scout.py", title="Run Scout", icon=":material/play_arrow:"),
        st.Page("pages/intelligence.py", title="Intelligence", icon=":material/insights:"),
        st.Page("pages/reports.py", title="Reports & History", icon=":material/description:"),
    ],
}

navigation = st.navigation(pages)
navigation.run()
