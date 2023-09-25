# mutable
N_DOCS = 3

LIMIT_ANSWERS_PER_WEEK = 3
LIMIT_BLOCKS_PER_WEEK = 3
LIMIT_MAX_USERS = 500

# non-mutable
TIMESTAMP_ORIGIN = "2023-01-01"

# from .env
import os

import openai
from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())

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
# SQLALCHEMY_DATABASE_URL = "sqlite:///./data/test.db"

WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
WHATSAPP_NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")
