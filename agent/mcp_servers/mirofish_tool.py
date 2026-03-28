"""MiroFish API client — drives the full simulation lifecycle (7 steps with polling)."""

import asyncio
import io
from typing import Callable

import httpx

from config import MIROFISH_API_URL

# Polling config
POLL_INTERVAL_BASE = 3  # seconds
POLL_INTERVAL_MAX = 15
POLL_TIMEOUT = 1800  # 30 minutes max per step


async def run_mirofish_pipeline(
    seed_document: str,
    simulation_requirement: str,
    event_callback: Callable | None = None,
    max_rounds: int = 10,
) -> dict:
    """Drive the full MiroFish simulation lifecycle. Returns dict with project_id, simulation_id, report_id, report_text, report_summary."""

    def emit(event_type: str, payload: dict):
        if event_callback:
            event_callback(event_type, payload)

    async with httpx.AsyncClient(base_url=MIROFISH_API_URL, timeout=120) as client:

        # ── Step 1: Ontology Generation ──
        emit("ontology_started", {"step": "ontology", "status": "running"})

        # Upload seed doc as file
        files = {"files": ("seed.txt", io.BytesIO(seed_document.encode()), "text/plain")}
        data = {"simulation_requirement": simulation_requirement}
        resp = await client.post("/api/graph/ontology/generate", files=files, data=data)
        resp.raise_for_status()
        ontology_result = resp.json()
        project_id = ontology_result.get("project_id")

        ontology = ontology_result.get("ontology", {})
        entity_types = [e.get("name") for e in ontology.get("entity_types", [])]
        relation_types = [r.get("name") for r in ontology.get("edge_types", [])]

        emit("ontology_complete", {
            "step": "ontology", "status": "complete",
            "project_id": project_id,
            "entity_types": entity_types,
            "relation_types": relation_types,
        })

        # ── Step 2: Graph Build ──
        emit("graph_started", {"step": "graph", "status": "running"})

        resp = await client.post("/api/graph/build", json={"project_id": project_id})
        resp.raise_for_status()
        build_result = resp.json()
        task_id = build_result.get("task_id")

        # Poll for graph build completion
        graph_id = await _poll_graph_build(client, task_id, emit)

        emit("graph_complete", {
            "step": "graph", "status": "complete",
            "graph_id": graph_id,
        })

        # ── Step 3: Create Simulation ──
        emit("simulation_create_started", {"step": "simulation_create", "status": "running"})

        resp = await client.post("/api/simulation/create", json={
            "project_id": project_id,
            "graph_id": graph_id,
            "enable_twitter": True,
            "enable_reddit": False,
        })
        resp.raise_for_status()
        sim_result = resp.json()
        simulation_id = sim_result.get("simulation_id")

        emit("simulation_create_complete", {
            "step": "simulation_create", "status": "complete",
            "simulation_id": simulation_id,
        })

        # ── Step 4: Prepare (profiles + config) ──
        emit("prepare_started", {"step": "prepare", "status": "running"})

        resp = await client.post("/api/simulation/prepare", json={
            "simulation_id": simulation_id,
            "use_llm_for_profiles": True,
            "parallel_profile_count": 5,
        })
        resp.raise_for_status()
        prepare_result = resp.json()
        prepare_task_id = prepare_result.get("task_id")

        # Poll for preparation completion
        await _poll_prepare(client, simulation_id, prepare_task_id, emit)

        emit("prepare_complete", {"step": "prepare", "status": "complete", "simulation_id": simulation_id})

        # ── Step 5: Run Simulation ──
        emit("simulation_run_started", {"step": "simulation", "status": "running"})

        resp = await client.post("/api/simulation/start", json={
            "simulation_id": simulation_id,
            "platform": "parallel",
            "max_rounds": max_rounds,
        })
        resp.raise_for_status()

        # Poll for simulation completion
        await _poll_simulation_run(client, simulation_id, emit)

        emit("simulation_run_complete", {"step": "simulation", "status": "complete", "simulation_id": simulation_id})

        # ── Step 6: Generate Report ──
        emit("report_started", {"step": "report", "status": "running"})

        resp = await client.post("/api/report/generate", json={"simulation_id": simulation_id})
        resp.raise_for_status()
        report_result = resp.json()
        report_id = report_result.get("report_id")
        report_task_id = report_result.get("task_id")

        # Poll for report completion
        await _poll_report(client, simulation_id, report_id, report_task_id, emit)

        emit("report_complete", {"step": "report", "status": "complete", "report_id": report_id})

        # ── Step 7: Fetch Report ──
        resp = await client.get(f"/api/report/by-simulation/{simulation_id}")
        resp.raise_for_status()
        report_data = resp.json()

        # Extract report text from sections
        report_text = ""
        report_summary = ""
        if "sections" in report_data:
            for section in report_data["sections"]:
                report_text += section.get("content", "") + "\n\n"
            report_summary = report_text[:1000]
        elif "report" in report_data:
            report_obj = report_data["report"]
            report_text = report_obj.get("content", "") or report_obj.get("summary", "")
            report_summary = report_text[:1000]

        return {
            "project_id": project_id,
            "graph_id": graph_id,
            "simulation_id": simulation_id,
            "report_id": report_id,
            "report_text": report_text,
            "report_summary": report_summary,
        }


async def _poll_graph_build(client: httpx.AsyncClient, task_id: str, emit: Callable) -> str:
    """Poll graph build status until complete. Returns graph_id."""
    elapsed = 0
    interval = POLL_INTERVAL_BASE
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(interval)
        elapsed += interval

        resp = await client.post("/api/graph/build/status", json={"task_id": task_id})
        if resp.status_code != 200:
            continue
        data = resp.json()
        status = data.get("status", "")
        progress = data.get("progress", 0)

        emit("graph_progress", {"step": "graph", "status": "running", "progress": progress})

        if status in ("completed", "complete", "done"):
            return data.get("graph_id", "")
        if status in ("failed", "error"):
            raise RuntimeError(f"Graph build failed: {data}")

        interval = min(interval * 1.5, POLL_INTERVAL_MAX)

    raise TimeoutError("Graph build timed out")


async def _poll_prepare(client: httpx.AsyncClient, simulation_id: str, task_id: str, emit: Callable):
    """Poll simulation prepare status until complete."""
    elapsed = 0
    interval = POLL_INTERVAL_BASE
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(interval)
        elapsed += interval

        resp = await client.post("/api/simulation/prepare/status", json={
            "task_id": task_id,
            "simulation_id": simulation_id,
        })
        if resp.status_code != 200:
            continue
        data = resp.json()
        status = data.get("status", "")
        progress = data.get("progress", 0)

        emit("prepare_progress", {
            "step": "prepare", "status": "running",
            "progress": progress,
            "profiles_ready": data.get("profiles_ready", 0),
            "profiles_total": data.get("profiles_total", 0),
        })

        if status in ("completed", "complete", "done"):
            return
        if status in ("failed", "error"):
            raise RuntimeError(f"Simulation prepare failed: {data}")

        interval = min(interval * 1.5, POLL_INTERVAL_MAX)

    raise TimeoutError("Simulation prepare timed out")


async def _poll_simulation_run(client: httpx.AsyncClient, simulation_id: str, emit: Callable):
    """Poll simulation run status until complete."""
    elapsed = 0
    interval = POLL_INTERVAL_BASE
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(interval)
        elapsed += interval

        resp = await client.get(f"/api/simulation/{simulation_id}/run-status")
        if resp.status_code != 200:
            continue
        data = resp.json()
        runner_status = data.get("runner_status", "")
        current_round = data.get("current_round", 0)
        total_rounds = data.get("total_rounds", 0)

        emit("simulation_progress", {
            "step": "simulation", "status": "running",
            "round": current_round,
            "total_rounds": total_rounds,
            "actions_count": data.get("twitter_actions_count", 0),
        })

        if runner_status in ("completed", "complete", "done", "stopped"):
            return
        if runner_status in ("failed", "error"):
            raise RuntimeError(f"Simulation run failed: {data}")

        interval = min(interval * 1.2, POLL_INTERVAL_MAX)

    raise TimeoutError("Simulation run timed out")


async def _poll_report(client: httpx.AsyncClient, simulation_id: str, report_id: str, task_id: str, emit: Callable):
    """Poll report generation status until complete."""
    elapsed = 0
    interval = POLL_INTERVAL_BASE
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(interval)
        elapsed += interval

        resp = await client.post("/api/report/generate/status", json={
            "task_id": task_id,
            "simulation_id": simulation_id,
        })
        if resp.status_code != 200:
            continue
        data = resp.json()
        status = data.get("status", "")

        emit("report_progress", {
            "step": "report", "status": "running",
            "sections_done": data.get("sections_done", 0),
            "sections_total": data.get("sections_total", 0),
        })

        if status in ("completed", "complete", "done"):
            return
        if status in ("failed", "error"):
            raise RuntimeError(f"Report generation failed: {data}")

        interval = min(interval * 1.5, POLL_INTERVAL_MAX)

    raise TimeoutError("Report generation timed out")
