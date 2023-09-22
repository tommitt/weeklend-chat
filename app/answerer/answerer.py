import datetime
import logging

from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.docstore.document import Document
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session

from app.answerer.messages import MESSAGE_INVALID_QUERY, MESSAGE_NOTHING_RELEVANT
from app.answerer.prompts import (
    PROMPT_CONTEXT_ANSWER,
    PROMPT_EXTRACT_FILTERS,
    RSCHEMA_ANSWER_EVENT_SUMMARY,
    RSCHEMA_ANSWER_INTRO,
    RSCHEMA_EXTRACT_DATE,
    RSCHEMA_EXTRACT_INVALID,
    RSCHEMA_EXTRACT_RECOMMENDATIONS,
    RSCHEMA_EXTRACT_TIME,
)
from app.constants import N_DOCS
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

    def run_extract_filters(self, user_query: str) -> tuple[bool, bool, dict]:
        """Self-query to extract filters for later retrieval"""
        today_date = datetime.date.today()

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

        if response["query_start_date"] == "NO_DATE":
            response["query_start_date"] = today_date
        if response["query_end_date"] == "NO_DATE":
            response["query_end_date"] = today_date + datetime.timedelta(days=6)

        filters = [
            Comparison(
                comparator="lte",
                attribute="start_date",
                value=date_to_timestamp(response["query_end_date"]),
            ),
            Comparison(
                comparator="gte",
                attribute="end_date",
                value=date_to_timestamp(response["query_start_date"]),
            ),
        ]

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

    def run_generate_answer(self, user_query: str, docs: list[Document]) -> str:
        prompt = ChatPromptTemplate.from_template(template=PROMPT_CONTEXT_ANSWER)

        output_parser = StructuredOutputParser.from_response_schemas(
            [ResponseSchema(name="intro", description=RSCHEMA_ANSWER_INTRO)]
            + [
                ResponseSchema(
                    name=f"event_summary_{i+1}",
                    description=RSCHEMA_ANSWER_EVENT_SUMMARY.format(number=i + 1),
                )
                for i in range(len(docs))
            ]
        )

        response_raw = self.llm(
            prompt.format_messages(
                context="\n\n".join(
                    [f"{i+1}. ```{doc.page_content}```" for i, doc in enumerate(docs)]
                ),
                user_query=user_query,
                k=len(docs),
                format_instructions=output_parser.get_format_instructions(),
            )
        )
        response = output_parser.parse(response_raw.content)

        event_recommendations = []
        for i, doc in enumerate(docs):
            db_event = get_event_by_id(db=self.db, id=doc.metadata["id"])
            if db_event is None:
                raise Exception(
                    f"Event in vectorstore is not present in db (id={doc.metadata['id']})."
                )

            event_recommendations.append(
                f"{i+1}. "
                + response[f"event_summary_{i+1}"]
                + (f"\n📍 {db_event.location}" if db_event.location is not None else "")
                + (f"\n🌐 {db_event.url}" if db_event.url is not None else "")
            )

        return "\n\n".join([response["intro"]] + event_recommendations)

    def run(self, user_query: str) -> AnswerOutput:
        is_invalid, needs_recommendations, filter_kwargs = self.run_extract_filters(
            user_query=user_query
        )

        if is_invalid:
            return AnswerOutput(answer=MESSAGE_INVALID_QUERY, type=AnswerType.blocked)

        if not needs_recommendations:
            return AnswerOutput(answer=None, type=AnswerType.unanswered)

        relevant_docs = self.vectorstore.similarity_search(
            user_query, k=N_DOCS, **filter_kwargs
        )

        if not len(relevant_docs):
            return AnswerOutput(
                answer=MESSAGE_NOTHING_RELEVANT, type=AnswerType.template
            )
        else:
            return AnswerOutput(
                answer=self.run_generate_answer(
                    user_query=user_query, docs=relevant_docs
                ),
                type=AnswerType.ai,
                used_event_ids=[
                    relevant_docs[i].metadata["id"] for i in range(len(relevant_docs))
                ],
            )
