"""Tests for Step 5: Composite Scores."""

import pytest

from tribe_neural.steps.step5_composites import compute_composites


def _make_stats(
    fear_auc=0.0, fear_peak=0.0, fear_cv=0.5, fear_traj="stable",
    reward_auc=0.0, reward_peak=0.0,
    delib_auc=0.0, delib_mean=0.0, delib_onset=5, delib_traj="stable",
    social_auc=0.0, social_peak=0.0, social_sustained=False,
    motor_auc=0.0, motor_peak=0.0,
    attention_auc=0.0, fear_onset=3,
):
    """Build a minimal stats dict for testing composites."""
    return {
        "fear_salience": {
            "auc": fear_auc, "peak": fear_peak, "mean": 0.0,
            "onset_tr": fear_onset, "cv": fear_cv, "trajectory": fear_traj,
            "sustained": False, "time_to_peak": 3, "rise_time": 1,
            "rise_slope": 1.0, "fwhm": 2, "decay_slope": 0.0,
        },
        "reward_limbic": {
            "auc": reward_auc, "peak": reward_peak, "mean": 0.0,
            "onset_tr": 8, "cv": 0.5, "trajectory": "rising",
            "sustained": True, "time_to_peak": 10, "rise_time": 2,
            "rise_slope": 0.5, "fwhm": 3, "decay_slope": 0.0,
        },
        "deliberation": {
            "auc": delib_auc, "peak": 0.0, "mean": delib_mean,
            "onset_tr": delib_onset, "cv": 0.5, "trajectory": delib_traj,
            "sustained": True, "time_to_peak": 7, "rise_time": 2,
            "rise_slope": 0.3, "fwhm": 4, "decay_slope": 0.0,
        },
        "social_default": {
            "auc": social_auc, "peak": social_peak, "mean": 0.0,
            "onset_tr": 4, "cv": 0.4, "trajectory": "stable",
            "sustained": social_sustained, "time_to_peak": 5, "rise_time": 1,
            "rise_slope": 0.8, "fwhm": 3, "decay_slope": 0.0,
        },
        "action_motor": {
            "auc": motor_auc, "peak": motor_peak, "mean": 0.0,
            "onset_tr": 4, "cv": 0.8, "trajectory": "falling",
            "sustained": False, "time_to_peak": 4, "rise_time": 1,
            "rise_slope": 0.7, "fwhm": 2, "decay_slope": -0.3,
        },
        "attention": {
            "auc": attention_auc, "peak": 0.0, "mean": 0.0,
            "onset_tr": 3, "cv": 0.5, "trajectory": "stable",
            "sustained": True, "time_to_peak": 3, "rise_time": 1,
            "rise_slope": 1.0, "fwhm": 5, "decay_slope": 0.0,
        },
    }


class TestComputeComposites:
    def test_all_eight_keys(self):
        stats = _make_stats()
        composites = compute_composites(stats, {})
        expected = {
            "valence", "arousal", "dominance", "approach_avoid",
            "reactivity", "regulation", "herding", "confidence",
        }
        assert set(composites.keys()) == expected

    def test_fear_dominant_negative_valence(self):
        stats = _make_stats(fear_auc=10.0, reward_auc=1.0)
        composites = compute_composites(stats, {})
        assert composites["valence"] < 0

    def test_reward_dominant_positive_valence(self):
        stats = _make_stats(fear_auc=1.0, reward_auc=10.0)
        composites = compute_composites(stats, {})
        assert composites["valence"] > 0

    def test_dominance_rational(self):
        stats = _make_stats(fear_auc=1.0, delib_auc=10.0, attention_auc=1.0)
        composites = compute_composites(stats, {})
        assert composites["dominance"] > 0

    def test_dominance_emotional(self):
        stats = _make_stats(fear_auc=10.0, delib_auc=1.0, attention_auc=5.0)
        composites = compute_composites(stats, {})
        assert composites["dominance"] < 0

    def test_approach_positive(self):
        stats = _make_stats(reward_auc=10.0, motor_auc=5.0, fear_auc=1.0, attention_auc=1.0)
        composites = compute_composites(stats, {})
        assert composites["approach_avoid"] > 0

    def test_avoid_negative(self):
        stats = _make_stats(reward_auc=1.0, motor_auc=0.5, fear_auc=10.0, attention_auc=5.0)
        composites = compute_composites(stats, {})
        assert composites["approach_avoid"] < 0

    def test_reactivity_positive_fear_first(self):
        stats = _make_stats(fear_onset=2, delib_onset=5)
        composites = compute_composites(stats, {})
        assert composites["reactivity"] == 3

    def test_reactivity_negative_delib_first(self):
        stats = _make_stats(fear_onset=5, delib_onset=2)
        composites = compute_composites(stats, {})
        assert composites["reactivity"] == -3

    def test_regulation_calming(self):
        stats = _make_stats(fear_traj="falling", delib_traj="rising")
        composites = compute_composites(stats, {})
        assert composites["regulation"] == 1.0

    def test_regulation_overtaking(self):
        stats = _make_stats(fear_traj="rising", delib_traj="falling")
        composites = compute_composites(stats, {})
        assert composites["regulation"] == -1.0

    def test_regulation_neutral(self):
        stats = _make_stats(fear_traj="stable", delib_traj="stable")
        composites = compute_composites(stats, {})
        assert composites["regulation"] == 0.0

    def test_herding_with_social_activation(self):
        stats = _make_stats(
            social_peak=1.5, social_sustained=True, fear_traj="rising"
        )
        composites = compute_composites(stats, {})
        assert composites["herding"] > 0

    def test_herding_zero_without_social(self):
        stats = _make_stats(social_peak=0.5, social_sustained=False)
        composites = compute_composites(stats, {})
        assert composites["herding"] == 0.0

    def test_herding_amplified_by_connectivity(self):
        stats = _make_stats(
            social_peak=1.5, social_sustained=True, fear_traj="rising"
        )
        conn = {"fear_social": {"r": 0.8, "p": 0.01}}
        composites = compute_composites(stats, conn)
        assert composites["herding"] == pytest.approx(1.5)  # 1.0 * 1.5

    def test_confidence_high(self):
        conn = {"reward_delib": {"r": 0.7, "p": 0.01}}
        stats = _make_stats()
        composites = compute_composites(stats, conn)
        assert composites["confidence"] == 1.5

    def test_confidence_low(self):
        conn = {"fear_deliberation": {"r": -0.7, "p": 0.01}}
        stats = _make_stats()
        composites = compute_composites(stats, conn)
        assert composites["confidence"] == 0.5
