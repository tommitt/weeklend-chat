import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from langchain.document_loaders import DataFrameLoader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from constants import CHROMA_DIR, DB_PATH
from utils.datetime_utils import date_to_timestamp

_ = load_dotenv(find_dotenv())


df = pd.read_csv(DB_PATH)

for i, row in df.iterrows():
    if not pd.isna(row["start_date"]):
        df.loc[i, "start_date"] = date_to_timestamp(row["start_date"])
    if not pd.isna(row["end_date"]):
        df.loc[i, "end_date"] = date_to_timestamp(row["end_date"])

loader = DataFrameLoader(df, page_content_column="description")
docs = loader.load()

# documents are short so splitting isn't needed
# text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
# docs = text_splitter.split_documents(docs)

embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])

db = Chroma.from_documents(docs, embeddings, persist_directory=CHROMA_DIR)
db.persist()
