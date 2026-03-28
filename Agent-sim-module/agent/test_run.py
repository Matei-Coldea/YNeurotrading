"""Minimal test run — searches for 1 market, does 1 web search. Low token usage."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import run

asyncio.run(run(
    "Search Polymarket for 1 active market about US politics. "
    "Then do a quick web search about that topic. "
    "Report what you found. Do NOT place any trades.",
    max_turns=10,
))
