import datetime
import logging

from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate
from langchain.schema.agent import AgentFinish
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnableSerializable
from langchain.tools import StructuredTool
from langchain.tools.render import format_tool_to_openai_tool
from sqlalchemy.orm import Session

from app.answerer.prompts import (
    AGENT_SYSTEM_PROMPT,
    RECOMMENDER_SYSTEM_PROMPT,
    SEARCH_TOOL_DESCRIPTION,
)
from app.answerer.schemas import AnswerOutput, SearchEventsToolInput
from app.constants import N_EVENTS_CONTEXT, N_EVENTS_MAX
from app.db.enums import AnswerType
from app.db.services import get_event_by_id
from app.utils.conn import get_llm, get_vectorstore, get_vectorstore_translator
from app.utils.datetime_utils import date_to_timestamp


class Answerer:
    def __init__(self, db: Session, today_date: datetime.date | None = None) -> None:
        self.db = db
        self.today_date = (
            today_date if today_date is not None else datetime.date.today()
        )
        self.llm = get_llm()
        self.vectorstore = get_vectorstore()
        self.vectorstore_translator = get_vectorstore_translator()
        self.set_search_tool()

    def search_events(
        self,
        user_query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        time: str | None = None,
    ) -> str:
        """Search available events that are most relevant to the user's query."""
        # filter out events based on start and end dates
        start_date_dt = (
            self.today_date
            if start_date is None
            else datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        )
        end_date_dt = (
            self.today_date + datetime.timedelta(days=6)
            if end_date is None
            else datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        )

        filters = [
            Comparison(
                comparator="lte",
                attribute="start_date",
                value=date_to_timestamp(end_date_dt),
            ),
            Comparison(
                comparator="gte",
                attribute="end_date",
                value=date_to_timestamp(start_date_dt),
            ),
        ]

        # filter out events that are closed in the query's days of the week
        # the code finds all days of the week in the given range
        # it then adds a filter where the event must be open in at least one day in the range
        # example: query is from Monday to Tuesday,
        # the filter becomes: OR(NOT closed on Monday, NOT closed on Tuesday)
        days_of_week_in_range = set(
            [
                (start_date_dt + datetime.timedelta(days=i)).strftime("%A")
                for i in range((end_date_dt - start_date_dt).days + 1)
            ]
        )

        map_closed_days = {
            "Monday": "is_closed_mon",
            "Tuesday": "is_closed_tue",
            "Wednesday": "is_closed_wed",
            "Thursday": "is_closed_thu",
            "Friday": "is_closed_fri",
            "Saturday": "is_closed_sat",
            "Sunday": "is_closed_sun",
        }
        filters_closed_days = []
        for day_of_week, attribute in map_closed_days.items():
            if day_of_week in days_of_week_in_range:
                filters_closed_days.append(
                    Comparison(comparator="eq", attribute=attribute, value=False)
                )

        filters.append(Operation(operator="or", arguments=filters_closed_days))

        # filter out events based on time of the day
        if time == "daytime":
            filters.append(
                Comparison(comparator="eq", attribute="is_during_day", value=True)
            )
        elif time == "nighttime":
            filters.append(
                Comparison(comparator="eq", attribute="is_during_night", value=True)
            )

        _, filter_kwargs = self.vectorstore_translator.visit_structured_query(
            structured_query=StructuredQuery(
                query=user_query, filter=Operation(operator="and", arguments=filters)
            )
        )

        relevant_docs = self.vectorstore.similarity_search(
            user_query, k=N_EVENTS_CONTEXT, **filter_kwargs
        )

        doc_texts = []
        for doc in relevant_docs:
            db_event = get_event_by_id(db=self.db, id=doc.metadata["id"])
            if db_event is None:
                raise Exception(
                    f"Event in vectorstore is not present in db (id={doc.metadata['id']})."
                )
            doc_texts.append(
                f"ID: {db_event.id}\n"
                + f"Description: {doc.page_content}\n"
                + (f"URL: {db_event.url}\n" if db_event.url is not None else "")
                + (
                    f"Location: {db_event.location}\n"
                    if db_event.location is not None
                    else ""
                )
            )
        return "\n----------\n".join(doc_texts)

    def set_search_tool(self) -> None:
        """Set search tool for searching events."""
        self.search_tool = StructuredTool(
            name="search_events",
            description=SEARCH_TOOL_DESCRIPTION.format(today_date=self.today_date),
            args_schema=SearchEventsToolInput,
            func=self.search_events,
            return_direct=True,
        )

    def get_agent(
        self, previous_conversation: list[tuple[str, str]]
    ) -> RunnableSerializable:
        """Get LLM agent that decides whether to search for events or directly answer."""
        prompt = ChatPromptTemplate.from_messages(
            [("system", AGENT_SYSTEM_PROMPT)]
            + previous_conversation
            + [("human", "{user_query}")]
        )

        return (
            prompt
            | self.llm.bind(tools=[format_tool_to_openai_tool(self.search_tool)])
            | OpenAIToolsAgentOutputParser()
        )

    def get_recommender(
        self, previous_conversation: list[tuple[str, str]]
    ) -> RunnableSerializable:
        """Get LLM chain for recommending events given the searched events as context."""
        system_prompt = SystemMessagePromptTemplate(
            prompt=PromptTemplate.from_template(
                template=RECOMMENDER_SYSTEM_PROMPT,
                partial_variables={"k": N_EVENTS_MAX},
            )
        )

        prompt = ChatPromptTemplate.from_messages(
            [system_prompt] + previous_conversation + [("human", "{user_query}")]
        )

        return prompt | self.llm | StrOutputParser()

    def run(
        self, user_query: str, previous_conversation: list[tuple[str, str]] = []
    ) -> AnswerOutput:
        """Run answerer on user query - it routes the LLM and tool calls."""
        agent = self.get_agent(previous_conversation)
        agent_output = agent.invoke({"user_query": user_query})
        if isinstance(agent_output, AgentFinish):
            # TODO: flag AnswerType.blocked events
            return AnswerOutput(
                answer=agent_output.return_values["output"],
                type=AnswerType.conversational,
            )

        recommender = self.get_recommender(previous_conversation)
        tool_input = SearchEventsToolInput(**agent_output[0].tool_input)
        logging.info(f"Calling {self.search_tool.name} tool with input: {tool_input}")
        context = self.search_tool.run(tool_input.dict())
        recommender_output = recommender.invoke(
            {"user_query": user_query, "context": context}
        )
        # TODO: add used_event_ids
        return AnswerOutput(answer=recommender_output, type=AnswerType.ai)
