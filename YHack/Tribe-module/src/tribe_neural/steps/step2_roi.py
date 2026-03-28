"""Step 2: ROI timeseries extraction using 3-layer approach."""

from __future__ import annotations

import numpy as np


def extract_timeseries(
    preds: np.ndarray,
    schaefer_mask: np.ndarray,
    nimare_weights: np.ndarray,
    signature_weights: np.ndarray | None = None,
) -> np.ndarray:
    """Extract a single ROI timeseries from cortical predictions.

    Combines Schaefer mask (Layer 1) with NiMARE weights (Layer 2).
    If a trained signature is provided (Layer 3), returns that instead.

    Args:
        preds: Array of shape (n_TRs, 20484).
        schaefer_mask: Boolean array of shape (20484,).
        nimare_weights: Float array of shape (20484,).
        signature_weights: Optional signed weight array of shape (20484,).

    Returns:
        1-D array of shape (n_TRs,).
    """
    n_trs = preds.shape[0]

    # Layer 3: signature dot product (preferred if available)
    if signature_weights is not None:
        return np.array(
            [np.dot(preds[t, :], signature_weights) for t in range(n_trs)]
        )

    # Layers 1+2: Schaefer mask * NiMARE weights -> weighted average
    combined = nimare_weights * schaefer_mask
    w_sum = combined.sum()
    if w_sum > 0:
        return np.array(
            [np.dot(preds[t, :], combined) / w_sum for t in range(n_trs)]
        )

    # Fallback: unweighted mean within Schaefer mask
    return preds[:, schaefer_mask].mean(axis=1)


def extract_all(
    preds: np.ndarray,
    masks: dict[str, np.ndarray],
    weight_maps: dict[str, np.ndarray],
    signatures: dict[str, np.ndarray | None],
) -> dict[str, np.ndarray]:
    """Extract timeseries for all 6 ROIs.

    Args:
        preds: Array of shape (n_TRs, 20484).
        masks: Dict mapping ROI names to boolean arrays (20484,).
        weight_maps: Dict mapping NiMARE term names to float arrays (20484,).
        signatures: Dict mapping signature names to arrays or None.

    Returns:
        Dict mapping 6 ROI names to 1-D arrays of shape (n_TRs,).
    """
    mapping: dict[str, tuple[str, np.ndarray | None]] = {
        "fear_salience": ("fear", signatures.get("vifs")),
        "reward_limbic": ("reward", None),
        "deliberation": ("conflict", None),
        "social_default": ("social", None),
        "attention": ("uncertainty", None),
        "action_motor": ("motor", None),
    }

    roi_ts: dict[str, np.ndarray] = {}
    for roi_name, (weight_key, sig) in mapping.items():
        w = weight_maps.get(weight_key, masks[roi_name].astype(float))
        roi_ts[roi_name] = extract_timeseries(preds, masks[roi_name], w, sig)

    return roi_ts
