"""Polymarket tools — read-only market data wrapping Gamma API + py-clob-client."""

import json
from typing import Annotated

import httpx
from py_clob_client.client import ClobClient
from agents import function_tool

from config import GAMMA_API_URL, CLOB_API_URL

# Shared clients (read-only, no auth)
clob_client = ClobClient(CLOB_API_URL)
http_client = httpx.Client(base_url=GAMMA_API_URL, timeout=30)


@function_tool
def search_markets(
    query: Annotated[str, "Search query to match against market titles"],
    limit: Annotated[int, "Maximum number of events to return"] = 30,
    volume_num_min: Annotated[int, "Minimum volume in USD to filter out low-activity markets"] = 5000,
) -> str:
    """Search Polymarket for prediction markets matching a query. Returns events sorted by volume (highest first) with their markets, outcomes, and prices."""
    params: dict = {
        "title_contains": query,
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume",
        "ascending": "false",
    }
    if volume_num_min:
        params["volume_num_min"] = volume_num_min
    resp = http_client.get("/events", params=params)
    resp.raise_for_status()
    events = resp.json()
    results = []
    for event in events:
        markets = event.get("markets", [])
        # Pick only the highest-volume market per event to avoid flooding
        # results with sub-markets from the same event (e.g., 50 state-level
        # election markets from one "US Elections" event)
        top = max(markets, key=lambda m: float(m.get("volume") or 0)) if markets else None
        if top:
            results.append({
                "event_title": event.get("title"),
                "market_id": top.get("id"),
                "question": top.get("question"),
                "outcomes": top.get("outcomes"),
                "outcome_prices": top.get("outcomePrices"),
                "volume": top.get("volume"),
                "liquidity": top.get("liquidity"),
                "end_date": top.get("endDate") or event.get("endDate"),
                "token_ids": top.get("clobTokenIds") or [],
                "other_markets_in_event": len(markets) - 1,
            })
    return json.dumps(results, default=str)


@function_tool
def get_market_details(
    market_id: Annotated[str, "The Polymarket market ID"],
) -> str:
    """Get detailed information about a specific Polymarket market by its ID."""
    resp = http_client.get(f"/markets/{market_id}")
    resp.raise_for_status()
    m = resp.json()
    return json.dumps({
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
    }, default=str)


@function_tool
def get_active_markets(
    tag: Annotated[str, "Optional tag to filter markets (e.g., 'Politics', 'Sports', 'Pop Culture')"] = "",
    limit: Annotated[int, "Maximum number of markets to return"] = 50,
    volume_num_min: Annotated[int, "Minimum volume in USD to filter out low-activity markets"] = 10000,
) -> str:
    """List active Polymarket markets sorted by volume (highest first), optionally filtered by tag. Good for discovering trading opportunities with real liquidity."""
    params: dict = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume",
        "ascending": "false",
    }
    if tag:
        params["tag"] = tag
    if volume_num_min:
        params["volume_num_min"] = volume_num_min
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
    return json.dumps(results, default=str)


@function_tool
def get_market_tags() -> str:
    """List all available market category tags on Polymarket (e.g., Politics, Sports, Crypto)."""
    resp = http_client.get("/tags")
    resp.raise_for_status()
    return json.dumps(resp.json(), default=str)


@function_tool
def get_orderbook(
    token_id: Annotated[str, "The CLOB token ID for a specific market outcome"],
) -> str:
    """Get the full orderbook (bids and asks) for a market outcome token. Use this to assess liquidity and depth before trading."""
    book = clob_client.get_order_book(token_id)
    return json.dumps({
        "token_id": token_id,
        "bids": [{"price": o.price, "size": o.size} for o in book.bids] if book.bids else [],
        "asks": [{"price": o.price, "size": o.size} for o in book.asks] if book.asks else [],
    }, default=str)


@function_tool
def get_price(
    token_id: Annotated[str, "The CLOB token ID for a specific market outcome"],
) -> str:
    """Get the current best price for a market outcome token."""
    price = clob_client.get_price(token_id, "BUY")
    return json.dumps({"token_id": token_id, "price": price}, default=str)


@function_tool
def get_midpoint(
    token_id: Annotated[str, "The CLOB token ID for a specific market outcome"],
) -> str:
    """Get the midpoint price between best bid and best ask for a market outcome token."""
    mid = clob_client.get_midpoint(token_id)
    return json.dumps({"token_id": token_id, "midpoint": mid}, default=str)


# Export tool lists for different agents
polymarket_all_tools = [
    search_markets,
    get_market_details,
    get_active_markets,
    get_market_tags,
    get_orderbook,
    get_price,
    get_midpoint,
]

# Read-only market discovery tools (for main agent)
polymarket_discovery_tools = [
    search_markets,
    get_market_details,
    get_active_markets,
    get_market_tags,
    get_orderbook,
    get_price,
    get_midpoint,
]

# Trading-relevant tools (for trader agent)
polymarket_trading_tools = [
    get_orderbook,
    get_price,
    get_midpoint,
]
