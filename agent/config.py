import os
from pathlib import Path

# Polymarket API endpoints (all read-only, no auth needed)
GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"

# Paper trading settings
STARTING_BALANCE = 1000.0
MAX_TRADE_SIZE = 100.0
MAX_POSITION_PCT = 0.30  # max 30% of portfolio in one market

# Paths
AGENT_DIR = Path(__file__).parent
DATA_DIR = AGENT_DIR / "data"
DB_PATH = DATA_DIR / "portfolio.db"
PIPELINE_DB_PATH = DATA_DIR / "pipeline.db"

# MiroFish API
MIROFISH_API_URL = os.getenv("MIROFISH_API_URL", "http://localhost:5001")

# Agent server
AGENT_SERVER_PORT = int(os.getenv("AGENT_SERVER_PORT", "8000"))
