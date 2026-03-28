# Neuro-Trade

**A brain-enhanced swarm intelligence engine for prediction market trading.**

Neuro-Trade is a Polymarket trading agent that uses neurologically-grounded social simulations to predict public sentiment. It combines MiroFish (multi-agent social simulation), Meta's TRIBE v2 (brain encoding model), and an autonomous trading agent into a single pipeline.

---

## Core Components

### 1. Trading Agent (Orchestrator)

The top-level autonomous agent that scans Polymarket for opportunities and decides how to act. Built on the OpenAI Agents SDK with MCP tool servers for Polymarket API access (Gamma API for market discovery, CLOB API for live pricing) and paper trading.

Key components in `agent/`:
- `main.py` — Entry point, single autonomous agent (replaces earlier multi-agent LangGraph design)
- `mcp_servers/polymarket_server.py` — Market discovery + order book tools
- `mcp_servers/paper_trading_server.py` — Virtual trading engine
- `mcp_servers/web_search.py` — Web search integration
- `paper_trading/` — Portfolio state management, fill engine, trade journal

For the hackathon demo, uses paper trading against real Polymarket order books (real prices, simulated money).

### 2. MiroFish Social Simulation (Y.com)

A forked/modified version of MiroFish that simulates a fake social media platform ("Y.com"). When the trading agent encounters a sentiment-dependent bet, it triggers a MiroFish simulation:

- Seed the simulation with the event description (e.g., a Super Bowl ad, a political announcement)
- MiroFish extracts entities, builds a knowledge graph, generates agent personas
- Agents with distinct personalities (media outlets, influencers, regular users) interact on a simulated Twitter-like platform
- Runs turn-based: each round, active agents see their feed and decide to post, like, repost, quote, or do nothing
- All actions stored in SQLite for analysis

MiroFish needs to be "Americanized" for US-centric scenarios: swap LLM from Qwen-Plus to GPT-4o/Claude, translate system prompts to English, adjust timezone configs from Beijing to EST/PST.

### 3. TRIBE v2 Brain Injection (Beta)

Meta's TRIBE v2 model (~3.8B params for text-only path) predicts fMRI brain responses to text stimuli. Now integrated into the MiroFish agent loop via:

- `scripts/neural_agent.py` — Monkey-patches `SocialAgent.perform_action_by_llm()` to inject neural state into the agent's system prompt before each decision
- `scripts/feed_narrative.py` — Converts the agent's current OASIS social feed (posts, likes, shares) into a natural ~250-word narrative for TRIBEv2 input
- `scripts/fmri_client.py` — Async HTTP client that sends narratives to the TRIBEv2 server and returns neural state strings
- `scripts/test_fmri_single.py` — End-to-end test harness (`python test_fmri_single.py --sim sim_ID [--agent N]`)

**Workflow per agent per round:**
1. Get the agent's current social feed from OASIS
2. Build a natural language narrative from the feed content and engagement metrics
3. Send narrative to TRIBEv2 server → receive predicted neural activation state
4. Inject neural state into agent's system prompt (e.g., threat/reward/uncertainty scores, brain region activations)
5. Agent makes action decision with neural context
6. Original prompt is restored after decision (graceful degradation if TRIBEv2 unavailable)

### 4. fMRI-RAG (Emotion Mapping)

Instead of naively mapping brain regions to emotions (which is bad neuroscience — "reverse inference"), we use a retrieval-based approach:

- Build a reference database of TRIBE v2 outputs for stimuli with known emotional labels
- Reference data sourced from the Stanford Emotional Narratives Dataset (SEND): 193 annotated videos with continuous human valence ratings and text transcripts
- During simulation, compare each post's TRIBE v2 cortical pattern against the reference database using cosine similarity
- Produces an emotional profile per post: e.g., {"outrage": 0.42, "anxiety": 0.31, "surprise": 0.18, ...}
- This emotional profile is injected into the agent's LLM prompt to modulate their response — high amygdala-region activation leads to more emotional/amplifying behavior

### 5. Y.com Frontend + Brain Visualization

The Y.com feed is integrated into MiroFish's Vue.js frontend at `/y/:simulationId`. It presents agent posts in a Twitter/X-styled dark theme interface:

- **Three-column layout** — Left sidebar (Y branding + nav), center feed (tweet cards), right panel (simulation stats)
- **Live mode** — During running simulations, polls for new tweets every 3s with animated entry
- **Historical mode** — For completed simulations, loads posts from SQLite with infinite scroll pagination
- **Tweet cards** — Avatar (deterministic color from agent name), display name, @handle, content, quoted tweets, engagement buttons with X.com hover colors (reply=blue, repost=green, like=pink)
- **Reposts** — Display the original post content with a "reposted by" header, resolved via SQL JOIN on `original_post_id`
- **Entry points** — "Y" button in SimulationRunView header (opens new tab), "Y.com Feed" button in HistoryDatabase modal

Key files: `YFeedView.vue`, `YTweet.vue`, `YSidebar.vue`

Backend: `GET /api/simulation/<id>/posts-feed` JOINs `post` + `user` + original post tables in the SQLite database.

Brain activity visualization (cortical heatmap, emotion distribution) is planned as a future addition to the right panel.

### 6. Multi-Agent Orchestration (Stretch Goal)

Optional: multiple trading agents can form teams to split large simulations across compute. Each agent is responsible for simulating a subset of personas in the MiroFish simulation (e.g., agent A simulates users 0-9, agent B simulates 10-19). Results are merged. Could use CrewAI (47k stars) for the team orchestration layer.

This is the highest-risk, lowest-demo-value component — cut first if time is tight.

---

## Benchmarking Strategy

MiroFish has no published benchmarks against real-world outcomes. Neuro-Trade would be the first to validate it.

**Approach:** Pick a past event with well-documented public sentiment (Super Bowl ad with USA Today Ad Meter scores, or a political event with real-time Twitter sentiment data from the TED-S dataset). Run the simulation on the event, then compare:

1. Vanilla MiroFish prediction vs. real public sentiment (baseline)
2. MiroFish + TRIBE v2 brain-enhanced prediction vs. real public sentiment (our improvement)

Show that neurologically-grounded agents produce sentiment predictions closer to reality than pure LLM role-play.

---

## Tech Stack Summary

| Component | Technology |
|-----------|-----------|
| Trading agent framework | OpenAI Agents SDK + MCP tool servers |
| Polymarket integration | Gamma API (market discovery) + CLOB API (live pricing), paper trading engine |
| Social simulation engine | MiroFish (built on OASIS by CAMEL-AI) |
| Brain encoding model | Meta TRIBE v2 (~3.8B params text-only, ~709MB checkpoint + LLaMA 3.2-3B + Wav2Vec-BERT) |
| Emotion reference DB | Stanford Emotional Narratives Dataset (SEND) processed through TRIBE v2 |
| LLM for agents | GPT-4o or GPT-4o-mini (via OpenAI API) |
| Graph memory | Neo4j AuraDB (free tier) |
| Simulation data | SQLite (twitter_simulation.db per simulation) |
| Frontend | Vue 3 + Vite (MiroFish dashboard + integrated Y.com feed) |
| Orchestration (stretch) | CrewAI |
