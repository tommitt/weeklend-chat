import datetime

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools.render import format_tool_to_openai_tool
from sqlalchemy.orm import Session

from app.answerer.prompts import SYSTEM_PROMPT
from app.answerer.tools import search_events
from app.db.enums import AnswerType
from app.db.schemas import AnswerOutput
from app.utils.conn import get_llm, get_vectorstore, get_vectorstore_translator


class Answerer:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm()
        self.vectorstore = get_vectorstore()
        self.vectorstore_translator = get_vectorstore_translator()

    def run(self, user_query: str, today_date: datetime.date) -> AnswerOutput:
        # TODO: add previous conversations
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{user_query}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        tools = [search_events]

        agent = (
            {
                "user_query": lambda x: x["user_query"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                    x["intermediate_steps"]
                ),
            }
            | prompt
            | self.llm.bind(tools=[format_tool_to_openai_tool(tool) for tool in tools])
            | OpenAIToolsAgentOutputParser()
        )
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        agent_output = agent_executor.invoke({"user_query": user_query})

        return AnswerOutput(
            answer=agent_output["output"],
            type=AnswerType.ai,
            # TODO: get used_event_ids=json.dumps([])
        )
