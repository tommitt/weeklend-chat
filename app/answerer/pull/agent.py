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
    MESSAGE_REGISTERED_DYNAMIC_BUSINESS,
    MESSAGE_REGISTERED_STATIC_BUSINESS,
)
from app.answerer.pull.prompts import BUSINESS_SYSTEM_PROMPT, EVENT_SYSTEM_PROMPT
from app.answerer.schemas import AnswerOutput
from app.db.enums import AnswerType, BusinessType
from app.db.models import BusinessORM
from app.utils.conn import get_llm


class UpdateBusinessToolInput(BaseModel):
    name: str = Field(description="The name of the organization")
    description: str = Field(description="The description of the organization")
    type: BusinessType = Field(
        description="The type of experiences the organization provides"
    )


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
        db_business: BusinessORM | None = None,
        today_date: datetime.date | None = None,
    ) -> None:
        self.db = db
        self.db_business = db_business
        self.today_date = (
            today_date if today_date is not None else datetime.date.today()
        )
        self.llm = get_llm()
        self.set_tools()

    def update_business(
        self,
        name: str,
        description: str,
        type: BusinessType,
    ) -> str:
        # TODO: register business information
        if type == BusinessType.static:
            return MESSAGE_REGISTERED_STATIC_BUSINESS.format(name=name)
        elif type == BusinessType.dynamic:
            return MESSAGE_REGISTERED_DYNAMIC_BUSINESS.format(name=name)
        else:
            raise Exception(f"Business of type {type} not accepted.")

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
        return "Correctly registered event."

    def set_tools(self) -> None:
        """
        Set tools for the llm to use:
        - register_event: register event to database.
        """
        self.business_tool = StructuredTool(
            name="update_business",
            description="Register information of an organization.",
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
        # TODO: route when business is already updated
        prompt = ChatPromptTemplate.from_messages(
            [("system", BUSINESS_SYSTEM_PROMPT)]
            + previous_conversation
            + [("human", "{user_query}")]
        )
        agent = (
            prompt
            | self.llm.bind(tools=[format_tool_to_openai_tool(self.business_tool)])
            | OpenAIToolsAgentOutputParser()
        )

        agent_output = agent.invoke({"user_query": user_query})

        if isinstance(agent_output, AgentFinish):
            return AnswerOutput(
                answer=agent_output.return_values["output"],
                type=AnswerType.conversational,
            )

        tool_input = UpdateBusinessToolInput(**agent_output[0].tool_input)
        logging.info(f"Calling {self.business_tool.name} tool with input: {tool_input}")
        business_answer = self.business_tool.run(tool_input.dict())
        return AnswerOutput(answer=business_answer, type=AnswerType.template)
