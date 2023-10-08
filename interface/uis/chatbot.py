import requests
import streamlit as st

from interface.backend import FASTAPI_URL


def ui() -> None:
    st.title("Weeklend 🤖")

    if "init_chatbot" not in st.session_state:
        st.session_state["init_chatbot"] = True
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": "Ciao Weeklender! 👋🏻\nVuoi consigli su cosa fare a Torino?",
            }
        ]

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("Chiedi qualcosa...")
    if user_query:
        st.chat_message("user").markdown(user_query)
        st.session_state["messages"].append({"role": "user", "content": user_query})

        with st.spinner("Sto pensando..."):
            response = requests.post(
                f"{FASTAPI_URL}/chatbot",
                params={"user_query": user_query},
            ).json()

        with st.chat_message("assistant"):
            st.markdown(response["answer"])
        st.session_state["messages"].append(
            {"role": "assistant", "content": response["answer"]}
        )
