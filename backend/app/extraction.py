"""
backend/app/extraction.py
Gemma 4 vision extraction: images and PDFs -> structured account/transaction data.
"""
import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Optional

import ollama
from pydantic import BaseModel, field_validator, model_validator

MODEL = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")
CATEGORIES = [
    "Food", "Groceries", "Transport", "Shopping", "Bills",
    "Rent", "Entertainment", "Health", "EMI", "Salary", "Transfers", "Other"
]


# ── Pydantic models ──────────────────────────────────────────────────────────

class ExtractedTransaction(BaseModel):
    date: str                 # YYYY-MM-DD
    merchant: str
    amount: float             # always positive
    direction: str            # debit | credit
    category: str = "Other"
    confidence: float = 0.8   # 0-1

    @field_validator("direction")
    @classmethod
    def normalise_direction(cls, v):
        v = v.lower().strip()
        if v in ("dr", "debit", "paid", "out", "withdraw", "deducted"):
            return "debit"
        if v in ("cr", "credit", "received", "in", "deposit"):
            return "credit"
        return v

    @field_validator("category")
    @classmethod
    def normalise_category(cls, v):
        if v in CATEGORIES:
            return v
        return "Other"

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v):
        return abs(float(v))

    @field_validator("date")
    @classmethod
    def normalise_date(cls, v):
        v = str(v).strip()
        # Already ISO
        if re.match(r"^\d{4}-\d{2}-\d{2}", v):
            return v[:10]
        # DD-MM-YYYY or DD/MM/YYYY
        m = re.match(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", v)
        if m:
            d, mo, y = m.groups()
            return f"{y}-{int(mo):02d}-{int(d):02d}"
        # DD Mon YYYY
        months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
                  "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
        m2 = re.match(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", v)
        if m2:
            d, mo, y = m2.groups()
            mo_num = months.get(mo.lower()[:3], 1)
            return f"{y}-{mo_num:02d}-{int(d):02d}"
        return v


class ExtractedAccount(BaseModel):
    name: str
    type: str   # bank|wallet|card|loan|investment|insurance
    balance: float

    @field_validator("type")
    @classmethod
    def normalise_type(cls, v):
        v = v.lower().strip()
        mapping = {
            "savings": "bank", "current": "bank", "checking": "bank",
            "credit card": "card", "credit_card": "card",
            "upi": "wallet", "prepaid": "wallet",
            "home loan": "loan", "personal loan": "loan",
            "mutual fund": "investment", "fd": "investment", "stocks": "investment",
            "life insurance": "insurance", "health insurance": "insurance",
        }
        return mapping.get(v, v if v in ("bank","wallet","card","loan","investment","insurance") else "bank")


class ExtractionResult(BaseModel):
    accounts: list[ExtractedAccount] = []
    transactions: list[ExtractedTransaction] = []


# ── Prompt ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a financial data extraction specialist. 
Extract ALL accounts and ALL transactions from the financial document image.

Rules:
- date: YYYY-MM-DD format only
- amount: positive number (no currency symbols, no commas)
- direction: exactly "debit" or "credit"  
- category: must be one of: Food, Groceries, Transport, Shopping, Bills, Rent, Entertainment, Health, EMI, Salary, Transfers, Other
- confidence: 0.0-1.0 (how clearly visible the data is)
- Extract EVERY row, even duplicates — duplicates are important anomaly signals
- For UPI "paid to" = debit, "received from" = credit
- For bank statements: Dr = debit, Cr = credit
- Merchant names like "Uber (03:14 AM)" — keep the full text including time

Return ONLY valid JSON matching the schema. No explanation text."""

SCHEMA = {
    "type": "object",
    "properties": {
        "accounts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":    {"type": "string"},
                    "type":    {"type": "string", "enum": ["bank","wallet","card","loan","investment","insurance"]},
                    "balance": {"type": "number"}
                },
                "required": ["name","type","balance"]
            }
        },
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date":       {"type": "string"},
                    "merchant":   {"type": "string"},
                    "amount":     {"type": "number"},
                    "direction":  {"type": "string", "enum": ["debit","credit"]},
                    "category":   {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "required": ["date","merchant","amount","direction"]
            }
        }
    },
    "required": ["accounts","transactions"]
}


# ── Core extraction ───────────────────────────────────────────────────────────

def _image_to_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _pdf_to_images(path: Path) -> list[bytes]:
    """Convert PDF pages to PNG bytes using PyMuPDF."""
    import fitz  # PyMuPDF
    doc = fitz.open(str(path))
    images = []
    for page in doc:
        mat = fitz.Matrix(2.0, 2.0)   # 2x zoom for clarity
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    return images


def _call_gemma(image_bytes: bytes, attempt: int = 0, prev_error: str = "") -> dict:
    """Send one image to Gemma, return parsed JSON dict."""
    user_prompt = (
        "Extract all accounts and transactions from this financial document.\n"
        + (f"Previous attempt failed: {prev_error}\nFix and try again.\n" if prev_error else "")
        + "Return ONLY JSON with 'accounts' and 'transactions' arrays."
    )

    resp = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt, "images": [image_bytes]},
        ],
        format=SCHEMA,
        options={"temperature": 0, "num_predict": 4096},
    )

    text = resp["message"]["content"].strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _extract_from_image_bytes(image_bytes: bytes, source: str) -> ExtractionResult:
    """Extract from a single image with up to 2 retries on validation error."""
    last_error = ""
    for attempt in range(3):
        try:
            raw = _call_gemma(image_bytes, attempt, last_error)
            result = ExtractionResult.model_validate(raw)
            # Mark low-confidence transactions for review
            for t in result.transactions:
                if t.confidence < 0.7:
                    t.confidence = t.confidence  # will be handled at insert time
            return result
        except Exception as e:
            last_error = str(e)[:200]
            print(f"  [extraction] attempt {attempt+1} failed for {source}: {last_error[:80]}")
    
    print(f"  [extraction] all retries exhausted for {source}, returning empty")
    return ExtractionResult()


def extract_from_file(path: str | Path) -> ExtractionResult:
    """
    Main entry point. Accepts image or PDF.
    Returns merged ExtractionResult across all pages.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    print(f"[extraction] Processing {path.name} ...")

    all_accounts: list[ExtractedAccount] = []
    all_transactions: list[ExtractedTransaction] = []

    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        with open(path, "rb") as f:
            img_bytes = f.read()
        result = _extract_from_image_bytes(img_bytes, path.name)
        all_accounts.extend(result.accounts)
        all_transactions.extend(result.transactions)

    elif suffix == ".pdf":
        page_images = _pdf_to_images(path)
        for i, img_bytes in enumerate(page_images):
            result = _extract_from_image_bytes(img_bytes, f"{path.name}:p{i+1}")
            all_accounts.extend(result.accounts)
            all_transactions.extend(result.transactions)

    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    print(f"[extraction] {path.name}: {len(all_accounts)} accounts, {len(all_transactions)} transactions")
    return ExtractionResult(accounts=all_accounts, transactions=all_transactions)
