import requests
import streamlit as st

from app.loader.scraper import SUPPORTED_SOURCES
from interface.backend import FASTAPI_URL


def ui() -> None:
    st.title("Weeklend 🎚️")

    st.divider()

    st.header("Scraper")
    source = st.selectbox("Source", options=SUPPORTED_SOURCES)
    if st.button("Run scraper!", use_container_width=True):
        with st.spinner("Running scraper..."):
            _ = requests.post(f"{FASTAPI_URL}/control_panel/scraper/{source}")

    st.divider()

    st.header("Loader")
    col1, col2 = st.columns(2)

    if col1.button("Get non-vectorized events", use_container_width=True):
        events_name = requests.post(f"{FASTAPI_URL}/control_panel/loader/show").json()
    else:
        events_name = []
    st.table({"Name": events_name})

    if col2.button("Vectorize them!", use_container_width=True):
        with st.spinner("Generating embeddings..."):
            _ = requests.post(f"{FASTAPI_URL}/control_panel/loader/vectorize")
