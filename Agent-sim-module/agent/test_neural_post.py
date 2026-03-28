"""Quick test: compare two neural state formats for tweet generation on the same scenario."""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from openai import AsyncOpenAI

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

# --- Scenario (from mirofish_scenarios/2) ---
SCENARIO_SEED = (Path(__file__).parent.parent / "mirofish_scenarios" / "2_seed.txt").read_text()

TASK = """Write a single tweet (under 280 characters). Be authentic — typos, slang, and raw emotion are fine. Do not use hashtags unless it feels natural. Do not explain yourself. Just the tweet, nothing else."""

# --- Version A: simple neural state (original) ---
NEURAL_STATE_SIMPLE = """[Simulated neural state for this moment:
Threat response: 2.5/3.0 (sustained, falling)
Reward anticipation: 0.3/3.0 (rising)
Social awareness: 1.2/3.0 (herding)
Analytical engagement: 0.6/3.0 (disengaged)
Uncertainty: 1.5/3.0 (sustained)
Action urgency: 0.7/3.0
Is your fear driven by the crowd or by fundamentals: crowd-driven
Can you think clearly under this stress: no
Overall feeling: negative
Overall activation: high
Emotional vs rational: emotional
Approach or avoid: strong avoid
Confidence in your read: low]"""

# --- Version B: detailed neural state (new format) ---
NEURAL_STATE_DETAILED = """[Neural state reading for this moment]

Dominant response: threat and fear response (peak=1.78)
Weakest response: reward and opportunity detection (peak=0.51)

Processing sequence (what activated first → last): threat and fear response(3s) → awareness of others and social pressure(4s) → uncertainty and vigilance(4s) → urge to act (motor readiness)(6s) → analytical thinking and rational control(8s) → reward and opportunity detection(12s)

Brain region activations (peak: 0=nothing, 1=moderate, 2+=intense | auc: total response effort, higher=more sustained | cv: 0=steady, >1=conflicted/oscillating):
  threat and fear response: peak=1.78 auc=11.2 onset=3s sustained falling cv=0.68 curve(early→late): 0.0 → 1.4 → 1.8 → 0.9 → 0.4
  reward and opportunity detection: peak=0.51 auc=5.1 onset=12s sustained rising cv=0.52 curve(early→late): 0.0 → 0.1 → 0.2 → 0.4 → 0.5
  analytical thinking and rational control: peak=0.91 auc=9.0 onset=8s sustained rising cv=0.55 curve(early→late): 0.0 → 0.2 → 0.7 → 0.9 → 0.7
  awareness of others and social pressure: peak=1.41 auc=15.3 onset=4s sustained stable cv=0.46 curve(early→late): 0.0 → 0.8 → 1.4 → 1.2 → 1.0
  urge to act (motor readiness): peak=0.71 auc=3.8 onset=6s faded falling cv=0.81 curve(early→late): 0.0 → 0.3 → 0.7 → 0.4 → 0.1
  uncertainty and vigilance: peak=1.52 auc=15.8 onset=4s sustained stable cv=0.48 curve(early→late): 0.0 → 0.9 → 1.5 → 1.3 → 0.9

How these responses interact (+1=reinforce each other, 0=independent, -1=suppress each other):
  fear ↔ social awareness: 0.72
  fear ↔ analytical thinking: -0.58
  fear ↔ reward detection: -0.81
  reward ↔ analytical thinking: 0.85
  reward ↔ social awareness: -0.12
  action urge ↔ fear: 0.61
  action urge ↔ reward: -0.42

Summary:
  valence: -1.18 (negative=feels bad, positive=feels good)
  arousal: 1.31 (0=calm, 1+=activated, 2+=intense)
  dominance: -0.38 (-1=overwhelmed by emotion, +1=in rational control)
  approach or avoid: -0.55 (-1=flee/sell, +1=pursue/buy)
  reactivity: 3 TRs (positive=emotion activated before thinking, negative=thinking activated before emotion)
  regulation: 1.0 (+1=calming down successfully, -1=emotion overtaking reason)
  herding: 1.50 (0=thinking independently, 1+=following the crowd)
  confidence: 0.50 (<0.7=uncertain about this read, >1.2=confident)"""


def build_prompt(neural_state: str) -> str:
    return f"""You are a regular person on Twitter. You just saw breaking news and you're about to post a tweet reacting to it.

Here is the news context:
{SCENARIO_SEED}

{neural_state}

Use the above as your internal emotional state when deciding what to post. Do not mention these numbers or labels in your post. They represent how you are feeling, not what you would say.

{TASK}"""


async def generate_tweet(client: AsyncOpenAI, system_prompt: str) -> str:
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Post your tweet."},
        ],
        max_completion_tokens=150,
        temperature=1.0,
    )
    return resp.choices[0].message.content.strip()


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    print(f"Model: {MODEL}")
    print(f"Scenario: RESTRICT Act (mirofish_scenarios/2)")
    print("=" * 60)

    # Run both in parallel
    simple_task = generate_tweet(client, build_prompt(NEURAL_STATE_SIMPLE))
    detailed_task = generate_tweet(client, build_prompt(NEURAL_STATE_DETAILED))
    tweet_simple, tweet_detailed = await asyncio.gather(simple_task, detailed_task)

    print(f"\n[A] SIMPLE neural state:")
    print(f"    {tweet_simple}")
    print(f"\n[B] DETAILED neural state:")
    print(f"    {tweet_detailed}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
