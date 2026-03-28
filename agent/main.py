"""Neuro-Trade: Autonomous Polymarket paper trading agent powered by Claude Agent SDK."""

import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    HookMatcher,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

from mcp_servers.polymarket_server import polymarket_server
from mcp_servers.paper_trading_server import paper_trading_server
from prompts.main_agent import MAIN_SYSTEM_PROMPT
from prompts.researcher import RESEARCHER_PROMPT
from prompts.trader import TRADER_PROMPT
from config import MAX_TRADE_SIZE


# --- Safety hook: enforce max trade size ---

async def enforce_trade_limits(input_data: dict, tool_use_id: str | None, context: Any) -> dict:
    tool_input = input_data.get("tool_input", {})
    amount = tool_input.get("amount_usd", 0)
    if amount > MAX_TRADE_SIZE:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Trade size ${amount:.2f} exceeds max ${MAX_TRADE_SIZE:.2f}",
            }
        }
    return {}


async def main():
    options = ClaudeAgentOptions(
        system_prompt=MAIN_SYSTEM_PROMPT,
        mcp_servers={
            "polymarket": polymarket_server,
            "paper_trading": paper_trading_server,
            # Future: "simulation": simulation_server
        },
        allowed_tools=[
            # Main agent can use sub-agents and read market data
            "Agent",
            "mcp__polymarket__search_markets",
            "mcp__polymarket__get_market_details",
            "mcp__polymarket__get_active_markets",
            "mcp__polymarket__get_market_tags",
            "mcp__polymarket__get_orderbook",
            "mcp__polymarket__get_price",
            "mcp__polymarket__get_midpoint",
            "mcp__paper_trading__get_portfolio",
            "mcp__paper_trading__get_pnl_summary",
            "mcp__paper_trading__get_trade_history",
        ],
        agents={
            "researcher": AgentDefinition(
                description="Web research specialist. Use this to research a prediction market topic — gathers news, analysis, and sentiment.",
                prompt=RESEARCHER_PROMPT,
                tools=["WebSearch", "WebFetch"],
                model="sonnet",
            ),
            "trader": AgentDefinition(
                description="Trading execution specialist. Use this to analyze orderbooks and execute paper trades on Polymarket.",
                prompt=TRADER_PROMPT,
                tools=[
                    "mcp__polymarket__get_orderbook",
                    "mcp__polymarket__get_price",
                    "mcp__polymarket__get_midpoint",
                    "mcp__paper_trading__buy",
                    "mcp__paper_trading__sell",
                    "mcp__paper_trading__get_portfolio",
                ],
                model="sonnet",
            ),
        },
        hooks={
            "PreToolUse": [
                HookMatcher(
                    matcher="mcp__paper_trading__buy",
                    hooks=[enforce_trade_limits],
                ),
            ],
        },
        max_turns=50,
    )

    print("=== Neuro-Trade Paper Trading Agent ===")
    print("Starting with $1,000 paper money against real Polymarket orderbooks.\n")

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "Scan Polymarket for interesting prediction markets. "
            "Find 2-3 markets where you think public sentiment or recent news creates an edge. "
            "Research each one, then make paper trades where you see value."
        )
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
            elif isinstance(message, ResultMessage):
                print(f"\n=== Agent finished (stop reason: {message.stop_reason}) ===")
                if message.result:
                    print(message.result)


if __name__ == "__main__":
    asyncio.run(main())
