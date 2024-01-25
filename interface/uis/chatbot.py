import datetime

import requests
import streamlit as st

from app.answerer.chats import ChatType
from app.answerer.push.messages import MESSAGE_WELCOME
from app.answerer.schemas import AnswerOutput
from app.db.enums import AnswerType
from app.db.schemas import BusinessInDB, UserInDB
from app.utils.conversation_utils import streamlit_to_langchain_conversation
from interface.backend import FASTAPI_URL
from interface.utils.schemas import ChatbotInput

MESSAGE_START_CHAT = """👉 Clicca su "invia" per iniziare chat"""


def ui() -> None:
    st.title("Weeklend 🤖")

    if "init_chatbot" not in st.session_state:
        st.session_state["init_chatbot"] = True
        st.session_state["messages"] = []
        st.session_state["last_answer_ai"] = False

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
        pending_event_id = 0 if st.session_state["last_answer_ai"] else None

    else:
        col1, col2 = st.columns(2)
        start_chat_message = col1.text_input(
            "Start chat message", value=MESSAGE_START_CHAT, label_visibility="collapsed"
        )
        if col2.button("Welcome message", use_container_width=True):
            st.session_state["messages"] += [
                {"role": "user", "content": start_chat_message},
                {"role": "assistant", "content": MESSAGE_WELCOME},
            ]

        user = UserInDB(
            id=-9,
            phone_number="999999999999",
            is_blocked=False,
            registered_at=datetime.datetime.now(),
        )
        pending_event_id = None

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
                    pending_event_id=pending_event_id,
                ).json(),
            )
            answer_out = AnswerOutput(**response.json())

            st.session_state["last_answer_ai"] = answer_out.type == AnswerType.ai

        st.chat_message("assistant").markdown(answer_out.answer)
        st.session_state["messages"] += [
            {"role": "user", "content": user_query},
            {"role": "assistant", "content": answer_out.answer},
        ]
