"""Paper trading tools — simulated trading against real Polymarket orderbooks."""

import json
from typing import Annotated

from agents import function_tool

from config import STARTING_BALANCE, MAX_TRADE_SIZE
from paper_trading.portfolio import Portfolio
from paper_trading.fill_engine import simulate_buy, simulate_sell
from paper_trading.journal import add_entry, get_entries
from mcp_servers.polymarket_server import clob_client

# Shared portfolio instance
portfolio = Portfolio()


@function_tool
def buy(
    token_id: Annotated[str, "The CLOB token ID for the outcome to buy"],
    market_question: Annotated[str, "The market question (for record keeping)"],
    outcome: Annotated[str, "The outcome name (e.g., 'Yes' or 'No')"],
    amount_usd: Annotated[float, "Dollar amount to spend on this purchase"],
) -> str:
    """Buy shares of a Polymarket outcome using paper money. Simulates a market buy against the real orderbook with realistic slippage."""
    if amount_usd > MAX_TRADE_SIZE:
        return json.dumps({"error": f"Trade size ${amount_usd:.2f} exceeds max ${MAX_TRADE_SIZE:.2f}"})

    balance = portfolio.get_balance()
    if amount_usd > balance:
        return json.dumps({"error": f"Insufficient balance: have ${balance:.2f}, want to spend ${amount_usd:.2f}"})

    book = clob_client.get_order_book(token_id)
    asks = [{"price": o.price, "size": o.size} for o in book.asks] if book.asks else []
    if not asks:
        return json.dumps({"error": f"No asks in orderbook for token {token_id} — market may be illiquid"})

    try:
        midpoint = float(clob_client.get_midpoint(token_id))
    except Exception:
        midpoint = None

    fill = simulate_buy(asks, amount_usd, midpoint)
    if fill.shares == 0:
        return json.dumps({"error": "Could not fill any shares — orderbook may be empty or prices too high"})

    portfolio.record_buy(token_id, market_question, outcome, fill.shares, fill.avg_price, fill.total_cost)

    return json.dumps({
        "status": "filled",
        "token_id": token_id,
        "outcome": outcome,
        "shares_acquired": round(fill.shares, 4),
        "avg_price": round(fill.avg_price, 4),
        "total_cost": round(fill.total_cost, 2),
        "slippage": f"{fill.slippage:.2%}",
        "remaining_balance": round(portfolio.get_balance(), 2),
    })


@function_tool
def sell(
    token_id: Annotated[str, "The CLOB token ID for the outcome to sell"],
    shares: Annotated[float, "Number of shares to sell"],
) -> str:
    """Sell shares of a Polymarket outcome for paper money. Simulates a market sell against the real orderbook."""
    position = portfolio.get_position(token_id)
    if not position:
        return json.dumps({"error": f"No position found for token {token_id}"})
    if position.shares < shares:
        return json.dumps({"error": f"Insufficient shares: have {position.shares:.4f}, want to sell {shares:.4f}"})

    book = clob_client.get_order_book(token_id)
    bids = [{"price": o.price, "size": o.size} for o in book.bids] if book.bids else []
    if not bids:
        return json.dumps({"error": f"No bids in orderbook for token {token_id} — market may be illiquid"})

    try:
        midpoint = float(clob_client.get_midpoint(token_id))
    except Exception:
        midpoint = None

    fill = simulate_sell(bids, shares, midpoint)
    if fill.shares == 0:
        return json.dumps({"error": "Could not fill any shares — orderbook may be empty"})

    portfolio.record_sell(token_id, fill.shares, fill.avg_price, fill.total_cost)

    return json.dumps({
        "status": "filled",
        "token_id": token_id,
        "outcome": position.outcome,
        "shares_sold": round(fill.shares, 4),
        "avg_price": round(fill.avg_price, 4),
        "total_proceeds": round(fill.total_cost, 2),
        "slippage": f"{fill.slippage:.2%}",
        "remaining_balance": round(portfolio.get_balance(), 2),
    })


@function_tool
def get_portfolio() -> str:
    """Get current paper trading portfolio: cash balance and all open positions."""
    balance = portfolio.get_balance()
    positions = portfolio.get_positions()
    return json.dumps({
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
    }, default=str)


@function_tool
def get_trade_history(
    limit: Annotated[int, "Maximum number of trades to return"] = 20,
) -> str:
    """Get recent paper trade history."""
    trades = portfolio.get_trade_history(limit)
    return json.dumps([
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
    ], default=str)


@function_tool
def get_pnl_summary() -> str:
    """Get paper trading P&L summary: cash balance, number of trades, and profit/loss."""
    return json.dumps(portfolio.get_pnl_summary(), default=str)


@function_tool
def reset_portfolio(
    starting_balance: Annotated[float, "Starting balance in USD"] = STARTING_BALANCE,
) -> str:
    """Reset the paper trading portfolio to a fresh state with a specified starting balance."""
    portfolio.reset(starting_balance)
    return json.dumps({"status": "reset", "new_balance": starting_balance})


@function_tool
def log_trade_analysis(
    market_question: Annotated[str, "The market question"],
    action: Annotated[str, "What you did: 'buy', 'sell', or 'skip'"],
    reasoning: Annotated[str, "Your analysis: research findings, probability estimate, edge calculation, and why you decided to act (or not)"],
    probability_estimate: Annotated[float, "Your estimated probability for the Yes outcome (0.0 to 1.0)"],
    market_price: Annotated[float, "The market's current implied probability"],
) -> str:
    """Log your analysis and reasoning for a trade decision. This persists across runs so you can recall why you made each trade. ALWAYS call this after every trade or skip decision."""
    add_entry({
        "market_question": market_question,
        "action": action,
        "reasoning": reasoning,
        "probability_estimate": probability_estimate,
        "market_price": market_price,
    })
    return json.dumps({"status": "logged"})


@function_tool
def get_trade_journal(
    limit: Annotated[int, "Maximum number of journal entries to return"] = 20,
) -> str:
    """Read your past trade analysis journal. Use this at the start of each run to recall your previous reasoning and positions."""
    entries = get_entries(limit)
    if not entries:
        return json.dumps({"entries": [], "message": "No previous journal entries. This is a fresh start."})
    return json.dumps({"entries": entries, "count": len(entries)}, default=str)


# Export tool lists
paper_trading_all_tools = [
    buy, sell, get_portfolio, get_trade_history, get_pnl_summary, reset_portfolio,
    log_trade_analysis, get_trade_journal,
]
