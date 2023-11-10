import logging

import pinecone
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers.self_query.base import PineconeTranslator
from langchain.vectorstores import Pinecone, VectorStore

from app.constants import (
    EMBEDDING_SIZE,
    OPENAI_API_KEY,
    PINECONE_API_KEY,
    PINECONE_ENV,
    PINECONE_INDEX,
    PINECONE_NAMESPACE,
)


def get_llm():
    return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)


def get_vectorstore() -> VectorStore:
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    if PINECONE_INDEX not in pinecone.list_indexes():
        logging.info(f"Creating Pinecone index at: {PINECONE_INDEX}")

        pinecone.create_index(
            name=PINECONE_INDEX,
            metric="cosine",
            dimension=EMBEDDING_SIZE,
            source_collection=(
                # retrieve from collections if present
                PINECONE_INDEX
                if PINECONE_INDEX in pinecone.list_collections()
                else ""
            ),
        )
    return Pinecone(
        index=pinecone.Index(PINECONE_INDEX),
        embedding=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        text_key="text",
        namespace=PINECONE_NAMESPACE,
    )


def get_vectorstore_translator():
    return PineconeTranslator()
