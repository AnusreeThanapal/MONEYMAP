"""
backend/app/ingest.py
File ingestion: extract, normalise, store. Also demo load with hash cache.
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import ollama

from app.database import get_db
from app.extraction import extract_from_file, ExtractionResult, ExtractedTransaction, CATEGORIES

MODEL      = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
CACHE_DIR  = Path(__file__).parent.parent / "extraction_cache"
DEMO_DIR   = Path(__file__).parent.parent.parent / "demo_data"

UPLOAD_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


# ── Merchant normalisation ────────────────────────────────────────────────────

MERCHANT_MAP = {
    "swiggy":        "Swiggy",
    "zomato":        "Zomato",
    "amazon":        "Amazon",
    "bigbasket":     "BigBasket",
    "big basket":    "BigBasket",
    "uber":          "Uber",
    "ola":           "Ola",
    "jio":           "Jio",
    "bsnl":          "BSNL",
    "netflix":       "Netflix",
    "hotstar":       "Hotstar",
    "myntra":        "Myntra",
    "flipkart":      "Flipkart",
    "phonepe":       "PhonePe",
    "paytm":         "Paytm",
    "zepto":         "Zepto",
    "pharmasy":      "PharmEasy",
    "pharmeasy":     "PharmEasy",
    "apollo":        "Apollo Pharmacy",
    "pvr":           "PVR Cinemas",
    "bookmyshow":    "BookMyShow",
    "makemytrip":    "MakeMyTrip",
    "lic":           "LIC",
    "sbi":           "SBI",
    "hdfc":          "HDFC",
    "icici":         "ICICI",
}


def normalise_merchant(name: str) -> str:
    key = name.lower().strip()
    for pattern, canonical in MERCHANT_MAP.items():
        if pattern in key:
            return canonical
    # Capitalise words
    return " ".join(w.capitalize() for w in name.strip().split())


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _load_cache(fhash: str) -> Optional[ExtractionResult]:
    cache_file = CACHE_DIR / f"{fhash}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        return ExtractionResult.model_validate(data)
    return None


def _save_cache(fhash: str, result: ExtractionResult):
    if result.accounts or result.transactions:
        cache_file = CACHE_DIR / f"{fhash}.json"
        cache_file.write_text(result.model_dump_json())


# ── Categorisation fallback via Gemma ────────────────────────────────────────

def _categorise_with_llm(merchants: list[str]) -> dict[str, str]:
    """Ask Gemma to categorise a batch of uncategorised merchants."""
    if not merchants:
        return {}
    cats_str = ", ".join(CATEGORIES)
    prompt = (
        f"Categorise each merchant into exactly one of: {cats_str}\n"
        f"Return a JSON object mapping merchant name to category.\n"
        f"Merchants: {json.dumps(merchants)}"
    )
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        text = resp["message"]["content"].strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        result = json.loads(text)
        return {k: (v if v in CATEGORIES else "Other") for k, v in result.items()}
    except Exception:
        return {m: "Other" for m in merchants}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_or_create_account(conn, name: str, atype: str, balance: float, source: str) -> int:
    row = conn.execute(
        "SELECT id FROM accounts WHERE name=? AND type=?", (name, atype)
    ).fetchone()
    if row:
        conn.execute("UPDATE accounts SET balance=?, source=? WHERE id=?",
                     (balance, source, row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO accounts(name, type, balance, source) VALUES(?,?,?,?)",
        (name, atype, balance, source)
    )
    return cur.lastrowid


def _txn_exists(conn, account_id: int, date: str, merchant: str,
                amount: float, source_file: str) -> bool:
    """True if the SAME transaction from a DIFFERENT file already exists."""
    row = conn.execute(
        """SELECT id FROM transactions
           WHERE account_id=? AND date=? AND merchant=? AND ABS(amount-?)< 0.01
             AND source_file != ?
        """,
        (account_id, date, merchant, amount, source_file)
    ).fetchone()
    return row is not None


# ── Main ingest function ──────────────────────────────────────────────────────

def ingest_file(file_path: Path, use_cache: bool = True) -> dict:
    """
    Extract, normalise and store one file.
    Returns summary dict.
    """
    fhash  = _file_hash(file_path)
    source = file_path.name

    # Try cache
    result: Optional[ExtractionResult] = None
    if use_cache:
        result = _load_cache(fhash)
        if result:
            print(f"[ingest] {source}: cache hit")

    if result is None:
        try:
            result = extract_from_file(file_path)
            _save_cache(fhash, result)
        except Exception as e:
            return {"file": source, "error": str(e), "transactions": 0}

    conn = get_db()
    inserted = 0
    skipped  = 0
    needs_review = 0

    try:
        # Derive account from extraction, fall back to filename
        account_name = source
        account_type = "bank"
        account_bal  = 0.0

        if result.accounts:
            a            = result.accounts[0]
            account_name = a.name
            account_type = a.type
            account_bal  = a.balance

        account_id = _get_or_create_account(conn, account_name, account_type, account_bal, source)

        # Collect merchants needing LLM categorisation
        uncategorised = []
        for t in result.transactions:
            if t.category == "Other":
                uncategorised.append(normalise_merchant(t.merchant))

        cat_map = _categorise_with_llm(list(set(uncategorised))) if uncategorised else {}

        for t in result.transactions:
            norm_merchant = normalise_merchant(t.merchant)
            # Skip exact cross-file duplicates
            if _txn_exists(conn, account_id, t.date, norm_merchant, t.amount, source):
                skipped += 1
                continue

            category = t.category
            if category == "Other" and norm_merchant in cat_map:
                category = cat_map[norm_merchant]

            review = 1 if t.confidence < 0.7 else 0
            conn.execute(
                """INSERT INTO transactions
                   (account_id, date, merchant, amount, direction, category, confidence, source_file, needs_review)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (account_id, t.date, norm_merchant, t.amount, t.direction,
                 category, t.confidence, source, review)
            )
            inserted    += 1
            needs_review += review

        conn.commit()
    finally:
        conn.close()

    return {
        "file":         source,
        "transactions": inserted,
        "skipped":      skipped,
        "needs_review": needs_review,
    }


def ingest_demo() -> list[dict]:
    """Ingest all demo data files, using cache for speed on repeated calls."""
    results = []
    for fname in ["bank_statement_1.png", "bank_statement_2.png",
                  "upi_screenshot.png", "credit_card_statement.pdf",
                  "loan_insurance.pdf"]:
        fpath = DEMO_DIR / fname
        if fpath.exists():
            summary = ingest_file(fpath, use_cache=True)
            results.append(summary)
        else:
            results.append({"file": fname, "error": "not found"})
    return results
