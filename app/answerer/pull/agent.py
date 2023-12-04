import datetime
import logging
from typing import Optional

from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.schema.agent import AgentFinish
from langchain.tools import StructuredTool
from langchain.tools.render import format_tool_to_openai_tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.answerer.pull.messages import (
    MESSAGE_REGISTERED_EVENT,
    MESSAGE_UPDATED_BUSINESS,
)
from app.answerer.pull.prompts import (
    BUSINESS_INFO_PROMPT,
    BUSINESS_SYSTEM_PROMPT,
    EVENT_SYSTEM_PROMPT,
)
from app.answerer.schemas import AnswerOutput
from app.db.enums import AnswerType
from app.db.schemas import BusinessInDB
from app.utils.conn import get_llm


class UpdateBusinessToolInput(BaseModel):
    name: str = Field(description="The name of the business")
    description: str = Field(description="The description of the business")


class RegisterEventToolInput(BaseModel):
    name: str = Field(description="The name of the event")
    description: str = Field(
        description="The description of the event. It should be at least 240 characters"
    )
    url: str = Field(description="External URL linking to the event's website")
    start_date: datetime.date = Field(description="The start date of the event")
    end_date: Optional[datetime.date] = Field(description="The end date of the event")
    location: Optional[str] = Field(description="Location where the event happens.")


class AiAgent:
    def __init__(
        self,
        db: Session,
        business: BusinessInDB,
        today_date: datetime.date | None = None,
    ) -> None:
        self.db = db
        self.business = business
        self.today_date = (
            today_date if today_date is not None else datetime.date.today()
        )
        self.llm = get_llm()
        self.set_tools()

    def update_business(
        self,
        name: str,
        description: str,
    ) -> str:
        # TODO: register business information
        return MESSAGE_UPDATED_BUSINESS.format(name=name, description=description)

    def register_event(
        self,
        name: str,
        description: str,
        url: str,
        start_date: datetime.date,
        end_date: datetime.date | None = None,
        location: str | None = None,
    ) -> str:
        # TODO: register event
        return MESSAGE_REGISTERED_EVENT.format(
            name=name,
            description=description,
            url=url,
            start_date=start_date,
            end_date=end_date,
            location=location,
        )

    def set_tools(self) -> None:
        """
        Set tools for the llm to use:
        - update_business: update business information.
        - register_event: register event to database.
        """
        self.business_tool = StructuredTool(
            name="update_business",
            description="Register information of a business.",
            args_schema=UpdateBusinessToolInput,
            func=self.update_business,
        )
        self.event_tool = StructuredTool(
            name="register_event",
            description="Register an event to the database.",
            args_schema=RegisterEventToolInput,
            func=self.register_event,
        )

    def run(
        self, user_query: str, previous_conversation: list[tuple[str, str]] = []
    ) -> AnswerOutput:
        """Run AI agent on user query - it routes the LLM and tool calls."""

        if self.business.name is None:
            system_prompt = [("system", BUSINESS_SYSTEM_PROMPT)]
            tool = self.business_tool
        else:
            system_prompt = [
                (
                    "system",
                    EVENT_SYSTEM_PROMPT.format(today_date=self.today_date),
                ),
                (
                    "human",
                    BUSINESS_INFO_PROMPT.format(
                        name=self.business.name, description=self.business.description
                    ),
                ),
            ]
            tool = self.event_tool

        prompt = ChatPromptTemplate.from_messages(
            system_prompt + previous_conversation + [("human", "{user_query}")]
        )
        agent = (
            prompt
            | self.llm.bind(tools=[format_tool_to_openai_tool(tool)])
            | OpenAIToolsAgentOutputParser()
        )
        agent_output = agent.invoke({"user_query": user_query})

        if isinstance(agent_output, AgentFinish):
            return AnswerOutput(
                answer=agent_output.return_values["output"],
                type=AnswerType.conversational,
            )

        tool_input = tool.args_schema(**agent_output[0].tool_input)
        logging.info(f"Calling {tool.name} tool with input: {tool_input}")
        tool_output = tool.run(tool_input.dict())
        # TODO: add created event id to AnswerOutput
        return AnswerOutput(answer=tool_output, type=AnswerType.template)
