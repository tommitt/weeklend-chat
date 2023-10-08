import requests
import streamlit as st

from interface.backend import FASTAPI_URL


def ui() -> None:
    st.title("Weeklend 📊")

    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start date")
    end_date = col2.date_input("End date")

    if st.button("Get stats"):
        response = requests.post(
            f"{FASTAPI_URL}/dashboard",
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        ).json()
        st.write(response)
