# TRIBE v2 Neural Processing Module

## Project Overview
This module takes naturalistic text, processes it through a neural interpretation pipeline (TRIBE v2), and returns labeled neural state values. It is a standalone processing module — no agent logic, persona modulation, or simulation orchestration.

**Function signature:** `def process(text: str) -> str`

## Architecture
The pipeline has 6 sequential steps:
1. **TRIBE v2 Forward Pass** — text → predicted cortical activation (20,484 vertices)
2. **ROI Timeseries Extraction** — 20,484 vertices → 6 meaningful timeseries (3-layer approach)
3. **Summary Statistics** — 11 stats per ROI (66 total)
4. **Pairwise Connectivity** — 7 Pearson correlations between ROI pairs
5. **Composite Scores** — 8 summary values (valence, arousal, dominance, etc.)
6. **Format Output** — all data into ~30-line LLM-readable string (plain-language labels, inline scales, dominant signal callout)

## Key Context Files
- `docs/01-module-scope.md` — input/output contract, caller responsibilities
- `docs/02-tribe-forward-pass.md` — Step 1: TRIBE v2 inference details
- `docs/03-roi-extraction.md` — Step 2: three-layer ROI extraction (Schaefer + NiMARE + nltools)
- `docs/04-statistics.md` — Step 3: 11 summary statistics per ROI
- `docs/05-connectivity.md` — Step 4: pairwise connectivity computation
- `docs/06-composites.md` — Step 5: 8 composite score formulas
- `docs/07-format-output.md` — Step 6: output formatting with 4 LLM-readability fixes (plain ROI names, readable connectivity pairs, temporal curve arrows, dominant signal callout)
- `docs/08-setup.md` — dependencies, installation, one-time data downloads

## Performance
- Total: ~2-5 seconds per call (GPU), dominated by TRIBE v2 inference
- Steps 2-6 combined: <30ms
- Called once per simulation tick, not once per agent

## Dependencies
- `tribev2` (Facebook Research), `nilearn`, `nibabel`, `scipy`, `nimare`, `nltools`
- `HF_TOKEN` environment variable required for TRIBE v2 model weights (no interactive login needed)
- One-time downloads: Neurosynth database (~1GB), VIFS/PINES signatures from Neurovault
