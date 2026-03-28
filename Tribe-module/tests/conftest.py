"""Shared test fixtures with synthetic neural data."""

from __future__ import annotations

import numpy as np
import pytest

from tribe_neural.constants import NUM_VERTICES


@pytest.fixture
def synthetic_preds() -> np.ndarray:
    """Synthetic TRIBE output: 15 TRs, 20484 vertices."""
    rng = np.random.default_rng(42)
    return rng.standard_normal((15, NUM_VERTICES)).astype(np.float32)


@pytest.fixture
def rising_ts() -> np.ndarray:
    """Timeseries that clearly rises over time."""
    return np.array([0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 1.7])


@pytest.fixture
def peaked_ts() -> np.ndarray:
    """Timeseries that spikes then declines (fear-like)."""
    return np.array([0.0, 0.3, 0.8, 1.4, 1.8, 1.5, 1.0, 0.6, 0.3, 0.1])


@pytest.fixture
def flat_ts() -> np.ndarray:
    """Constant near-zero timeseries."""
    return np.full(10, 0.05)


@pytest.fixture
def all_zero_ts() -> np.ndarray:
    """All-zero timeseries."""
    return np.zeros(10)


@pytest.fixture
def short_ts() -> np.ndarray:
    """Very short timeseries (2 TRs)."""
    return np.array([0.5, 1.0])


@pytest.fixture
def synthetic_roi_ts() -> dict[str, np.ndarray]:
    """Dict of 6 ROI timeseries with known properties."""
    return {
        "fear_salience": np.array(
            [0.0, 0.5, 1.2, 1.8, 1.5, 1.0, 0.7, 0.4, 0.2, 0.1,
             0.0, 0.0, 0.0, 0.0, 0.0]
        ),
        "reward_limbic": np.array(
            [0.0, 0.0, 0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.5, 0.5,
             0.5, 0.5, 0.5, 0.5, 0.5]
        ),
        "deliberation": np.array(
            [0.0, 0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 0.9, 0.8,
             0.7, 0.7, 0.7, 0.7, 0.7]
        ),
        "social_default": np.array(
            [0.0, 0.3, 0.8, 1.2, 1.4, 1.3, 1.1, 1.0, 1.0, 1.0,
             1.0, 1.0, 1.0, 1.0, 1.0]
        ),
        "action_motor": np.array(
            [0.0, 0.1, 0.3, 0.5, 0.7, 0.5, 0.3, 0.1, 0.0, 0.0,
             0.0, 0.0, 0.0, 0.0, 0.0]
        ),
        "attention": np.array(
            [0.0, 0.4, 1.0, 1.5, 1.4, 1.3, 1.2, 1.0, 0.9, 0.9,
             0.9, 0.9, 0.9, 0.9, 0.9]
        ),
    }


@pytest.fixture
def synthetic_masks() -> dict[str, np.ndarray]:
    """6 boolean masks covering non-overlapping vertex ranges."""
    masks = {}
    rois = [
        "fear_salience", "reward_limbic", "deliberation",
        "social_default", "action_motor", "attention",
    ]
    chunk = NUM_VERTICES // len(rois)
    for i, name in enumerate(rois):
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[i * chunk : (i + 1) * chunk] = True
        masks[name] = mask
    return masks


@pytest.fixture
def synthetic_weights() -> dict[str, np.ndarray]:
    """Uniform weight maps for testing (weight=1.0 everywhere)."""
    return {
        term: np.ones(NUM_VERTICES, dtype=np.float32)
        for term in ["fear", "reward", "conflict", "social", "uncertainty", "motor"]
    }


@pytest.fixture
def synthetic_signatures() -> dict[str, np.ndarray | None]:
    """No signatures (all None) — forces Layer 1+2 path."""
    return {"vifs": None, "pines": None}


@pytest.fixture
def fear_dominant_stats(synthetic_roi_ts) -> dict:
    """Stats computed from synthetic_roi_ts (fear-dominant)."""
    from tribe_neural.steps.step3_stats import extract_stats
    return {name: extract_stats(ts) for name, ts in synthetic_roi_ts.items()}


@pytest.fixture
def fear_dominant_connectivity(synthetic_roi_ts) -> dict:
    """Connectivity computed from synthetic_roi_ts."""
    from tribe_neural.steps.step4_connectivity import compute_connectivity
    return compute_connectivity(synthetic_roi_ts)
