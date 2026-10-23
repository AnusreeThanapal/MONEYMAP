"""
backend/app/analytics.py
Pure-Python analytics — no LLM, reads SQLite directly.
"""
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from app.database import get_db


def _fmt_inr(amount: float) -> str:
    """Indian number format: 2,45,000.00"""
    s = f"{abs(amount):.2f}"
    integer, decimal = s.split(".")
    n = len(integer)
    if n <= 3:
        result = integer
    else:
        result = integer[-3:]
        integer = integer[:-3]
        while integer:
            result = integer[-2:] + "," + result
            integer = integer[:-2]
    sign = "-" if amount < 0 else ""
    return f"{sign}₹{result}.{decimal}"


def net_worth() -> dict:
    """Sum of all asset balances minus liability balances."""
    conn = get_db()
    rows = conn.execute("SELECT type, SUM(balance) FROM accounts GROUP BY type").fetchall()
    conn.close()

    assets      = 0.0
    liabilities = 0.0
    by_type     = {}
    for row in rows:
        t, bal = row["type"], row["SUM(balance)"] or 0.0
        by_type[t] = bal
        if t in ("loan", "card"):
            liabilities += abs(bal)
        else:
            assets += bal

    nw = assets - liabilities
    return {
        "net_worth":    nw,
        "assets":       assets,
        "liabilities":  liabilities,
        "by_type":      by_type,
        "formatted":    _fmt_inr(nw),
    }


def total_balance() -> dict:
    """Total balance across bank + wallet accounts only."""
    conn = get_db()
    row = conn.execute(
        "SELECT SUM(balance) FROM accounts WHERE type IN ('bank','wallet')"
    ).fetchone()
    conn.close()
    bal = row[0] or 0.0
    return {"total_balance": bal, "formatted": _fmt_inr(bal)}


def spending_by_category(period: str = "last_30_days") -> dict:
    """Debits grouped by category for the given period."""
    conn    = get_db()
    cutoff  = _period_cutoff(period)
    rows    = conn.execute(
        """SELECT category, SUM(amount) as total
           FROM transactions
           WHERE direction='debit' AND date >= ?
           GROUP BY category
           ORDER BY total DESC""",
        (cutoff,)
    ).fetchall()
    conn.close()
    categories = {r["category"]: r["total"] for r in rows}
    total = sum(categories.values())
    return {
        "period":     period,
        "categories": categories,
        "total":      total,
        "formatted":  _fmt_inr(total),
    }


def monthly_trend() -> list[dict]:
    """Monthly income vs spending for the last 6 months."""
    conn = get_db()
    rows = conn.execute(
        """SELECT strftime('%Y-%m', date) as month,
                  SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) as income,
                  SUM(CASE WHEN direction='debit'  THEN amount ELSE 0 END) as spending
           FROM transactions
           GROUP BY month
           ORDER BY month DESC
           LIMIT 6"""
    ).fetchall()
    conn.close()
    return [
        {
            "month":    r["month"],
            "income":   r["income"] or 0.0,
            "spending": r["spending"] or 0.0,
            "savings":  (r["income"] or 0.0) - (r["spending"] or 0.0),
        }
        for r in reversed(rows)
    ]


def savings_rate() -> dict:
    """Average savings rate over the last 3 months."""
    conn   = get_db()
    cutoff = _period_cutoff("last_90_days")
    row    = conn.execute(
        """SELECT
               SUM(CASE WHEN direction='credit' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN direction='debit'  THEN amount ELSE 0 END) as spending
           FROM transactions WHERE date >= ?""",
        (cutoff,)
    ).fetchone()
    conn.close()

    income   = row["income"]   or 0.0
    spending = row["spending"] or 0.0
    savings  = income - spending
    rate     = (savings / income * 100) if income > 0 else 0.0
    return {
        "income":        income,
        "spending":      spending,
        "savings":       savings,
        "rate_percent":  round(rate, 1),
    }


def liabilities_summary() -> dict:
    """Cards and loans with outstanding balances."""
    conn = get_db()
    rows = conn.execute(
        "SELECT name, type, balance FROM accounts WHERE type IN ('loan','card') ORDER BY balance"
    ).fetchall()
    conn.close()
    items = [{"name": r["name"], "type": r["type"], "balance": r["balance"]} for r in rows]
    total = sum(abs(r["balance"]) for r in rows)
    return {"liabilities": items, "total": total, "formatted": _fmt_inr(total)}


def _get_reference_date() -> date:
    try:
        conn = get_db()
        row = conn.execute("SELECT MAX(date) FROM transactions").fetchone()
        conn.close()
        if row and row[0]:
            latest_txn = date.fromisoformat(row[0][:10])
            if (date.today() - latest_txn).days > 60:
                return latest_txn
    except Exception:
        pass
    return date.today()


def _period_cutoff(period: str) -> str:
    ref = _get_reference_date()
    if period == "last_30_days":
        return (ref - timedelta(days=30)).isoformat()
    if period == "last_90_days":
        return (ref - timedelta(days=90)).isoformat()
    if period == "this_month":
        return ref.replace(day=1).isoformat()
    return "2000-01-01"


def get_summary() -> dict:
    """Everything the dashboard needs in one call."""
    return {
        "net_worth":           net_worth(),
        "total_balance":       total_balance(),
        "spending_by_category": spending_by_category("last_90_days"),
        "monthly_trend":       monthly_trend(),
        "savings_rate":        savings_rate(),
        "liabilities":         liabilities_summary(),
    }
