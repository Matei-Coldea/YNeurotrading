from .models import FillResult


def simulate_buy(asks: list[dict], amount_usd: float, midpoint: float | None = None) -> FillResult:
    """Simulate a market buy by walking the ask side of the orderbook.

    Args:
        asks: List of {"price": str/float, "size": str/float} sorted by price ascending.
        amount_usd: Dollar amount to spend.
        midpoint: Optional midpoint price for slippage calculation.

    Returns:
        FillResult with shares acquired, average price, total cost, and slippage.
    """
    # Sort asks ascending by price (cheapest first) — CLOB API may return them in any order
    asks = sorted(asks, key=lambda x: float(x["price"]))

    remaining_usd = amount_usd
    total_shares = 0.0
    total_spent = 0.0

    for level in asks:
        if remaining_usd <= 0:
            break
        price = float(level["price"])
        size = float(level["size"])
        if price <= 0:
            continue

        max_shares_at_level = remaining_usd / price
        fill_shares = min(size, max_shares_at_level)
        cost = fill_shares * price

        total_shares += fill_shares
        total_spent += cost
        remaining_usd -= cost

    if total_shares == 0:
        return FillResult(shares=0, avg_price=0, total_cost=0, slippage=0)

    avg_price = total_spent / total_shares
    slippage = (avg_price - midpoint) / midpoint if midpoint and midpoint > 0 else 0.0

    return FillResult(
        shares=total_shares,
        avg_price=avg_price,
        total_cost=total_spent,
        slippage=slippage,
    )


def simulate_sell(bids: list[dict], shares: float, midpoint: float | None = None) -> FillResult:
    """Simulate a market sell by walking the bid side of the orderbook.

    Args:
        bids: List of {"price": str/float, "size": str/float} sorted by price descending.
        shares: Number of shares to sell.
        midpoint: Optional midpoint price for slippage calculation.

    Returns:
        FillResult with shares sold, average price, total proceeds, and slippage.
    """
    # Sort bids descending by price (highest first) — CLOB API may return them in any order
    bids = sorted(bids, key=lambda x: float(x["price"]), reverse=True)

    remaining_shares = shares
    total_proceeds = 0.0
    total_sold = 0.0

    for level in bids:
        if remaining_shares <= 0:
            break
        price = float(level["price"])
        size = float(level["size"])
        if price <= 0:
            continue

        fill_shares = min(size, remaining_shares)
        proceeds = fill_shares * price

        total_sold += fill_shares
        total_proceeds += proceeds
        remaining_shares -= fill_shares

    if total_sold == 0:
        return FillResult(shares=0, avg_price=0, total_cost=0, slippage=0)

    avg_price = total_proceeds / total_sold
    slippage = (midpoint - avg_price) / midpoint if midpoint and midpoint > 0 else 0.0

    return FillResult(
        shares=total_sold,
        avg_price=avg_price,
        total_cost=total_proceeds,
        slippage=slippage,
    )
