"""Recipients - manage report distribution recipients and preferences
(V2 Phase 9, FR-016).

A thin HTTP client of the FastAPI backend: no recipient management logic
lives here.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Recipients")
st.caption("Manage who receives Scout's executive reports and how often.")

st.subheader("Add Recipient")
with st.form("add_recipient_form", clear_on_submit=True):
    name = st.text_input("Name*")
    email = st.text_input("Email*")
    frequency = st.selectbox("Preferred Frequency", ["daily", "weekly"], index=0)
    channels = st.multiselect("Preferred Channels", ["email", "teams"], default=["email"])
    submitted = st.form_submit_button("Add Recipient")

    if submitted:
        if not name.strip() or not email.strip():
            st.error("Name and email are required.")
        else:
            try:
                response = requests.post(
                    f"{BACKEND_URL}/recipients",
                    json={
                        "name": name,
                        "email": email,
                        "preferred_frequency": frequency,
                        "preferred_channels": channels,
                    },
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                st.error(f"Could not add recipient: {exc}")
            else:
                st.success(f"Added {name}.")

st.divider()
st.subheader("Recipients")

try:
    response = requests.get(f"{BACKEND_URL}/recipients", timeout=10)
    response.raise_for_status()
    recipients = response.json()
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
    recipients = []

if not recipients:
    st.info("No recipients added yet.")
else:
    for recipient in recipients:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{recipient['name']}**")
                st.caption(f"{recipient['email']} - {recipient.get('preferred_frequency') or 'no frequency set'}")
            with col2:
                status = recipient.get("delivery_status") or "enabled"
                if status == "enabled":
                    st.success(status)
                else:
                    st.warning(status)
            with col3:
                if status == "enabled":
                    if st.button("Disable", key=f"disable_{recipient['id']}"):
                        requests.post(f"{BACKEND_URL}/recipients/{recipient['id']}/disable", timeout=10)
                        st.rerun()
                else:
                    if st.button("Enable", key=f"enable_{recipient['id']}"):
                        requests.post(f"{BACKEND_URL}/recipients/{recipient['id']}/enable", timeout=10)
                        st.rerun()
            with col4:
                if st.button("Remove", key=f"remove_{recipient['id']}"):
                    requests.delete(f"{BACKEND_URL}/recipients/{recipient['id']}", timeout=10)
                    st.rerun()
