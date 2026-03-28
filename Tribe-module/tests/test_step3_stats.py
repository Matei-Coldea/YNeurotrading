"""Tests for Step 3: Summary Statistics."""

import numpy as np
import pytest

from tribe_neural.steps.step3_stats import extract_stats


class TestExtractStats:
    def test_rising_trajectory(self, rising_ts):
        s = extract_stats(rising_ts)
        assert s["trajectory"] == "rising"
        assert s["peak"] == pytest.approx(1.7)
        assert s["time_to_peak"] == 9  # last element

    def test_peaked_trajectory(self, peaked_ts):
        s = extract_stats(peaked_ts)
        # Peaked signal may be "falling" or "stable" depending on symmetry
        assert s["trajectory"] in ("falling", "stable")
        assert s["peak"] == pytest.approx(1.8)
        assert s["time_to_peak"] == 4  # index of 1.8
        assert s["onset_tr"] < s["time_to_peak"]
        assert s["rise_time"] > 0
        assert s["fwhm"] > 0

    def test_clearly_falling_trajectory(self):
        # Asymmetric: high first half, very low second half
        ts = np.array([0.0, 1.0, 2.0, 1.8, 1.5, 0.3, 0.1, 0.0, 0.0, 0.0])
        s = extract_stats(ts)
        assert s["trajectory"] == "falling"

    def test_flat_signal(self, flat_ts):
        s = extract_stats(flat_ts)
        assert s["trajectory"] == "stable"
        assert s["peak"] == pytest.approx(0.05)
        assert s["auc"] == pytest.approx(0.45, abs=0.1)

    def test_all_zero(self, all_zero_ts):
        s = extract_stats(all_zero_ts)
        assert s["peak"] == 0.0
        assert s["auc"] == 0.0
        assert s["onset_tr"] == 10  # equals n (never crossed threshold)
        assert s["sustained"] is False

    def test_short_timeseries(self, short_ts):
        s = extract_stats(short_ts)
        assert s["trajectory"] == "stable"  # n < 4
        assert s["peak"] == pytest.approx(1.0)

    def test_sustained_flag(self):
        # Last 3 values above 0.5 * threshold
        ts = np.array([0.0, 0.0, 0.5, 1.0, 1.5, 1.5, 1.5])
        s = extract_stats(ts)
        assert s["sustained"] is True

    def test_not_sustained(self):
        # Last 3 values are near zero
        ts = np.array([0.0, 1.0, 2.0, 1.5, 0.1, 0.0, 0.0])
        s = extract_stats(ts)
        assert s["sustained"] is False

    def test_constant_nonzero(self):
        ts = np.full(10, 1.0)
        s = extract_stats(ts)
        assert s["cv"] == pytest.approx(0.0, abs=0.01)
        assert s["trajectory"] == "stable"

    def test_all_eleven_keys_present(self, peaked_ts):
        s = extract_stats(peaked_ts)
        expected_keys = {
            "peak", "mean", "auc", "onset_tr", "time_to_peak",
            "rise_time", "rise_slope", "fwhm", "sustained",
            "trajectory", "cv", "decay_slope",
        }
        assert set(s.keys()) == expected_keys

    def test_rise_slope_positive(self, peaked_ts):
        s = extract_stats(peaked_ts)
        assert s["rise_slope"] > 0

    def test_auc_nonnegative(self):
        # Even with negative values, AUC clips to 0
        ts = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])
        s = extract_stats(ts)
        assert s["auc"] >= 0
