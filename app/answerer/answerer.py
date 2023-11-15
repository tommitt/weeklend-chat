import datetime

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from langchain.tools.render import format_tool_to_openai_tool
from sqlalchemy.orm import Session

from app.answerer.prompts import SEARCH_EVENTS_TOOL_DESCRIPTION, SYSTEM_PROMPT
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

    def search_events(
        self,
        user_query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        time: str | None = None,
    ) -> str:
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
                f"ID: {doc.metadata['id']}\n"
                + f"Description: {doc.page_content}\n"
                + (f"URL: {db_event.url}\n" if db_event.url is not None else "")
                + (
                    f"Location: {db_event.location}\n"
                    if db_event.location is not None
                    else ""
                )
            )
        return "\n----------\n".join(doc_texts)

    def run(
        self, user_query: str, previous_conversation: list[tuple] = []
    ) -> AnswerOutput:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    SYSTEM_PROMPT.format(k=N_EVENTS_MAX),
                )
            ]
            + previous_conversation
            + [
                ("human", "{user_query}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        tools = [
            StructuredTool(
                name="search_events",
                description=SEARCH_EVENTS_TOOL_DESCRIPTION.format(
                    today_date=self.today_date
                ),
                args_schema=SearchEventsToolInput,
                func=self.search_events,
            )
        ]

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
