"""Phase-based agent orchestrator — drives scan, simulation, and trade phases."""

import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_api,
    set_tracing_disabled,
)

from api_models import Opportunity, ScanRequest
from pipeline_db import PipelineDB
from mcp_servers.polymarket_server import polymarket_all_tools
from mcp_servers.paper_trading_server import paper_trading_all_tools, buy, sell, portfolio as paper_portfolio
from mcp_servers.web_search import web_search
from prompts.main_agent import SCAN_SYSTEM_PROMPT, TRADE_PROPOSAL_PROMPT
from config import MIROFISH_API_URL

# Load .env
_agent_dir = Path(__file__).parent
_env_candidates = [_agent_dir / ".env", _agent_dir.parent / "mirofish" / ".env"]
for env_path in _env_candidates:
    if env_path.exists():
        load_dotenv(env_path)
        break

API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("LLM_MODEL_NAME", "gpt-4.1")

_client_initialized = False


def _ensure_client():
    global _client_initialized
    if not _client_initialized:
        client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL, max_retries=5)
        set_default_openai_client(client, use_for_tracing=False)
        set_default_openai_api("responses")
        set_tracing_disabled(True)
        _client_initialized = True


def _parse_json_objects(text: str) -> list[dict]:
    """Extract JSON objects from agent output, handling markdown code blocks."""
    objects = []
    # Try to find JSON in code blocks first
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text)
    search_text = "\n".join(code_blocks) if code_blocks else text

    # Find JSON objects by matching braces
    depth = 0
    start = None
    for i, ch in enumerate(search_text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(search_text[start:i + 1])
                    objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None
    return objects


# ──── Scan Phase ────


async def run_scan(db: PipelineDB, req: ScanRequest | None = None) -> int:
    """Scan Polymarket for sentiment-driven markets using the OpenAI Agent."""
    _ensure_client()

    scan_agent = Agent(
        name="market-scanner",
        instructions=SCAN_SYSTEM_PROMPT,
        tools=polymarket_all_tools + [web_search],
        model=MODEL,
    )

    prompt = "Scan Polymarket for prediction markets where social simulation would give us a trading edge."
    if req and req.tags:
        prompt += f" Focus on these categories: {', '.join(req.tags)}."
    if req and req.query:
        prompt += f" Also search for: {req.query}."
    if req and req.limit:
        prompt += f" Find up to {req.limit} markets."

    db.add_event("scan_started", payload={"prompt": prompt})

    result = await Runner.run(scan_agent, prompt, max_turns=30)

    # Parse opportunities from agent output
    json_objects = _parse_json_objects(result.final_output)
    count = 0
    for obj in json_objects:
        if "market_question" not in obj:
            continue
        opp_id = f"opp_{uuid.uuid4().hex[:8]}"
        opp = Opportunity(
            id=opp_id,
            status="discovered",
            market_id=obj.get("market_id", ""),
            market_question=obj["market_question"],
            market_description=obj.get("market_description"),
            outcomes=obj.get("outcomes"),
            outcome_prices=obj.get("outcome_prices"),
            token_ids=obj.get("token_ids"),
            volume=obj.get("volume"),
            liquidity=obj.get("liquidity"),
            end_date=obj.get("end_date"),
            tags=obj.get("tags"),
            agent_hypothesis=obj.get("agent_hypothesis"),
            probability_estimate=obj.get("probability_estimate"),
            market_price=obj.get("market_price"),
            estimated_edge=obj.get("estimated_edge"),
            simulation_rationale=obj.get("simulation_rationale"),
            simulation_potential=obj.get("simulation_potential"),
            web_research_summary=obj.get("web_research_summary"),
        )
        db.create_opportunity(opp)
        db.add_event("market_found", opportunity_id=opp_id, payload={
            "market_question": opp.market_question,
            "simulation_potential": opp.simulation_potential,
        })
        count += 1

    return count


# ──── Simulation Phase (Option B: project creation only, user does steps in MiroFish) ────


async def start_simulation_project(db: PipelineDB, opp_id: str) -> dict:
    """Generate seed doc + prompt, create MiroFish project (ontology only). Returns {project_id}.
    The user then walks through MiroFish UI for the remaining steps."""
    import io
    import httpx

    opp = db.get_opportunity(opp_id)
    if not opp:
        raise ValueError(f"Opportunity {opp_id} not found")

    db.update_opportunity(opp_id, status="simulation_running")
    db.add_event("simulation_started", opportunity_id=opp_id)

    # Step 1: Generate seed document and simulation requirement
    _ensure_client()
    seed_doc, sim_req = await _generate_seed_and_prompt(opp)
    db.update_opportunity(opp_id, seed_document=seed_doc, simulation_requirement=sim_req)
    db.add_event("seed_generated", opportunity_id=opp_id, payload={
        "seed_length": len(seed_doc), "requirement_length": len(sim_req),
    })

    # Step 2: Call MiroFish ontology/generate to create the project
    async with httpx.AsyncClient(base_url=MIROFISH_API_URL, timeout=120) as client:
        files = {"files": ("seed.txt", io.BytesIO(seed_doc.encode()), "text/plain")}
        data = {"simulation_requirement": sim_req}
        resp = await client.post("/api/graph/ontology/generate", files=files, data=data)
        resp.raise_for_status()
        result = resp.json()

    # MiroFish wraps response in {"data": {...}, "success": true}
    result_data = result.get("data", result)
    project_id = result_data.get("project_id")
    db.update_opportunity(opp_id, mirofish_project_id=project_id)
    db.add_event("project_created", opportunity_id=opp_id, payload={"project_id": project_id})

    return {"project_id": project_id}


async def sync_mirofish_status(db: PipelineDB, opp_id: str):
    """Check MiroFish API for simulation/report completion, update opportunity."""
    import httpx

    opp = db.get_opportunity(opp_id)
    if not opp or not opp.mirofish_project_id:
        raise ValueError(f"No MiroFish project for opportunity {opp_id}")

    async with httpx.AsyncClient(base_url=MIROFISH_API_URL, timeout=30) as client:
        # Find simulation for this project
        if not opp.mirofish_simulation_id:
            resp = await client.get("/api/simulation/list", params={"project_id": opp.mirofish_project_id})
            if resp.status_code == 200:
                sims = resp.json()
                sim_list = sims if isinstance(sims, list) else sims.get("simulations", sims.get("data", []))
                if sim_list:
                    sim = sim_list[0] if isinstance(sim_list[0], dict) else {"simulation_id": sim_list[0]}
                    sim_id = sim.get("simulation_id") or sim.get("id")
                    if sim_id:
                        db.update_opportunity(opp_id, mirofish_simulation_id=sim_id)
                        opp.mirofish_simulation_id = sim_id

        # Check simulation run status
        if opp.mirofish_simulation_id:
            resp = await client.get(f"/api/simulation/{opp.mirofish_simulation_id}/run-status")
            if resp.status_code == 200:
                run_data = resp.json()
                run_data = run_data.get("data", run_data) if isinstance(run_data, dict) else run_data
                runner_status = run_data.get("runner_status", "")
                if runner_status in ("completed", "complete", "done", "stopped"):
                    # Check for report
                    if not opp.mirofish_report_id:
                        report_id = None
                        report_complete = False

                        # Try report/check endpoint
                        resp2 = await client.get(f"/api/report/check/{opp.mirofish_simulation_id}")
                        if resp2.status_code == 200:
                            rd = resp2.json()
                            rd = rd.get("data", rd) if isinstance(rd, dict) else rd
                            report_id = rd.get("report_id")
                            report_complete = rd.get("report_status") in ("completed", "complete")

                        # Fallback: try report/by-simulation endpoint
                        if not report_id:
                            resp3 = await client.get(f"/api/report/by-simulation/{opp.mirofish_simulation_id}")
                            if resp3.status_code == 200:
                                rd3 = resp3.json()
                                rd3 = rd3.get("data", rd3) if isinstance(rd3, dict) else rd3
                                report_id = rd3.get("report_id") or rd3.get("id")
                                if report_id:
                                    report_complete = True  # If by-simulation returns it, it's done

                        if report_id:
                            db.update_opportunity(
                                opp_id,
                                mirofish_report_id=report_id,
                                status="simulation_complete" if report_complete else "simulation_running",
                            )
                            return db.get_opportunity(opp_id)

                    if opp.mirofish_report_id:
                        db.update_opportunity(opp_id, status="simulation_complete")
                        return db.get_opportunity(opp_id)

    return db.get_opportunity(opp_id)


async def analyze_report(db: PipelineDB, opp_id: str) -> dict:
    """Fetch MiroFish report, LLM generates trade proposal. Returns proposal dict."""
    import httpx

    opp = db.get_opportunity(opp_id)
    if not opp:
        raise ValueError(f"Opportunity {opp_id} not found")

    # First sync to make sure we have simulation_id and report_id
    if not opp.mirofish_report_id:
        opp = await sync_mirofish_status(db, opp_id)

    if not opp.mirofish_simulation_id:
        raise ValueError("No simulation found for this opportunity. Complete the simulation in MiroFish first.")

    # Fetch report from MiroFish
    report_text = ""
    async with httpx.AsyncClient(base_url=MIROFISH_API_URL, timeout=60) as client:
        resp = await client.get(f"/api/report/by-simulation/{opp.mirofish_simulation_id}")
        if resp.status_code == 200:
            report_data = resp.json()
            report_data = report_data.get("data", report_data) if isinstance(report_data, dict) else report_data
            # Full markdown content is the best source
            if report_data.get("markdown_content"):
                report_text = report_data["markdown_content"]
            # Fall back to outline sections
            elif report_data.get("outline", {}).get("sections"):
                for section in report_data["outline"]["sections"]:
                    report_text += section.get("content", "") + "\n\n"
            elif "sections" in report_data:
                for section in report_data["sections"]:
                    report_text += section.get("content", "") + "\n\n"

    if not report_text:
        raise ValueError("Could not fetch report from MiroFish. Generate the report in MiroFish first.")

    db.update_opportunity(opp_id, simulation_report_summary=report_text[:1000])

    # Generate trade proposal
    await _generate_trade_proposal(db, opp_id, report_text)

    opp = db.get_opportunity(opp_id)
    return {
        "trade_side": opp.trade_side,
        "trade_outcome": opp.trade_outcome,
        "trade_amount_usd": opp.trade_amount_usd,
        "trade_reasoning": opp.trade_reasoning,
        "simulation_sentiment": opp.simulation_sentiment,
        "probability_estimate": opp.probability_estimate,
        "estimated_edge": opp.estimated_edge,
    }


async def _generate_seed_and_prompt(opp: Opportunity) -> tuple[str, str]:
    """Use the LLM to generate a seed document and simulation requirement from market context."""
    _ensure_client()

    prompt = f"""Generate a seed document and simulation requirement for a social simulation about this prediction market.

Market Question: {opp.market_question}
Market Description: {opp.market_description or 'N/A'}
Agent Hypothesis: {opp.agent_hypothesis or 'N/A'}
Web Research: {opp.web_research_summary or 'N/A'}
Tags: {', '.join(opp.tags) if opp.tags else 'N/A'}

Output a JSON object with two fields:
- "seed_document": A 200-500 word news article describing the event/topic. Write it as a factual news piece that captures the key facts, stakeholders, and controversy.
- "simulation_requirement": A prompt for MiroFish describing what to simulate. Include: what platforms to simulate (Twitter), what mix of agents (60-70% individuals, 30-40% organizations/media), what behaviors to watch for, and how long to simulate (24-48 hours).

Output ONLY the JSON object, nothing else."""

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    text = response.choices[0].message.content
    objects = _parse_json_objects(text)
    if objects:
        return objects[0].get("seed_document", ""), objects[0].get("simulation_requirement", "")

    # Fallback: use market question directly
    return (
        f"News: {opp.market_question}\n\n{opp.market_description or ''}\n\n{opp.web_research_summary or ''}",
        f"Simulate public Twitter reaction to: {opp.market_question}. "
        f"Include 60-70% individual users and 30-40% organizations/media. Simulate 24 hours."
    )


async def _generate_trade_proposal(db: PipelineDB, opp_id: str, report_text: str):
    """Use the LLM to generate a trade proposal based on simulation results."""
    opp = db.get_opportunity(opp_id)
    if not opp:
        return

    _ensure_client()

    yes_price = opp.outcome_prices[0] if opp.outcome_prices and len(opp.outcome_prices) > 0 else "N/A"
    no_price = opp.outcome_prices[1] if opp.outcome_prices and len(opp.outcome_prices) > 1 else "N/A"
    yes_token = opp.token_ids[0] if opp.token_ids and len(opp.token_ids) > 0 else "N/A"
    no_token = opp.token_ids[1] if opp.token_ids and len(opp.token_ids) > 1 else "N/A"

    prompt = TRADE_PROPOSAL_PROMPT.format(
        simulation_report=report_text[:3000],  # Truncate to avoid token limits
        market_question=opp.market_question,
        yes_price=yes_price,
        no_price=no_price,
        pre_sim_estimate=opp.probability_estimate,
        yes_token_id=yes_token,
        no_token_id=no_token,
    )

    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    text = response.choices[0].message.content
    objects = _parse_json_objects(text)
    if not objects:
        db.add_event("error", opportunity_id=opp_id, payload={"message": "Failed to parse trade proposal"})
        return

    proposal = objects[0]
    updates = {
        "status": "trade_proposed",
        "trade_side": proposal.get("trade_side"),
        "trade_outcome": proposal.get("trade_outcome"),
        "trade_token_id": proposal.get("trade_token_id"),
        "trade_amount_usd": proposal.get("trade_amount_usd"),
        "trade_reasoning": proposal.get("trade_reasoning"),
        "simulation_sentiment": proposal.get("simulation_sentiment"),
        "probability_estimate": proposal.get("probability_estimate", opp.probability_estimate),
        "estimated_edge": proposal.get("estimated_edge", opp.estimated_edge),
    }
    db.update_opportunity(opp_id, **updates)
    db.add_event("trade_proposed", opportunity_id=opp_id, payload={
        "trade_side": proposal.get("trade_side"),
        "trade_outcome": proposal.get("trade_outcome"),
        "trade_amount_usd": proposal.get("trade_amount_usd"),
        "estimated_edge": proposal.get("estimated_edge"),
    })


# ──── Trade Execution Phase ────


async def execute_trade(db: PipelineDB, opp_id: str):
    """Execute the approved paper trade."""
    opp = db.get_opportunity(opp_id)
    if not opp:
        raise ValueError(f"Opportunity {opp_id} not found")

    if opp.trade_side == "skip":
        db.update_opportunity(opp_id, status="trade_executed")
        db.add_event("trade_skipped", opportunity_id=opp_id)
        return

    if not opp.trade_token_id or not opp.trade_amount_usd:
        raise ValueError("Trade proposal missing token_id or amount")

    # Use the paper trading buy/sell tools directly
    from mcp_servers.paper_trading_server import portfolio as paper_portfolio
    from paper_trading.fill_engine import simulate_buy, simulate_sell
    from mcp_servers.polymarket_server import clob_client

    token_id = opp.trade_token_id
    amount = opp.trade_amount_usd

    if opp.trade_side == "buy":
        book = clob_client.get_order_book(token_id)
        asks = [{"price": o.price, "size": o.size} for o in book.asks] if book.asks else []
        if not asks:
            db.update_opportunity(opp_id, status="failed")
            db.add_event("error", opportunity_id=opp_id, payload={"message": "No asks in orderbook"})
            return

        try:
            midpoint = float(clob_client.get_midpoint(token_id))
        except Exception:
            midpoint = None

        fill = simulate_buy(asks, amount, midpoint)
        if fill.shares == 0:
            db.update_opportunity(opp_id, status="failed")
            db.add_event("error", opportunity_id=opp_id, payload={"message": "Could not fill any shares"})
            return

        paper_portfolio.record_buy(
            token_id, opp.market_question, opp.trade_outcome or "Yes",
            fill.shares, fill.avg_price, fill.total_cost,
        )

        db.update_opportunity(
            opp_id,
            status="trade_executed",
            trade_fill_price=fill.avg_price,
            trade_fill_shares=fill.shares,
        )
        db.add_event("trade_executed", opportunity_id=opp_id, payload={
            "side": "buy",
            "shares": round(fill.shares, 4),
            "avg_price": round(fill.avg_price, 4),
            "total_cost": round(fill.total_cost, 2),
            "slippage": f"{fill.slippage:.2%}",
        })

    elif opp.trade_side == "sell":
        position = paper_portfolio.get_position(token_id)
        if not position:
            db.update_opportunity(opp_id, status="failed")
            db.add_event("error", opportunity_id=opp_id, payload={"message": "No position to sell"})
            return

        book = clob_client.get_order_book(token_id)
        bids = [{"price": o.price, "size": o.size} for o in book.bids] if book.bids else []
        if not bids:
            db.update_opportunity(opp_id, status="failed")
            db.add_event("error", opportunity_id=opp_id, payload={"message": "No bids in orderbook"})
            return

        try:
            midpoint = float(clob_client.get_midpoint(token_id))
        except Exception:
            midpoint = None

        shares_to_sell = position.shares
        fill = simulate_sell(bids, shares_to_sell, midpoint)
        if fill.shares == 0:
            db.update_opportunity(opp_id, status="failed")
            db.add_event("error", opportunity_id=opp_id, payload={"message": "Could not fill sell"})
            return

        paper_portfolio.record_sell(token_id, fill.shares, fill.avg_price, fill.total_cost)

        db.update_opportunity(
            opp_id,
            status="trade_executed",
            trade_fill_price=fill.avg_price,
            trade_fill_shares=fill.shares,
        )
        db.add_event("trade_executed", opportunity_id=opp_id, payload={
            "side": "sell",
            "shares": round(fill.shares, 4),
            "avg_price": round(fill.avg_price, 4),
            "total_proceeds": round(fill.total_cost, 2),
            "slippage": f"{fill.slippage:.2%}",
        })
