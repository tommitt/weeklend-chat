import datetime
import os

from dotenv import find_dotenv, load_dotenv
from langchain.chains.query_constructor.ir import Comparison, Operation, StructuredQuery
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.output_parsers.json import parse_and_check_json_markdown
from langchain.retrievers.self_query.chroma import ChromaTranslator
from langchain.vectorstores import Chroma

from answerer.messages import MESSAGE_NOTHING_RELEVANT
from answerer.prompts import PROMPT_CONTEXT_ANSWER, PROMPT_EXTRACT_DATE
from constants import CHROMA_DIR, N_DOCS
from utils.datetime_utils import date_to_timestamp


class Answerer:
    def __init__(self) -> None:
        _ = load_dotenv(find_dotenv())

        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.environ["OPENAI_API_KEY"],
        )

        self.db = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=OpenAIEmbeddings(
                openai_api_key=os.environ["OPENAI_API_KEY"]
            ),
        )

        self.translator = ChromaTranslator()

    def run(self, user_query: str, today_date: datetime.date) -> str:
        # filter extraction (custom self-query)
        dates_query = PROMPT_EXTRACT_DATE.format(
            today_date=today_date.strftime("%Y-%m-%d (%A)"), user_query=user_query
        )

        dates_response = parse_and_check_json_markdown(
            self.llm.predict(dates_query), ["query_start_date", "query_end_date"]
        )

        if dates_response["query_start_date"] == "NO_DATE":
            dates_response["query_start_date"] = today_date
        if dates_response["query_end_date"] == "NO_DATE":
            dates_response["query_end_date"] = today_date

        filter = Operation(
            operator="and",
            arguments=[
                Comparison(
                    comparator="lte",
                    attribute="start_date",
                    value=date_to_timestamp(dates_response["query_end_date"]),
                ),
                Comparison(
                    comparator="gte",
                    attribute="end_date",
                    value=date_to_timestamp(dates_response["query_start_date"]),
                ),
            ],
        )

        _, filter_kwargs = self.translator.visit_structured_query(
            structured_query=StructuredQuery(query=user_query, filter=filter)
        )

        # retriever of similar documents
        relevant_docs = self.db.similarity_search(user_query, k=N_DOCS, **filter_kwargs)

        # answer generation
        if not len(relevant_docs):
            answer = MESSAGE_NOTHING_RELEVANT
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
