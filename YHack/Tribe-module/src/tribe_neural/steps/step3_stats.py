"""Step 3: Extract 11 summary statistics from each ROI timeseries."""

from __future__ import annotations

import numpy as np


def extract_stats(ts: np.ndarray) -> dict:
    """Compute 11 interpretable features from a single ROI timeseries.

    Args:
        ts: 1-D array of activation values, one per TR.

    Returns:
        Dict with keys: peak, mean, auc, onset_tr, time_to_peak,
        rise_time, rise_slope, fwhm, sustained, trajectory, cv, decay_slope.
    """
    n = len(ts)
    peak = float(np.max(ts))
    mean_val = float(np.mean(ts))
    std = float(np.std(ts))
    threshold = max(std, 0.3)

    above = np.where(ts > threshold)[0]
    onset = int(above[0]) if len(above) > 0 else n

    ttp = int(np.argmax(ts))
    rt = max(0, ttp - onset)

    auc = float(np.trapezoid(np.maximum(ts, 0)))

    hm = peak / 2
    ah = ts >= hm
    if ah.any():
        indices = np.where(ah)[0]
        fwhm = int(indices[-1] - indices[0] + 1)
    else:
        fwhm = 0

    sustained = bool(np.mean(ts[-3:]) > 0.5 * threshold) if n >= 3 else False

    if n >= 4:
        fh = np.mean(ts[: n // 2])
        sh = np.mean(ts[n // 2 :])
        if sh > fh + 0.3 * std:
            trajectory = "rising"
        elif sh < fh - 0.3 * std:
            trajectory = "falling"
        else:
            trajectory = "stable"
    else:
        trajectory = "stable"

    if rt > 0:
        rise_slope = float((peak - ts[onset]) / rt)
    else:
        rise_slope = float(peak)

    cv = float(std / (abs(mean_val) + 1e-6))

    pp = ts[ttp:]
    if len(pp) > 2 and np.mean(pp) > 0.01:
        decay_slope = float(
            np.polyfit(np.arange(len(pp)), np.log(np.maximum(pp, 0.01)), 1)[0]
        )
    else:
        decay_slope = 0.0

    return {
        "peak": peak,
        "mean": mean_val,
        "auc": auc,
        "onset_tr": onset,
        "time_to_peak": ttp,
        "rise_time": rt,
        "rise_slope": rise_slope,
        "fwhm": fwhm,
        "sustained": sustained,
        "trajectory": trajectory,
        "cv": cv,
        "decay_slope": decay_slope,
    }
