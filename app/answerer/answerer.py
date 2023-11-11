import datetime
import logging

from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.docstore.document import Document
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.answerer.messages import (
    MESSAGE_AI_OUTRO,
    MESSAGE_ANSWER_NOT_NEEDED,
    MESSAGE_INVALID_QUERY,
    MESSAGE_NOTHING_RELEVANT,
)
from app.answerer.prompts import (
    PROMPT_CONTEXT_ANSWER,
    PROMPT_EXTRACT_FILTERS,
    RSCHEMA_ANSWER_EVENT_ID,
    RSCHEMA_ANSWER_EVENT_SUMMARY,
    RSCHEMA_ANSWER_INTRO,
    RSCHEMA_EXTRACT_DATE,
    RSCHEMA_EXTRACT_INVALID,
    RSCHEMA_EXTRACT_RECOMMENDATIONS,
    RSCHEMA_EXTRACT_TIME,
)
from app.constants import N_EVENTS_CONTEXT, N_EVENTS_MAX
from app.db.enums import AnswerType
from app.db.schemas import AnswerOutput
from app.db.services import get_event_by_id
from app.utils.conn import get_llm, get_vectorstore, get_vectorstore_translator
from app.utils.datetime_utils import date_to_timestamp


class Answerer:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = get_llm()
        self.vectorstore = get_vectorstore()
        self.vectorstore_translator = get_vectorstore_translator()

    def run_extract_filters(
        self, user_query: str, today_date: datetime.date
    ) -> tuple[bool, bool, dict]:
        """Self-query to extract filters for later retrieval"""
        prompt = ChatPromptTemplate.from_template(template=PROMPT_EXTRACT_FILTERS)

        output_parser = StructuredOutputParser.from_response_schemas(
            [
                ResponseSchema(
                    name="query_is_invalid",
                    description=RSCHEMA_EXTRACT_INVALID,
                    type="boolean",
                ),
                ResponseSchema(
                    name="query_needs_recommendations",
                    description=RSCHEMA_EXTRACT_RECOMMENDATIONS,
                    type="boolean",
                ),
                ResponseSchema(
                    name="query_start_date",
                    description=RSCHEMA_EXTRACT_DATE.format(start_end="start"),
                ),
                ResponseSchema(
                    name="query_end_date",
                    description=RSCHEMA_EXTRACT_DATE.format(start_end="end"),
                ),
                ResponseSchema(name="query_time", description=RSCHEMA_EXTRACT_TIME),
            ]
        )

        response_raw = self.llm(
            prompt.format_messages(
                today_date=today_date.strftime("%Y-%m-%d (%A)"),
                user_query=user_query,
                format_instructions=output_parser.get_format_instructions(),
            )
        )
        response = output_parser.parse(response_raw.content)

        logging.info(
            "\n".join([f"Filter {key}: {response[key]}" for key in response.keys()])
        )

        start_date = (
            today_date
            if response["query_start_date"] == "NO_DATE"
            else datetime.datetime.strptime(
                response["query_start_date"], "%Y-%m-%d"
            ).date()
        )
        end_date = (
            today_date + datetime.timedelta(days=6)
            if response["query_end_date"] == "NO_DATE"
            else datetime.datetime.strptime(
                response["query_end_date"], "%Y-%m-%d"
            ).date()
        )

        filters = [
            Comparison(
                comparator="lte",
                attribute="start_date",
                value=date_to_timestamp(end_date),
            ),
            Comparison(
                comparator="gte",
                attribute="end_date",
                value=date_to_timestamp(start_date),
            ),
        ]

        # filter out events that are closed in the query's days of the week
        # the code finds all days of the week in the given range
        # it then adds a filter where the event must be open in at least one day in the range
        # example: query is from Monday to Tuesday,
        # the filter becomes: OR(NOT closed on Monday, NOT closed on Tuesday)
        days_of_week_in_range = set(
            [
                (start_date + datetime.timedelta(days=i)).strftime("%A")
                for i in range((end_date - start_date).days + 1)
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
        for day_of_week, db_attribute in map_closed_days.items():
            if day_of_week in days_of_week_in_range:
                filters_closed_days.append(
                    Comparison(comparator="eq", attribute=db_attribute, value=False)
                )

        filters.append(Operation(operator="or", arguments=filters_closed_days))

        if response["query_time"] == "daytime":
            filters.append(
                Comparison(comparator="eq", attribute="is_during_day", value=True)
            )
        elif response["query_time"] == "nighttime":
            filters.append(
                Comparison(comparator="eq", attribute="is_during_night", value=True)
            )

        _, filter_kwargs = self.vectorstore_translator.visit_structured_query(
            structured_query=StructuredQuery(
                query=user_query, filter=Operation(operator="and", arguments=filters)
            )
        )

        return (
            response["query_is_invalid"],
            response["query_needs_recommendations"],
            filter_kwargs,
        )

    def run_generate_answer(
        self, user_query: str, docs: list[Document]
    ) -> AnswerOutput:
        prompt = ChatPromptTemplate.from_template(template=PROMPT_CONTEXT_ANSWER)

        output_parser = StructuredOutputParser.from_response_schemas(
            [ResponseSchema(name="intro", description=RSCHEMA_ANSWER_INTRO)]
            + [
                rs
                for i in range(N_EVENTS_MAX)
                for rs in (
                    ResponseSchema(
                        name=f"event_id_{i+1}",
                        description=RSCHEMA_ANSWER_EVENT_ID.format(number=i + 1),
                        type="integer",
                    ),
                    ResponseSchema(
                        name=f"event_summary_{i+1}",
                        description=RSCHEMA_ANSWER_EVENT_SUMMARY.format(number=i + 1),
                    ),
                )
            ]
        )

        response_raw = self.llm(
            prompt.format_messages(
                context="\n\n".join(
                    [
                        f"ID {doc.metadata['id']}:\n```{doc.page_content}```"
                        for doc in docs
                    ]
                ),
                user_query=user_query,
                k=N_EVENTS_MAX,
                format_instructions=output_parser.get_format_instructions(),
            )
        )
        response = output_parser.parse(response_raw.content)

        recommendation_ids = [
            response[f"event_id_{i+1}"]
            for i in range(N_EVENTS_MAX)
            if response[f"event_id_{i+1}"] != 0
        ]
        if len(recommendation_ids) == 0:
            return AnswerOutput(
                answer=response["intro"],
                type=AnswerType.template,
            )

        recommendation_summaries = []
        for i, event_id in enumerate(recommendation_ids):
            db_event = get_event_by_id(db=self.db, id=event_id)
            if db_event is None:
                raise Exception(
                    f"Event in vectorstore is not present in db (id={event_id})."
                )

            recommendation_summaries.append(
                f"{i+1}. "
                + response[f"event_summary_{i+1}"]
                + (f"\n📍 {db_event.location}" if db_event.location is not None else "")
                + (f"\n🌐 {db_event.url}" if db_event.url is not None else "")
                + (
                    f"\n💰 {db_event.price_level}"
                    if db_event.price_level is not None
                    else ""
                )
            )

        elaborated_answer = "\n\n".join(
            [response["intro"]] + recommendation_summaries + [MESSAGE_AI_OUTRO]
        )

        return AnswerOutput(
            answer=elaborated_answer,
            type=AnswerType.ai,
            used_event_ids=recommendation_ids,
        )

    def run(self, user_query: str, today_date: datetime.date) -> AnswerOutput:
        is_invalid, needs_recommendations, filter_kwargs = self.run_extract_filters(
            user_query=user_query, today_date=today_date
        )

        if is_invalid:
            return AnswerOutput(answer=MESSAGE_INVALID_QUERY, type=AnswerType.blocked)

        if not needs_recommendations:
            return AnswerOutput(
                answer=MESSAGE_ANSWER_NOT_NEEDED, type=AnswerType.template
            )

        relevant_docs = self.vectorstore.similarity_search(
            user_query, k=N_EVENTS_CONTEXT, **filter_kwargs
        )

        if not len(relevant_docs):
            return AnswerOutput(
                answer=MESSAGE_NOTHING_RELEVANT, type=AnswerType.template
            )
        else:
            return self.run_generate_answer(user_query=user_query, docs=relevant_docs)
