"""
scripts/test_extraction.py
Run extraction on all demo files, print results, compare to ground_truth.json.
"""
import json
import sys
from pathlib import Path

# Make sure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extraction import extract_from_file

DEMO = Path(__file__).parent.parent.parent / "demo_data"
GT   = DEMO / "ground_truth.json"

FILES = [
    "bank_statement_1.png",
    "bank_statement_2.png",
    "upi_screenshot.png",
    "credit_card_statement.pdf",
    "loan_insurance.pdf",
]


def main():
    gt = json.loads(GT.read_text())

    total_txns   = 0
    total_accts  = 0
    all_results  = {}

    for fname in FILES:
        fpath = DEMO / fname
        print(f"\n{'='*60}")
        print(f"FILE: {fname}")
        print("="*60)
        result = extract_from_file(fpath)
        all_results[fname] = result

        print(f"  Accounts ({len(result.accounts)}):")
        for a in result.accounts:
            print(f"    [{a.type}] {a.name} -> Rs {a.balance:,.0f}")

        print(f"  Transactions ({len(result.transactions)}):")
        for t in result.transactions:
            flag = " ⚠️ review" if t.confidence < 0.7 else ""
            print(f"    {t.date} | {t.merchant[:30]:<30} | {'Rs':>4} {t.amount:>10,.0f} | {t.direction:<6} | {t.category}{flag}")

        total_txns  += len(result.transactions)
        total_accts += len(result.accounts)

    print(f"\n{'='*60}")
    print("ACCURACY CHECK vs ground_truth.json")
    print("="*60)
    print(f"  Total transactions extracted : {total_txns}")
    print(f"  Ground truth (approx)        : {gt['total_transactions_approx']}")

    # Check anomalies detected in raw data
    all_txns = []
    for r in all_results.values():
        all_txns.extend(r.transactions)

    print(f"\nSeeded anomaly coverage:")
    for anomaly in gt["anomalies"]:
        merchant = anomaly["merchant"].split("(")[0].strip()
        amount   = anomaly["amount"]
        found    = [t for t in all_txns if merchant.lower() in t.merchant.lower()
                    and abs(t.amount - amount) < 1]
        print(f"  [{anomaly['type']}] {merchant} Rs {amount} -> found {len(found)} match(es)")

    print(f"\nExtraction accuracy: {total_txns}/{gt['total_transactions_approx']} transactions")
    pct = total_txns / max(gt['total_transactions_approx'], 1) * 100
    print(f"  = {pct:.0f}% of expected count")


if __name__ == "__main__":
    main()
