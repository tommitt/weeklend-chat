import requests
import streamlit as st

from app.answerer.chats import ChatType
from app.answerer.schemas import AnswerOutput
from app.utils.conversation_utils import streamlit_to_langchain_conversation
from interface.backend import FASTAPI_URL
from interface.utils.schemas import ChatbotInput


def ui() -> None:
    st.title("Weeklend 🤖")

    if "init_chatbot" not in st.session_state:
        st.session_state["init_chatbot"] = True
        st.session_state["messages"] = []

    ref_date = st.date_input("Data di riferimento")
    chat_type = st.selectbox("Tipo di chat", options=[e.value for e in ChatType])

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("Chiedi qualcosa...")
    if user_query:
        st.chat_message("user").markdown(user_query)
        st.session_state["messages"].append({"role": "user", "content": user_query})

        with st.spinner("Sto pensando..."):
            response = requests.post(
                f"{FASTAPI_URL}/chatbot/{chat_type}",
                data=ChatbotInput(
                    user_query=user_query,
                    today_date=ref_date,
                    previous_conversation=streamlit_to_langchain_conversation(
                        st.session_state["messages"]
                    ),
                ).json(),
            )
            answer_out = AnswerOutput(**response.json())

        with st.chat_message("assistant"):
            st.markdown(answer_out.answer)
        st.session_state["messages"].append(
            {"role": "assistant", "content": answer_out.answer}
        )
