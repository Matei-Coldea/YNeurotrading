"""Test run — find 1 market, research it, place 1 small paper trade. All fictional."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import run

asyncio.run(run(
    "Search Polymarket for any 1 active prediction market with good liquidity (any topic is fine). "
    "Pick one that looks interesting. Research the topic briefly, then place ONE small paper trade "
    "($20-30) if you see any edge. If the first search doesn't find US politics, that's fine — "
    "trade on whatever interesting market you find. "
    "Report your reasoning and the trade result. "
    "This is paper trading with fictional money — no real funds are involved.",
    max_turns=20,
))
