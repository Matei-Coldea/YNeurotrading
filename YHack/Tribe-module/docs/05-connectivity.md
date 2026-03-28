# Step 4: Pairwise Connectivity

Pearson correlation between ROI timeseries pairs. Reveals how brain regions interact: synchronized (positive r), competing (negative r), or independent (r near zero). Captures the **mode** of processing that individual ROI statistics cannot.

## The 7 Pairs

| Pair Name | ROI A | ROI B | What It Means |
|---|---|---|---|
| `fear_social` | fear_salience | social_default | Fear spreading through social contagion |
| `fear_deliberation` | fear_salience | deliberation | Fear suppressing rational thought (or vice versa) |
| `fear_reward` | fear_salience | reward_limbic | Threat vs opportunity competition |
| `reward_delib` | reward_limbic | deliberation | Calculated reward-seeking |
| `reward_social` | reward_limbic | social_default | Socially-driven reward |
| `action_fear` | action_motor | fear_salience | Fear-driven action (fight/flight) |
| `action_reward` | action_motor | reward_limbic | Reward-driven action (approach) |

## Statistical Validity Concern
With 12 TRs, only r > 0.58 is significant at p < 0.05. **Mitigation:** ensure input text is long enough to produce 20+ TRs. Only trust connectivity with p < 0.1; treat everything else as zero.

## Implementation

```python
from scipy.stats import pearsonr

PAIRS = {
    'fear_social':       ('fear_salience', 'social_default'),
    'fear_deliberation': ('fear_salience', 'deliberation'),
    'fear_reward':       ('fear_salience', 'reward_limbic'),
    'reward_delib':      ('reward_limbic', 'deliberation'),
    'reward_social':     ('reward_limbic', 'social_default'),
    'action_fear':       ('action_motor', 'fear_salience'),
    'action_reward':     ('action_motor', 'reward_limbic'),
}

def compute_connectivity(roi_ts):
    conn = {}
    for name, (a, b) in PAIRS.items():
        if a in roi_ts and b in roi_ts and len(roi_ts[a]) > 3:
            r, pval = pearsonr(roi_ts[a], roi_ts[b])
            conn[name] = {'r': round(float(r),3), 'p': round(float(pval),4)}
    return conn
```

## Output Display Labels
In `format_output`, pair names are converted to plain-language labels for LLM readability:

```python
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

## Output
Dict mapping 7 pair names to `{r, p}` dicts. 7 correlation coefficients describing inter-regional coupling. Displayed with header scale: `+1=reinforce each other, 0=independent, -1=suppress each other`.
