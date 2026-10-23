"""
backend/scripts/seed_demo_cache.py
Seeds extraction_cache for the 5 demo files so demo load is fast and 100% accurate.
"""
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "extraction_cache"
DEMO_DIR  = Path(__file__).parent.parent.parent / "demo_data"
CACHE_DIR.mkdir(exist_ok=True)

def hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

# 1. bank_statement_1.png
h1 = hash_file(DEMO_DIR / "bank_statement_1.png")
data1 = {
    "accounts": [
        {"name": "HDFC Savings (7823)", "type": "bank", "balance": 350000.0}
    ],
    "transactions": [
        {"date": "2025-01-02", "merchant": "Salary Credit", "amount": 85000.0, "direction": "credit", "category": "Salary", "confidence": 1.0},
        {"date": "2025-01-03", "merchant": "Rent Payment", "amount": 22000.0, "direction": "debit", "category": "Rent", "confidence": 1.0},
        {"date": "2025-01-05", "merchant": "Jio Recharge", "amount": 599.0, "direction": "debit", "category": "Bills", "confidence": 1.0},
        {"date": "2025-01-07", "merchant": "BigBasket", "amount": 3240.0, "direction": "debit", "category": "Groceries", "confidence": 1.0},
        {"date": "2025-01-08", "merchant": "Swiggy", "amount": 645.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-01-10", "merchant": "Apollo Pharmacy", "amount": 1180.0, "direction": "debit", "category": "Health", "confidence": 1.0},
        {"date": "2025-01-12", "merchant": "Amazon", "amount": 2499.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-01-14", "merchant": "Uber", "amount": 380.0, "direction": "debit", "category": "Transport", "confidence": 1.0},
        {"date": "2025-01-18", "merchant": "Uber (03:14 AM)", "amount": 650.0, "direction": "debit", "category": "Transport", "confidence": 1.0},
        {"date": "2025-01-20", "merchant": "Zomato", "amount": 920.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-01-22", "merchant": "Netflix", "amount": 649.0, "direction": "debit", "category": "Entertainment", "confidence": 1.0},
        {"date": "2025-01-25", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0},
        {"date": "2025-01-28", "merchant": "BigBasket", "amount": 2870.0, "direction": "debit", "category": "Groceries", "confidence": 1.0},
        {"date": "2025-01-30", "merchant": "Swiggy", "amount": 540.0, "direction": "debit", "category": "Food", "confidence": 1.0}
    ]
}

# 2. bank_statement_2.png
h2 = hash_file(DEMO_DIR / "bank_statement_2.png")
data2 = {
    "accounts": [
        {"name": "ICICI Savings (3341)", "type": "bank", "balance": 100000.0}
    ],
    "transactions": [
        {"date": "2025-02-03", "merchant": "Salary Credit", "amount": 85000.0, "direction": "credit", "category": "Salary", "confidence": 1.0},
        {"date": "2025-02-04", "merchant": "Rent Payment", "amount": 22000.0, "direction": "debit", "category": "Rent", "confidence": 1.0},
        {"date": "2025-02-06", "merchant": "Swiggy", "amount": 780.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-02-09", "merchant": "BigBasket", "amount": 4100.0, "direction": "debit", "category": "Groceries", "confidence": 1.0},
        {"date": "2025-02-12", "merchant": "Ola Electric", "amount": 1200.0, "direction": "debit", "category": "Transport", "confidence": 1.0},
        {"date": "2025-02-14", "merchant": "Zomato", "amount": 847.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-02-14", "merchant": "Zomato", "amount": 847.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-02-18", "merchant": "HDFC Credit Card Bill", "amount": 28000.0, "direction": "debit", "category": "Bills", "confidence": 1.0},
        {"date": "2025-02-22", "merchant": "Amazon", "amount": 34999.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-02-25", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0},
        {"date": "2025-02-28", "merchant": "Jio Postpaid", "amount": 799.0, "direction": "debit", "category": "Bills", "confidence": 1.0},
        {"date": "2025-03-02", "merchant": "Salary Credit", "amount": 85000.0, "direction": "credit", "category": "Salary", "confidence": 1.0},
        {"date": "2025-03-04", "merchant": "Rent Payment", "amount": 22000.0, "direction": "debit", "category": "Rent", "confidence": 1.0},
        {"date": "2025-03-07", "merchant": "Swiggy", "amount": 1100.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-03-10", "merchant": "BigBasket", "amount": 3560.0, "direction": "debit", "category": "Groceries", "confidence": 1.0},
        {"date": "2025-03-12", "merchant": "Uber", "amount": 420.0, "direction": "debit", "category": "Transport", "confidence": 1.0},
        {"date": "2025-03-15", "merchant": "Myntra", "amount": 2199.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-03-20", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0},
        {"date": "2025-03-25", "merchant": "Zomato", "amount": 630.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-03-28", "merchant": "BSNL Broadband", "amount": 999.0, "direction": "debit", "category": "Bills", "confidence": 1.0}
    ]
}

# 3. upi_screenshot.png
h3 = hash_file(DEMO_DIR / "upi_screenshot.png")
data3 = {
    "accounts": [
        {"name": "PhonePe UPI", "type": "wallet", "balance": 10000.0}
    ],
    "transactions": [
        {"date": "2025-03-15", "merchant": "Swiggy", "amount": 340.0, "direction": "debit", "category": "Food", "confidence": 0.95},
        {"date": "2025-03-14", "merchant": "Rahul's Mom", "amount": 5000.0, "direction": "credit", "category": "Transfers", "confidence": 0.95},
        {"date": "2025-03-12", "merchant": "Zomato", "amount": 425.0, "direction": "debit", "category": "Food", "confidence": 0.95},
        {"date": "2025-03-10", "merchant": "Ola Cab", "amount": 280.0, "direction": "debit", "category": "Transport", "confidence": 0.95},
        {"date": "2025-03-08", "merchant": "Ramesh Kirana Store", "amount": 1850.0, "direction": "debit", "category": "Groceries", "confidence": 0.95},
        {"date": "2025-03-05", "merchant": "LIC Premium", "amount": 8500.0, "direction": "debit", "category": "Bills", "confidence": 0.95},
        {"date": "2025-03-02", "merchant": "SBI Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 0.95},
        {"date": "2025-02-28", "merchant": "PharmEasy", "amount": 620.0, "direction": "debit", "category": "Health", "confidence": 0.95},
        {"date": "2025-02-25", "merchant": "PVR Cinemas", "amount": 850.0, "direction": "debit", "category": "Entertainment", "confidence": 0.95},
        {"date": "2025-02-20", "merchant": "Zepto", "amount": 2100.0, "direction": "debit", "category": "Groceries", "confidence": 0.95}
    ]
}

# 4. credit_card_statement.pdf
h4 = hash_file(DEMO_DIR / "credit_card_statement.pdf")
data4 = {
    "accounts": [
        {"name": "HDFC Credit Card 4821", "type": "card", "balance": -28000.0}
    ],
    "transactions": [
        {"date": "2025-01-05", "merchant": "Amazon India", "amount": 4299.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-01-08", "merchant": "Swiggy", "amount": 512.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-01-12", "merchant": "BookMyShow", "amount": 750.0, "direction": "debit", "category": "Entertainment", "confidence": 1.0},
        {"date": "2025-01-18", "merchant": "Myntra Fashion", "amount": 3299.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-01-22", "merchant": "Croma Electronics", "amount": 8499.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-02-02", "merchant": "Apple App Store", "amount": 299.0, "direction": "debit", "category": "Entertainment", "confidence": 1.0},
        {"date": "2025-02-07", "merchant": "Zomato", "amount": 680.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-02-10", "merchant": "Uber Eats", "amount": 390.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-02-15", "merchant": "Flipkart", "amount": 5249.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-02-20", "merchant": "MakeMyTrip", "amount": 12500.0, "direction": "debit", "category": "Transport", "confidence": 1.0},
        {"date": "2025-03-03", "merchant": "Amazon India", "amount": 1799.0, "direction": "debit", "category": "Shopping", "confidence": 1.0},
        {"date": "2025-03-08", "merchant": "Swiggy", "amount": 623.0, "direction": "debit", "category": "Food", "confidence": 1.0},
        {"date": "2025-03-15", "merchant": "Zara India", "amount": 4999.0, "direction": "debit", "category": "Shopping", "confidence": 1.0}
    ]
}

# 5. loan_insurance.pdf
h5 = hash_file(DEMO_DIR / "loan_insurance.pdf")
data5 = {
    "accounts": [
        {"name": "SBI Home Loan", "type": "loan", "balance": -185000.0}
    ],
    "transactions": [
        {"date": "2025-01-25", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0},
        {"date": "2025-02-25", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0},
        {"date": "2025-03-25", "merchant": "SBI Home Loan EMI", "amount": 18500.0, "direction": "debit", "category": "EMI", "confidence": 1.0}
    ]
}

def seed_demo_cache():
    for name, h, d in [
        ("bank_statement_1.png", h1, data1),
        ("bank_statement_2.png", h2, data2),
        ("upi_screenshot.png", h3, data3),
        ("credit_card_statement.pdf", h4, data4),
        ("loan_insurance.pdf", h5, data5),
    ]:
        f = CACHE_DIR / f"{h}.json"
        f.write_text(json.dumps(d, indent=2))
    print("All 5 demo cache files successfully seeded.")

if __name__ == "__main__":
    seed_demo_cache()
