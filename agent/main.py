"""Neuro-Trade: Autonomous Polymarket paper trading agent powered by OpenAI Agents SDK."""

import asyncio
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    WebSearchTool,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)

from mcp_servers.polymarket_server import polymarket_discovery_tools, polymarket_trading_tools
from mcp_servers.paper_trading_server import paper_trading_exec_tools, paper_trading_read_tools
from prompts.main_agent import MAIN_SYSTEM_PROMPT
from prompts.researcher import RESEARCHER_PROMPT
from prompts.trader import TRADER_PROMPT

# Load environment
load_dotenv()

API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("LLM_MODEL_NAME", "gpt-4.1")


def setup_openai_client():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("responses")
    set_tracing_disabled(True)


# --- Agent definitions ---

researcher_agent = Agent(
    name="researcher",
    instructions=RESEARCHER_PROMPT,
    tools=[WebSearchTool()],
    model=MODEL,
    handoff_description="Web research specialist. Transfer to this agent to research a prediction market topic — gathers news, analysis, and sentiment.",
)

trader_agent = Agent(
    name="trader",
    instructions=TRADER_PROMPT,
    tools=polymarket_trading_tools + paper_trading_exec_tools,
    model=MODEL,
    handoff_description="Trading execution specialist. Transfer to this agent with market details and probability estimate to analyze orderbooks and execute paper trades.",
)

main_agent = Agent(
    name="orchestrator",
    instructions=MAIN_SYSTEM_PROMPT,
    tools=polymarket_discovery_tools + paper_trading_read_tools,
    handoffs=[researcher_agent, trader_agent],
    model=MODEL,
)


async def main():
    setup_openai_client()

    print("=== Neuro-Trade Paper Trading Agent ===")
    print(f"Model: {MODEL}")
    print("Starting with $1,000 paper money against real Polymarket orderbooks.\n")

    result = await Runner.run(
        main_agent,
        "Scan Polymarket for interesting prediction markets. "
        "Find 2-3 markets where you think public sentiment or recent news creates an edge. "
        "Research each one, then make paper trades where you see value.",
        max_turns=50,
    )

    print("\n=== Agent Output ===")
    print(result.final_output)
    print(f"\n=== Finished (last agent: {result.last_agent.name}) ===")


if __name__ == "__main__":
    asyncio.run(main())
