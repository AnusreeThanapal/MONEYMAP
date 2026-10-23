"""
backend/tests/test_anomalies.py
Tests for all anomaly detection rules with seeded data.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import database
from app.anomalies import detect_duplicates, detect_large_transactions, detect_night_transactions


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", db_path)
    import app.anomalies as anm
    monkeypatch.setattr(anm, "get_db", database.get_db)
    database.init_db()

    conn = database.get_db()
    # Insert accounts
    conn.execute("INSERT INTO accounts(name, type, balance, source) VALUES ('Test Bank','bank',100000,'test')")
    # Regular food transactions
    txns = [
        (1, '2025-01-05', 'Swiggy',          500,   'debit', 'Food',     1.0, 'a.png', 0),
        (1, '2025-01-08', 'Zomato',           600,   'debit', 'Food',     1.0, 'a.png', 0),
        (1, '2025-01-10', 'Swiggy',           450,   'debit', 'Food',     1.0, 'a.png', 0),
        (1, '2025-01-12', 'Zomato',           700,   'debit', 'Food',     1.0, 'a.png', 0),
        # Anomaly 1: duplicate charge
        (1, '2025-02-14', 'Zomato',           847,   'debit', 'Food',     1.0, 'b.png', 0),
        (1, '2025-02-14', 'Zomato',           847,   'debit', 'Food',     1.0, 'b.png', 0),
        # Anomaly 2: large transaction in Shopping
        (1, '2025-01-05', 'Amazon',          2000,   'debit', 'Shopping', 1.0, 'a.png', 0),
        (1, '2025-01-10', 'Flipkart',        1800,   'debit', 'Shopping', 1.0, 'a.png', 0),
        (1, '2025-01-15', 'Myntra',          2200,   'debit', 'Shopping', 1.0, 'a.png', 0),
        (1, '2025-02-22', 'Amazon',         35000,   'debit', 'Shopping', 1.0, 'b.png', 0),
        # Anomaly 3: night transaction
        (1, '2025-01-18', 'Uber (03:14 AM)',  650,   'debit', 'Transport',1.0, 'a.png', 0),
    ]
    conn.executemany(
        "INSERT INTO transactions(account_id,date,merchant,amount,direction,category,confidence,source_file,needs_review) VALUES(?,?,?,?,?,?,?,?,?)",
        txns
    )
    conn.commit()
    conn.close()
    yield


def _get_txns():
    conn = database.get_db()
    rows = conn.execute(
        """SELECT t.*, a.name as account FROM transactions t
           JOIN accounts a ON t.account_id=a.id"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_detect_duplicates():
    txns   = _get_txns()
    result = detect_duplicates(txns)
    assert len(result) >= 1
    assert any(a["reason_code"] == "DUPLICATE_CHARGE" for a in result)
    dup = next(a for a in result if a["reason_code"] == "DUPLICATE_CHARGE")
    assert dup["transaction"]["merchant"] == "Zomato"
    assert dup["transaction"]["amount"]   == pytest.approx(847)


def test_detect_large_transactions():
    txns   = _get_txns()
    result = detect_large_transactions(txns)
    assert len(result) >= 1
    large  = next((a for a in result if a["reason_code"] == "LARGE_TRANSACTION"), None)
    assert large is not None
    assert large["transaction"]["amount"] >= 30000


def test_detect_night_transactions():
    txns   = _get_txns()
    result = detect_night_transactions(txns)
    assert len(result) >= 1
    night  = result[0]
    assert night["reason_code"] == "NIGHT_TRANSACTION"
    assert "Uber" in night["transaction"]["merchant"]


def test_all_three_seeded_anomalies_caught():
    """All 3 demo anomalies must be detected."""
    from app.anomalies import detect_all
    # Add the anomalous txns to a fresh context
    all_anm = detect_all()
    codes   = [a["reason_code"] for a in all_anm]
    assert "DUPLICATE_CHARGE"   in codes, "Duplicate not found"
    assert "LARGE_TRANSACTION"  in codes, "Large txn not found"
    assert "NIGHT_TRANSACTION"  in codes, "Night txn not found"
