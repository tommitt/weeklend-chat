import datetime
import logging

from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers.self_query.chroma import ChromaTranslator
from langchain.vectorstores import Chroma

from app.answerer.messages import MESSAGE_INVALID_QUERY, MESSAGE_NOTHING_RELEVANT
from app.answerer.prompts import PROMPT_CONTEXT_ANSWER, PROMPT_EXTRACT_FILTERS
from app.constants import CHROMA_DIR, N_DOCS, OPENAI_API_KEY
from app.db.enums import AnswerType
from app.db.schemas import AnswerOutput
from app.utils.datetime_utils import date_to_timestamp


class Answerer:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        self.db = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        )

        self.translator = ChromaTranslator()

    def run_extract_filters(self, user_query: str) -> tuple[bool, dict]:
        """Self-query to extract filters for later retrieval"""
        today_date = datetime.date.today()

        prompt = ChatPromptTemplate.from_template(
            template=PROMPT_EXTRACT_FILTERS + "\n\n{format_instructions}"
        )

        output_parser = StructuredOutputParser.from_response_schemas(
            [
                ResponseSchema(
                    name="query_is_invalid",
                    description="This tells if the query is invalid. Output True if it is invalid, False otherwise.",
                    type="boolean",
                ),
                ResponseSchema(
                    name="query_start_date",
                    description='This is the start of the range in format "YYYY-MM-DD". If this information is not found, output "NO_DATE".',
                ),
                ResponseSchema(
                    name="query_end_date",
                    description='This is the end of the range in format "YYYY-MM-DD". If this information is not found, output "NO_DATE".',
                ),
                ResponseSchema(
                    name="query_time",
                    description='This is the time of the day. It can be either "daytime", "nighttime" or "both".',
                ),
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

        _, filter_kwargs = self.translator.visit_structured_query(
            structured_query=StructuredQuery(
                query=user_query, filter=Operation(operator="and", arguments=filters)
            )
        )

        return response["query_is_invalid"], filter_kwargs

    def run_generate_answer(self, user_query: str, docs: list[Document]) -> str:
        prompt = ChatPromptTemplate.from_template(
            template=PROMPT_CONTEXT_ANSWER + "\n\n{format_instructions}"
        )

        output_parser = StructuredOutputParser.from_response_schemas(
            [
                ResponseSchema(
                    name="intro",
                    description="This is your intro to the message.",
                )
            ]
            + [
                ResponseSchema(
                    name=f"event_summary_{i+1}",
                    description=f"This is a long summary of event number {i+1}.",
                )
                for i in range(len(docs))
            ]
            + [
                ResponseSchema(
                    name="outro",
                    description="This is your outro to the message. This must include a commentary on the relevance of the given events to the user's question. It can also be an empty string.",
                )
            ]
        )

        response_raw = self.llm(
            prompt.format_messages(
                context="\n\n".join(
                    [f"{i+1}. ```{doc.page_content}```" for i, doc in enumerate(docs)]
                ),
                question=user_query,
                k=len(docs),
                format_instructions=output_parser.get_format_instructions(),
            )
        )
        response = output_parser.parse(response_raw.content)

        answer = "\n\n".join(
            [response["intro"]]
            + [
                f"{i+1}. "
                + response[f"event_summary_{i+1}"]
                + (
                    f'\n📍 {docs[i].metadata["location"]}'
                    if docs[i].metadata["location"]
                    else ""
                )
                + (f'\n🌐 {docs[i].metadata["url"]}' if docs[i].metadata["url"] else "")
                for i in range(len(docs))
            ]
            + [response["outro"]]
        )

        return answer

    def run(self, user_query: str) -> AnswerOutput:
        is_invalid, filter_kwargs = self.run_extract_filters(user_query=user_query)
        if is_invalid:
            return AnswerOutput(answer=MESSAGE_INVALID_QUERY, type=AnswerType.blocked)

        relevant_docs = self.db.similarity_search(user_query, k=N_DOCS, **filter_kwargs)

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
