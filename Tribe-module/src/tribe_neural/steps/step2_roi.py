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


# VIFS signature is disabled for text inputs.  VIFS was trained on
# real fMRI responses to *visual* fear stimuli.  TRIBE v2's text
# pathway (LLaMA → TTS → Wav2Vec) produces spatial patterns that
# anti-correlate with VIFS, making the dot product negative for all
# text — including genuinely fearful text.  Falling back to the
# NiMARE weighted-average (Layers 1+2) gives correct directionality.
_DISABLED_SIGNATURES: set[str] = {"vifs"}

# action_motor (SomMot network) always shows high baseline activation
# for text inputs because TTS triggers speech-motor cortex.  This is
# a confound, not an emotional signal.  We demean it and exclude it
# from the global-std calculation so it doesn't drown out the actual
# emotional ROIs.
_SPEECH_CONFOUND_ROI = "action_motor"


def extract_all(
    preds: np.ndarray,
    masks: dict[str, np.ndarray],
    weight_maps: dict[str, np.ndarray],
    signatures: dict[str, np.ndarray | None],
) -> dict[str, np.ndarray]:
    """Extract timeseries for all 6 ROIs.

    Applies three corrections for text-pathway artifacts:
    1. VIFS signature is disabled (anti-correlates with text predictions).
    2. action_motor is demeaned to remove the speech-motor confound.
    3. Global normalization uses only non-motor ROIs so that the
       constant motor baseline doesn't compress emotional variation.

    Args:
        preds: Array of shape (n_TRs, 20484).
        masks: Dict mapping ROI names to boolean arrays (20484,).
        weight_maps: Dict mapping NiMARE term names to float arrays (20484,).
        signatures: Dict mapping signature names to arrays or None.

    Returns:
        Dict mapping 6 ROI names to 1-D normalized arrays of shape (n_TRs,).
    """
    # (weight_key, signature_name, signature_array)
    mapping: dict[str, tuple[str, str | None, np.ndarray | None]] = {
        "fear_salience": ("fear", "vifs", signatures.get("vifs")),
        "reward_limbic": ("reward", None, None),
        "deliberation": ("conflict", None, None),
        "social_default": ("social", None, None),
        "attention": ("uncertainty", None, None),
        "action_motor": ("motor", None, None),
    }

    roi_ts: dict[str, np.ndarray] = {}
    for roi_name, (weight_key, sig_name, sig) in mapping.items():
        # Disable signatures that don't transfer to text predictions
        if sig is not None and sig_name in _DISABLED_SIGNATURES:
            sig = None
        w = weight_maps.get(weight_key, masks[roi_name].astype(float))

        # Broaden reward_limbic with "memory" weights — autobiographical
        # recall regions (hippocampus, medial temporal) co-activate during
        # positive emotional content but aren't captured by the narrow
        # Neurosynth "reward" term alone.
        if roi_name == "reward_limbic" and "memory" in weight_maps:
            w = w + 0.5 * weight_maps["memory"]

        roi_ts[roi_name] = extract_timeseries(preds, masks[roi_name], w, sig)

    # Demean action_motor to remove constant speech-motor baseline,
    # then clip negatives so demeaning doesn't create artificial peaks.
    if _SPEECH_CONFOUND_ROI in roi_ts:
        ts = roi_ts[_SPEECH_CONFOUND_ROI]
        roi_ts[_SPEECH_CONFOUND_ROI] = np.maximum(ts - ts.mean(), 0.0)

    # Global normalization: compute std from emotional ROIs only
    # (excluding motor) so the speech confound doesn't compress
    # the actual emotional variation.
    emotional_vals = np.concatenate([
        ts for name, ts in roi_ts.items()
        if name != _SPEECH_CONFOUND_ROI
    ])
    global_std = float(emotional_vals.std())
    if global_std > 1e-6:
        for name in roi_ts:
            roi_ts[name] = roi_ts[name] / global_std

    return roi_ts
