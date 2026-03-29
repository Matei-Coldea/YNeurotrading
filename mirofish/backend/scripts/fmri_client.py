"""Async HTTP client for the TRIBEv2 neural processing server."""

from __future__ import annotations

import os

import aiohttp

FMRI_TIMEOUT = aiohttp.ClientTimeout(total=60)


def _server_url() -> str:
    return os.getenv("FMRI_SERVER_URL", "http://localhost:8000")


async def warmup() -> bool:
    """Ping /health to wake up the RunPod pod. Call once before simulation starts."""
    url = f"{_server_url()}/health"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                ok = resp.status == 200
                if ok:
                    data = await resp.json()
                    print(f"[fMRI] Warmup → 200 OK (gpu={data.get('gpu_available')})", flush=True)
                else:
                    print(f"[fMRI] Warmup → {resp.status} FAILED", flush=True)
                return ok
    except Exception as exc:
        print(f"[fMRI] Warmup → unreachable: {exc}", flush=True)
        return False


async def get_neural_state(text: str) -> str | None:
    """Send narrative text to TRIBEv2 server, return neural state string.

    Creates its own HTTP session per call (avoids shared-session issues
    with OASIS's concurrent agent execution).
    """
    url = f"{_server_url()}/process"
    word_count = len(text.split())
    try:
        import time as _time
        t0 = _time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"text": text},
                timeout=FMRI_TIMEOUT,
            ) as resp:
                elapsed = _time.perf_counter() - t0
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("result")
                    chars = len(result) if result else 0
                    print(f"[fMRI] Process → {word_count} words in, {chars} chars back, {elapsed:.1f}s", flush=True)
                    return result
                body = await resp.text()
                print(f"[fMRI] Process → FAILED status={resp.status} ({body[:200]})", flush=True)
                return None
    except Exception as exc:
        print(f"[fMRI] Process → ERROR: {exc}", flush=True)
        return None
