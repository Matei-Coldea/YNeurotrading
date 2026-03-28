"""Trade journal — persists analysis and reasoning to a JSON file so the agent has memory across runs."""

import json
from datetime import datetime
from pathlib import Path

from config import DATA_DIR

JOURNAL_PATH = DATA_DIR / "trade_journal.json"


def _load() -> list[dict]:
    if JOURNAL_PATH.exists():
        return json.loads(JOURNAL_PATH.read_text())
    return []


def _save(entries: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOURNAL_PATH.write_text(json.dumps(entries, indent=2, default=str))


def add_entry(entry: dict):
    entries = _load()
    entry["timestamp"] = datetime.now().isoformat()
    entries.append(entry)
    _save(entries)


def get_entries(limit: int = 20) -> list[dict]:
    entries = _load()
    return entries[-limit:]
