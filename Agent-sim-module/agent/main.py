"""Neuro-Trade: Autonomous Polymarket paper trading agent powered by OpenAI Agents SDK."""

import asyncio
import os
import sys
from pathlib import Path

# Ensure agent/ is on sys.path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)

from mcp_servers.polymarket_server import polymarket_all_tools
from mcp_servers.paper_trading_server import paper_trading_all_tools
from mcp_servers.web_search import web_search
from prompts.main_agent import MAIN_SYSTEM_PROMPT
from logger import AgentLogger, get_logger

# Load .env — check agent/ first, fall back to mirofish/
_agent_dir = Path(__file__).parent
_env_candidates = [_agent_dir / ".env", _agent_dir.parent / "mirofish" / ".env"]
for env_path in _env_candidates:
    if env_path.exists():
        load_dotenv(env_path)
        break

API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("LLM_MODEL_NAME", "gpt-4.1")


def setup_openai_client():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, max_retries=5)
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("responses")
    set_tracing_disabled(True)


def build_agent():
    # Single agent with all tools — web search, market data, and paper trading.
    # Handoffs caused ping-pong issues with gpt-5.4-nano; a single agent with
    # clear workflow instructions is more reliable.
    # When we add MiroFish simulation later, it can be added as another tool here
    # or as a handoff to a dedicated simulation agent (with a larger model).
    return Agent(
        name="neuro-trader",
        instructions=MAIN_SYSTEM_PROMPT,
        tools=polymarket_all_tools + paper_trading_all_tools + [web_search],
        model=MODEL,
    )


async def run(prompt: str, max_turns: int = 50):
    setup_openai_client()
    agent = build_agent()
    log, log_file = get_logger()

    log.info(f"Model: {MODEL}")
    log.info(f"Log file: {log_file}")
    print(f"=== Neuro-Trade Paper Trading Agent ===")
    print(f"Model: {MODEL}")
    print(f"Log: {log_file}\n")

    result = await Runner.run(
        agent,
        prompt,
        max_turns=max_turns,
        hooks=AgentLogger(),
    )

    print(f"\n=== Agent Output ===")
    print(result.final_output)
    print(f"\n=== Finished ===")
    log.info(f"Final output:\n{result.final_output}")
    return result


async def main():
    await run(
        "Scan Polymarket for interesting prediction markets. "
        "Find 2-3 markets where you think public sentiment or recent news creates an edge. "
        "Research each one, then make paper trades where you see value.",
        max_turns=50,
    )


if __name__ == "__main__":
    if "--server" in sys.argv:
        from server import start
        start()
    else:
        asyncio.run(main())
