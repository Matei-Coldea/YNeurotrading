# Step 6: Format Output

## Design Philosophy
Pass **all** computed data to the LLM. Nothing is thrown away. No categorical conversions. But raw code variable names and unitless values are replaced with plain-language labels and human-readable scales so the LLM can interpret without decoding.

## Four LLM-Readability Fixes

### Fix 1: Plain-Language ROI Names
`fear_salience` → `threat and fear response`. Code variable names require the LLM to guess meaning. `social_default` is especially bad — "default" means the default mode network to a neuroscientist, but the LLM might read it as "the default social setting." A fixed mapping dict handles this once.

### Fix 2: Plain-Language Connectivity Pairs
`fear_deliberation: r=-0.58` → `fear ↔ analytical thinking: -0.58`. The bidirectional arrow and readable names make the relationship immediately clear. The header scale (`+1=reinforce, -1=suppress`) removes ambiguity about what the number means.

### Fix 3: Temporal Context on Timeseries Shapes
`shape=[0.0,1.4,1.8,0.9,0.4]` → `curve(early→late): 0.0 → 1.4 → 1.8 → 0.9 → 0.4`. Arrows make the temporal direction unambiguous and read as a story: starts at nothing, rises, peaks, declines.

### Fix 4: Dominant Signal Callout
The LLM no longer has to compare 6 peaks to find the dominant response. `argmax`/`argmin` on peaks gives one line at the top for immediate orientation before the detail section.

Additionally: `onset=TR2` → `onset=3s` (TRs are meaningless to the LLM; seconds are universal). Composite scores get inline scale annotations so the LLM knows what the numbers mean without external reference.

## Label Constants

```python
ROI_LABELS = {
    "fear_salience":  "threat and fear response",
    "reward_limbic":  "reward and opportunity detection",
    "deliberation":   "analytical thinking and rational control",
    "social_default": "awareness of others and social pressure",
    "action_motor":   "urge to act (motor readiness)",
    "attention":      "uncertainty and vigilance",
}

PAIR_LABELS = {
    "fear_social":       "fear ↔ social awareness",
    "fear_deliberation": "fear ↔ analytical thinking",
    "fear_reward":       "fear ↔ reward detection",
    "reward_delib":      "reward ↔ analytical thinking",
    "reward_social":     "reward ↔ social awareness",
    "action_fear":       "action urge ↔ fear",
    "action_reward":     "action urge ↔ reward",
}
```

## Implementation

```python
def format_output(stats, connectivity, composites, roi_ts):
    lines = ["[Neural state reading for this moment]", ""]

    # 1. Dominant signal callout
    peaks = {name: s["peak"] for name, s in stats.items()}
    strongest = max(peaks, key=peaks.get)
    weakest = min(peaks, key=peaks.get)
    lines.append(f"Dominant response: {ROI_LABELS[strongest]} "
                 f"(peak={peaks[strongest]:.2f})")
    lines.append(f"Weakest response: {ROI_LABELS[weakest]} "
                 f"(peak={peaks[weakest]:.2f})")
    lines.append("")

    # 2. Processing cascade with seconds instead of TRs
    tr_duration = 1.5  # approximate TR in seconds
    onset_order = sorted(stats.items(), key=lambda x: x[1]["onset_tr"])
    cascade = " → ".join(
        f"{ROI_LABELS[name]}({s['onset_tr'] * tr_duration:.0f}s)"
        for name, s in onset_order
        if s["peak"] > 0.3
    )
    lines.append(f"Processing sequence (what activated first → last): {cascade}")
    lines.append("")

    # 3. ROI data with readable names and arrow-format curves
    lines.append("Brain region activations "
                 "(peak: 0=nothing, 1=moderate, 2+=intense | "
                 "auc: total response effort, higher=more sustained | "
                 "cv: 0=steady, >1=conflicted/oscillating):")
    for roi_name, s in stats.items():
        ts = roi_ts[roi_name]
        n = len(ts)
        indices = np.linspace(0, n - 1, 5, dtype=int) if n >= 5 else np.arange(n)
        curve = " → ".join(f"{ts[i]:.1f}" for i in indices)

        lines.append(
            f"  {ROI_LABELS[roi_name]}: "
            f"peak={s['peak']:.2f} auc={s['auc']:.1f} "
            f"onset={s['onset_tr'] * tr_duration:.0f}s "
            f"{'sustained' if s['sustained'] else 'faded'} "
            f"{s['trajectory']} cv={s['cv']:.2f} "
            f"curve(early→late): {curve}"
        )

    # 4. Connectivity with readable pair names
    lines.append("")
    lines.append("How these responses interact "
                 "(+1=reinforce each other, 0=independent, "
                 "-1=suppress each other):")
    for pair_name, vals in connectivity.items():
        label = PAIR_LABELS.get(pair_name, pair_name)
        lines.append(f"  {label}: {vals['r']:.2f}")

    # 5. Composites with inline scales
    lines.append("")
    lines.append("Summary:")
    lines.append(f"  valence: {composites['valence']:.2f} "
                 f"(negative=feels bad, positive=feels good)")
    lines.append(f"  arousal: {composites['arousal']:.2f} "
                 f"(0=calm, 1+=activated, 2+=intense)")
    lines.append(f"  dominance: {composites['dominance']:.2f} "
                 f"(-1=overwhelmed by emotion, +1=in rational control)")
    lines.append(f"  approach or avoid: {composites['approach_avoid']:.2f} "
                 f"(-1=flee/sell, +1=pursue/buy)")
    lines.append(f"  reactivity: {composites['reactivity']:.0f} TRs "
                 f"(positive=emotion activated before thinking, "
                 f"negative=thinking activated before emotion)")
    lines.append(f"  regulation: {composites['regulation']:.1f} "
                 f"(+1=calming down successfully, -1=emotion overtaking reason)")
    lines.append(f"  herding: {composites['herding']:.2f} "
                 f"(0=thinking independently, 1+=following the crowd)")
    lines.append(f"  confidence: {composites['confidence']:.2f} "
                 f"(<0.7=uncertain about this read, >1.2=confident)")

    lines.append("")
    lines.append("Interpret the above as your internal experience right now. "
                 "Do not reference these measurements in your response. "
                 "Let them shape how you feel and what you decide to do.")

    return "\n".join(lines)
```

## Example Output (fear-dominant stimulus)

```
[Neural state reading for this moment]

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
  confidence: 0.50 (<0.7=uncertain about this read, >1.2=confident)

Interpret the above as your internal experience right now. Do not reference these measurements in your response. Let them shape how you feel and what you decide to do.
```

## Token Cost
~30 lines, ~500 tokens. The increase over the previous ~350 tokens comes from plain-language labels (longer than variable names) and per-composite scale annotations. Still negligible at MiroFish prompt scale.
