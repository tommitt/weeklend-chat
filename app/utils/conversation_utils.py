from app.db.enums import AnswerType
from app.db.models import BusinessConversationORM, ConversationORM


def db_to_langchain_conversation(
    db_conversations: list[ConversationORM | BusinessConversationORM],
) -> list[tuple[str, str]]:
    conversation = []
    for db_conversation in db_conversations:
        conversation.append(("human", db_conversation.from_message))
        if db_conversation.answer_type != AnswerType.unanswered:
            conversation.append(("ai", db_conversation.to_message))
    return conversation


def streamlit_to_langchain_conversation(messages: list[dict]) -> list[tuple]:
    conversation = []
    for message in messages:
        conversation.append((message["role"], message["content"]))
    return conversation
