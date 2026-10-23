"""
backend/app/anomalies.py
Pure-Python anomaly detection. No LLM for detection math.
Gemma is used only to generate human-readable explanations (cached).
"""
import json
import math
import os
import re
from typing import Optional

import ollama

from app.database import get_db

MODEL = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")

NIGHT_START = 1   # 1 AM
NIGHT_END   = 5   # 5 AM


# ── Detection ─────────────────────────────────────────────────────────────────

def _all_transactions() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT t.id, t.date, t.merchant, t.amount, t.direction, t.category,
                  t.source_file, t.confidence, a.name as account
           FROM transactions t
           JOIN accounts a ON t.account_id = a.id
           ORDER BY t.date"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def detect_duplicates(txns: list[dict]) -> list[dict]:
    """Exact duplicates: same merchant, amount, date (any direction)."""
    seen   = {}
    result = []
    for t in txns:
        key = (t["date"], t["merchant"].lower(), round(t["amount"], 2))
        if key in seen:
            result.append({
                "id":          t["id"],
                "transaction": t,
                "reason_code": "DUPLICATE_CHARGE",
                "severity":    "high",
                "detail":      f"Duplicate of transaction #{seen[key]}",
            })
        else:
            seen[key] = t["id"]
    return result


def detect_large_transactions(txns: list[dict]) -> list[dict]:
    """Amounts more than 2 std dev above mean within category, debits only.
    Also catches any single debit > 10x the category median."""
    by_cat: dict[str, list[float]] = {}
    for t in txns:
        if t["direction"] == "debit":
            by_cat.setdefault(t["category"], []).append(t["amount"])

    result = []
    for t in txns:
        if t["direction"] != "debit":
            continue
        cat    = t["category"]
        vals   = by_cat.get(cat, [])
        if len(vals) < 3:
            continue
        mean = sum(vals) / len(vals)
        std  = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
        # Use median for 10x check (more robust than mean for skewed data)
        sorted_vals = sorted(vals)
        median = sorted_vals[len(sorted_vals) // 2]
        is_stat_outlier   = std > 0 and t["amount"] > mean + 2 * std
        is_10x_median     = median > 0 and t["amount"] > 10 * median
        if is_stat_outlier or is_10x_median:
            result.append({
                "id":          t["id"],
                "transaction": t,
                "reason_code": "LARGE_TRANSACTION",
                "severity":    "medium",
                "detail":      f"₹{t['amount']:,.0f} vs median ₹{median:,.0f} in {cat}",
            })
    return result


def detect_night_transactions(txns: list[dict]) -> list[dict]:
    """Transactions with time in merchant name or date between 1 AM–5 AM."""
    result = []
    for t in txns:
        merchant = t["merchant"]
        # Look for time pattern like "03:14 AM" in merchant name
        m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?", merchant)
        if m:
            hour = int(m.group(1))
            ampm = (m.group(3) or "").upper()
            if ampm == "PM" and hour != 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
            if NIGHT_START <= hour < NIGHT_END:
                result.append({
                    "id":          t["id"],
                    "transaction": t,
                    "reason_code": "NIGHT_TRANSACTION",
                    "severity":    "low",
                    "detail":      f"Transaction at {m.group(0)} — unusual hour",
                })
    return result


def detect_large_first_time(txns: list[dict]) -> list[dict]:
    """Large transaction from a merchant never seen before (first-time ≥ ₹5000)."""
    seen_merchants: set[str] = set()
    result = []
    for t in sorted(txns, key=lambda x: x["date"]):
        key = t["merchant"].lower()
        if key not in seen_merchants:
            if t["direction"] == "debit" and t["amount"] >= 5000:
                result.append({
                    "id":          t["id"],
                    "transaction": t,
                    "reason_code": "LARGE_FIRST_MERCHANT",
                    "severity":    "low",
                    "detail":      f"First transaction with {t['merchant']}: ₹{t['amount']:,.0f}",
                })
            seen_merchants.add(key)
    return result


def detect_all() -> list[dict]:
    """Run all detectors and return deduplicated anomalies."""
    txns     = _all_transactions()
    all_anm  = (
        detect_duplicates(txns)
        + detect_large_transactions(txns)
        + detect_night_transactions(txns)
    )
    # Deduplicate by transaction ID
    seen = set()
    deduped = []
    for a in all_anm:
        tid = a["id"]
        if tid not in seen:
            seen.add(tid)
            deduped.append(a)
    return deduped


# ── LLM explanation ───────────────────────────────────────────────────────────

def _get_cached_explanation(key: str) -> Optional[str]:
    conn = get_db()
    row  = conn.execute(
        "SELECT text FROM anomaly_explanations WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return row["text"] if row else None


def _cache_explanation(key: str, text: str):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO anomaly_explanations(key, text) VALUES(?,?)", (key, text)
    )
    conn.commit()
    conn.close()


def explain_anomaly(anomaly: dict) -> str:
    """Get or generate a plain-language explanation for an anomaly."""
    t      = anomaly["transaction"]
    key    = f"{anomaly['reason_code']}:{t['id']}"
    cached = _get_cached_explanation(key)
    if cached:
        return cached

    facts = (
        f"Transaction: {t['merchant']} on {t['date']}, amount ₹{t['amount']:,.0f}, "
        f"category {t['category']}, reason: {anomaly['reason_code']}. "
        f"Detail: {anomaly['detail']}"
    )
    prompt = (
        f"Explain this financial anomaly in 1-2 plain sentences for a non-expert user. "
        f"Use only these facts: {facts}. "
        f"Do NOT add advice. Do NOT calculate. Just explain what was found."
    )
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 100},
        )
        text = resp["message"]["content"].strip()
    except Exception as e:
        text = anomaly["detail"]

    _cache_explanation(key, text)
    return text


def get_anomalies_with_explanations() -> list[dict]:
    """Detect all anomalies and attach LLM-generated explanations."""
    anomalies = detect_all()
    result    = []
    for a in anomalies:
        explanation = explain_anomaly(a)
        result.append({**a, "explanation": explanation})
    return result
