"""Pipeline orchestrator — calls Steps 1-6 in sequence."""

from __future__ import annotations

import logging
import time

from tribe_neural.init_resources import Resources
from tribe_neural.steps.step1_tribe import run_tribe
from tribe_neural.steps.step2_roi import extract_all
from tribe_neural.steps.step3_stats import extract_stats
from tribe_neural.steps.step4_connectivity import compute_connectivity
from tribe_neural.steps.step5_composites import compute_composites
from tribe_neural.steps.step6_format import format_output
from tribe_neural.validation import PipelineError

logger = logging.getLogger(__name__)


def process(text: str, resources: Resources) -> str:
    """Run the full 6-step neural processing pipeline.

    Args:
        text: Naturalistic text string, ready for TRIBE v2.
        resources: Pre-loaded model, masks, weights, and signatures.

    Returns:
        Formatted ~30-line LLM-readable neural state string.

    Raises:
        PipelineError: If any step fails.
    """
    t0 = time.perf_counter()

    # Step 1: TRIBE v2 forward pass (2-5s on GPU)
    try:
        preds = run_tribe(text, resources.model)
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(step=1, detail=str(exc)) from exc

    t1 = time.perf_counter()
    logger.info("Step 1 (TRIBE): %.1fms", (t1 - t0) * 1000)

    # Step 2: ROI timeseries extraction (<10ms)
    try:
        roi_ts = extract_all(
            preds, resources.masks, resources.weight_maps, resources.signatures
        )
    except Exception as exc:
        raise PipelineError(step=2, detail=str(exc)) from exc

    t2 = time.perf_counter()
    logger.info("Step 2 (ROI): %.1fms", (t2 - t1) * 1000)

    # Step 3: Summary statistics (<10ms)
    try:
        stats = {name: extract_stats(ts) for name, ts in roi_ts.items()}
    except Exception as exc:
        raise PipelineError(step=3, detail=str(exc)) from exc

    t3 = time.perf_counter()
    logger.info("Step 3 (Stats): %.1fms", (t3 - t2) * 1000)

    # Step 4: Pairwise connectivity (<5ms)
    try:
        connectivity = compute_connectivity(roi_ts)
    except Exception as exc:
        raise PipelineError(step=4, detail=str(exc)) from exc

    t4 = time.perf_counter()
    logger.info("Step 4 (Connectivity): %.1fms", (t4 - t3) * 1000)

    # Step 5: Composite scores (<1ms)
    try:
        composites = compute_composites(stats, connectivity)
    except Exception as exc:
        raise PipelineError(step=5, detail=str(exc)) from exc

    t5 = time.perf_counter()
    logger.info("Step 5 (Composites): %.1fms", (t5 - t4) * 1000)

    # Step 6: Format output (<1ms)
    try:
        result = format_output(stats, connectivity, composites, roi_ts)
    except Exception as exc:
        raise PipelineError(step=6, detail=str(exc)) from exc

    t6 = time.perf_counter()
    logger.info("Step 6 (Format): %.1fms", (t6 - t5) * 1000)
    logger.info("Total pipeline: %.1fms", (t6 - t0) * 1000)

    return result
