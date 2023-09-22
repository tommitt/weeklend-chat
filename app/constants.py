# mutable
N_DOCS = 3

LIMIT_MAX_USERS = 500
LIMIT_ANSWERS_PER_WEEK = 3
LIMIT_BLOCKS_PER_WEEK = 3

# non-mutable
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/test.db"
PINECONE_INDEX = "weeklend-beta"
PINECONE_NAMESPACE = "events"
TIMESTAMP_ORIGIN = "2023-01-01"

# from .env
import os

import openai
from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.organization = os.environ["OPENAI_ORGANIZATION_ID"]

WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
WHATSAPP_NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")
