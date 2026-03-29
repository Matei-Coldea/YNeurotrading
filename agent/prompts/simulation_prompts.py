"""Prompts for generating seed documents and simulation requirements from market context.

Seed documents feed into MiroFish's ontology generation + NER pipeline:
- An LLM designs 10 entity types from the seed + simulation_requirement
- NER extracts ONLY concrete named entities matching those types (abstract concepts are rejected)
- Each extracted entity becomes a simulation agent with a generated persona
- Text is chunked into 500-char segments for NER — entity-relationship pairs must be co-located

Therefore seeds must be ENTITY-DENSE: name specific people, organizations, media outlets, and
state their relationships explicitly within the same paragraph.
"""

SEED_GENERATION_PROMPT_DIRECT = """\
You are generating a seed document for a social media simulation about a prediction market where \
PUBLIC OPINION DIRECTLY DETERMINES THE OUTCOME (e.g., approval ratings, boycott participation, \
petition signatures, public votes, social media campaigns).

## Market Context
- **Question**: {market_question}
- **Description**: {market_description}
- **Current Prices**: Yes={yes_price}, No={no_price}
- **Tags**: {tags}
- **Research Findings**: {web_research}
- **Agent Hypothesis**: {hypothesis}

## CRITICAL: Entity Recognition Requirements
This seed document will be processed by an entity recognition system that extracts NAMED ENTITIES \
to create simulation agents. The system REJECTS abstract concepts ("public opinion", "the trend", \
"sentiment") — it can ONLY extract concrete named entities (people, organizations, companies, \
media outlets, government bodies). Every entity you name becomes a simulation agent.

## Seed Document Requirements (800-1200 words)
Write a detailed news/analysis article that is DENSE with named entities. Include ALL of the following:

### Named Stakeholders (aim for 15-25 named entities total)
- Name specific individuals with their roles: "Senator Maria Torres (D-CA)", "Fox News anchor Brett Hayes", \
"Greenpeace spokesperson Aisha Patel" — NOT "a senator", "a news anchor", "an activist"
- Name specific organizations: "The Heritage Foundation", "ACLU", "Chamber of Commerce" — NOT "conservative groups", "civil liberties organizations"
- Name specific media outlets and journalists who cover this topic
- Name specific government bodies or committees involved

### Explicit Relationships (critical for graph edges)
State relationships directly and close together (within the same paragraph):
- "Senator Torres opposes the bill, citing concerns raised by the National Education Association"
- "The Chamber of Commerce endorsed the proposal, contradicting the position of the Small Business Alliance"
- These become edges in the knowledge graph. Entity-relationship pairs MUST be co-located, not spread across distant paragraphs.

### Sentiment Landscape with Attribution
- Don't say "polls show support" — say "A Reuters/Ipsos poll found 58% of Democrats support the measure, \
while the Heritage Foundation's survey showed 72% of Republicans oppose it"
- Attribution to named pollsters/organizations creates extractable entities

### Controversy Points with Named Combatants
- Not "there is disagreement" but "The ACLU filed an amicus brief opposing, while the Federalist Society's \
Leonard Hawkins argued in favor at a Senate hearing"

### Historical Precedent
- Reference specific past events with named actors: "When a similar measure was proposed in 2023, \
former Governor James Blake successfully rallied opposition through a viral Twitter campaign"

### Demographic Representation
- Name representative voices from different demographics to create diverse agent personas:
  a college student, a small business owner, a retired veteran, a tech worker, a rural farmer
- Give them names and brief context: "College senior Emily Zhao at UT Austin tweeted..."

### Media Framing
- Name specific outlets and their editorial stance: "The New York Times editorial board endorsed the measure, \
while the Wall Street Journal's opinion page called it 'regulatory overreach'"

## Simulation Requirement (output separately)
Write a 50-100 word simulation requirement that specifies:
- Platform: Twitter
- Agent mix designed to produce diverse opinion types: 50% individual citizens (diverse demographics — \
young/old, liberal/conservative, urban/rural), 30% media and journalist accounts, 20% organizations and advocacy groups
- Duration: 48 simulated hours
- What to watch for: opinion coalescence vs fragmentation, tipping points where one side gains momentum, \
viral narrative frames that shift the balance, bandwagon effects, demographic clustering of opinion

## Output Format
Output a JSON object with exactly two fields:
```json
{{
  "seed_document": "The 800-1200 word entity-dense article...",
  "simulation_requirement": "The 50-100 word simulation spec..."
}}
```
"""

SEED_GENERATION_PROMPT_FALLBACK = """\
Given this Polymarket prediction market and research findings, generate two things:

1. A **seed document** (800-1200 words): Write a detailed factual news/analysis article describing \
the event/topic. CRITICAL: The document will be processed by entity recognition — it must be dense \
with NAMED ENTITIES (specific people with roles, named organizations, named media outlets, government \
bodies). Do NOT use generic terms like "activists" or "officials" — always name them specifically. \
Include key facts, stakeholders, controversy points, and recent developments. Aim for 15-25 named \
entities with their relationships stated explicitly.

2. A **simulation requirement** (50-100 words): A prompt telling the simulation engine what to \
simulate. Specify:
   - Platform: Twitter
   - Agent mix: 50% individual users (diverse demographics), 30% media/journalists, 20% organizations
   - Duration: 48 simulated hours
   - What behaviors to watch for (polarization, consensus, viral takes, information cascades, etc.)

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
