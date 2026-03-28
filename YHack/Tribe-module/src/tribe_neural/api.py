"""FastAPI application — exposes the neural processing pipeline on port 8000."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from tribe_neural.init_resources import Resources, load_resources
from tribe_neural.pipeline import process
from tribe_neural.validation import PipelineError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Semaphore to prevent concurrent GPU requests from OOM
_gpu_semaphore = asyncio.Semaphore(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all resources at startup, release on shutdown."""
    logger.info("Loading resources...")
    resources = load_resources()
    app.state.resources = resources
    logger.info("All resources loaded — server ready")
    yield


app = FastAPI(
    title="TRIBE v2 Neural Processing",
    version="0.1.0",
    lifespan=lifespan,
)


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


class HealthResponse(BaseModel):
    status: str
    gpu_available: bool


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        import torch

        gpu = torch.cuda.is_available()
    except ImportError:
        gpu = False
    return HealthResponse(status="ok", gpu_available=gpu)


@app.post("/process", response_model=ProcessResponse)
async def process_endpoint(req: ProcessRequest):
    resources: Resources = app.state.resources
    t0 = time.perf_counter()

    async with _gpu_semaphore:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, process, req.text, resources)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return ProcessResponse(result=result, processing_time_ms=round(elapsed_ms, 1))


@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError):
    logger.error("Pipeline error at step %d: %s", exc.step, exc.detail)
    return JSONResponse(
        status_code=500,
        content={"error": "Processing failed", "step": exc.step},
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
