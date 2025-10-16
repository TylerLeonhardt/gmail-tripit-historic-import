"""Settings and configuration management"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Gmail API
SCOPES = ['https://mail.google.com/']
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

# TripIt
TRIPIT_EMAIL = os.getenv("TRIPIT_EMAIL", "plans@tripit.com")

# Database
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "state.db"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "processor.log"))

# Rate Limiting
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
FORWARD_BATCH_SIZE = int(os.getenv("FORWARD_BATCH_SIZE", "50"))

# Search Query
DEFAULT_SEARCH_QUERY = """
(subject:(confirmation OR itinerary) (flight OR airline))
OR "boarding pass"
OR from:(united.com OR delta.com OR aa.com OR southwest.com OR jetblue.com)
after:2000/01/01
""".strip()

SEARCH_QUERY = os.getenv("SEARCH_QUERY", DEFAULT_SEARCH_QUERY)

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
