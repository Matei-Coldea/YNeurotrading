"""Step 5: Compute 8 composite scores from statistics and connectivity."""

from __future__ import annotations


def compute_composites(stats: dict, conn: dict) -> dict:
    """Compute 8 higher-level summary values.

    Args:
        stats: Dict mapping ROI names to their 11-stat dicts.
        conn: Dict mapping pair names to {"r": float, "p": float}.

    Returns:
        Dict with keys: valence, arousal, dominance, approach_avoid,
        reactivity, regulation, herding, confidence.
    """
    s = stats

    # Valence: positive <-> negative (AUC-weighted)
    valence = (
        0.35 * s["reward_limbic"]["auc"]
        - 0.30 * s["fear_salience"]["auc"]
        + 0.15 * s["deliberation"]["mean"]
        - 0.20 * s.get("attention", {}).get("auc", 0)
    )

    # Arousal: overall activation intensity
    arousal = (
        0.20 * s["fear_salience"]["auc"]
        + 0.20 * s["reward_limbic"]["auc"]
        + 0.20 * s["fear_salience"]["peak"]
        + 0.15 * s["social_default"]["auc"]
        + 0.15 * s.get("attention", {}).get("auc", 0)
        + 0.10 * s["action_motor"]["peak"]
    )

    # Dominance: rational vs emotional (-1 to +1 ratio)
    emo = s["fear_salience"]["auc"] + s.get("attention", {}).get("auc", 0)
    rat = s["deliberation"]["auc"]
    dominance = (rat - emo) / (rat + emo + 1e-6)

    # Approach-avoid: buy vs sell (-1 to +1 ratio)
    approach = s["reward_limbic"]["auc"] + 0.5 * s["action_motor"]["auc"]
    avoid = s["fear_salience"]["auc"] + s.get("attention", {}).get("auc", 0)
    approach_avoid = (approach - avoid) / (approach + avoid + 1e-6)

    # Reactivity: fear onset - deliberation onset (TRs)
    reactivity = s["deliberation"]["onset_tr"] - s["fear_salience"]["onset_tr"]

    # Regulation: fear falling while deliberation rising?
    ft = s["fear_salience"]["trajectory"]
    dt = s["deliberation"]["trajectory"]
    if ft == "falling" and dt in ("rising", "stable"):
        regulation = 1.0
    elif ft == "rising" and dt == "falling":
        regulation = -1.0
    else:
        regulation = 0.0

    # Herding: social activation + connectivity adjustment
    herding = 0.0
    if s["social_default"]["peak"] > 1.0 and s["social_default"]["sustained"]:
        herding = 1.0 if ft == "rising" else 0.5
    fsr = conn.get("fear_social", {}).get("r", 0)
    if fsr > 0.5:
        herding *= 1.5
    elif fsr < -0.3:
        herding *= 0.3

    # Confidence: from connectivity + variability
    rdr = conn.get("reward_delib", {}).get("r", 0)
    fdr = conn.get("fear_deliberation", {}).get("r", 0)
    if rdr > 0.5:
        confidence = 1.5
    elif fdr < -0.5:
        confidence = 0.5
    elif s["fear_salience"]["cv"] > 1.5:
        confidence = 0.6
    else:
        confidence = 1.0

    return {
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "approach_avoid": approach_avoid,
        "reactivity": reactivity,
        "regulation": regulation,
        "herding": herding,
        "confidence": confidence,
    }
