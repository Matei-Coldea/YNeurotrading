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

SEED_GENERATION_PROMPT_INDIRECT = """\
You are generating a seed document for a social media simulation about a prediction market where \
the OUTCOME IS NOT SOLELY DETERMINED BY PUBLIC OPINION (it's influenced by legislators, courts, \
regulators, political pressure, etc.).

## PURPOSE OF THIS SIMULATION
We are NOT trying to predict the event outcome. We are trying to detect BELIEF MOMENTUM — whether \
people are starting to believe one outcome is more or less likely. When collective belief shifts, \
the market price follows. If we detect a belief shift before the market prices it in, we can buy \
the side beliefs are moving toward and sell when the price catches up.

Therefore, the seed document must present AMBIGUOUS, EVOLVING information that gives simulation \
agents reason to UPDATE THEIR BELIEFS over the course of the simulation. We need to see belief \
shifts, not stable consensus. Include competing narratives, conflicting evidence, and credible \
arguments for both sides — so agents have material to change their minds about.

## Market Context
- **Question**: {market_question}
- **Description**: {market_description}
- **Current Prices**: Yes={yes_price}, No={no_price}
- **Tags**: {tags}
- **Research Findings**: {web_research}
- **Agent Hypothesis**: {hypothesis}

## CRITICAL: Entity Recognition Requirements
This seed document will be processed by an entity recognition system that extracts NAMED ENTITIES \
to create simulation agents. The system REJECTS abstract concepts ("market sentiment", "the trend", \
"risk appetite") — it can ONLY extract concrete named entities (people, organizations, companies, \
media outlets, government bodies). Every entity you name becomes a simulation agent.

## Seed Document Requirements (800-1200 words)
Write a detailed news/analysis article that is DENSE with named entities. The article must present \
the issue as an ACTIVE, EVOLVING DEBATE with recent catalysts that are shifting opinion. This is \
crucial — a static description produces flat simulation output with no momentum signal.

### Recent Catalysts and Ambiguous Developments
- Start with the LATEST developments that could cause people to update their beliefs. Present \
information that is genuinely AMBIGUOUS — it could be interpreted as making the outcome more or \
less likely. This is what causes belief shifts in the simulation.
- "On Tuesday, a leaked memo from the Department of Justice revealed..." \
"Yesterday, Senator Maria Torres reversed her position, citing..."
- Name specific events with dates and the named people involved
- Include developments that DIFFERENT people will interpret differently

### Named Voices Arguing "This Is Increasingly Likely"
- People and organizations making credible arguments that the outcome will happen: \
"Former intelligence chief David Brennan argued on CNN that 'the conditions are now in place'"
- "A coalition of policy experts, led by Brookings fellow Sarah Chen, published an analysis showing..."
- These agents will push belief momentum in one direction

### Named Voices Arguing "This Won't Happen"
- The OTHER side with credible counter-arguments: \
"State Department veteran Robert Kagan dismissed the analysis as 'wishful thinking based on incomplete data'"
- OR voices providing evidence against: "Pentagon spokesperson Lisa Huang pointed to intelligence \
suggesting the opposite trajectory"
- Both sides need credible named voices so the simulation has genuine tension

### Named Media Voices with Competing Framings
- Journalists and outlets framing the story DIFFERENTLY: "The Wall Street Journal's editorial board \
called the development 'a turning point,' while Financial Times correspondent James Kynge argued \
it was 'noise, not signal'"
- Media disagreement creates the conditions for belief shifts as agents weigh competing framings

### Named Public Voices (diverse, persuadable)
- Ordinary people representing different perspectives who could change their minds: \
"factory worker Tom Rodriguez in Detroit says 'I didn't think this was possible but now I'm not so sure'"
- "startup founder Priya Mehta in Austin remains skeptical but admits 'the evidence is mounting'"
- Include people who are UNCERTAIN or RECONSIDERING — these are the agents whose belief shifts \
we want to detect

### Explicit Relationships (critical for graph edges)
State relationships directly and close together (within the same paragraph):
- "Senator Torres, who chairs the Judiciary Committee, faces pressure from both the ACLU and \
the Fraternal Order of Police, which endorsed her opponent"
- Entity-relationship pairs MUST be co-located within ~500 characters.

### Conflicting Data and Evidence
- Present data that both sides can cite: "A Reuters poll shows 52% believe the outcome is likely, \
up from 38% last month — but a separate analysis by Goldman Sachs puts the probability at only 25%"
- "Intelligence sources cited by the BBC suggest X, while diplomatic cables obtained by Reuters suggest Y"
- Conflicting evidence causes agents to debate and update beliefs during the simulation

### Decision-Maker Signals (ambiguous)
- What are the actual decision-makers hinting? Present their signals as OPEN TO INTERPRETATION: \
"Three Fed governors have made comments this week that analysts are split on — dovish or just cautious?"
- "Insiders say the committee vote is 'too close to call,' but two members made contradictory statements"
- Ambiguous signals give agents room to form different beliefs and shift them

### Key Uncertainties
- What genuine unknowns make this hard to predict? These are where belief momentum happens.
- "The timeline depends on factors that even insiders disagree about"
- "Market pricing at {yes_price} suggests X, but betting volume has tripled — suggesting beliefs are in flux"

## Simulation Requirement (output separately)
Write a 50-100 word simulation requirement that specifies:
- Platform: Twitter
- Agent mix: 40% individual citizens (diverse backgrounds — include people who are UNCERTAIN and \
open to updating their beliefs), 25% media and journalist accounts (with competing framings), \
20% analysts and commentators (some bullish, some bearish), 15% political figures and insiders
- Duration: 48 simulated hours
- CRITICAL — what to watch for: BELIEF MOMENTUM (are agents updating what they think will happen? \
Is perceived likelihood shifting toward one outcome?), tipping points where uncertain agents pick \
a side, whether one interpretation of events is winning over the other, the DIRECTION of belief \
change matters more than the final distribution

## Output Format
Output a JSON object with exactly two fields:
```json
{{
  "seed_document": "The 800-1200 word entity-dense article with ambiguous evidence and competing narratives...",
  "simulation_requirement": "The 50-100 word simulation spec focused on detecting belief momentum..."
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
