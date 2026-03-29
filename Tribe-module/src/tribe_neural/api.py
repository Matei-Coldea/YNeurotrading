"""FastAPI application — CPU-only HTTP layer that enqueues GPU work via ARQ."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from arq.connections import ArqRedis, RedisSettings, create_pool
from arq.jobs import Job, JobStatus
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from tribe_neural.validation import PipelineError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_REDIS_SETTINGS = RedisSettings(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
)

# How long /process will wait for the GPU worker to finish (seconds).
# With queued jobs, a request may wait for prior jobs to complete first,
# so this needs to be generous: (max_queue_depth * inference_time).
_JOB_TIMEOUT = float(os.environ.get("TRIBE_JOB_TIMEOUT", "300"))

# Poll interval when waiting for a job result (seconds).
_POLL_INTERVAL = 0.25


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open a Redis connection pool at startup, close on shutdown."""
    logger.info("Connecting to Redis at %s:%s ...", _REDIS_SETTINGS.host, _REDIS_SETTINGS.port)
    pool: ArqRedis = await create_pool(_REDIS_SETTINGS)
    app.state.arq = pool
    logger.info("Redis connected — API ready (GPU work is handled by ARQ workers)")
    yield
    await pool.aclose()


app = FastAPI(
    title="TRIBE v2 Neural Processing",
    version="0.2.0",
    lifespan=lifespan,
)


# ── Request / Response models ────────────────────────────────────────

class ProcessRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=20,
        max_length=10_000,
        description="Naturalistic text for TRIBE v2 processing",
    )


class ProcessResponse(BaseModel):
    result: str
    processing_time_ms: float


class EnqueueResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: ProcessResponse | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    gpu_available: bool


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        import torch
        gpu = torch.cuda.is_available()
    except ImportError:
        gpu = False
    return HealthResponse(status="ok", gpu_available=gpu)


@app.post("/process", response_model=ProcessResponse)
async def process_sync(req: ProcessRequest):
    """Enqueue text for GPU processing and wait for the result.

    This is the synchronous endpoint — it blocks until the GPU worker
    finishes (up to _JOB_TIMEOUT seconds).  Use /enqueue + /job/{id}
    if you prefer async polling.
    """
    import asyncio

    pool: ArqRedis = app.state.arq
    t0 = time.perf_counter()

    job: Job = await pool.enqueue_job("process_text", req.text)
    logger.info("Enqueued job %s", job.job_id)

    deadline = t0 + _JOB_TIMEOUT
    while time.perf_counter() < deadline:
        status = await job.status()
        if status == JobStatus.complete:
            info = await job.result_info()
            if info and info.success:
                data = info.result
                # Include queue wait time in the total
                total_ms = (time.perf_counter() - t0) * 1000
                return ProcessResponse(
                    result=data["result"],
                    processing_time_ms=round(total_ms, 1),
                )
            else:
                error_msg = str(info.result) if info else "Unknown error"
                raise PipelineError(step=0, detail=f"Worker failed: {error_msg}")
        if status == JobStatus.not_found:
            raise PipelineError(step=0, detail="Job lost from queue")
        await asyncio.sleep(_POLL_INTERVAL)

    raise PipelineError(step=0, detail=f"Job timed out after {_JOB_TIMEOUT}s")


@app.post("/enqueue", response_model=EnqueueResponse)
async def enqueue(req: ProcessRequest):
    """Enqueue text for GPU processing and return the job ID immediately.

    Poll /job/{job_id} to check status and retrieve results.
    """
    pool: ArqRedis = app.state.arq
    job: Job = await pool.enqueue_job("process_text", req.text)
    logger.info("Enqueued job %s", job.job_id)
    return EnqueueResponse(job_id=job.job_id)


@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    """Check the status of an enqueued job."""
    pool: ArqRedis = app.state.arq
    job = Job(job_id=job_id, redis=pool)
    status = await job.status()

    if status == JobStatus.complete:
        info = await job.result_info()
        if info and info.success:
            data = info.result
            return JobStatusResponse(
                job_id=job_id,
                status="complete",
                result=ProcessResponse(
                    result=data["result"],
                    processing_time_ms=data["processing_time_ms"],
                ),
            )
        else:
            return JobStatusResponse(
                job_id=job_id,
                status="failed",
                error=str(info.result) if info else "Unknown error",
            )

    return JobStatusResponse(
        job_id=job_id,
        status=status.value if hasattr(status, "value") else str(status),
    )


# ── Error handlers ───────────────────────────────────────────────────

@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError):
    logger.error("Pipeline error at step %d: %s", exc.step, exc.detail)
    return JSONResponse(
        status_code=500,
        content={"error": "Processing failed", "step": exc.step, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
