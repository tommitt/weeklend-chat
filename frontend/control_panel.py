import streamlit as st

from app.db.db import SessionLocal
from app.loader.loader import Loader
from app.loader.scraper import Scraper


def app():
    st.title("Weeklend 📊")

    if "init" not in st.session_state:
        st.session_state["init"] = True
        st.session_state["db"] = SessionLocal()
        st.session_state["scraper"] = Scraper(
            identifier="guidatorino", db=st.session_state["db"]
        )
        st.session_state["loader"] = Loader(db=st.session_state["db"])

    st.divider()

    st.header("Scraper")
    source = st.selectbox(
        "Source", options=st.session_state["scraper"]._supported_sources
    )
    if source != st.session_state["scraper"].identifier:
        st.session_state["scraper"] = Scraper(
            identifier=source, db=st.session_state["db"]
        )
    if st.button("Run scraper!", use_container_width=True):
        with st.spinner("Running scraper..."):
            st.session_state["scraper"].run()

    st.divider()

    st.header("Loader")
    col1, col2 = st.columns(2)

    if col1.button("Get non-vectorized events", use_container_width=True):
        st.session_state["loader"].get_not_vectorized_events()

    if col2.button("Vectorize them!", use_container_width=True):
        with st.spinner("Generating embeddings..."):
            st.session_state["loader"].vectorize_events()

    st.table({"Name": [e.name for e in st.session_state["loader"].events]})
