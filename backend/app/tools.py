"""
backend/app/tools.py
Typed Python financial tool functions with matching Ollama tool schemas.
LLM selects these; Python executes. No arithmetic by the LLM.
"""
from datetime import date, timedelta
from typing import Optional

from app.database import get_db
from app.analytics import (
    spending_by_category as _spending,
    net_worth as _net_worth,
    savings_rate as _savings_rate,
    monthly_trend as _monthly_trend,
    _period_cutoff,
)


# ── Tool implementations ──────────────────────────────────────────────────────

def get_spending(category: Optional[str] = None,
                 period: str = "last_30_days") -> dict:
    """
    Get total spending, optionally filtered by category.
    period: last_30_days | last_90_days | this_month
    """
    conn   = get_db()
    cutoff = _period_cutoff(period)
    if category:
        row = conn.execute(
            """SELECT SUM(amount) as total, COUNT(*) as count
               FROM transactions
               WHERE direction='debit' AND date>=? AND LOWER(category)=LOWER(?)""",
            (cutoff, category)
        ).fetchone()
        total = row["total"] or 0.0
        count = row["count"] or 0
        conn.close()
        return {
            "category": category,
            "period":   period,
            "total":    total,
            "count":    count,
            "formatted": f"₹{_fmt(total)}",
        }
    else:
        result = _spending(period)
        conn.close()
        return result


def get_net_worth() -> dict:
    """Get current net worth: total assets minus total liabilities."""
    return _net_worth()


def get_savings_rate() -> dict:
    """Get savings rate (income minus spending / income) over last 90 days."""
    return _savings_rate()


def project_goal(target_amount: float, months: int) -> dict:
    """
    Project whether a savings goal is feasible.
    Returns required monthly saving, current average monthly surplus, and feasibility.
    """
    sr = _savings_rate()
    mt = _monthly_trend()

    # Average monthly surplus from actual data
    if mt:
        avg_surplus = sum(m["savings"] for m in mt) / len(mt)
    else:
        avg_surplus = sr["savings"] / 3 if sr["income"] else 0

    required_monthly = target_amount / max(months, 1)
    shortfall        = required_monthly - avg_surplus
    feasible         = avg_surplus >= required_monthly

    return {
        "target_amount":      target_amount,
        "months":             months,
        "required_monthly":   required_monthly,
        "avg_monthly_surplus": avg_surplus,
        "shortfall":          max(shortfall, 0),
        "surplus_over_need":  max(-shortfall, 0),
        "feasible":           feasible,
        "formatted_required": f"₹{_fmt(required_monthly)}",
        "formatted_surplus":  f"₹{_fmt(avg_surplus)}",
    }


def what_if(category: str, reduction_percent: float) -> dict:
    """
    What if I reduce spending in a category by X%?
    Returns monthly and yearly savings from that change.
    """
    result      = get_spending(category, "last_30_days")
    monthly_now = result["total"]
    monthly_new = monthly_now * (1 - reduction_percent / 100)
    monthly_saved = monthly_now - monthly_new
    yearly_saved  = monthly_saved * 12
    return {
        "category":           category,
        "reduction_percent":  reduction_percent,
        "current_monthly":    monthly_now,
        "new_monthly":        monthly_new,
        "monthly_savings":    monthly_saved,
        "yearly_savings":     yearly_saved,
        "formatted_monthly":  f"₹{_fmt(monthly_saved)}",
        "formatted_yearly":   f"₹{_fmt(yearly_saved)}",
    }


def detect_anomalies() -> dict:
    """Detect suspicious transactions: duplicates, large amounts, night transactions."""
    from app.anomalies import detect_all
    anomalies = detect_all()
    return {
        "count":     len(anomalies),
        "anomalies": [
            {
                "id":       a["id"],
                "merchant": a["transaction"]["merchant"],
                "amount":   a["transaction"]["amount"],
                "date":     a["transaction"]["date"],
                "reason":   a["reason_code"],
                "severity": a["severity"],
            }
            for a in anomalies
        ],
    }


def _fmt(v: float) -> str:
    s = f"{abs(v):.2f}"
    integer, decimal = s.split(".")
    if len(integer) <= 3:
        return f"{integer}.{decimal}"
    result  = integer[-3:]
    integer = integer[:-3]
    while integer:
        result  = integer[-2:] + "," + result
        integer = integer[:-2]
    return f"{result}.{decimal}"


# ── Tool schemas for ollama ───────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_spending",
            "description": (
                "Get total spending amount. Use this for ANY question about "
                "how much was spent on food, groceries, shopping, transport, etc. "
                "Always call this tool — never estimate spending yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category name: Food, Groceries, Transport, Shopping, Bills, Rent, Entertainment, Health, EMI, Salary, Transfers, Other. Omit for all categories.",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["last_30_days", "last_90_days", "this_month"],
                        "description": "Time period. Default last_30_days.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_net_worth",
            "description": (
                "Get the current net worth (assets minus liabilities). "
                "Use for any question about net worth, total wealth, or overall financial position."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_savings_rate",
            "description": (
                "Get the savings rate as a percentage of income. "
                "Use for questions about savings, how much is being saved, or savings percentage."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "project_goal",
            "description": (
                "Check if a financial goal is achievable. Use for questions like "
                "'Can I afford X in Y months?' or 'Is it feasible to save for Z?'. "
                "Always call this tool — never calculate feasibility yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target_amount": {
                        "type": "number",
                        "description": "Goal amount in INR rupees (e.g. 300000 for ₹3,00,000)",
                    },
                    "months": {
                        "type": "integer",
                        "description": "Number of months to reach the goal",
                    },
                },
                "required": ["target_amount", "months"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "what_if",
            "description": (
                "Calculate savings if spending in a category is reduced by a percentage. "
                "Use for 'what if I cut X by Y%' questions. Never calculate this yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Spending category (Food, Shopping, Transport, etc.)",
                    },
                    "reduction_percent": {
                        "type": "number",
                        "description": "Percentage reduction (e.g. 30 for 30%)",
                    },
                },
                "required": ["category", "reduction_percent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": (
                "Detect suspicious or unusual transactions: duplicates, large amounts, "
                "night-time transactions. Use for questions about anything suspicious, "
                "unusual or anomalous in spending."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_FUNCTIONS = {
    "get_spending":      get_spending,
    "get_net_worth":     get_net_worth,
    "get_savings_rate":  get_savings_rate,
    "project_goal":      project_goal,
    "what_if":           what_if,
    "detect_anomalies":  detect_anomalies,
}
