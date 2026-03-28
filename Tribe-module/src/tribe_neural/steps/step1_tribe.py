"""Step 1: TRIBE v2 forward pass — text to cortical predictions."""

from __future__ import annotations

import logging
import os
import tempfile

import numpy as np

from tribe_neural.constants import NUM_VERTICES
from tribe_neural.validation import PipelineError

logger = logging.getLogger(__name__)


def run_tribe(text: str, model: object) -> np.ndarray:
    """Run TRIBE v2 inference on naturalistic text.

    Writes text to a temp file (TRIBE v2 expects a file path), runs the
    model, and returns predicted cortical surface activations.

    Args:
        text: Naturalistic text string.
        model: Loaded TribeModel instance.

    Returns:
        Array of shape (n_TRs, 20484).

    Raises:
        PipelineError: If inference fails or output is invalid.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f:
        f.write(text)
        path = f.name

    try:
        df = model.get_events_dataframe(text_path=path)
        preds, _ = model.predict(events=df)
    except Exception as exc:
        raise PipelineError(step=1, detail=f"TRIBE v2 inference failed: {exc}") from exc
    finally:
        os.unlink(path)

    if preds.ndim != 2 or preds.shape[1] != NUM_VERTICES:
        raise PipelineError(
            step=1,
            detail=(
                f"Unexpected TRIBE output shape {preds.shape}, "
                f"expected (n_TRs, {NUM_VERTICES})"
            ),
        )

    if preds.shape[0] == 0:
        raise PipelineError(
            step=1,
            detail="TRIBE v2 returned 0 timepoints — text may be too short",
        )

    if np.isnan(preds).any():
        raise PipelineError(
            step=1, detail="TRIBE v2 output contains NaN values"
        )

    logger.info("TRIBE v2 produced %d TRs", preds.shape[0])
    return preds
