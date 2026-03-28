"""Logging hooks for the OpenAI Agents SDK — logs every tool call, handoff, and agent turn."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from agents import RunHooks, RunContextWrapper, Agent, Tool

# Set up file + console logging
LOG_DIR = Path(__file__).parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger("neurotrading")
logger.setLevel(logging.DEBUG)

# File handler — detailed
fh = logging.FileHandler(log_file)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh)

# Console handler — concise
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(ch)


class AgentLogger(RunHooks):
    """Logs agent lifecycle events for debugging and analysis."""

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        logger.info(f"Agent started: {agent.name}")

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output) -> None:
        out_str = str(output)[:200] if output else "(no output)"
        logger.info(f"Agent ended: {agent.name} — output: {out_str}")
        logger.debug(f"Agent {agent.name} full output: {output}")

    async def on_handoff(self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent) -> None:
        logger.info(f"Handoff: {from_agent.name} → {to_agent.name}")

    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        logger.info(f"Tool call: {agent.name} → {tool.name}")

    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        result_str = str(result)[:300] if result else "(no result)"
        logger.info(f"Tool result: {tool.name} — {result_str}")
        logger.debug(f"Tool {tool.name} full result: {result}")


def get_logger():
    return logger, log_file
