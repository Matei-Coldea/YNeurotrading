"""Integration test: Steps 2-6 with synthetic data."""

import numpy as np
import pytest

from tribe_neural.steps.step2_roi import extract_all
from tribe_neural.steps.step3_stats import extract_stats
from tribe_neural.steps.step4_connectivity import compute_connectivity
from tribe_neural.steps.step5_composites import compute_composites
from tribe_neural.steps.step6_format import format_output


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
