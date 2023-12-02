from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from sqlalchemy.orm import Session

from app.answerer.pull.prompts import SYSTEM_PROMPT
from app.answerer.schemas import AnswerOutput
from app.db.enums import AnswerType
from app.utils.conn import get_llm


class AiAgent:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm()
        self.set_tools()

    def set_tools(self) -> None:
        """
        Set tools for the llm to use:
        - None
        """
        pass

    def run(
        self, user_query: str, previous_conversation: list[tuple[str, str]] = []
    ) -> AnswerOutput:
        """Run AI agent on user query - it routes the LLM and tool calls."""
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT)]
            + previous_conversation
            + [("human", "{user_query}")]
        )
        chain = prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"user_query": user_query})
        return AnswerOutput(answer=answer, type=AnswerType.conversational)
