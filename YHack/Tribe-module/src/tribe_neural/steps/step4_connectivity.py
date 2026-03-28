"""Step 4: Pairwise connectivity between ROI timeseries."""

from __future__ import annotations

from scipy.stats import pearsonr

from tribe_neural.constants import PAIRS


def compute_connectivity(roi_ts: dict) -> dict:
    """Compute Pearson correlation between 7 predefined ROI pairs.

    Pairs with fewer than 4 timepoints are skipped (correlation unreliable).

    Args:
        roi_ts: Dict mapping ROI names to 1-D numpy arrays.

    Returns:
        Dict mapping pair names to {"r": float, "p": float}.
    """
    conn: dict = {}
    for name, (a, b) in PAIRS.items():
        if a in roi_ts and b in roi_ts and len(roi_ts[a]) > 3:
            r, pval = pearsonr(roi_ts[a], roi_ts[b])
            conn[name] = {"r": round(float(r), 3), "p": round(float(pval), 4)}
    return conn
