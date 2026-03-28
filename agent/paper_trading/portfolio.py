import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import DB_PATH, DATA_DIR, STARTING_BALANCE
from .models import Position, Trade, PortfolioSnapshot


class Portfolio:
    def __init__(self, db_path: Path = DB_PATH):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    balance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    token_id TEXT PRIMARY KEY,
                    market_question TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    shares REAL NOT NULL,
                    avg_cost REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id TEXT NOT NULL,
                    market_question TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    side TEXT NOT NULL,
                    shares REAL NOT NULL,
                    price REAL NOT NULL,
                    amount_usd REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            # Insert initial balance if not exists
            row = conn.execute("SELECT balance FROM portfolio WHERE id = 1").fetchone()
            if row is None:
                now = datetime.now().isoformat()
                conn.execute(
                    "INSERT INTO portfolio (id, balance, created_at, updated_at) VALUES (1, ?, ?, ?)",
                    (STARTING_BALANCE, now, now),
                )

    def get_balance(self) -> float:
        with self._conn() as conn:
            row = conn.execute("SELECT balance FROM portfolio WHERE id = 1").fetchone()
            return row["balance"]

    def get_positions(self) -> list[Position]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM positions WHERE shares > 0").fetchall()
            return [Position(**dict(r)) for r in rows]

    def get_position(self, token_id: str) -> Position | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM positions WHERE token_id = ?", (token_id,)).fetchone()
            if row and row["shares"] > 0:
                return Position(**dict(row))
            return None

    def record_buy(
        self, token_id: str, market_question: str, outcome: str, shares: float, avg_price: float, total_cost: float
    ):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            # Update balance
            conn.execute(
                "UPDATE portfolio SET balance = balance - ?, updated_at = ? WHERE id = 1",
                (total_cost, now),
            )
            # Update or insert position
            existing = conn.execute("SELECT * FROM positions WHERE token_id = ?", (token_id,)).fetchone()
            if existing:
                old_shares = existing["shares"]
                old_cost = existing["avg_cost"]
                new_shares = old_shares + shares
                new_avg = (old_shares * old_cost + shares * avg_price) / new_shares
                conn.execute(
                    "UPDATE positions SET shares = ?, avg_cost = ? WHERE token_id = ?",
                    (new_shares, new_avg, token_id),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (token_id, market_question, outcome, shares, avg_cost, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (token_id, market_question, outcome, shares, avg_price, now),
                )
            # Record trade
            conn.execute(
                "INSERT INTO trades (token_id, market_question, outcome, side, shares, price, amount_usd, created_at) VALUES (?, ?, ?, 'buy', ?, ?, ?, ?)",
                (token_id, market_question, outcome, shares, avg_price, total_cost, now),
            )

    def record_sell(self, token_id: str, shares: float, avg_price: float, proceeds: float):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            existing = conn.execute("SELECT * FROM positions WHERE token_id = ?", (token_id,)).fetchone()
            if not existing or existing["shares"] < shares:
                raise ValueError(f"Insufficient shares to sell: have {existing['shares'] if existing else 0}, want {shares}")

            new_shares = existing["shares"] - shares
            conn.execute(
                "UPDATE positions SET shares = ? WHERE token_id = ?",
                (new_shares, token_id),
            )
            conn.execute(
                "UPDATE portfolio SET balance = balance + ?, updated_at = ? WHERE id = 1",
                (proceeds, now),
            )
            conn.execute(
                "INSERT INTO trades (token_id, market_question, outcome, side, shares, price, amount_usd, created_at) VALUES (?, ?, ?, 'sell', ?, ?, ?, ?)",
                (token_id, existing["market_question"], existing["outcome"], shares, avg_price, proceeds, now),
            )

    def get_trade_history(self, limit: int = 20) -> list[Trade]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [Trade(**dict(r)) for r in rows]

    def get_pnl_summary(self) -> dict:
        with self._conn() as conn:
            balance = conn.execute("SELECT balance FROM portfolio WHERE id = 1").fetchone()["balance"]
            positions = self.get_positions()
            trades = conn.execute("SELECT * FROM trades").fetchall()

            total_trades = len(trades)
            sells = [t for t in trades if t["side"] == "sell"]
            winning_sells = [t for t in sells if t["price"] > 0]  # simplified

            return {
                "cash_balance": balance,
                "num_positions": len(positions),
                "total_trades": total_trades,
                "total_sells": len(sells),
                "starting_balance": STARTING_BALANCE,
                "cash_pnl": balance - STARTING_BALANCE,
            }

    def reset(self, starting_balance: float = STARTING_BALANCE):
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM trades")
            conn.execute("DELETE FROM positions")
            conn.execute(
                "UPDATE portfolio SET balance = ?, updated_at = ? WHERE id = 1",
                (starting_balance, now),
            )
