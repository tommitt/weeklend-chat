import datetime

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from langchain.tools.render import format_tool_to_openai_tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.answerer.pull.prompts import (
    REGISTER_EVENT_TOOL_DESCRIPTION,
    REGISTER_PLACE_TOOL_DESCRIPTION,
    SYSTEM_PROMPT,
)
from app.answerer.schemas import AnswerOutput
from app.db.enums import AnswerType
from app.utils.conn import get_llm


class RegisterEventToolInput(BaseModel):
    name: str = Field(description="The name of the event")
    description: str = Field(description="The description of the event")
    url: str = Field(description="External URL linking to the website")
    start_date: datetime.date = Field(description="The start date of the event")
    end_date: datetime.date = Field(description="The end date of the event")


class RegisterPlaceToolInput(BaseModel):
    name: str = Field(description="The name of the place")
    description: str = Field(description="The description of the place")
    url: str = Field(description="External URL linking to the website")
    closing_days: list[int] = Field(
        description="Week days when the place is closed. Monday is 1, Sunday is 7."
    )


class AiAgent:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm()
        self.set_tools()

    def register_event(
        self,
        name: str,
        description: str,
        url: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> str:
        return "Correctly registered event."

    def register_place(
        self,
        name: str,
        description: str,
        url: str,
        closing_days: list[int],
    ) -> str:
        return "Correctly registered place."

    def set_tools(self) -> None:
        """
        Set tools for the llm to use:
        - register_event: register event to database.
        """
        self.register_tools = [
            StructuredTool(
                name="register_event",
                description=REGISTER_EVENT_TOOL_DESCRIPTION,
                args_schema=RegisterEventToolInput,
                func=self.register_event,
            ),
            StructuredTool(
                name="register_place",
                description=REGISTER_PLACE_TOOL_DESCRIPTION,
                args_schema=RegisterPlaceToolInput,
                func=self.register_place,
            ),
        ]

    def run(
        self, user_query: str, previous_conversation: list[tuple[str, str]] = []
    ) -> AnswerOutput:
        """Run AI agent on user query - it routes the LLM and tool calls."""
        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT)]
            + previous_conversation
            + [
                ("human", "{user_query}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        chain = (
            {
                "user_query": lambda x: x["user_query"],
                "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                    x["intermediate_steps"]
                ),
            }
            | prompt
            | self.llm.bind(
                tools=[format_tool_to_openai_tool(tool) for tool in self.register_tools]
            )
            | OpenAIToolsAgentOutputParser()
        )

        agent_executor = AgentExecutor(
            agent=chain, tools=self.register_tools, verbose=True
        )
        agent_output = agent_executor.invoke({"user_query": user_query})

        return AnswerOutput(
            answer=agent_output["output"], type=AnswerType.conversational
        )
