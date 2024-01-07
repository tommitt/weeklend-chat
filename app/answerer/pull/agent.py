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
    MESSAGE_URL_NOT_PROVIDED,
)
from app.answerer.pull.prompts import (
    BUSINESS_INFO_PROMPT,
    BUSINESS_SYSTEM_PROMPT,
    BUSINESS_TOOL_DESCRIPTION,
    EVENT_SYSTEM_PROMPT,
    EVENT_TOOL_DESCRIPTION,
)
from app.answerer.schemas import AnswerOutput, DayTimeEnum
from app.db.enums import AnswerType, CityEnum
from app.db.schemas import BusinessInDB, Event
from app.db.services import register_event, update_business_info
from app.loader.loader import Loader
from app.utils.conn import get_llm

PULL_CHAT_SOURCE = "pullchat_v1"


class UpdateBusinessToolInput(BaseModel):
    name: str = Field(description="The name of the business")
    description: str = Field(description="The description of the business")


class RegisterEventToolInput(BaseModel):
    name: str = Field(description="Event's name")
    description: str = Field(description="Event's description")
    location: str = Field(description="Event's location")
    start_date: datetime.date = Field(description="Event's start date")
    end_date: Optional[datetime.date] = Field(description="Event's end date")
    url: Optional[str] = Field(description="Event's website URL")
    time_of_day: Optional[DayTimeEnum] = Field(description="Event's time of the day")


class AiAgent:
    def __init__(
        self,
        db: Session | None,
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
    ) -> AnswerOutput:
        if self.db is not None:
            _ = update_business_info(
                db=self.db,
                business_id=self.business.id,
                name=name,
                description=description,
            )
        return AnswerOutput(
            answer=MESSAGE_UPDATED_BUSINESS.format(name=name, description=description),
            type=AnswerType.template,
        )

    def register_event(
        self,
        name: str,
        description: str,
        location: str,
        start_date: datetime.date,
        end_date: datetime.date | None = None,
        url: str | None = None,
        time_of_day: DayTimeEnum | None = None,
    ) -> AnswerOutput:
        if url is None:
            return AnswerOutput(
                answer=MESSAGE_URL_NOT_PROVIDED, type=AnswerType.template
            )

        if self.db is not None:
            event = Event(
                description="\n".join([name, description]),
                is_vectorized=False,
                business_id=self.business.id,
                city=CityEnum.Torino,
                start_date=start_date,
                end_date=end_date if end_date is not None else start_date,
                is_during_day=(
                    time_of_day in [DayTimeEnum.daytime, DayTimeEnum.entire_day, None]
                ),
                is_during_night=(
                    time_of_day in [DayTimeEnum.nighttime, DayTimeEnum.entire_day, None]
                ),
                name=name,
                location=location,
                url=url,
            )
            db_event = register_event(
                db=self.db, event_in=event, source=PULL_CHAT_SOURCE
            )
            events_loader = Loader(db=self.db)
            # AWS Lambda cannot run functions asynchronously
            events_loader.vectorize_event(db_event, async_add=False)
            event_ids = [db_event.id]
        else:
            event_ids = []

        return AnswerOutput(
            answer=MESSAGE_REGISTERED_EVENT.format(
                name=name,
                description=description,
                url=url,
                start_date=start_date,
                end_date=end_date,
                location=location,
                time_of_day=time_of_day,
            ),
            type=AnswerType.template,
            used_event_ids=event_ids,
        )

    def set_tools(self) -> None:
        """
        Set tools for the llm to use:
        - update_business: update business information.
        - register_event: register event to database.
        """
        self.business_tool = StructuredTool(
            name="update_business",
            description=BUSINESS_TOOL_DESCRIPTION,
            args_schema=UpdateBusinessToolInput,
            func=self.update_business,
        )
        self.event_tool = StructuredTool(
            name="register_event",
            description=EVENT_TOOL_DESCRIPTION,
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
        return tool.run(tool_input.dict())
