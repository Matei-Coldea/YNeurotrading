"""Paper trading MCP server — simulated trading against real Polymarket orderbooks."""

import json
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from ..config import STARTING_BALANCE
from ..paper_trading.portfolio import Portfolio
from ..paper_trading.fill_engine import simulate_buy, simulate_sell
from .polymarket_server import clob_client

# Shared portfolio instance
portfolio = Portfolio()


def _text(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, default=str)}]}


def _error(msg: str) -> dict:
    return {"content": [{"type": "text", "text": json.dumps({"error": msg})}], "is_error": True}


@tool(
    "buy",
    "Buy shares of a Polymarket outcome using paper money. Simulates a market buy against the real orderbook with realistic slippage.",
    {"token_id": str, "market_question": str, "outcome": str, "amount_usd": float},
)
async def buy(args: dict[str, Any]) -> dict:
    token_id = args["token_id"]
    amount_usd = args["amount_usd"]
    market_question = args["market_question"]
    outcome = args["outcome"]

    balance = portfolio.get_balance()
    if amount_usd > balance:
        return _error(f"Insufficient balance: have ${balance:.2f}, want to spend ${amount_usd:.2f}")

    # Fetch real orderbook
    book = clob_client.get_order_book(token_id)
    asks = [{"price": o.price, "size": o.size} for o in book.asks] if book.asks else []
    if not asks:
        return _error(f"No asks in orderbook for token {token_id} — market may be illiquid")

    # Get midpoint for slippage calc
    try:
        midpoint = float(clob_client.get_midpoint(token_id))
    except Exception:
        midpoint = None

    fill = simulate_buy(asks, amount_usd, midpoint)
    if fill.shares == 0:
        return _error("Could not fill any shares — orderbook may be empty or prices too high")

    portfolio.record_buy(token_id, market_question, outcome, fill.shares, fill.avg_price, fill.total_cost)

    return _text({
        "status": "filled",
        "token_id": token_id,
        "outcome": outcome,
        "shares_acquired": round(fill.shares, 4),
        "avg_price": round(fill.avg_price, 4),
        "total_cost": round(fill.total_cost, 2),
        "slippage": f"{fill.slippage:.2%}",
        "remaining_balance": round(portfolio.get_balance(), 2),
    })


@tool(
    "sell",
    "Sell shares of a Polymarket outcome for paper money. Simulates a market sell against the real orderbook.",
    {"token_id": str, "shares": float},
)
async def sell(args: dict[str, Any]) -> dict:
    token_id = args["token_id"]
    shares = args["shares"]

    position = portfolio.get_position(token_id)
    if not position:
        return _error(f"No position found for token {token_id}")
    if position.shares < shares:
        return _error(f"Insufficient shares: have {position.shares:.4f}, want to sell {shares:.4f}")

    book = clob_client.get_order_book(token_id)
    bids = [{"price": o.price, "size": o.size} for o in book.bids] if book.bids else []
    if not bids:
        return _error(f"No bids in orderbook for token {token_id} — market may be illiquid")

    try:
        midpoint = float(clob_client.get_midpoint(token_id))
    except Exception:
        midpoint = None

    fill = simulate_sell(bids, shares, midpoint)
    if fill.shares == 0:
        return _error("Could not fill any shares — orderbook may be empty")

    portfolio.record_sell(token_id, fill.shares, fill.avg_price, fill.total_cost)

    return _text({
        "status": "filled",
        "token_id": token_id,
        "outcome": position.outcome,
        "shares_sold": round(fill.shares, 4),
        "avg_price": round(fill.avg_price, 4),
        "total_proceeds": round(fill.total_cost, 2),
        "slippage": f"{fill.slippage:.2%}",
        "remaining_balance": round(portfolio.get_balance(), 2),
    })


@tool(
    "get_portfolio",
    "Get current paper trading portfolio: cash balance and all open positions.",
    {},
)
async def get_portfolio(args: dict[str, Any]) -> dict:
    balance = portfolio.get_balance()
    positions = portfolio.get_positions()
    return _text({
        "cash_balance": round(balance, 2),
        "positions": [
            {
                "token_id": p.token_id,
                "market_question": p.market_question,
                "outcome": p.outcome,
                "shares": round(p.shares, 4),
                "avg_cost": round(p.avg_cost, 4),
            }
            for p in positions
        ],
        "num_positions": len(positions),
    })


@tool(
    "get_trade_history",
    "Get recent paper trade history.",
    {"limit": int},
)
async def get_trade_history(args: dict[str, Any]) -> dict:
    limit = args.get("limit", 20)
    trades = portfolio.get_trade_history(limit)
    return _text([
        {
            "id": t.id,
            "side": t.side,
            "outcome": t.outcome,
            "market_question": t.market_question,
            "shares": round(t.shares, 4),
            "price": round(t.price, 4),
            "amount_usd": round(t.amount_usd, 2),
            "created_at": str(t.created_at),
        }
        for t in trades
    ])


@tool(
    "get_pnl_summary",
    "Get paper trading P&L summary: cash balance, number of trades, and profit/loss.",
    {},
)
async def get_pnl_summary(args: dict[str, Any]) -> dict:
    return _text(portfolio.get_pnl_summary())


@tool(
    "reset_portfolio",
    "Reset the paper trading portfolio to a fresh state with a specified starting balance.",
    {"starting_balance": float},
)
async def reset_portfolio(args: dict[str, Any]) -> dict:
    balance = args.get("starting_balance", STARTING_BALANCE)
    portfolio.reset(balance)
    return _text({"status": "reset", "new_balance": balance})


paper_trading_tools = [buy, sell, get_portfolio, get_trade_history, get_pnl_summary, reset_portfolio]

paper_trading_server = create_sdk_mcp_server(
    name="paper_trading",
    version="0.1.0",
    tools=paper_trading_tools,
)
