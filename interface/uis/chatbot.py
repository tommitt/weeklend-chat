import datetime

import requests
import streamlit as st

from app.answerer.chats import ChatType
from app.answerer.schemas import AnswerOutput
from app.db.schemas import BusinessInDB, UserInDB
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
    if chat_type == ChatType.pull:
        col1, col2 = st.columns(2)
        business_name = col1.text_input("Nome del Business")
        business_description = col2.text_input("Descrizione del Business")
        user = BusinessInDB(
            id=-9,
            phone_number="999999999999",
            registered_at=datetime.datetime.now(),
            name=None if business_name == "" else business_name,
            description=None if business_description == "" else business_description,
        )
    else:
        user = UserInDB(
            id=-9,
            phone_number="999999999999",
            is_blocked=False,
            registered_at=datetime.datetime.now(),
        )

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_query = st.chat_input("Chiedi qualcosa...")
    if user_query:
        st.chat_message("user").markdown(user_query)

        with st.spinner("Sto pensando..."):
            response = requests.post(
                f"{FASTAPI_URL}/chatbot/{chat_type}",
                data=ChatbotInput(
                    user_query=user_query,
                    today_date=ref_date,
                    previous_conversation=streamlit_to_langchain_conversation(
                        st.session_state["messages"]
                    ),
                    user=user,
                ).json(),
            )
            answer_out = AnswerOutput(**response.json())

        st.chat_message("assistant").markdown(answer_out.answer)
        st.session_state["messages"] += [
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": answer_out.answer},
        ]
