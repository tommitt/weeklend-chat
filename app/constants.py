# mutable
N_EVENTS_MAX = 3
N_EVENTS_CONTEXT = 6  # >= N_EVENTS_MAX

CONVERSATION_HOURS_WINDOW = 6  # in hours
CONVERSATION_MAX_MESSAGES = 10

LIMIT_ANSWERS_PER_WEEK = 10
LIMIT_BLOCKS_PER_WEEK = 3
LIMIT_MAX_USERS = 500

THRESHOLD_NOT_DELIVERED_ANSWER = 300  # in seconds

# non-mutable
TIMESTAMP_ORIGIN = "2023-01-01"
FAKE_USER_ID = -1
EMBEDDING_SIZE = 1536  # that's specific to OpenAIEmbeddings

# from .env
import os

import openai
from dotenv import load_dotenv

load_dotenv(override=True)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.organization = os.environ["OPENAI_ORGANIZATION_ID"]

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENV = os.environ.get("PINECONE_ENV")
PINECONE_INDEX = os.environ.get("PINECONE_INDEX")
PINECONE_NAMESPACE = os.environ.get("PINECONE_NAMESPACE")

SQLALCHEMY_DATABASE_URL = f"""\
postgresql\
://{os.environ.get("POSTGRES_USER")}\
:{os.environ.get("POSTGRES_PASSWORD")}\
@{os.environ.get("POSTGRES_HOST")}\
:{os.environ.get("POSTGRES_PORT")}\
/{os.environ.get("POSTGRES_DATABASE")}\
"""

WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
WHATSAPP_NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")
