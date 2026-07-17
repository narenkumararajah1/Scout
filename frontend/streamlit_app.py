"""Streamlit dashboard - a thin client that talks to the FastAPI backend over HTTP.

No business logic lives here. All state and processing belong to the
FastAPI backend; this file only renders data returned by its API.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Scout", layout="wide")
st.title("Scout")
st.caption("AI-powered sales intelligence platform")

st.subheader("Backend Status")

try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    response.raise_for_status()
    st.success(f"Connected to FastAPI backend at {BACKEND_URL}")
    st.json(response.json())
except requests.RequestException as exc:
    st.error(f"Could not reach FastAPI backend at {BACKEND_URL}")
    st.caption(str(exc))
