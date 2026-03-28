"""Tests for Step 6: Output Formatting."""

import numpy as np
import pytest

from tribe_neural.steps.step5_composites import compute_composites
from tribe_neural.steps.step6_format import format_output


class TestFormatOutput:
    def test_starts_with_header(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert out.startswith("[Neural state reading for this moment]")

    def test_dominant_response_present(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "Dominant response:" in out
        assert "Weakest response:" in out

    def test_uses_plain_language_labels(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        # Should use ROI_LABELS, not variable names
        assert "threat and fear response" in out
        assert "reward and opportunity detection" in out
        assert "analytical thinking and rational control" in out
        # Should NOT contain raw variable names as labels
        assert "fear_salience:" not in out

    def test_connectivity_uses_pair_labels(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "fear \u2194 analytical thinking" in out
        assert "fear \u2194 reward detection" in out

    def test_temporal_arrows_present(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "curve(early\u2192late):" in out
        assert "\u2192" in out  # arrows in cascade and curves

    def test_onset_in_seconds(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        # Onset should be in seconds, not TRs (no "onset=TR" in output)
        assert "onset=" in out
        assert "s " in out  # "onset=3s" etc.

    def test_composites_have_inline_scales(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "negative=feels bad, positive=feels good" in out
        assert "0=calm" in out
        assert "-1=flee/sell, +1=pursue/buy" in out
        assert "0=thinking independently" in out

    def test_trailing_instruction(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "Interpret the above as your internal experience" in out

    def test_processing_sequence_present(
        self, fear_dominant_stats, fear_dominant_connectivity, synthetic_roi_ts
    ):
        composites = compute_composites(
            fear_dominant_stats, fear_dominant_connectivity
        )
        out = format_output(
            fear_dominant_stats, fear_dominant_connectivity,
            composites, synthetic_roi_ts,
        )
        assert "Processing sequence (what activated first" in out
