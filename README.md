# Neuro-Trade

**A brain-enhanced swarm intelligence engine for prediction market trading.**

Neuro-Trade is a Polymarket trading agent that uses neurologically-grounded social simulations to predict public sentiment. It combines [MiroFish](https://github.com/nikmcfly/MiroFish-Offline) (multi-agent social simulation), Meta's TRIBE v2 (brain encoding model), and an autonomous trading agent into a single pipeline.

## Architecture

```
Polymarket API                MiroFish Social Sim          TRIBE v2 Brain Model
(market discovery)            (agent-based Twitter sim)     (fMRI predictions)
       |                              |                           |
       v                              v                           v
  Trading Agent  <----------  Sentiment Analysis  <------  Neural State Injection
  (OpenAI Agents SDK)         (post aggregation)          (fMRI activation → prompt)
       |                              |
       v                              v
  Paper Trading               Y.com Live Feed
  (simulated orders)          (Twitter-style UI)
```

### Core Components

| Component | Status | Description |
|-----------|--------|-------------|
| **Trading Agent** | Working | OpenAI Agents SDK with Polymarket API (Gamma + CLOB), MCP tool servers, paper trading |
| **MiroFish Social Sim** | Working | Multi-agent Twitter simulation with synthetic population support |
| **TRIBE v2 Brain Injection** | Beta | fMRI-based neural state injection into agent prompts via TRIBEv2 server |
| **fMRI-RAG Emotion Mapping** | Planned | Cosine similarity against SEND dataset reference DB |
| **Y.com Frontend** | Working | Twitter/X-styled live feed integrated into MiroFish dashboard, supports historical playback |
| **Multi-Agent Orchestration** | Stretch goal | CrewAI-based distributed simulation |

## Project Structure

```
YNeurotrading/
|-- agent/                        # Trading agent (OpenAI Agents SDK + Polymarket)
|   |-- main.py                   # Entry point — autonomous paper trading agent
|   |-- mcp_servers/              # MCP tool servers (polymarket, paper trading, web search)
|   |-- paper_trading/            # Virtual portfolio, fill engine, trade journal
|   |-- prompts/                  # System prompts for agent
|   |-- test_neural_post.py       # Neural state format comparison tests
|   +-- test_trade.py             # Paper trading tests
|
|-- mirofish/                     # MiroFish-Offline (social simulation engine)
|   |-- backend/
|   |   |-- app/api/              # Flask API (simulation, graph, report endpoints)
|   |   |-- app/services/         # Core services (runner, manager, synthetic entities, reports)
|   |   |-- app/storage/          # Neo4j + SQLite persistence
|   |   +-- scripts/
|   |       |-- run_twitter_simulation.py      # Main Twitter simulation orchestrator
|   |       |-- run_parallel_simulation.py     # Multi-platform runner (Twitter + Reddit)
|   |       |-- neural_agent.py               # Monkey-patches agents with fMRI neural state
|   |       |-- fmri_client.py                # Async HTTP client for TRIBEv2 server
|   |       |-- feed_narrative.py             # Converts OASIS feed to TRIBEv2 narrative input
|   |       +-- test_fmri_single.py           # End-to-end fMRI pipeline test
|   |-- frontend/src/
|   |   |-- views/YFeedView.vue               # Y.com feed page (live + historical)
|   |   |-- components/YTweet.vue             # Tweet card component (X.com styling)
|   |   |-- components/YSidebar.vue           # Y.com sidebar with branding
|   |   +-- components/Step1-5.vue            # Original MiroFish workflow steps
|   +-- docker-compose.yml
|
|-- mirofish_scenarios/           # Simulation scenario files (seed docs + prompts)
|   |-- 1_seed.txt                # Apple/NeuraTech acquisition scenario
|   |-- 1_prompt.txt
|   |-- 2_seed.txt                # RESTRICT Act scenario
|   +-- 2_prompt.txt
|
|-- features.md                   # Full project specification
+-- README.md
```

## Quick Start: MiroFish Simulation

### Prerequisites

- Docker
- OpenAI API key
- Neo4j AuraDB Free instance (or local Neo4j)

### Setup

1. **Clone MiroFish** (already included):
   ```bash
   git clone https://github.com/nikmcfly/MiroFish-Offline.git mirofish
   ```

2. **Configure environment** — copy and edit `mirofish/.env`:
   ```env
   # LLM (OpenAI)
   LLM_API_KEY=<your-openai-key>
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_MODEL_NAME=gpt-4o-mini

   # Neo4j (AuraDB)
   NEO4J_URI=neo4j+s://<instance>.databases.neo4j.io
   NEO4J_USERNAME=<username>
   NEO4J_PASSWORD=<password>
   NEO4J_DATABASE=<database>

   # Embeddings (OpenAI)
   EMBEDDING_MODEL=text-embedding-3-small
   EMBEDDING_BASE_URL=https://api.openai.com

   # OASIS/CAMEL-AI (uses same OpenAI key)
   OPENAI_API_KEY=<your-openai-key>
   OPENAI_API_BASE_URL=https://api.openai.com/v1
   ```

3. **Start**:
   ```bash
   cd mirofish
   docker compose up -d --build
   ```

4. **Open** http://localhost:3000

### Running a Simulation

The 5-step MiroFish workflow:

1. **Graph Build** — Upload a seed document (from `mirofish_scenarios/`). MiroFish extracts entities and relationships into a Neo4j knowledge graph.

2. **Environment Setup** — Configure and generate agent personas. Toggle **"Add synthetic regular people"** to inject LLM-generated diverse everyday personas (students, engineers, parents, etc.) alongside the document-extracted entities. Click **Start Preparation**.

3. **Simulation** — Runs a Twitter simulation where agents post, like, repost, and quote-post based on their personas and feed content. Use the round slider to control duration. Click the **"Y" button** in the header to open the live Y.com feed in a new tab.

4. **Report** — AI-generated analysis of the simulation results.

5. **Chat** — Interactive conversation with individual agents.

### Y.com Feed

The Y.com feed (`/y/:simulationId`) is a Twitter/X-styled interface that displays agent posts:

- **Live mode** — During a running simulation, polls for new tweets every 3 seconds with animated entry
- **Historical mode** — For completed simulations, loads all posts with infinite scroll
- **Access** — Click "Y" button during simulation, or "Y.com Feed" button from the history modal on the home page
- Posts show author avatars, handles, content, quoted tweets, and engagement metrics (likes, reposts)
- Reposts display the original post content with a "reposted by" header

### Synthetic Population Feature

MiroFish normally only creates agents from entities named in the seed document (companies, politicians, orgs). We added a **synthetic entity generator** that:

- Uses a single LLM call to generate N diverse persona sketches tailored to the simulation topic
- Writes synthetic entities to Neo4j with a `:Synthetic` label and `INTERESTED_IN` edge to the topic node
- Feeds them through the same profile/config pipeline as real entities
- Displays them with distinct teal styling (dashed border) in the graph visualization

This enables general population sentiment sampling — seeing how regular people would react to a news event, not just institutional voices.

### Modifications to MiroFish

Key changes made to the upstream MiroFish-Offline codebase:

- **Cloud LLM support** — Switched from Ollama to OpenAI API (`max_completion_tokens`, OpenAI embedding endpoint)
- **AuraDB support** — Neo4j driver passes database name, supports `neo4j+s://` URIs
- **Docker simplification** — Removed Ollama and Neo4j containers (cloud services only)
- **Twitter-only mode** — Uses `run_parallel_simulation.py --twitter-only` for proper action logging
- **Synthetic entity generation** — New module for LLM-generated diverse population
- **Y.com feed UI** — Twitter/X-styled frontend (`YFeedView`, `YTweet`, `YSidebar` components) with live and historical modes
- **Posts-feed API** — New `/api/simulation/<id>/posts-feed` endpoint JOINing posts with user data for Y.com display
- **Neural state injection** — `neural_agent.py` monkey-patches OASIS agents with TRIBEv2 fMRI integration
- **Feed narrative builder** — `feed_narrative.py` converts OASIS social feeds into natural language narratives for brain model input
- **Run state tracking fix** — Fixed `simulated_hours` field reading from action logs
- **Error logging** — Added traceback logging to ontology generation endpoint

## Scenarios

Scenarios live in `mirofish_scenarios/`. Each has two files:

- `{n}_seed.txt` — The document/news article to simulate reactions to
- `{n}_prompt.txt` — The simulation requirement describing what to simulate

| # | Scenario | Description |
|---|----------|-------------|
| 1 | Apple/NeuraTech | Apple acquires AI startup for $2B, competitor and consumer reactions |
| 2 | RESTRICT Act | Senate passes sweeping tech ban bill, diverse public reaction |

## Roadmap

See [features.md](features.md) for the full specification. Key next steps:

- [x] Integrate TRIBE v2 brain encoding into the MiroFish agent loop
- [x] Build Y.com frontend for simulation feed display
- [ ] Build fMRI-RAG emotion mapping using SEND dataset
- [ ] Add brain activity visualization to Y.com frontend
- [ ] Connect MiroFish sentiment output to the trading agent
- [ ] Benchmark MiroFish predictions against real-world sentiment data
