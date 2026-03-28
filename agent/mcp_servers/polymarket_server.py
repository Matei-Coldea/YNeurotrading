"""Polymarket MCP server — read-only market data tools wrapping Gamma API + py-clob-client."""

import json
from typing import Any

import httpx
from py_clob_client.client import ClobClient

from claude_agent_sdk import tool, create_sdk_mcp_server

from ..config import GAMMA_API_URL, CLOB_API_URL

# Shared clients (read-only, no auth)
clob_client = ClobClient(CLOB_API_URL)
http_client = httpx.Client(base_url=GAMMA_API_URL, timeout=30)


def _text(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, default=str)}]}


@tool(
    "search_markets",
    "Search Polymarket for prediction markets matching a query. Returns events with their markets, outcomes, and prices.",
    {"query": str, "limit": int},
)
async def search_markets(args: dict[str, Any]) -> dict:
    query = args["query"]
    limit = args.get("limit", 10)
    resp = http_client.get(
        "/events",
        params={"title_contains": query, "active": "true", "closed": "false", "limit": limit},
    )
    resp.raise_for_status()
    events = resp.json()
    results = []
    for event in events:
        markets = event.get("markets", [])
        results.append({
            "event_id": event.get("id"),
            "title": event.get("title"),
            "description": event.get("description", "")[:300],
            "end_date": event.get("endDate"),
            "markets": [
                {
                    "market_id": m.get("id"),
                    "question": m.get("question"),
                    "outcomes": m.get("outcomes"),
                    "outcome_prices": m.get("outcomePrices"),
                    "volume": m.get("volume"),
                    "liquidity": m.get("liquidity"),
                    "token_ids": [m.get("clobTokenIds", [None])[i] for i in range(len(m.get("outcomes", [])))],
                }
                for m in markets
            ],
        })
    return _text(results)


@tool(
    "get_market_details",
    "Get detailed information about a specific Polymarket market by its ID.",
    {"market_id": str},
)
async def get_market_details(args: dict[str, Any]) -> dict:
    market_id = args["market_id"]
    resp = http_client.get(f"/markets/{market_id}")
    resp.raise_for_status()
    m = resp.json()
    return _text({
        "market_id": m.get("id"),
        "question": m.get("question"),
        "description": m.get("description", "")[:500],
        "outcomes": m.get("outcomes"),
        "outcome_prices": m.get("outcomePrices"),
        "volume": m.get("volume"),
        "liquidity": m.get("liquidity"),
        "end_date": m.get("endDate"),
        "active": m.get("active"),
        "closed": m.get("closed"),
        "token_ids": m.get("clobTokenIds"),
        "tags": [t.get("label") for t in m.get("tags", [])],
    })


@tool(
    "get_active_markets",
    "List active Polymarket markets, optionally filtered by tag. Good for discovering trading opportunities.",
    {"tag": str, "limit": int},
)
async def get_active_markets(args: dict[str, Any]) -> dict:
    params: dict[str, Any] = {"active": "true", "closed": "false", "limit": args.get("limit", 20)}
    tag = args.get("tag")
    if tag:
        params["tag"] = tag
    resp = http_client.get("/markets", params=params)
    resp.raise_for_status()
    markets = resp.json()
    results = [
        {
            "market_id": m.get("id"),
            "question": m.get("question"),
            "outcomes": m.get("outcomes"),
            "outcome_prices": m.get("outcomePrices"),
            "volume": m.get("volume"),
            "liquidity": m.get("liquidity"),
            "end_date": m.get("endDate"),
        }
        for m in markets
    ]
    return _text(results)


@tool(
    "get_market_tags",
    "List all available market category tags on Polymarket (e.g., Politics, Sports, Crypto).",
    {},
)
async def get_market_tags(args: dict[str, Any]) -> dict:
    resp = http_client.get("/tags")
    resp.raise_for_status()
    return _text(resp.json())


@tool(
    "get_orderbook",
    "Get the full orderbook (bids and asks) for a market outcome token. Use this to assess liquidity and depth before trading.",
    {"token_id": str},
)
async def get_orderbook(args: dict[str, Any]) -> dict:
    token_id = args["token_id"]
    book = clob_client.get_order_book(token_id)
    return _text({
        "token_id": token_id,
        "bids": [{"price": o.price, "size": o.size} for o in book.bids] if book.bids else [],
        "asks": [{"price": o.price, "size": o.size} for o in book.asks] if book.asks else [],
    })


@tool(
    "get_price",
    "Get the current best price for a market outcome token.",
    {"token_id": str},
)
async def get_price(args: dict[str, Any]) -> dict:
    token_id = args["token_id"]
    price = clob_client.get_price(token_id, "BUY")
    return _text({"token_id": token_id, "price": price})


@tool(
    "get_midpoint",
    "Get the midpoint price between best bid and best ask for a market outcome token.",
    {"token_id": str},
)
async def get_midpoint(args: dict[str, Any]) -> dict:
    token_id = args["token_id"]
    mid = clob_client.get_midpoint(token_id)
    return _text({"token_id": token_id, "midpoint": mid})


# Export the MCP server and tool list
polymarket_tools = [
    search_markets,
    get_market_details,
    get_active_markets,
    get_market_tags,
    get_orderbook,
    get_price,
    get_midpoint,
]

polymarket_server = create_sdk_mcp_server(
    name="polymarket",
    version="0.1.0",
    tools=polymarket_tools,
)
