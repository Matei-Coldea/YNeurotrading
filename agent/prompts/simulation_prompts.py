"""Prompts for generating seed documents and simulation requirements from market context."""

SEED_GENERATION_PROMPT = """\
Given this Polymarket prediction market and research findings, generate two things:

1. A **seed document** (200-500 words): Write a factual news article describing the event/topic. Include key facts, stakeholders, controversy points, and recent developments. This document will be used to seed a social media simulation.

2. A **simulation requirement** (50-100 words): A prompt telling the simulation engine what to simulate. Specify:
   - Platform: Twitter
   - Agent mix: 60-70% individual users (diverse backgrounds, ages, political leanings), 30-40% organizations/media
   - Duration: 24-48 simulated hours
   - What behaviors to watch for (polarization, consensus, viral takes, etc.)

## Market Context
- **Question**: {market_question}
- **Description**: {market_description}
- **Current Prices**: Yes={yes_price}, No={no_price}
- **Tags**: {tags}
- **Research Findings**: {web_research}
- **Agent Hypothesis**: {hypothesis}

Output a JSON object with exactly two fields:
```json
{{
  "seed_document": "...",
  "simulation_requirement": "..."
}}
```
"""
