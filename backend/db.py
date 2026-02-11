"""SQLite watchlist database."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "watchlist.db")


DEFAULT_PAPER_CASH = 100_000.0


def init_db():
    """Create watchlist, portfolio, and trading tables if they don't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                company_name TEXT,
                added_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash_balance REAL NOT NULL DEFAULT 100000
            )
        """)
        conn.execute("INSERT OR IGNORE INTO account (id, cash_balance) VALUES (1, ?)", (DEFAULT_PAPER_CASH,))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                quantity REAL NOT NULL,
                avg_cost REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                created_at TEXT NOT NULL
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


# --- Portfolio (paper trading) ---

def get_cash_balance():
    """Return current paper cash balance."""
    with _conn() as conn:
        row = conn.execute("SELECT cash_balance FROM account WHERE id = 1").fetchone()
        return float(row["cash_balance"]) if row else DEFAULT_PAPER_CASH


def set_cash_balance(amount):
    """Set paper cash balance. Returns new balance."""
    with _conn() as conn:
        conn.execute("UPDATE account SET cash_balance = ? WHERE id = 1", (float(amount),))
        conn.commit()
        row = conn.execute("SELECT cash_balance FROM account WHERE id = 1").fetchone()
        return float(row["cash_balance"])


def get_positions():
    """Return list of {id, symbol, quantity, avg_cost, updated_at}."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, quantity, avg_cost, updated_at FROM portfolio ORDER BY symbol"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_position(symbol):
    """Get single position by symbol. Returns dict or None."""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, symbol, quantity, avg_cost, updated_at FROM portfolio WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        return _row_to_dict(row)


def execute_buy(symbol, quantity, price):
    """
    Execute a buy: deduct cash, add/update position, record order.
    Returns (True, positions, cash_balance) or (False, error_message, None).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol or quantity <= 0:
        return False, "Invalid symbol or quantity", None
    price = float(price)
    total = quantity * price
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        cash_row = conn.execute("SELECT cash_balance FROM account WHERE id = 1").fetchone()
        cash = float(cash_row["cash_balance"]) if cash_row else DEFAULT_PAPER_CASH
        if cash < total:
            return False, "Insufficient cash", None
        conn.execute("UPDATE account SET cash_balance = cash_balance - ? WHERE id = 1", (total,))
        row = conn.execute("SELECT id, symbol, quantity, avg_cost, updated_at FROM portfolio WHERE symbol = ?", (symbol,)).fetchone()
        if row:
            current_qty = float(row["quantity"])
            new_qty = current_qty + quantity
            new_avg = (current_qty * float(row["avg_cost"]) + quantity * price) / new_qty
            conn.execute(
                "UPDATE portfolio SET quantity = ?, avg_cost = ?, updated_at = ? WHERE symbol = ?",
                (new_qty, new_avg, now, symbol),
            )
        else:
            conn.execute(
                "INSERT INTO portfolio (symbol, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?)",
                (symbol, quantity, price, now),
            )
        conn.execute(
            "INSERT INTO orders (symbol, side, quantity, price, total, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (symbol, "buy", quantity, price, total, now),
        )
        conn.commit()
    return True, get_positions(), get_cash_balance()


def execute_sell(symbol, quantity, price):
    """
    Execute a sell: add cash, reduce/remove position, record order.
    Returns (True, positions, cash_balance) or (False, error_message, None).
    """
    symbol = (symbol or "").strip().upper()
    if not symbol or quantity <= 0:
        return False, "Invalid symbol or quantity", None
    price = float(price)
    total = quantity * price
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        row = conn.execute("SELECT id, symbol, quantity, avg_cost, updated_at FROM portfolio WHERE symbol = ?", (symbol,)).fetchone()
        if not row:
            return False, "No position to sell", None
        current_qty = float(row["quantity"])
        if quantity > current_qty + 0.0001:
            return False, "Insufficient shares to sell", None
        conn.execute("UPDATE account SET cash_balance = cash_balance + ? WHERE id = 1", (total,))
        new_qty = current_qty - quantity
        if new_qty <= 0.0001:
            conn.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
        else:
            conn.execute(
                "UPDATE portfolio SET quantity = ?, updated_at = ? WHERE symbol = ?",
                (new_qty, now, symbol),
            )
        conn.execute(
            "INSERT INTO orders (symbol, side, quantity, price, total, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (symbol, "sell", quantity, price, total, now),
        )
        conn.commit()
    return True, get_positions(), get_cash_balance()


def get_orders(limit=50):
    """Return recent orders (newest first)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, side, quantity, price, total, created_at FROM orders ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def reset_paper_account():
    """Reset cash to default, clear all positions and orders. Returns new cash balance."""
    with _conn() as conn:
        conn.execute("UPDATE account SET cash_balance = ? WHERE id = 1", (DEFAULT_PAPER_CASH,))
        conn.execute("DELETE FROM portfolio")
        conn.execute("DELETE FROM orders")
        conn.commit()
    return get_cash_balance()


def adjust_cash(amount, action="deposit"):
    """
    Deposit or withdraw paper cash. action is 'deposit' or 'withdraw'.
    Returns (True, new_balance) or (False, error_message).
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Invalid amount"
    if amount <= 0:
        return False, "Amount must be positive"
    with _conn() as conn:
        row = conn.execute("SELECT cash_balance FROM account WHERE id = 1").fetchone()
        cash = float(row["cash_balance"]) if row else DEFAULT_PAPER_CASH
        if action == "withdraw":
            if amount > cash:
                return False, "Insufficient cash to withdraw"
            new_cash = cash - amount
        else:
            new_cash = cash + amount
        conn.execute("UPDATE account SET cash_balance = ? WHERE id = 1", (new_cash,))
        conn.commit()
    return True, get_cash_balance()
