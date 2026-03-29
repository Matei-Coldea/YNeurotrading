"""ARQ GPU worker — loads the TRIBE model once, processes jobs from Redis."""

from __future__ import annotations

import logging
import time

from arq import cron  # noqa: F401 (available for future scheduled jobs)
from arq.connections import RedisSettings

from tribe_neural.init_resources import Resources, load_resources
from tribe_neural.pipeline import process

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Module-level handle; populated in startup().
_resources: Resources | None = None


async def startup(ctx: dict) -> None:
    """Load the TRIBE model + masks into GPU memory once per worker."""
    logger.info("GPU worker starting — loading resources...")
    resources = load_resources()
    ctx["resources"] = resources
    logger.info("GPU worker ready")


async def shutdown(ctx: dict) -> None:
    logger.info("GPU worker shutting down")


async def process_text(ctx: dict, text: str) -> dict:
    """Run the full pipeline for a single text input.

    Returns a dict (not a Pydantic model) so ARQ can serialize it
    through Redis without custom encoders.
    """
    resources: Resources = ctx["resources"]
    t0 = time.perf_counter()
    result = process(text, resources)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {"result": result, "processing_time_ms": round(elapsed_ms, 1)}


class WorkerSettings:
    """ARQ worker configuration.

    ARQ discovers this class by name when started with:
        arq tribe_neural.worker.WorkerSettings
    """

    functions = [process_text]
    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings(
        host=__import__("os").environ.get("REDIS_HOST", "localhost"),
        port=int(__import__("os").environ.get("REDIS_PORT", "6379")),
    )

    # One job at a time — the GPU can only handle one TRIBE inference.
    max_jobs = 1

    # How long to let a single job run before timing out (seconds).
    job_timeout = 120

    # How long results stay in Redis (seconds).
    keep_result = 300

    # Graceful shutdown timeout.
    health_check_interval = 10
