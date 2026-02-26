"""
Streamlit Dashboard — Track your job applications
Deploy free on: Hugging Face Spaces or Streamlit Community Cloud
Run locally: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Job Agent Dashboard",
    page_icon="🤖",
    layout="wide",
)

DB_PATH = "data/jobs.db"


@st.cache_data(ttl=30)
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM jobs ORDER BY created_at DESC", conn)
        runs = pd.read_sql("SELECT * FROM runs ORDER BY run_at DESC LIMIT 30", conn)
        conn.close()
        return df, runs
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame(), pd.DataFrame()


st.title("🤖 Autonomous Job Agent Dashboard")
st.caption("Tracks every job your agent found, scored, and applied to.")

df, runs = load_data()

if df.empty:
    st.info("No data yet. Run `python main.py` first!")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📋 Total Found", len(df))
col2.metric("🎯 Matched", len(df[df["match_score"] >= 0.42]))
col3.metric("✅ Applied", len(df[df["status"].isin(["submitted", "applied"])]))
col4.metric("Pending", len(df[df["status"] == "notified"]))
col5.metric("Avg Match", f"{df['match_score'].mean()*100:.0f}%" if len(df) > 0 else "N/A")

st.divider()

col_a, col_b, col_c = st.columns(3)
with col_a:
    status_filter = st.multiselect("Filter by Status", options=df["status"].unique().tolist(), default=df["status"].unique().tolist())
with col_b:
    source_filter = st.multiselect("Filter by Source", options=df["source"].unique().tolist(), default=df["source"].unique().tolist())
with col_c:
    min_score = st.slider("Min Match Score", 0, 100, 40)

filtered = df[
    df["status"].isin(status_filter) &
    df["source"].isin(source_filter) &
    (df["match_score"] * 100 >= min_score)
]

st.subheader(f"📋 Jobs ({len(filtered)})")
display_cols = ["title", "company", "location", "match_score", "source", "status", "created_at"]
available_cols = [c for c in display_cols if c in filtered.columns]
styled = filtered[available_cols].copy()
styled["match_score"] = (styled["match_score"] * 100).round(1).astype(str) + "%"
st.dataframe(styled, use_container_width=True, height=400)

st.subheader("🔍 Job Detail")
job_options = filtered["title"] + " @ " + filtered["company"]
if len(job_options) > 0:
    selected = st.selectbox("Select a job", job_options)
    if selected:
        idx = job_options[job_options == selected].index[0]
        job = filtered.loc[idx]
        col_l, col_r = st.columns([1, 2])
        with col_l:
            st.markdown(f"**Company:** {job.get('company', 'N/A')}")
            st.markdown(f"**Location:** {job.get('location', 'N/A')}")
            st.markdown(f"**Match Score:** {job.get('match_score', 'N/A')}")
            st.markdown(f"**Status:** `{job.get('status', 'N/A')}`")
            st.markdown(f"[🔗 View Job]({job.get('url', '#')})")
        with col_r:
            tab1, tab2 = st.tabs(["Cover Letter", "Resume Summary"])
            with tab1:
                st.text_area("Cover Letter", job.get("cover_letter", "Not generated"), height=300)
            with tab2:
                st.text_area("Resume Summary", job.get("resume_summary", "Not generated"), height=150)

st.divider()
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.subheader("Status Breakdown")
    st.bar_chart(df["status"].value_counts())
with col_c2:
    st.subheader("Source Breakdown")
    st.bar_chart(df["source"].value_counts())

if not runs.empty:
    st.divider()
    st.subheader("Agent Run History")
    st.dataframe(runs, use_container_width=True)
