"""Companies - manage monitored companies (V2 Phase 3, FR-002).

A thin HTTP client of the FastAPI backend: no company management logic
lives here, only display, user interaction, and workflow initiation
(docs/V2/IMPLEMENTATION_RULES.md Dashboard Rules).
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Companies")
st.caption("Add, remove, and manage monitoring for companies Scout tracks.")

st.subheader("Add Company")
with st.form("add_company_form", clear_on_submit=True):
    name = st.text_input("Name*")
    industry = st.text_input("Industry")
    headquarters = st.text_input("Headquarters")
    website = st.text_input("Website")
    submitted = st.form_submit_button("Add Company")

    if submitted:
        if not name.strip():
            st.error("Name is required.")
        else:
            try:
                response = requests.post(
                    f"{BACKEND_URL}/companies",
                    json={
                        "name": name,
                        "industry": industry or None,
                        "headquarters": headquarters or None,
                        "website": website or None,
                    },
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                st.error(f"Could not add company: {exc}")
            else:
                st.success(f"Added {name}.")

st.divider()
st.subheader("Monitored Companies")

try:
    response = requests.get(f"{BACKEND_URL}/companies", timeout=10)
    response.raise_for_status()
    companies = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    companies = []

if not companies:
    st.info("No companies added yet. Add one above.")
else:
    for company in companies:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{company['name']}**")
                details = ", ".join(
                    filter(None, [company.get("industry"), company.get("headquarters")])
                )
                if details:
                    st.caption(details)
            with col2:
                status = company["monitoring_status"]
                if status == "enabled":
                    st.success(status)
                else:
                    st.warning(status)
            with col3:
                if status == "enabled":
                    if st.button("Disable", key=f"disable_{company['id']}"):
                        requests.post(f"{BACKEND_URL}/companies/{company['id']}/disable", timeout=10)
                        st.rerun()
                else:
                    if st.button("Enable", key=f"enable_{company['id']}"):
                        requests.post(f"{BACKEND_URL}/companies/{company['id']}/enable", timeout=10)
                        st.rerun()
            with col4:
                if st.button("Remove", key=f"remove_{company['id']}"):
                    delete_response = requests.delete(f"{BACKEND_URL}/companies/{company['id']}", timeout=10)
                    if delete_response.status_code == 409:
                        st.error(delete_response.json().get("detail", "Cannot remove this company."))
                    else:
                        st.rerun()
