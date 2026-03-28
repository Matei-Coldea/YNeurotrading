"""Tests for Step 4: Pairwise Connectivity."""

import numpy as np
import pytest

from tribe_neural.steps.step4_connectivity import compute_connectivity


class TestComputeConnectivity:
    def test_perfectly_correlated(self):
        ts = np.linspace(0, 1, 15)
        roi_ts = {
            "fear_salience": ts,
            "social_default": ts,
            "deliberation": ts,
            "reward_limbic": ts,
            "action_motor": ts,
            "attention": ts,
        }
        conn = compute_connectivity(roi_ts)
        assert conn["fear_social"]["r"] == pytest.approx(1.0, abs=0.001)

    def test_anticorrelated(self):
        ts = np.linspace(0, 1, 15)
        roi_ts = {
            "fear_salience": ts,
            "social_default": -ts,
            "deliberation": ts,
            "reward_limbic": ts,
            "action_motor": ts,
            "attention": ts,
        }
        conn = compute_connectivity(roi_ts)
        assert conn["fear_social"]["r"] == pytest.approx(-1.0, abs=0.001)

    def test_independent_signals(self):
        rng = np.random.default_rng(123)
        roi_ts = {
            "fear_salience": rng.standard_normal(100),
            "social_default": rng.standard_normal(100),
            "deliberation": rng.standard_normal(100),
            "reward_limbic": rng.standard_normal(100),
            "action_motor": rng.standard_normal(100),
            "attention": rng.standard_normal(100),
        }
        conn = compute_connectivity(roi_ts)
        # With 100 random points, correlations should be near zero
        for pair in conn.values():
            assert abs(pair["r"]) < 0.3

    def test_short_timeseries_skipped(self):
        # Only 3 TRs — should skip all pairs
        ts = np.array([1.0, 2.0, 3.0])
        roi_ts = {
            "fear_salience": ts,
            "social_default": ts,
            "deliberation": ts,
            "reward_limbic": ts,
            "action_motor": ts,
            "attention": ts,
        }
        conn = compute_connectivity(roi_ts)
        assert len(conn) == 0

    def test_missing_roi(self):
        ts = np.linspace(0, 1, 15)
        roi_ts = {
            "fear_salience": ts,
            # social_default is missing
        }
        conn = compute_connectivity(roi_ts)
        assert "fear_social" not in conn

    def test_all_seven_pairs(self, synthetic_roi_ts):
        conn = compute_connectivity(synthetic_roi_ts)
        assert len(conn) == 7
        for pair in conn.values():
            assert "r" in pair
            assert "p" in pair
            assert -1.0 <= pair["r"] <= 1.0

    def test_p_values_present(self, synthetic_roi_ts):
        conn = compute_connectivity(synthetic_roi_ts)
        for pair in conn.values():
            assert 0.0 <= pair["p"] <= 1.0
