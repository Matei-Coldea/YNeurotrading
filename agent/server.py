"""Neuro-Trade Agent Server — FastAPI backend for the trading dashboard."""

import asyncio
import json
import sys
from pathlib import Path

# Ensure agent/ is on sys.path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from config import AGENT_SERVER_PORT
from api_models import Opportunity, ScanRequest, ScanStatus, PortfolioResponse
from pipeline_db import PipelineDB
from paper_trading.portfolio import Portfolio

# Load .env
_agent_dir = Path(__file__).parent
_env_candidates = [_agent_dir / ".env", _agent_dir.parent / "mirofish" / ".env"]
for env_path in _env_candidates:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Shared state
pipeline_db = PipelineDB()
portfolio = Portfolio()

# Scan state (in-memory, managed by orchestrator)
_scan_status = ScanStatus(status="idle", opportunities_found=0)
_scan_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown."""
    yield


app = FastAPI(title="Neuro-Trade Agent Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──── Scanning & Discovery ────


@app.post("/api/agent/scan")
async def start_scan(req: ScanRequest | None = None):
    """Trigger the agent to scan Polymarket for sentiment-driven markets."""
    global _scan_status
    async with _scan_lock:
        if _scan_status.status == "running":
            raise HTTPException(status_code=409, detail="Scan already running")
        _scan_status = ScanStatus(status="running", opportunities_found=0)

    pipeline_db.add_event("scan_started", payload={"tags": req.tags if req else None})

    # Import and run orchestrator in background
    from orchestrator import run_scan
    asyncio.create_task(_run_scan_background(req))

    return {"status": "running"}


async def _run_scan_background(req: ScanRequest | None):
    global _scan_status
    try:
        from orchestrator import run_scan
        count = await run_scan(pipeline_db, req)
        _scan_status = ScanStatus(status="complete", opportunities_found=count)
        pipeline_db.add_event("scan_complete", payload={"opportunities_found": count})
    except Exception as e:
        _scan_status = ScanStatus(status="idle", opportunities_found=0)
        pipeline_db.add_event("error", payload={"message": str(e), "phase": "scan"})


@app.get("/api/agent/scan/status")
async def get_scan_status():
    return _scan_status


# ──── Opportunities ────


@app.get("/api/agent/opportunities")
async def list_opportunities(status: str | None = Query(None)):
    opps = pipeline_db.list_opportunities(status=status)
    return {"opportunities": [o.model_dump() for o in opps]}


@app.get("/api/agent/opportunities/{opp_id}")
async def get_opportunity(opp_id: str):
    opp = pipeline_db.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"opportunity": opp.model_dump()}


@app.post("/api/agent/opportunities/{opp_id}/approve-simulation")
async def approve_simulation(opp_id: str):
    """User approves running a MiroFish simulation for this opportunity."""
    opp = pipeline_db.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status not in ("discovered", "simulation_proposed"):
        raise HTTPException(status_code=400, detail=f"Cannot start simulation from status '{opp.status}'")

    pipeline_db.update_opportunity(opp_id, status="simulation_approved")
    pipeline_db.add_event("simulation_approved", opportunity_id=opp_id)

    # Run simulation in background
    from orchestrator import run_simulation
    asyncio.create_task(_run_simulation_background(opp_id))

    return {"status": "simulation_approved", "opportunity_id": opp_id}


async def _run_simulation_background(opp_id: str):
    try:
        from orchestrator import run_simulation
        await run_simulation(pipeline_db, opp_id)
    except Exception as e:
        pipeline_db.update_opportunity(opp_id, status="failed")
        pipeline_db.add_event("error", opportunity_id=opp_id, payload={"message": str(e), "phase": "simulation"})


@app.post("/api/agent/opportunities/{opp_id}/reject")
async def reject_opportunity(opp_id: str):
    opp = pipeline_db.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    pipeline_db.update_opportunity(opp_id, status="rejected")
    pipeline_db.add_event("rejected", opportunity_id=opp_id)
    return {"status": "rejected", "opportunity_id": opp_id}


@app.post("/api/agent/opportunities/{opp_id}/approve-trade")
async def approve_trade(opp_id: str):
    """User approves the proposed trade."""
    opp = pipeline_db.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status != "trade_proposed":
        raise HTTPException(status_code=400, detail=f"No trade proposal pending (status: '{opp.status}')")

    pipeline_db.update_opportunity(opp_id, status="trade_approved")
    pipeline_db.add_event("trade_approved", opportunity_id=opp_id)

    # Execute trade in background
    from orchestrator import execute_trade
    asyncio.create_task(_run_trade_background(opp_id))

    return {"status": "trade_approved", "opportunity_id": opp_id}


async def _run_trade_background(opp_id: str):
    try:
        from orchestrator import execute_trade
        await execute_trade(pipeline_db, opp_id)
    except Exception as e:
        pipeline_db.update_opportunity(opp_id, status="failed")
        pipeline_db.add_event("error", opportunity_id=opp_id, payload={"message": str(e), "phase": "trade"})


@app.post("/api/agent/opportunities/{opp_id}/reject-trade")
async def reject_trade(opp_id: str):
    opp = pipeline_db.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.status != "trade_proposed":
        raise HTTPException(status_code=400, detail=f"No trade proposal pending (status: '{opp.status}')")
    pipeline_db.update_opportunity(opp_id, status="simulation_complete")  # Go back to post-simulation state
    pipeline_db.add_event("trade_rejected", opportunity_id=opp_id)
    return {"status": "trade_rejected", "opportunity_id": opp_id}


# ──── Portfolio ────


@app.get("/api/agent/portfolio")
async def get_portfolio():
    balance = portfolio.get_balance()
    positions = portfolio.get_positions()
    pnl = portfolio.get_pnl_summary()
    return PortfolioResponse(
        cash_balance=balance,
        positions=[
            {
                "token_id": p.token_id,
                "market_question": p.market_question,
                "outcome": p.outcome,
                "shares": round(p.shares, 4),
                "avg_cost": round(p.avg_cost, 4),
            }
            for p in positions
        ],
        pnl_summary=pnl,
        num_positions=len(positions),
    )


@app.get("/api/agent/portfolio/trades")
async def get_trade_history(limit: int = Query(20)):
    trades = portfolio.get_trade_history(limit)
    return {
        "trades": [
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
        ]
    }


# ──── SSE Event Stream ────


@app.get("/api/agent/stream")
async def event_stream(last_id: int = Query(0)):
    """Server-Sent Events stream for all pipeline events."""
    return EventSourceResponse(_generate_events(last_id=last_id))


@app.get("/api/agent/stream/{opp_id}")
async def event_stream_for_opportunity(opp_id: str, last_id: int = Query(0)):
    """SSE stream filtered to a single opportunity."""
    return EventSourceResponse(_generate_events(last_id=last_id, opp_id=opp_id))


async def _generate_events(last_id: int = 0, opp_id: str | None = None):
    """Yield SSE events as they appear in the events table."""
    current_id = last_id
    while True:
        events = pipeline_db.get_events(since_id=current_id, opportunity_id=opp_id)
        for event in events:
            current_id = event.id
            yield {
                "id": str(event.id),
                "event": event.event_type,
                "data": json.dumps({
                    "opportunity_id": event.opportunity_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }),
            }
        await asyncio.sleep(1)


# ──── Entry point ────


def start():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_SERVER_PORT)


if __name__ == "__main__":
    start()
