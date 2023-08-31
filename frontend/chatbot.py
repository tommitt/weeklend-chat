import streamlit as st

from answerer.answerer import Answerer


def app() -> None:
    st.title("Weeklend 🤖")

    if "init" not in st.session_state:
        st.session_state["init"] = True
        st.session_state["messages"] = []
        st.session_state["answerer"] = Answerer()

    date = st.date_input("Data di “oggi”")
    st.divider()

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Chiedi qualcosa...")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        with st.spinner("Sto pensando..."):
            response = st.session_state["answerer"].run(prompt, date)

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state["messages"].append({"role": "assistant", "content": response})
