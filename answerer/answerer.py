import datetime
import os

from dotenv import find_dotenv, load_dotenv
from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.retrievers.self_query.chroma import ChromaTranslator
from langchain.vectorstores import Chroma

from answerer.messages import MESSAGE_INVALID_QUERY, MESSAGE_NOTHING_RELEVANT
from answerer.prompts import PROMPT_CONTEXT_ANSWER, PROMPT_EXTRACT_FILTERS
from constants import CHROMA_DIR, N_DOCS
from utils.datetime_utils import date_to_timestamp


class Answerer:
    def __init__(self) -> None:
        _ = load_dotenv(find_dotenv())

        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        self.db = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=OpenAIEmbeddings(
                openai_api_key=os.environ["OPENAI_API_KEY"]
            ),
        )

        self.translator = ChromaTranslator()

        self.init_output_parsers()

    def init_output_parsers(self) -> None:
        self.filter_parser = StructuredOutputParser.from_response_schemas(
            [
                ResponseSchema(
                    name="query_is_invalid",
                    description="This tells if the query is invalid. Output True if it is invalid, False otherwise.",
                    type="boolean",
                ),
                ResponseSchema(
                    name="query_start_date",
                    description='This is the start of the range in format "YYYY-MM-DD". If this information is not found, output "NO DATE".',
                ),
                ResponseSchema(
                    name="query_end_date",
                    description='This is the end of the range in format "YYYY-MM-DD". If this information is not found, output "NO DATE".',
                ),
                ResponseSchema(
                    name="query_time",
                    description='This is the time of the day. It can be either "daytime", "nighttime" or "both".',
                ),
            ]
        )

    def run_extract_filters(
        self, user_query: str, today_date: datetime.date
    ) -> tuple[bool, dict]:
        """Self-query to extract filters for later retrieval"""
        prompt = ChatPromptTemplate.from_template(
            template=PROMPT_EXTRACT_FILTERS + "\n\n{format_instructions}"
        )

        response_raw = self.llm(
            prompt.format_messages(
                today_date=today_date.strftime("%Y-%m-%d (%A)"),
                user_query=user_query,
                format_instructions=self.filter_parser.get_format_instructions(),
            )
        )
        response = self.filter_parser.parse(response_raw.content)

        if response["query_start_date"] == "NO_DATE":
            response["query_start_date"] = today_date
        if response["query_end_date"] == "NO_DATE":
            response["query_end_date"] = today_date + datetime.timedelta(days=7)

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

    def run(self, user_query: str, today_date: datetime.date) -> str:
        # extract db filters
        is_invalid, filter_kwargs = self.run_extract_filters(user_query, today_date)
        if is_invalid:
            return MESSAGE_INVALID_QUERY

        # retriever of similar documents
        relevant_docs = self.db.similarity_search(user_query, k=N_DOCS, **filter_kwargs)

        # answer generation
        if not len(relevant_docs):
            return MESSAGE_NOTHING_RELEVANT
        else:
            query = PROMPT_CONTEXT_ANSWER.format(
                context="\n\n".join(
                    [f"```{doc.page_content}```" for doc in relevant_docs]
                ),
                question=user_query,
                k=N_DOCS,
            )

            answer = self.llm.predict(query)
            return answer
