"""One-time script: Validate VIFS transfer from real fMRI to TRIBE v2.

Processes 5 known stimuli through TRIBE v2, computes VIFS scores, and
checks that fear stimuli score higher than neutral. If validation fails,
creates a marker file and the pipeline falls back to NiMARE weighting.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Stimuli designed to evoke distinct neural responses
VALIDATION_STIMULI = {
    "fear": (
        "You hear a loud crash behind you. Someone screams. "
        "Glass is shattering everywhere and you feel your heart pounding."
    ),
    "neutral": (
        "You are reading a weather report. Tomorrow will be partly cloudy "
        "with a high of 72 degrees and light winds from the southwest."
    ),
    "positive": (
        "You just received news that you won a scholarship. Your family "
        "is celebrating and everyone is smiling and hugging you."
    ),
    "uncertain": (
        "The doctor says the test results are unusual but not conclusive. "
        "They want to run more tests next week before making any decisions."
    ),
    "surprise": (
        "You open your front door and find a large package you did not order. "
        "Inside is something completely unexpected that you cannot identify."
    ),
}


def main(data_dir: str) -> None:
    data_path = Path(data_dir)

    vifs_path = data_path / "vifs_surface.npy"
    if not vifs_path.exists():
        logger.error("VIFS surface file not found at %s — run project_signatures.py first", vifs_path)
        return

    vifs_weights = np.load(str(vifs_path))
    logger.info("Loaded VIFS weights: shape=%s", vifs_weights.shape)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        logger.error("HF_TOKEN not set — cannot load TRIBE model")
        return

    from tribev2.demo_utils import TribeModel

    logger.info("Loading TRIBE v2 model...")
    model = TribeModel.from_pretrained(
        "facebook/tribev2",
        cache_folder=str(data_path / "cache"),
    )

    import tempfile

    scores: dict[str, float] = {}
    for label, text in VALIDATION_STIMULI.items():
        logger.info("Processing stimulus: %s", label)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(text)
            path = f.name
        try:
            df = model.get_events_dataframe(text_path=path)
            preds, _ = model.predict(events=df)
            # VIFS score = mean dot product across TRs
            vifs_scores = np.array(
                [np.dot(preds[t, :], vifs_weights) for t in range(preds.shape[0])]
            )
            scores[label] = float(np.mean(vifs_scores))
            logger.info("  %s: VIFS score = %.4f", label, scores[label])
        finally:
            os.unlink(path)

    # Validation: fear should score higher than neutral
    fear_score = scores.get("fear", 0)
    neutral_score = scores.get("neutral", 0)

    if fear_score > neutral_score:
        logger.info("VALIDATION PASSED: fear (%.4f) > neutral (%.4f)",
                     fear_score, neutral_score)
        marker = data_path / "vifs_validated"
        marker.touch()
        # Remove failure marker if it exists
        fail_marker = data_path / "vifs_validation_failed"
        if fail_marker.exists():
            fail_marker.unlink()
    else:
        logger.warning(
            "VALIDATION FAILED: fear (%.4f) <= neutral (%.4f) — "
            "VIFS transfer does not work with TRIBE v2 predictions. "
            "Pipeline will fall back to NiMARE weighted averaging.",
            fear_score, neutral_score,
        )
        marker = data_path / "vifs_validation_failed"
        marker.touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate VIFS signature transfer to TRIBE v2"
    )
    parser.add_argument("--data-dir", required=True, help="Data directory")
    args = parser.parse_args()
    main(args.data_dir)
