"""Multi-provider LLM ensemble via Lava API for trade proposal voting."""

import asyncio
import json
import logging
import re
import statistics
from collections import Counter
from urllib.parse import quote

import httpx

from config import LAVA_FORWARD_URL

logger = logging.getLogger(__name__)


def _parse_json_objects(text: str) -> list[dict]:
    """Extract JSON objects from LLM output, handling markdown code blocks."""
    objects = []
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text)
    search_text = "\n".join(code_blocks) if code_blocks else text

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


def _build_request(provider: dict, prompt: str) -> tuple[str, dict, dict]:
    """Build URL, headers, and body for a provider request through Lava."""
    lava_url = f"{LAVA_FORWARD_URL}?u={quote(provider['endpoint'], safe='')}"

    headers = {
        "Content-Type": "application/json",
    }

    if provider["format"] == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        body = {
            "model": provider["model"],
            "max_tokens": 4096,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
    else:
        body = {
            "model": provider["model"],
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }

    return lava_url, headers, body


def _extract_text(provider: dict, data: dict) -> str:
    """Extract text content from a provider's response."""
    if provider["format"] == "anthropic":
        return data["content"][0]["text"]
    return data["choices"][0]["message"]["content"]


async def _call_provider(client: httpx.AsyncClient, provider: dict, prompt: str, lava_api_key: str) -> dict | None:
    """Call a single provider through Lava. Returns parsed proposal or None."""
    url, headers, body = _build_request(provider, prompt)
    headers["Authorization"] = f"Bearer {lava_api_key}"

    try:
        resp = await client.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        text = _extract_text(provider, data)
        objects = _parse_json_objects(text)
        if objects:
            logger.info(f"[ensemble] {provider['name']}: trade_side={objects[0].get('trade_side')}")
            return {"provider": provider["name"], "proposal": objects[0]}
        logger.warning(f"[ensemble] {provider['name']}: no JSON parsed from response")
    except Exception as e:
        logger.warning(f"[ensemble] {provider['name']} failed: {e}")
    return None


async def query_providers(prompt: str, providers: list[dict], lava_api_key: str) -> list[dict]:
    """Query all providers in parallel, return list of successful results."""
    async with httpx.AsyncClient() as client:
        tasks = [_call_provider(client, p, prompt, lava_api_key) for p in providers]
        results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def aggregate_votes(results: list[dict]) -> dict:
    """Aggregate multiple trade proposals via voting."""
    proposals = [r["proposal"] for r in results]
    providers = [r["provider"] for r in results]

    # Majority vote on trade_side
    sides = [p.get("trade_side", "skip") for p in proposals]
    side_counts = Counter(sides)
    winning_side = side_counts.most_common(1)[0][0]

    # If tied, default to skip
    top_count = side_counts.most_common(1)[0][1]
    ties = [s for s, c in side_counts.items() if c == top_count]
    if len(ties) > 1:
        winning_side = "skip"

    ensemble_agreement = top_count / len(proposals)

    # Majority vote on trade_outcome among non-skip voters
    non_skip = [p for p in proposals if p.get("trade_side") != "skip"]
    if non_skip and winning_side != "skip":
        outcomes = [p.get("trade_outcome", "Yes") for p in non_skip]
        winning_outcome = Counter(outcomes).most_common(1)[0][0]
        token_id = next(
            (p.get("trade_token_id") for p in non_skip if p.get("trade_outcome") == winning_outcome),
            proposals[0].get("trade_token_id"),
        )
    else:
        winning_outcome = proposals[0].get("trade_outcome")
        token_id = proposals[0].get("trade_token_id")

    # Median for numeric fields
    prob_estimates = [p["probability_estimate"] for p in proposals if p.get("probability_estimate") is not None]
    edge_estimates = [p["estimated_edge"] for p in proposals if p.get("estimated_edge") is not None]
    amounts = [p["trade_amount_usd"] for p in proposals if p.get("trade_amount_usd") is not None]

    # Concatenate reasoning
    reasoning_parts = []
    for prov, prop in zip(providers, proposals):
        r = prop.get("trade_reasoning", "")
        if r:
            reasoning_parts.append(f"[{prov}] {r}")
    combined_reasoning = " | ".join(reasoning_parts)

    # Average sentiment components
    sentiments = [p.get("simulation_sentiment") for p in proposals if isinstance(p.get("simulation_sentiment"), dict)]
    avg_sentiment = None
    if sentiments:
        all_keys = set()
        for s in sentiments:
            all_keys.update(s.keys())
        avg_sentiment = {}
        for k in all_keys:
            vals = [s[k] for s in sentiments if k in s and isinstance(s[k], (int, float))]
            avg_sentiment[k] = round(sum(vals) / len(vals), 3) if vals else 0

    return {
        "trade_side": winning_side,
        "trade_outcome": winning_outcome,
        "trade_token_id": token_id,
        "trade_amount_usd": min(amounts) if amounts else None,
        "probability_estimate": statistics.median(prob_estimates) if prob_estimates else None,
        "estimated_edge": statistics.median(edge_estimates) if edge_estimates else None,
        "trade_reasoning": combined_reasoning,
        "simulation_sentiment": avg_sentiment,
        "ensemble_agreement": ensemble_agreement,
    }
