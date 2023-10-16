import requests
import streamlit as st

from app.loader.manual_insertion import GFORM_SUPPORTED_SOURCES
from app.loader.scraper import SCRAPER_SUPPORTED_SOURCES
from interface.backend import FASTAPI_URL


def ui() -> None:
    st.title("Weeklend 🎚️")

    st.divider()
    st.header("💾 Database")

    st.subheader("Scrapers")
    scraper_source = st.selectbox(
        "Source", options=SCRAPER_SUPPORTED_SOURCES, key="scraper_source"
    )
    if st.button("Run", use_container_width=True, key="scraper_run"):
        with st.spinner("Running..."):
            _ = requests.post(f"{FASTAPI_URL}/control_panel/scraper/{scraper_source}")

    st.subheader("GForm insertions")
    gform_source = st.selectbox(
        "Source", options=GFORM_SUPPORTED_SOURCES, key="gform_source"
    )
    if st.button("Run", use_container_width=True, key="gform_run"):
        with st.spinner("Running..."):
            _ = requests.post(f"{FASTAPI_URL}/control_panel/gform/{gform_source}")

    st.divider()

    st.header("🏪 Vectorstore")
    col1, col2 = st.columns(2)

    if col1.button(
        "Get from database",
        help="Get all non-vectorized events from database",
        use_container_width=True,
    ):
        events_name = requests.post(f"{FASTAPI_URL}/control_panel/loader/show").json()
    else:
        events_name = []
    st.table({"Name": events_name})

    if col2.button("Vectorize all", use_container_width=True):
        with st.spinner("Generating embeddings..."):
            _ = requests.post(f"{FASTAPI_URL}/control_panel/loader/vectorize")
