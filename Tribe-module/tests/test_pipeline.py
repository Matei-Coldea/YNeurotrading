"""Integration test: Steps 2-6 with synthetic data."""

import numpy as np
import pytest

from tribe_neural.constants import NUM_VERTICES
from tribe_neural.steps.step2_roi import extract_all
from tribe_neural.steps.step3_stats import extract_stats
from tribe_neural.steps.step4_connectivity import compute_connectivity
from tribe_neural.steps.step5_composites import compute_composites
from tribe_neural.steps.step6_format import format_output


def _run_steps_2_to_5(preds, masks, weights, signatures):
    """Helper: run steps 2-5 and return (roi_ts, stats, conn, composites)."""
    roi_ts = extract_all(preds, masks, weights, signatures)
    stats = {name: extract_stats(ts) for name, ts in roi_ts.items()}
    conn = compute_connectivity(roi_ts)
    composites = compute_composites(stats, conn)
    return roi_ts, stats, conn, composites


def _make_composites_stats(
    fear_auc=0.0, fear_peak=0.0, fear_cv=0.5, fear_traj="stable",
    reward_auc=0.0, delib_auc=0.0, delib_mean=0.0,
    social_auc=0.0, social_peak=0.0,
    motor_auc=0.0, attention_auc=0.0,
    fear_onset=3, delib_onset=5,
):
    """Minimal stats dict for composites testing in integration tests."""
    base = {
        "auc": 0.0, "peak": 0.0, "mean": 0.0, "onset_tr": 5, "cv": 0.5,
        "trajectory": "stable", "sustained": True, "time_to_peak": 5,
        "rise_time": 1, "rise_slope": 0.5, "fwhm": 3, "decay_slope": 0.0,
    }
    return {
        "fear_salience": {**base, "auc": fear_auc, "peak": fear_peak,
                          "cv": fear_cv, "trajectory": fear_traj,
                          "onset_tr": fear_onset},
        "reward_limbic": {**base, "auc": reward_auc},
        "deliberation": {**base, "auc": delib_auc, "mean": delib_mean,
                         "onset_tr": delib_onset},
        "social_default": {**base, "auc": social_auc, "peak": social_peak},
        "action_motor": {**base, "auc": motor_auc},
        "attention": {**base, "auc": attention_auc},
    }


class TestPipelineIntegration:
    def test_full_pipeline_steps_2_through_6(
        self, synthetic_preds, synthetic_masks, synthetic_weights, synthetic_signatures
    ):
        """Run steps 2-6 end-to-end with synthetic 20484-vertex predictions."""
        # Step 2
        roi_ts = extract_all(
            synthetic_preds, synthetic_masks,
            synthetic_weights, synthetic_signatures,
        )
        assert len(roi_ts) == 6
        for ts in roi_ts.values():
            assert ts.shape == (15,)

        # Step 3
        stats = {name: extract_stats(ts) for name, ts in roi_ts.items()}
        assert len(stats) == 6
        for s in stats.values():
            assert len(s) == 12  # 11 stats + decay_slope = 12 keys

        # Step 4
        connectivity = compute_connectivity(roi_ts)
        assert len(connectivity) == 7

        # Step 5
        composites = compute_composites(stats, connectivity)
        assert len(composites) == 8

        # Step 6
        output = format_output(stats, connectivity, composites, roi_ts)
        assert isinstance(output, str)
        assert "[Neural state reading for this moment]" in output
        assert "Dominant response:" in output
        assert "Processing sequence" in output
        assert "Summary:" in output
        assert "valence:" in output

    def test_output_is_nonempty_string(
        self, synthetic_preds, synthetic_masks, synthetic_weights, synthetic_signatures
    ):
        roi_ts = extract_all(
            synthetic_preds, synthetic_masks,
            synthetic_weights, synthetic_signatures,
        )
        stats = {name: extract_stats(ts) for name, ts in roi_ts.items()}
        connectivity = compute_connectivity(roi_ts)
        composites = compute_composites(stats, connectivity)
        output = format_output(stats, connectivity, composites, roi_ts)
        assert len(output) > 100
        lines = output.strip().split("\n")
        assert len(lines) >= 20


class TestDifferentiation:
    """Verify the pipeline produces meaningfully different composites for
    different emotional activation patterns — the core requirement for the
    neural state to actually modulate agent behavior."""

    @pytest.fixture
    def masks_and_weights(self):
        """Non-overlapping masks + uniform weights for 6 ROIs."""
        rois = [
            "fear_salience", "reward_limbic", "deliberation",
            "social_default", "action_motor", "attention",
        ]
        chunk = NUM_VERTICES // len(rois)
        masks = {}
        for i, name in enumerate(rois):
            m = np.zeros(NUM_VERTICES, dtype=bool)
            m[i * chunk : (i + 1) * chunk] = True
            masks[name] = m
        weights = {
            t: np.ones(NUM_VERTICES, dtype=np.float32)
            for t in ["fear", "reward", "conflict", "social", "uncertainty", "motor"]
        }
        sigs = {"vifs": None, "pines": None}
        return masks, weights, sigs

    def _make_preds(self, n_trs, activation_map, masks):
        """Build synthetic preds where specific ROI regions are boosted.

        activation_map: dict mapping ROI name -> amplitude multiplier.
        """
        rng = np.random.default_rng(42)
        preds = rng.standard_normal((n_trs, NUM_VERTICES)).astype(np.float32) * 0.1
        for roi_name, amp in activation_map.items():
            preds[:, masks[roi_name]] += amp
        return preds

    def test_fear_vs_reward_valence(self, masks_and_weights):
        """Fear-heavy input -> negative valence, reward-heavy -> positive."""
        masks, weights, sigs = masks_and_weights

        fear_preds = self._make_preds(
            15, {"fear_salience": 2.0, "reward_limbic": 0.2}, masks,
        )
        reward_preds = self._make_preds(
            15, {"fear_salience": 0.2, "reward_limbic": 2.0}, masks,
        )

        _, _, _, fear_comp = _run_steps_2_to_5(fear_preds, masks, weights, sigs)
        _, _, _, reward_comp = _run_steps_2_to_5(reward_preds, masks, weights, sigs)

        assert fear_comp["valence"] < reward_comp["valence"]
        assert fear_comp["approach_avoid"] < reward_comp["approach_avoid"]

    def test_calm_vs_intense_arousal(self, masks_and_weights):
        """Low activation -> low arousal, high activation -> high arousal.
        Uses ramping signals (not flat offsets) so global normalization
        preserves the amplitude difference."""
        masks, weights, sigs = masks_and_weights
        n_trs = 15

        # Calm: small ramps
        rng = np.random.default_rng(42)
        calm_preds = rng.standard_normal((n_trs, NUM_VERTICES)).astype(np.float32) * 0.02
        ramp = np.linspace(0, 0.2, n_trs)[:, None]
        calm_preds[:, masks["fear_salience"]] += ramp
        calm_preds[:, masks["reward_limbic"]] += ramp
        calm_preds[:, masks["social_default"]] += ramp * 0.5
        calm_preds[:, masks["action_motor"]] += ramp * 0.3

        # Intense: large ramps on the same ROIs (15x stronger)
        intense_preds = rng.standard_normal((n_trs, NUM_VERTICES)).astype(np.float32) * 0.02
        ramp_big = np.linspace(0, 3.0, n_trs)[:, None]
        intense_preds[:, masks["fear_salience"]] += ramp_big
        intense_preds[:, masks["reward_limbic"]] += ramp_big
        intense_preds[:, masks["social_default"]] += ramp_big * 0.8
        intense_preds[:, masks["action_motor"]] += ramp_big * 0.5

        _, _, _, calm_comp = _run_steps_2_to_5(calm_preds, masks, weights, sigs)
        _, _, _, intense_comp = _run_steps_2_to_5(intense_preds, masks, weights, sigs)

        assert intense_comp["arousal"] > calm_comp["arousal"]

    def test_rational_vs_emotional_dominance(self, masks_and_weights):
        """Deliberation-heavy -> positive dominance, fear-heavy -> negative."""
        masks, weights, sigs = masks_and_weights

        rational_preds = self._make_preds(
            15, {"deliberation": 2.0, "fear_salience": 0.2, "attention": 0.2},
            masks,
        )
        emotional_preds = self._make_preds(
            15, {"deliberation": 0.2, "fear_salience": 2.0, "attention": 2.0},
            masks,
        )

        _, _, _, rat_comp = _run_steps_2_to_5(rational_preds, masks, weights, sigs)
        _, _, _, emo_comp = _run_steps_2_to_5(emotional_preds, masks, weights, sigs)

        assert rat_comp["dominance"] > emo_comp["dominance"]

    def test_short_vs_long_text_comparable(self, masks_and_weights):
        """Short (5 TRs) and long (20 TRs) inputs with same activation
        pattern should produce composites in the same direction thanks
        to z-score normalization."""
        masks, weights, sigs = masks_and_weights

        short_preds = self._make_preds(
            5, {"fear_salience": 2.0, "reward_limbic": 0.3}, masks,
        )
        long_preds = self._make_preds(
            20, {"fear_salience": 2.0, "reward_limbic": 0.3}, masks,
        )

        _, _, _, short_comp = _run_steps_2_to_5(short_preds, masks, weights, sigs)
        _, _, _, long_comp = _run_steps_2_to_5(long_preds, masks, weights, sigs)

        # Both should show negative valence (fear-dominant)
        assert short_comp["valence"] < 0
        assert long_comp["valence"] < 0
        # Both should show avoidance
        assert short_comp["approach_avoid"] < 0
        assert long_comp["approach_avoid"] < 0

    def test_social_herding_via_composites(self):
        """High social AUC with fear rising and positive fear-social
        connectivity produces higher herding than a low-social baseline.
        Tests the composite formula directly since z-scoring makes
        integration-level vertex tests unreliable for herding."""
        from tribe_neural.steps.step5_composites import compute_composites

        high_social = _make_composites_stats(
            social_auc=8.0, fear_traj="rising",
        )
        low_social = _make_composites_stats(
            social_auc=1.0, fear_traj="stable",
        )
        conn = {"fear_social": {"r": 0.6, "p": 0.02}}

        h_high = compute_composites(high_social, conn)["herding"]
        h_low = compute_composites(low_social, conn)["herding"]
        assert h_high > h_low
