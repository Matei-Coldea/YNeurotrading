"""Step 6: Format all computed data into an LLM-readable string."""

from __future__ import annotations

import numpy as np

from tribe_neural.constants import PAIR_LABELS, ROI_LABELS, TR_DURATION


def format_output(
    stats: dict,
    connectivity: dict,
    composites: dict,
    roi_ts: dict,
) -> str:
    """Produce ~30-line LLM-readable neural state string.

    Uses plain-language labels, arrow-format temporal curves, inline scales,
    and a dominant signal callout.

    Args:
        stats: Dict mapping ROI names to 11-stat dicts.
        connectivity: Dict mapping pair names to {"r", "p"} dicts.
        composites: Dict of 8 composite scores.
        roi_ts: Dict mapping ROI names to 1-D numpy timeseries arrays.

    Returns:
        Formatted multi-line string.
    """
    lines: list[str] = ["[Neural state reading for this moment]", ""]

    # 1. Dominant signal callout — use peak * sqrt(auc) so that a brief
    # spike (high peak, low auc) doesn't outrank a strong sustained
    # response.  Exclude social_default from the dominant contest because
    # narrative text always activates DMN heavily — it's a baseline for
    # any story, not a distinguishing emotional signal.
    _NARRATIVE_BASELINE_ROIS = {"social_default"}
    salience = {
        name: s["peak"] * (1.0 + s["auc"]) ** 0.5
        for name, s in stats.items()
        if name not in _NARRATIVE_BASELINE_ROIS
    }
    strongest = max(salience, key=salience.get)
    weakest = min(salience, key=salience.get)
    peaks = {name: s["peak"] for name, s in stats.items()}
    lines.append(
        f"Dominant response: {ROI_LABELS[strongest]} "
        f"(peak={peaks[strongest]:.2f})"
    )
    lines.append(
        f"Weakest response: {ROI_LABELS[weakest]} "
        f"(peak={peaks[weakest]:.2f})"
    )
    lines.append("")

    # 2. Processing cascade with seconds (all ROIs, no filtering)
    onset_order = sorted(stats.items(), key=lambda x: x[1]["onset_tr"])
    cascade = " \u2192 ".join(
        f"{ROI_LABELS[name]}({s['onset_tr'] * TR_DURATION:.0f}s)"
        for name, s in onset_order
    )
    lines.append(
        f"Processing sequence (what activated first \u2192 last): {cascade}"
    )
    lines.append("")

    # 3. ROI data — all 11 statistics per region
    lines.append(
        "Brain region activations "
        "(peak: 0=nothing, 1=moderate, 2+=intense | "
        "auc: total response effort, higher=more sustained | "
        "cv: 0=steady, >1=conflicted/oscillating):"
    )
    for roi_name, s in stats.items():
        ts = roi_ts[roi_name]
        n = len(ts)
        indices = (
            np.linspace(0, n - 1, 5, dtype=int) if n >= 5 else np.arange(n)
        )
        curve = " \u2192 ".join(f"{ts[i]:.1f}" for i in indices)

        lines.append(
            f"  {ROI_LABELS[roi_name]}:"
        )
        lines.append(
            f"    peak={s['peak']:.2f} mean={s['mean']:.2f} auc={s['auc']:.1f}"
        )
        lines.append(
            f"    onset={s['onset_tr'] * TR_DURATION:.0f}s "
            f"time_to_peak={s['time_to_peak'] * TR_DURATION:.0f}s "
            f"rise_time={s['rise_time'] * TR_DURATION:.0f}s "
            f"rise_slope={s['rise_slope']:.3f}"
        )
        lines.append(
            f"    fwhm={s['fwhm'] * TR_DURATION:.0f}s "
            f"{'sustained' if s['sustained'] else 'faded'} "
            f"{s['trajectory']} "
            f"cv={s['cv']:.2f} "
            f"decay_slope={s['decay_slope']:.3f}"
        )
        lines.append(
            f"    curve(early\u2192late): {curve}"
        )

    # 4. Connectivity with readable pair names
    lines.append("")
    lines.append(
        "How these responses interact "
        "(+1=reinforce each other, 0=independent, "
        "-1=suppress each other):"
    )
    for pair_name, vals in connectivity.items():
        label = PAIR_LABELS.get(pair_name, pair_name)
        lines.append(f"  {label}: r={vals['r']:.2f} p={vals['p']:.4f}")

    # 5. Composites with inline scales
    lines.append("")
    lines.append("Summary:")
    lines.append(
        f"  valence: {composites['valence']:.2f} "
        f"(negative=feels bad, positive=feels good)"
    )
    lines.append(
        f"  arousal: {composites['arousal']:.2f} "
        f"(0=calm, 1+=activated, 2+=intense)"
    )
    lines.append(
        f"  dominance: {composites['dominance']:.2f} "
        f"(-1=overwhelmed by emotion, +1=in rational control)"
    )
    lines.append(
        f"  approach or avoid: {composites['approach_avoid']:.2f} "
        f"(-1=flee/sell, +1=pursue/buy)"
    )
    lines.append(
        f"  reactivity: {composites['reactivity']:.0f} TRs "
        f"(positive=emotion activated before thinking, "
        f"negative=thinking activated before emotion)"
    )
    lines.append(
        f"  regulation: {composites['regulation']:.1f} "
        f"(+1=calming down successfully, -1=emotion overtaking reason)"
    )
    lines.append(
        f"  herding: {composites['herding']:.2f} "
        f"(0=thinking independently, 1+=following the crowd)"
    )
    lines.append(
        f"  confidence: {composites['confidence']:.2f} "
        f"(<0.7=uncertain about this read, >1.2=confident)"
    )

    lines.append("")
    lines.append(
        "Interpret the above as your internal experience right now. "
        "Do not reference these measurements in your response. "
        "Let them shape how you feel and what you decide to do."
    )

    return "\n".join(lines)
