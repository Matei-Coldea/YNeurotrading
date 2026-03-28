# Module Scope

## Single Responsibility
This module does one thing: takes a string of naturalistic text (already formatted for TRIBE v2), processes it through the full neural interpretation pipeline, and returns a formatted string of labeled neural state values.

**Not in scope:** agent logic, persona modulation, prompt construction, simulation orchestration.

## Function Contract

```python
def process(text: str) -> str:
    """
    Input:  naturalistic text string, ready for TRIBE v2.
            Example: 'You are listening to the news. The reporter says:
            Fed announces emergency 75 basis point rate hike.'

    Output: formatted string of labeled neural state values with
            plain-language labels, inline scales, and temporal curves.
            Example: 'Dominant response: threat and fear response (peak=1.78)'
            ... (~30 lines total with full numerical data)
    """
```

## Caller Responsibilities
- The **caller** converts raw news into naturalistic text **before** calling `process()`.
- The **caller** injects the returned string into an agent prompt **after** receiving it.
- This module has no knowledge of the upstream or downstream context.

## Processing Pipeline (6 Steps)
1. TRIBE v2 Forward Pass — text → cortical predictions `(n_TRs, 20484)`
2. ROI Timeseries Extraction — 20,484 vertices → 6 timeseries (3-layer approach)
3. Summary Statistics — 11 stats per ROI (66 total)
4. Pairwise Connectivity — 7 Pearson correlations
5. Composite Scores — 8 summary values
6. Format Output — ~30-line LLM-readable string with plain-language labels, inline scales, dominant signal callout

## Complete Module Entry Point

```python
def process(text: str) -> str:
    preds = run_tribe(text)                                          # Step 1: 2-5 sec on GPU
    roi_ts = extract_all(preds, masks, weight_maps, signatures)      # Step 2: <10ms
    stats = {name: extract_stats(ts) for name, ts in roi_ts.items()} # Step 3: <10ms
    connectivity = compute_connectivity(roi_ts)                       # Step 4: <5ms
    composites = compute_composites(stats, connectivity)              # Step 5: <1ms
    return format_output(stats, connectivity, composites, roi_ts)     # Step 6: <1ms
```
