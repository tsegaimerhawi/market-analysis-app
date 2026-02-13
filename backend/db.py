"""SQLite watchlist database."""
import json
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
        try:
            conn.execute(f"ALTER TABLE account ADD COLUMN initial_balance REAL DEFAULT {DEFAULT_PAPER_CASH}")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("UPDATE account SET initial_balance = ? WHERE id = 1 AND initial_balance IS NULL", (DEFAULT_PAPER_CASH,))
            conn.commit()
        except sqlite3.OperationalError:
            pass
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS limit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                limit_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_reasoning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                step TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                position_size REAL NOT NULL,
                reason TEXT NOT NULL,
                executed INTEGER NOT NULL DEFAULT 0,
                order_id INTEGER,
                guardrail_triggered INTEGER NOT NULL DEFAULT 0
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


def get_initial_balance():
    """Return the initial/starting balance used for performance calculation (set on reset)."""
    with _conn() as conn:
        row = conn.execute("SELECT initial_balance FROM account WHERE id = 1").fetchone()
        if row and row["initial_balance"] is not None:
            return float(row["initial_balance"])
        return DEFAULT_PAPER_CASH


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
        conn.execute("UPDATE account SET cash_balance = ?, initial_balance = ? WHERE id = 1", (DEFAULT_PAPER_CASH, DEFAULT_PAPER_CASH))
        conn.execute("DELETE FROM portfolio")
        conn.execute("DELETE FROM orders")
        conn.commit()
    return get_cash_balance()


def add_limit_order(symbol, side, quantity, limit_price):
    """Add a limit order. Returns (order dict) or (None, error)."""
    symbol = (symbol or "").strip().upper()
    if not symbol or side not in ("buy", "sell") or quantity <= 0 or limit_price <= 0:
        return None, "Invalid limit order"
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO limit_orders (symbol, side, quantity, limit_price, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
            (symbol, side, quantity, float(limit_price), now),
        )
        lid = cur.lastrowid
        conn.commit()
        row = conn.execute(
            "SELECT id, symbol, side, quantity, limit_price, status, created_at FROM limit_orders WHERE id = ?",
            (lid,),
        ).fetchone()
        return _row_to_dict(row), None


def get_limit_orders(limit=50):
    """Return limit orders, pending first then by id desc."""
    with _conn() as conn:
        rows = conn.execute(
            """SELECT id, symbol, side, quantity, limit_price, status, created_at
               FROM limit_orders ORDER BY status = 'pending' DESC, id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_pending_limit_orders():
    """Return only pending limit orders."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, symbol, side, quantity, limit_price, status, created_at FROM limit_orders WHERE status = 'pending' ORDER BY id",
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def mark_limit_order_filled(order_id):
    """Set limit order status to 'filled'."""
    with _conn() as conn:
        conn.execute("UPDATE limit_orders SET status = 'filled' WHERE id = ?", (order_id,))
        conn.commit()


def cancel_limit_order(order_id):
    """Cancel a pending limit order. Returns True if cancelled."""
    with _conn() as conn:
        cur = conn.execute("UPDATE limit_orders SET status = 'cancelled' WHERE id = ? AND status = 'pending'", (order_id,))
        conn.commit()
        return cur.rowcount > 0


# --- Trading agent ---

def get_agent_enabled():
    """Return True if the auto-trading agent is enabled."""
    with _conn() as conn:
        row = conn.execute("SELECT value FROM agent_settings WHERE key = 'enabled'").fetchone()
        return (row and row["value"] == "1")


def set_agent_enabled(enabled):
    """Set agent on/off."""
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO agent_settings (key, value) VALUES ('enabled', ?)", ("1" if enabled else "0",))
        conn.commit()


def get_agent_include_volatile():
    """Return True if agent should also trade volatile stocks (not in watchlist)."""
    with _conn() as conn:
        row = conn.execute("SELECT value FROM agent_settings WHERE key = 'include_volatile'").fetchone()
        return (row and row["value"] == "1")


def set_agent_include_volatile(include):
    """Set whether to include volatile stocks in agent cycle."""
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO agent_settings (key, value) VALUES ('include_volatile', ?)", ("1" if include else "0",))
        conn.commit()


def get_agent_stop_loss_pct():
    """Return stop-loss percentage (e.g. 5 = sell if position down 5%). None if disabled."""
    with _conn() as conn:
        row = conn.execute("SELECT value FROM agent_settings WHERE key = 'stop_loss_pct'").fetchone()
        if not row or row["value"] is None or row["value"] == "":
            return None
        try:
            return float(row["value"])
        except (TypeError, ValueError):
            return None


def set_agent_stop_loss_pct(pct):
    """Set stop-loss percentage. None or 0 to disable."""
    val = str(pct) if pct is not None and float(pct) > 0 else ""
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO agent_settings (key, value) VALUES ('stop_loss_pct', ?)", (val,))
        conn.commit()


def get_agent_take_profit_pct():
    """Return take-profit percentage (e.g. 10 = sell if position up 10%). None if disabled."""
    with _conn() as conn:
        row = conn.execute("SELECT value FROM agent_settings WHERE key = 'take_profit_pct'").fetchone()
        if not row or row["value"] is None or row["value"] == "":
            return None
        try:
            return float(row["value"])
        except (TypeError, ValueError):
            return None


def set_agent_take_profit_pct(pct):
    """Set take-profit percentage. None or 0 to disable."""
    val = str(pct) if pct is not None and float(pct) > 0 else ""
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO agent_settings (key, value) VALUES ('take_profit_pct', ?)", (val,))
        conn.commit()


def add_agent_reasoning(symbol, step, message, data=None):
    """Append a reasoning step for the UI."""
    with _conn() as conn:
        conn.execute(
            "INSERT INTO agent_reasoning (created_at, symbol, step, message, data) VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), symbol, step, message, json.dumps(data) if data is not None else None),
        )
        conn.commit()


def get_agent_reasoning(limit=100, symbol=None):
    """Get recent reasoning steps, optionally filtered by symbol."""
    with _conn() as conn:
        if symbol:
            rows = conn.execute(
                "SELECT id, created_at, symbol, step, message, data FROM agent_reasoning WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol.strip().upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, created_at, symbol, step, message, data FROM agent_reasoning ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            row = _row_to_dict(r)
            if row.get("data"):
                try:
                    row["data"] = json.loads(row["data"])
                except Exception:
                    pass
            out.append(row)
        return out


def add_agent_history(symbol, action, position_size, reason, executed=False, order_id=None, guardrail_triggered=False):
    """Log an agent decision/trade to history."""
    with _conn() as conn:
        conn.execute(
            """INSERT INTO agent_history (created_at, symbol, action, position_size, reason, executed, order_id, guardrail_triggered)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), symbol, action, float(position_size), reason, 1 if executed else 0, order_id, 1 if guardrail_triggered else 0),
        )
        conn.commit()


def get_agent_history(limit=50):
    """Get recent agent history entries."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, symbol, action, position_size, reason, executed, order_id, guardrail_triggered FROM agent_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def set_last_agent_history_executed(symbol, order_id):
    """Mark the most recent agent_history row for this symbol as executed with order_id."""
    with _conn() as conn:
        conn.execute(
            "UPDATE agent_history SET executed = 1, order_id = ? WHERE id = (SELECT id FROM agent_history WHERE symbol = ? ORDER BY id DESC LIMIT 1)",
            (order_id, symbol.strip().upper()),
        )
        conn.commit()


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
