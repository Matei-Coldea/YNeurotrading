# Neuro-Trade

**A brain-enhanced swarm intelligence engine for prediction market trading.**

Neuro-Trade is a Polymarket trading agent that uses neurologically-grounded social simulations to predict public sentiment. It combines MiroFish (multi-agent social simulation), Meta's TRIBE v2 (brain encoding model), and an autonomous trading agent into a single pipeline.

---

## Core Components

### 1. Trading Agent (Orchestrator)

The top-level autonomous agent that scans Polymarket for opportunities and decides how to act. Built on top of Polymarket's official API clients (Gamma API for market discovery, CLOB API for live pricing). Uses a LangGraph ReACT agent with tool-use — the simulation is just one tool among several (web search, market lookup, trade execution).

For the hackathon demo, uses paper trading against real Polymarket order books (real prices, simulated money) via polymarket/agents API wrappers.

### 2. MiroFish Social Simulation (Y.com)

A forked/modified version of MiroFish that simulates a fake social media platform ("Y.com"). When the trading agent encounters a sentiment-dependent bet, it triggers a MiroFish simulation:

- Seed the simulation with the event description (e.g., a Super Bowl ad, a political announcement)
- MiroFish extracts entities, builds a knowledge graph, generates agent personas
- Agents with distinct personalities (media outlets, influencers, regular users) interact on a simulated Twitter-like platform
- Runs turn-based: each round, active agents see their feed and decide to post, like, repost, quote, or do nothing
- All actions stored in SQLite for analysis

MiroFish needs to be "Americanized" for US-centric scenarios: swap LLM from Qwen-Plus to GPT-4o/Claude, translate system prompts to English, adjust timezone configs from Beijing to EST/PST.

### 3. TRIBE v2 Brain Injection

Meta's TRIBE v2 model (~3.8B params for text-only path) predicts fMRI brain responses to text stimuli. Integrated into the MiroFish agent loop to give agents neurologically-grounded emotional responses:

- Each round, before agents act, their current feed content is run through TRIBE v2
- TRIBE v2 outputs predicted fMRI activity across ~20k cortical vertices
- Text input is automatically converted to speech internally by TRIBE v2 before processing (uses LLaMA 3.2-3B + Wav2Vec-BERT)
- The fMRI output is averaged over time to produce a single cortical activation pattern per post

### 4. fMRI-RAG (Emotion Mapping)

Instead of naively mapping brain regions to emotions (which is bad neuroscience — "reverse inference"), we use a retrieval-based approach:

- Build a reference database of TRIBE v2 outputs for stimuli with known emotional labels
- Reference data sourced from the Stanford Emotional Narratives Dataset (SEND): 193 annotated videos with continuous human valence ratings and text transcripts
- During simulation, compare each post's TRIBE v2 cortical pattern against the reference database using cosine similarity
- Produces an emotional profile per post: e.g., {"outrage": 0.42, "anxiety": 0.31, "surprise": 0.18, ...}
- This emotional profile is injected into the agent's LLM prompt to modulate their response — high amygdala-region activation leads to more emotional/amplifying behavior

### 5. Y.com Frontend + Brain Visualization

A custom frontend (separate from MiroFish's built-in Vue.js dashboard) that presents the simulation as a demo:

- Left side: Y.com — a Twitter/X-styled social media feed showing agent posts, likes, reposts in real-time
- Right side: Brain activity visualization — shows the TRIBE v2 fMRI predictions as a cortical heatmap, plus the emotion distribution bar chart from the fMRI-RAG step
- Reads directly from MiroFish's SQLite database and TRIBE v2 outputs

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
| Trading agent framework | LangGraph ReACT + polymarket/agents API wrappers |
| Polymarket integration | Gamma API (market discovery) + CLOB API (live pricing), paper trading |
| Social simulation engine | MiroFish (built on OASIS by CAMEL-AI) |
| Brain encoding model | Meta TRIBE v2 (~3.8B params text-only, ~709MB checkpoint + LLaMA 3.2-3B + Wav2Vec-BERT) |
| Emotion reference DB | Stanford Emotional Narratives Dataset (SEND) processed through TRIBE v2 |
| LLM for agents | GPT-4o or Claude (replacing MiroFish's default Qwen-Plus) |
| Agent memory | Zep Cloud (free tier) |
| Simulation data | SQLite |
| Frontend | Custom (Y.com + brain viz), reads from MiroFish SQLite |
| Orchestration (stretch) | CrewAI |
