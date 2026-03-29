"""SQLite persistence for the opportunity pipeline and event log."""

import json
import sqlite3
from datetime import datetime

from config import PIPELINE_DB_PATH, DATA_DIR
from api_models import Opportunity, Event


class PipelineDB:
    def __init__(self, db_path=PIPELINE_DB_PATH):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        self._migrate_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'discovered',
                    market_id TEXT NOT NULL,
                    market_question TEXT NOT NULL,
                    market_description TEXT,
                    outcomes TEXT,
                    outcome_prices TEXT,
                    token_ids TEXT,
                    volume REAL,
                    liquidity REAL,
                    end_date TEXT,
                    tags TEXT,
                    agent_hypothesis TEXT,
                    probability_estimate REAL,
                    market_price REAL,
                    estimated_edge REAL,
                    simulation_rationale TEXT,
                    simulation_potential INTEGER,
                    simulation_category TEXT,
                    seed_document TEXT,
                    simulation_requirement TEXT,
                    mirofish_project_id TEXT,
                    mirofish_simulation_id TEXT,
                    mirofish_report_id TEXT,
                    simulation_report_summary TEXT,
                    simulation_sentiment TEXT,
                    trade_side TEXT,
                    trade_outcome TEXT,
                    trade_token_id TEXT,
                    trade_amount_usd REAL,
                    trade_reasoning TEXT,
                    trade_fill_price REAL,
                    trade_fill_shares REAL,
                    web_research_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id TEXT,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT NOT NULL
                )
            """)

    def _migrate_db(self):
        with self._conn() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(opportunities)").fetchall()}
            if "simulation_category" not in columns:
                conn.execute("ALTER TABLE opportunities ADD COLUMN simulation_category TEXT")
            if "ensemble_agreement" not in columns:
                conn.execute("ALTER TABLE opportunities ADD COLUMN ensemble_agreement REAL")

    # --- Opportunities ---

    def create_opportunity(self, opp: Opportunity) -> Opportunity:
        now = datetime.now().isoformat()
        opp.created_at = now
        opp.updated_at = now
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO opportunities (
                    id, status, market_id, market_question, market_description,
                    outcomes, outcome_prices, token_ids, volume, liquidity,
                    end_date, tags, agent_hypothesis, probability_estimate,
                    market_price, estimated_edge, simulation_rationale,
                    simulation_potential, simulation_category,
                    web_research_summary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp.id, opp.status, opp.market_id, opp.market_question,
                    opp.market_description,
                    json.dumps(opp.outcomes) if opp.outcomes else None,
                    json.dumps(opp.outcome_prices) if opp.outcome_prices else None,
                    json.dumps(opp.token_ids) if opp.token_ids else None,
                    opp.volume, opp.liquidity, opp.end_date,
                    json.dumps(opp.tags) if opp.tags else None,
                    opp.agent_hypothesis, opp.probability_estimate,
                    opp.market_price, opp.estimated_edge,
                    opp.simulation_rationale, opp.simulation_potential,
                    opp.simulation_category,
                    opp.web_research_summary, now, now,
                ),
            )
        return opp

    def get_opportunity(self, opp_id: str) -> Opportunity | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM opportunities WHERE id = ?", (opp_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_opportunity(row)

    def list_opportunities(self, status: str | None = None) -> list[Opportunity]:
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    """SELECT * FROM opportunities WHERE status = ?
                       ORDER BY
                         CASE WHEN simulation_category IS NOT NULL THEN 0 ELSE 1 END,
                         simulation_potential DESC NULLS LAST,
                         volume DESC NULLS LAST,
                         created_at DESC""",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM opportunities
                       ORDER BY
                         CASE WHEN status = 'discovered' THEN 0 ELSE 1 END,
                         CASE WHEN simulation_category IS NOT NULL THEN 0 ELSE 1 END,
                         simulation_potential DESC NULLS LAST,
                         volume DESC NULLS LAST,
                         created_at DESC"""
                ).fetchall()
            return [self._row_to_opportunity(r) for r in rows]

    def update_opportunity(self, opp_id: str, **kwargs) -> Opportunity | None:
        if not kwargs:
            return self.get_opportunity(opp_id)
        kwargs["updated_at"] = datetime.now().isoformat()
        # JSON-encode list/dict fields
        for key in ("outcomes", "outcome_prices", "token_ids", "tags", "simulation_sentiment"):
            if key in kwargs and kwargs[key] is not None and not isinstance(kwargs[key], str):
                kwargs[key] = json.dumps(kwargs[key])
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [opp_id]
        with self._conn() as conn:
            conn.execute(
                f"UPDATE opportunities SET {set_clause} WHERE id = ?", values
            )
        return self.get_opportunity(opp_id)

    def _row_to_opportunity(self, row: sqlite3.Row) -> Opportunity:
        d = dict(row)
        # Parse JSON fields
        for key in ("outcomes", "outcome_prices", "token_ids", "tags"):
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        if d.get("simulation_sentiment") and isinstance(d["simulation_sentiment"], str):
            try:
                d["simulation_sentiment"] = json.loads(d["simulation_sentiment"])
            except (json.JSONDecodeError, TypeError):
                pass
        return Opportunity(**d)

    def deduplicate_opportunities(self) -> int:
        """Remove duplicate opportunities keeping the most advanced one per market question."""
        status_priority = {
            'trade_executed': 7, 'trade_approved': 6, 'trade_proposed': 5,
            'simulation_complete': 4, 'simulation_running': 3, 'simulation_approved': 2,
            'simulation_proposed': 1, 'discovered': 0, 'rejected': -1, 'failed': -2,
        }
        opps = self.list_opportunities()
        by_question = {}
        for opp in opps:
            q = opp.market_question.strip().lower()
            if q not in by_question:
                by_question[q] = []
            by_question[q].append(opp)

        removed = 0
        with self._conn() as conn:
            for q, dupes in by_question.items():
                if len(dupes) <= 1:
                    continue
                dupes.sort(key=lambda o: (status_priority.get(o.status, -10), o.updated_at or ''), reverse=True)
                for opp in dupes[1:]:
                    conn.execute("DELETE FROM opportunities WHERE id = ?", (opp.id,))
                    removed += 1
        return removed

    # --- Events ---

    def add_event(self, event_type: str, opportunity_id: str | None = None, payload: dict | None = None) -> Event:
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                "INSERT INTO events (opportunity_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (opportunity_id, event_type, json.dumps(payload) if payload else None, now),
            )
            return Event(
                id=cursor.lastrowid,
                opportunity_id=opportunity_id,
                event_type=event_type,
                payload=payload,
                created_at=now,
            )

    def get_events(self, since_id: int = 0, opportunity_id: str | None = None, limit: int = 100) -> list[Event]:
        with self._conn() as conn:
            if opportunity_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE id > ? AND opportunity_id = ? ORDER BY id ASC LIMIT ?",
                    (since_id, opportunity_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
                    (since_id, limit),
                ).fetchall()
            events = []
            for r in rows:
                d = dict(r)
                if d.get("payload") and isinstance(d["payload"], str):
                    try:
                        d["payload"] = json.loads(d["payload"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                events.append(Event(**d))
            return events
