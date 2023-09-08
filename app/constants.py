# mutable
N_DOCS = 3

# non-mutable
CHROMA_DIR = "data/chroma/"
DB_PATH = "data/guidatorino_db.csv"
TIMESTAMP_ORIGIN = "2023-01-01"

# from .env
import os

from dotenv import find_dotenv, load_dotenv

_ = load_dotenv(find_dotenv())

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WHATSAPP_API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
WHATSAPP_NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
WHATSAPP_HOOK_TOKEN = os.environ.get("WHATSAPP_HOOK_TOKEN")
