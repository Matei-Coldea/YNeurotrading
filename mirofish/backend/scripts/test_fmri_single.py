"""Test the fMRI pipeline on a single agent from a past simulation.

Extracts one agent's persona + one feed snapshot from a historic simulation DB,
runs it through feed_narrative → fMRI server → prints the neural state.

Usage:
    python test_fmri_single.py --sim sim_19523de96449 [--agent 4]

If --agent is omitted, picks a random agent that has feed data.
Requires FMRI_SERVER_URL env var (defaults to http://localhost:8000).
"""

import argparse
import asyncio
import csv
import json
import os
import sqlite3
import sys

_scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _scripts_dir)

from dotenv import load_dotenv

# Load .env from project root
_project_root = os.path.abspath(os.path.join(_scripts_dir, "..", ".."))
for candidate in [
    os.path.join(_project_root, ".env"),
    os.path.join(_scripts_dir, "..", ".env"),
]:
    if os.path.exists(candidate):
        load_dotenv(candidate)
        break

import aiohttp
from feed_narrative import build_narrative
from fmri_client import get_neural_state


SIMS_DIR = os.path.join(_scripts_dir, "..", "uploads", "simulations")


def load_agent_persona(sim_dir: str, agent_id: int) -> str | None:
    """Read persona (user_char) for an agent from twitter_profiles.csv."""
    csv_path = os.path.join(sim_dir, "twitter_profiles.csv")
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["user_id"]) == agent_id:
                return row.get("user_char", "")
    return None


def load_agent_feed(sim_dir: str, agent_id: int, random_round: bool = True) -> str | None:
    """Get a feed snapshot for an agent from the trace table.

    Args:
        random_round: If True, pick a random refresh entry. Otherwise pick the latest.
    """
    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if random_round:
        cur.execute(
            "SELECT info, created_at FROM trace WHERE user_id=? AND action='refresh' "
            "ORDER BY RANDOM() LIMIT 1",
            (agent_id,),
        )
    else:
        cur.execute(
            "SELECT info, created_at FROM trace WHERE user_id=? AND action='refresh' "
            "ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # Reconstruct env_prompt-style string from the stored JSON
    try:
        data = json.loads(row[0])
        posts = data.get("posts", [])
        return f"After refreshing, you see some posts {json.dumps(posts)}"
    except (json.JSONDecodeError, TypeError):
        return row[0]


def pick_random_agent(sim_dir: str) -> int | None:
    """Pick a random agent_id that has feed data in the trace table."""
    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT user_id FROM trace WHERE action='refresh' "
        "ORDER BY RANDOM() LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_agent_name(sim_dir: str, agent_id: int) -> str:
    """Get agent display name from the DB."""
    db_path = os.path.join(sim_dir, "twitter_simulation.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM user WHERE user_id=?", (agent_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else f"agent_{agent_id}"


async def main():
    parser = argparse.ArgumentParser(description="Test fMRI pipeline on a single agent")
    parser.add_argument("--sim", required=True, help="Simulation ID (e.g. sim_19523de96449)")
    parser.add_argument("--agent", type=int, default=None, help="Agent user_id (random if omitted)")
    args = parser.parse_args()

    sim_dir = os.path.join(SIMS_DIR, args.sim)
    if not os.path.isdir(sim_dir):
        print(f"Simulation directory not found: {sim_dir}")
        sys.exit(1)

    agent_id = args.agent if args.agent is not None else pick_random_agent(sim_dir)
    if agent_id is None:
        print("No agents with feed data found in this simulation.")
        sys.exit(1)

    agent_name = get_agent_name(sim_dir, agent_id)

    # Load data
    persona = load_agent_persona(sim_dir, agent_id)
    feed = load_agent_feed(sim_dir, agent_id)

    print(f"=== fMRI Pipeline Test ===")
    print(f"Simulation: {args.sim}")
    print(f"Agent: {agent_name} (id={agent_id})")
    print()

    if persona:
        print(f"--- Persona (first 300 chars) ---")
        print(persona[:300] + "..." if len(persona) > 300 else persona)
        print()
    else:
        print("WARNING: No persona found for this agent.\n")

    if not feed:
        print("ERROR: No feed data found for this agent.")
        sys.exit(1)

    print(f"--- Raw Feed ---")
    print(feed[:500] + "..." if len(feed) > 500 else feed)
    print()

    # Step 1: Build narrative
    narrative = build_narrative(feed)
    if not narrative:
        print("ERROR: Could not build narrative from feed.")
        sys.exit(1)

    word_count = len(narrative.split())
    print(f"--- Narrative ({word_count} words) ---")
    print(narrative)
    print()

    # Step 2: Call fMRI server
    fmri_url = os.getenv("FMRI_SERVER_URL", "http://localhost:8000")
    print(f"--- Calling fMRI server at {fmri_url} ---")

    async with aiohttp.ClientSession() as session:
        neural_state = await get_neural_state(narrative, session)

    if neural_state:
        print(f"--- Neural State ---")
        print(neural_state)
    else:
        print("WARNING: fMRI server returned no result (is it running?)")
        print("Narrative was generated successfully — you can test the server separately.")

    print()
    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
