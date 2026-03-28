# Step 5: Composite Scores

Eight summary values computed from the statistics and connectivity. AUC-weighted, ratio-based, incorporating temporal dynamics.

## The 8 Composites

| Score | Range | Output Label | Inline Scale (shown to LLM) |
|---|---|---|---|
| `valence` | continuous | `valence` | `negative=feels bad, positive=feels good` |
| `arousal` | continuous (≥0) | `arousal` | `0=calm, 1+=activated, 2+=intense` |
| `dominance` | -1 to +1 | `dominance` | `-1=overwhelmed by emotion, +1=in rational control` |
| `approach_avoid` | -1 to +1 | `approach or avoid` | `-1=flee/sell, +1=pursue/buy` |
| `reactivity` | integer TRs | `reactivity` | `positive=emotion activated before thinking, negative=thinking activated before emotion` |
| `regulation` | -1, 0, or 1 | `regulation` | `+1=calming down successfully, -1=emotion overtaking reason` |
| `herding` | 0 to ~2.25 | `herding` | `0=thinking independently, 1+=following the crowd` |
| `confidence` | 0.5 to 1.5 | `confidence` | `<0.7=uncertain about this read, >1.2=confident` |

Each composite is output with its inline scale annotation so the LLM can interpret the number without external reference.

## Implementation

```python
def compute_composites(stats, conn):
    s = stats

    # Valence: positive <-> negative (AUC-weighted)
    valence = (0.35*s['reward_limbic']['auc'] - 0.30*s['fear_salience']['auc']
              + 0.15*s['deliberation']['mean'] - 0.20*s.get('attention',{}).get('auc',0))

    # Arousal: overall activation intensity
    arousal = (0.20*s['fear_salience']['auc'] + 0.20*s['reward_limbic']['auc']
              + 0.20*s['fear_salience']['peak'] + 0.15*s['social_default']['auc']
              + 0.15*s.get('attention',{}).get('auc',0) + 0.10*s['action_motor']['peak'])

    # Dominance: rational vs emotional (-1 to +1 ratio)
    emo = s['fear_salience']['auc'] + s.get('attention',{}).get('auc',0)
    rat = s['deliberation']['auc']
    dominance = (rat-emo)/(rat+emo+1e-6)

    # Approach-avoid: buy vs sell (-1 to +1 ratio)
    approach = s['reward_limbic']['auc'] + 0.5*s['action_motor']['auc']
    avoid = s['fear_salience']['auc'] + s.get('attention',{}).get('auc',0)
    approach_avoid = (approach-avoid)/(approach+avoid+1e-6)

    # Reactivity: fear onset - deliberation onset (TRs)
    reactivity = s['deliberation']['onset_tr'] - s['fear_salience']['onset_tr']

    # Regulation: fear falling while deliberation rising?
    ft, dt = s['fear_salience']['trajectory'], s['deliberation']['trajectory']
    regulation = 1.0 if ft=='falling' and dt in ['rising','stable'] else -1.0 if ft=='rising' and dt=='falling' else 0.0

    # Herding: social activation + connectivity adjustment
    herding = 0.0
    if s['social_default']['peak']>1.0 and s['social_default']['sustained']:
        herding = 1.0 if ft=='rising' else 0.5
    fsr = conn.get('fear_social',{}).get('r',0)
    if fsr>0.5: herding *= 1.5
    elif fsr<-0.3: herding *= 0.3

    # Confidence: from connectivity + variability
    rdr = conn.get('reward_delib',{}).get('r',0)
    fdr = conn.get('fear_deliberation',{}).get('r',0)
    if rdr>0.5: confidence=1.5
    elif fdr<-0.5: confidence=0.5
    elif s['fear_salience']['cv']>1.5: confidence=0.6
    else: confidence=1.0

    return {'valence':valence,'arousal':arousal,'dominance':dominance,
            'approach_avoid':approach_avoid,'reactivity':reactivity,
            'regulation':regulation,'herding':herding,'confidence':confidence}
```

## Interpretation Notes
- **Valence** uses weighted coefficients: reward (0.35), fear (-0.30), deliberation (0.15), attention (-0.20)
- **Dominance** and **approach_avoid** are ratio-based with epsilon to avoid division by zero
- **Herding** has a multiplicative connectivity adjustment — strong fear-social coupling amplifies, anti-correlation suppresses
- **Confidence** uses discrete thresholds, not continuous — this is intentional
