"""SQLite watchlist database."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "watchlist.db")


def init_db():
    """Create watchlist table if it doesn't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                company_name TEXT,
                added_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def add_to_watchlist(symbol, company_name=None):
    """Add a company by symbol. Returns (id, symbol, company_name, added_at) or None if duplicate."""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    with _conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO watchlist (symbol, company_name, added_at) VALUES (?, ?, ?)",
                (symbol, company_name or symbol, datetime.utcnow().isoformat()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, symbol, company_name, added_at FROM watchlist WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return _row_to_dict(row)
        except sqlite3.IntegrityError:
            return None


def remove_from_watchlist(symbol_or_id):
    """Remove by symbol (e.g. 'AAPL') or by id (integer). Returns True if deleted."""
    with _conn() as conn:
        if isinstance(symbol_or_id, int) or (isinstance(symbol_or_id, str) and symbol_or_id.isdigit()):
            cur = conn.execute("DELETE FROM watchlist WHERE id = ?", (int(symbol_or_id),))
        else:
            cur = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (str(symbol_or_id).strip().upper(),))
        conn.commit()
        return cur.rowcount > 0


def get_watchlist():
    """Return list of {id, symbol, company_name, added_at}."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, company_name, added_at FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def _row_to_dict(row):
    if row is None:
        return None
    return dict(zip(row.keys(), row))
