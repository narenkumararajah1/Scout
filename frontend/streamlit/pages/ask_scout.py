"""Ask Scout - conversational access to Scout's existing intelligence
(V2 Phase 11, FR-018).

A thin HTTP client of the FastAPI backend: no retrieval or LLM logic
lives here. Conversation history is kept in Streamlit session state only
- DATA_MODEL.md defines no persisted "Conversation" entity, since this
interface answers from already-persisted intelligence rather than
creating new business records.
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.title("Ask Scout")
st.caption(
    "Ask questions about companies Scout has researched. Answers come from Scout's "
    "existing intelligence only - no new research is performed."
)

if "conversation_history" not in st.session_state:
    st.session_state["conversation_history"] = []

with st.form("ask_scout_form", clear_on_submit=True):
    question = st.text_input("Question", placeholder="e.g. Which companies are investing in AI?")
    submitted = st.form_submit_button("Ask")

    if submitted:
        if not question.strip():
            st.error("Enter a question.")
        else:
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/conversation/ask", json={"question": question}, timeout=60
                    )
                    response.raise_for_status()
                except requests.RequestException as exc:
                    detail = None
                    if exc.response is not None:
                        try:
                            detail = exc.response.json().get("detail")
                        except ValueError:
                            detail = exc.response.text
                    st.session_state["conversation_history"].append(
                        {"question": question, "answer": None, "error": detail or str(exc)}
                    )
                else:
                    answer = response.json()["answer"]
                    st.session_state["conversation_history"].append(
                        {"question": question, "answer": answer, "error": None}
                    )

st.divider()

if not st.session_state["conversation_history"]:
    st.caption("No questions asked yet.")
else:
    for entry in reversed(st.session_state["conversation_history"]):
        with st.container(border=True):
            st.write(f"**Q:** {entry['question']}")
            if entry["error"]:
                st.error(f"Could not get an answer: {entry['error']}")
            else:
                st.write(f"**A:** {entry['answer']}")
