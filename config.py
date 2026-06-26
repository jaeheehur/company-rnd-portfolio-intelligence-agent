import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_EMBED_MODEL = "gemini-embedding-001"

GOOGLE_CLOUD_PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
BIGQUERY_PATENTS_TABLE = "patents-public-data.patents.publications"

DART_API_KEY = os.environ["DART_API_KEY"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

REPORTS_DIR = "data/reports"
