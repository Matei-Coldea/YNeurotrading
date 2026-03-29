"""Async HTTP client for the TRIBEv2 neural processing server."""

from __future__ import annotations

import logging
import os

import aiohttp

logger = logging.getLogger("mirofish.fmri_client")

FMRI_TIMEOUT = aiohttp.ClientTimeout(total=300)


def _server_url() -> str:
    return os.getenv("FMRI_SERVER_URL", "http://localhost:8000")


async def warmup(session: aiohttp.ClientSession) -> bool:
    """Ping /health to wake up the RunPod pod. Call once before simulation starts.

    Returns True if the server is reachable, False otherwise.
    """
    url = f"{_server_url()}/health"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            ok = resp.status == 200
            if ok:
                logger.info("fMRI server is up: %s", await resp.json())
            else:
                logger.warning("fMRI server health check returned %d", resp.status)
            return ok
    except Exception as exc:
        logger.warning("fMRI server unreachable: %r", exc)
        return False


async def get_neural_state(
    text: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Send narrative text to TRIBEv2 server, return neural state string.

    Returns *None* on any failure so the agent can proceed without
    a neural state (graceful degradation).
    """
    url = f"{_server_url()}/process"
    try:
        async with session.post(
            url,
            json={"text": text},
            timeout=FMRI_TIMEOUT,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("result")
            logger.warning("fMRI server returned status %d", resp.status)
            return None
    except Exception as exc:
        logger.warning("fMRI request failed: %r", exc)
        return None
