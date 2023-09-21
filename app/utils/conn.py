# import pinecone
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers.self_query.base import ChromaTranslator  # PineconeTranslator
from langchain.vectorstores import Chroma, VectorStore  # Pinecone

from app.constants import CHROMA_DIR, OPENAI_API_KEY


def get_llm():
    return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)


def get_vectorstore() -> VectorStore:
    return Chroma(
        # persist_directory=chromadb.PersistentClient(path=CHROMA_DIR),
        persist_directory=CHROMA_DIR,
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
    )
    # pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    #     if PINECONE_INDEX not in pinecone.list_indexes():
    #         pinecone.create_index(
    #             name=PINECONE_INDEX,
    #             metric="cosine",
    #             dimension=1536,  # that's specific to OpenAIEmbeddings
    #             source_collection=(
    #                 PINECONE_INDEX
    #                 if PINECONE_INDEX in pinecone.list_collections()
    #                 else None
    #             ),
    #         )
    #     self.vectorstore = Pinecone(
    #         pinecone.Index(PINECONE_INDEX),
    #         OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY).embed_query,
    #         "text",
    #     )


def get_vectorstore_translator():
    return ChromaTranslator()
    # return PineconeTranslator()
