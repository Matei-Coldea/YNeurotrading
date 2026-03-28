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
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("responses")
    set_tracing_disabled(True)


def build_agents():
    # Create orchestrator first (referenced by sub-agents for handoff-back)
    main_agent = Agent(
        name="orchestrator",
        instructions=MAIN_SYSTEM_PROMPT,
        tools=polymarket_discovery_tools + paper_trading_read_tools,
        handoffs=[],  # filled below
        model=MODEL,
    )

    researcher_agent = Agent(
        name="researcher",
        instructions=RESEARCHER_PROMPT + "\n\nAfter completing your research brief, ALWAYS transfer back to the orchestrator so it can continue the trading workflow.",
        tools=[WebSearchTool()],
        handoffs=[main_agent],
        model=MODEL,
        handoff_description="Web research specialist. Transfer to this agent to research a prediction market topic — gathers news, analysis, and sentiment.",
    )

    trader_agent = Agent(
        name="trader",
        instructions=TRADER_PROMPT + "\n\nAfter executing a trade (or deciding not to), ALWAYS transfer back to the orchestrator so it can continue with the next market or wrap up.",
        tools=polymarket_trading_tools + paper_trading_exec_tools,
        handoffs=[main_agent],
        model=MODEL,
        handoff_description="Trading execution specialist. Transfer to this agent with market details and probability estimate to analyze orderbooks and execute paper trades.",
    )

    # Wire up orchestrator handoffs
    main_agent.handoffs = [researcher_agent, trader_agent]

    return main_agent


async def run(prompt: str, max_turns: int = 50):
    setup_openai_client()
    agent = build_agents()
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
    print(f"\n=== Finished (last agent: {result.last_agent.name}) ===")
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
    asyncio.run(main())
