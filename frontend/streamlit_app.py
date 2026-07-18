"""Streamlit dashboard entry point - defines navigation only.

Page content lives under frontend/pages/. No business logic lives here
or in any page: all state and processing belong to the FastAPI backend;
Streamlit only renders data returned by its API.
"""

import streamlit as st

st.set_page_config(page_title="Scout", layout="wide")

pages = [
    st.Page("pages/run_scout.py", title="Run Scout", icon=":material/play_arrow:"),
    st.Page("pages/companies.py", title="Companies", icon=":material/apartment:"),
    st.Page("pages/intelligence.py", title="Intelligence", icon=":material/insights:"),
    st.Page("pages/reports.py", title="Reports & History", icon=":material/description:"),
]

navigation = st.navigation(pages)
navigation.run()
