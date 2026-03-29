"""Pydantic models for the Agent Server API."""

from datetime import datetime
from pydantic import BaseModel, Field


class Opportunity(BaseModel):
    id: str
    status: str = "discovered"
    # Market data
    market_id: str
    market_question: str
    market_description: str | None = None
    outcomes: list[str] | None = None
    outcome_prices: list[str] | None = None
    token_ids: list[str] | None = None
    volume: float | None = None
    liquidity: float | None = None
    end_date: str | None = None
    tags: list[str] | None = None
    # Agent analysis
    agent_hypothesis: str | None = None
    probability_estimate: float | None = None
    market_price: float | None = None
    estimated_edge: float | None = None
    simulation_rationale: str | None = None
    simulation_potential: int | None = None  # 1-5
    simulation_category: str | None = None  # "direct" or "indirect"
    # MiroFish simulation
    seed_document: str | None = None
    simulation_requirement: str | None = None
    mirofish_project_id: str | None = None
    mirofish_simulation_id: str | None = None
    mirofish_report_id: str | None = None
    simulation_report_summary: str | None = None
    simulation_sentiment: dict | None = None
    # Trade proposal + execution
    trade_side: str | None = None
    trade_outcome: str | None = None
    trade_token_id: str | None = None
    trade_amount_usd: float | None = None
    trade_reasoning: str | None = None
    trade_fill_price: float | None = None
    trade_fill_shares: float | None = None
    web_research_summary: str | None = None
    ensemble_agreement: float | None = None
    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Event(BaseModel):
    id: int | None = None
    opportunity_id: str | None = None
    event_type: str
    payload: dict | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScanRequest(BaseModel):
    tags: list[str] | None = None
    query: str | None = None
    limit: int = 10


class ScanStatus(BaseModel):
    status: str  # "idle" | "running" | "complete"
    opportunities_found: int = 0


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[dict]
    pnl_summary: dict
    num_positions: int
