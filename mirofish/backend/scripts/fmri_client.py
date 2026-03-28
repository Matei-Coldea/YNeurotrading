"""Async HTTP client for the TRIBEv2 neural processing server."""

from __future__ import annotations

import logging
import os

import aiohttp

logger = logging.getLogger("mirofish.fmri_client")

FMRI_SERVER_URL = os.getenv("FMRI_SERVER_URL", "http://localhost:8000")
FMRI_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def get_neural_state(
    text: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Send narrative text to TRIBEv2 server, return neural state string.

    Returns *None* on any failure so the agent can proceed without
    a neural state (graceful degradation).
    """
    try:
        async with session.post(
            f"{FMRI_SERVER_URL}/process",
            json={"text": text},
            timeout=FMRI_TIMEOUT,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("result")
            logger.warning("fMRI server returned status %d", resp.status)
            return None
    except Exception as exc:
        logger.warning("fMRI request failed: %s", exc)
        return None
