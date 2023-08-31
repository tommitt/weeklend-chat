import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from langchain.document_loaders import DataFrameLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from constants import CHROMA_DIR, DB_PATH

_ = load_dotenv(find_dotenv())


df = pd.read_csv(DB_PATH)
cols = [
    "Promoter Location (Supplier - Indirizzo)",
    "start_date",  # it's already a timestamp
    "end_date",  # it's already a timestamp
    "Descrizione",
]
loader = DataFrameLoader(df[cols], page_content_column="Descrizione")
docs = loader.load()

# documents are short so splitting isn't needed
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
# docs = text_splitter.split_documents(docs)

embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])

db = Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_DIR)
db.persist()
