"""Tests for Step 2: ROI Timeseries Extraction."""

import numpy as np
import pytest

from tribe_neural.constants import NUM_VERTICES
from tribe_neural.steps.step2_roi import extract_all, extract_timeseries


class TestExtractTimeseries:
    def test_weighted_average(self):
        preds = np.ones((5, NUM_VERTICES))
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[:100] = True
        weights = np.ones(NUM_VERTICES)
        ts = extract_timeseries(preds, mask, weights)
        # All ones, mask selects 100 vertices, weights=1 -> avg = 1.0
        assert ts.shape == (5,)
        np.testing.assert_allclose(ts, 1.0, atol=0.01)

    def test_signature_overrides_weighted(self):
        preds = np.ones((5, NUM_VERTICES))
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[:100] = True
        weights = np.ones(NUM_VERTICES)
        sig = np.zeros(NUM_VERTICES)
        sig[:50] = 2.0  # signature has different weights
        ts = extract_timeseries(preds, mask, weights, signature_weights=sig)
        # dot product of ones with sig = sum(sig) = 100.0
        assert ts.shape == (5,)
        assert ts[0] == pytest.approx(100.0)

    def test_fallback_when_weights_zero(self):
        preds = np.ones((5, NUM_VERTICES)) * 3.0
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[:100] = True
        weights = np.zeros(NUM_VERTICES)  # all zero weights
        ts = extract_timeseries(preds, mask, weights)
        # Falls back to unweighted mean of masked vertices
        assert ts.shape == (5,)
        np.testing.assert_allclose(ts, 3.0, atol=0.01)

    def test_output_shape_matches_trs(self):
        n_trs = 20
        preds = np.random.default_rng(42).standard_normal((n_trs, NUM_VERTICES))
        mask = np.zeros(NUM_VERTICES, dtype=bool)
        mask[:500] = True
        weights = np.ones(NUM_VERTICES)
        ts = extract_timeseries(preds, mask, weights)
        assert ts.shape == (n_trs,)


class TestExtractAll:
    def test_returns_six_rois(
        self, synthetic_preds, synthetic_masks, synthetic_weights, synthetic_signatures
    ):
        roi_ts = extract_all(
            synthetic_preds, synthetic_masks,
            synthetic_weights, synthetic_signatures,
        )
        assert len(roi_ts) == 6
        expected_rois = {
            "fear_salience", "reward_limbic", "deliberation",
            "social_default", "action_motor", "attention",
        }
        assert set(roi_ts.keys()) == expected_rois

    def test_timeseries_length_matches_trs(
        self, synthetic_preds, synthetic_masks, synthetic_weights, synthetic_signatures
    ):
        roi_ts = extract_all(
            synthetic_preds, synthetic_masks,
            synthetic_weights, synthetic_signatures,
        )
        for name, ts in roi_ts.items():
            assert ts.shape == (15,), f"{name} has wrong shape"

    def test_with_vifs_signature(
        self, synthetic_preds, synthetic_masks, synthetic_weights
    ):
        vifs = np.random.default_rng(99).standard_normal(NUM_VERTICES).astype(np.float32)
        sigs = {"vifs": vifs, "pines": None}
        roi_ts = extract_all(
            synthetic_preds, synthetic_masks, synthetic_weights, sigs,
        )
        # fear_salience should use signature path (dot product)
        assert roi_ts["fear_salience"].shape == (15,)
        # Other ROIs should use weighted average (no signature)
        assert roi_ts["deliberation"].shape == (15,)
