from datetime import datetime
from pydantic import BaseModel, Field


class Position(BaseModel):
    token_id: str
    market_question: str
    outcome: str
    shares: float
    avg_cost: float
    created_at: datetime = Field(default_factory=datetime.now)


class Trade(BaseModel):
    id: int | None = None
    token_id: str
    market_question: str
    outcome: str
    side: str  # "buy" or "sell"
    shares: float
    price: float
    amount_usd: float
    created_at: datetime = Field(default_factory=datetime.now)


class FillResult(BaseModel):
    shares: float
    avg_price: float
    total_cost: float
    slippage: float  # vs midpoint, as fraction


class PortfolioSnapshot(BaseModel):
    balance: float
    positions: list[Position]
    total_value: float
    unrealized_pnl: float
