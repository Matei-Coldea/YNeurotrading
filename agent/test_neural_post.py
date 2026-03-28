"""Quick test: given a simulated neural state, prompt an LLM to write a tweet for a mirofish scenario."""

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

# --- Neural state baked into the system prompt ---
SYSTEM_PROMPT = f"""You are a regular person on Twitter. You just saw breaking news and you're about to post a tweet reacting to it.

Here is the news context:
{SCENARIO_SEED}

[Simulated neural state for this moment:
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
Confidence in your read: low]

Use the above as your internal emotional state when deciding what to post. Do not mention these numbers or labels in your post. They represent how you are feeling, not what you would say.

Write a single tweet (under 280 characters). Be authentic — typos, slang, and raw emotion are fine. Do not use hashtags unless it feels natural. Do not explain yourself. Just the tweet, nothing else."""


async def main():
    client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

    print(f"Model: {MODEL}")
    print(f"Scenario: RESTRICT Act (mirofish_scenarios/2)")
    print("---")

    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Post your tweet."},
        ],
        max_completion_tokens=150,
        temperature=1.0,
    )

    tweet = resp.choices[0].message.content.strip()
    print(f"\n🐦 Generated tweet:\n{tweet}")


if __name__ == "__main__":
    asyncio.run(main())
