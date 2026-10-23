"""
backend/tests/test_analytics.py
Unit tests for analytics with a small fixture database.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import analytics, database


@pytest.fixture(autouse=True)
def test_db(tmp_path, monkeypatch):
    """Create an isolated test database for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", db_path)
    # Also patch analytics so it uses the monkeypatched DB_PATH
    import importlib
    import app.analytics as ana
    monkeypatch.setattr(ana, "get_db", database.get_db)
    database.init_db()

    # Seed fixture data
    conn = database.get_db()
    conn.executescript("""
        INSERT INTO accounts(name, type, balance, source) VALUES
          ('HDFC Savings', 'bank',        350000, 'test'),
          ('ICICI Savings', 'bank',       100000, 'test'),
          ('PhonePe',       'wallet',      10000, 'test'),
          ('HDFC CC',       'card',       -28000, 'test'),
          ('SBI Home Loan', 'loan',      -185000, 'test');

        INSERT INTO transactions(account_id, date, merchant, amount, direction, category, confidence, source_file, needs_review) VALUES
          (1, '2025-01-02', 'Salary Credit',  85000, 'credit', 'Salary',    1.0, 'test.png', 0),
          (1, '2025-01-03', 'Rent Payment',   22000, 'debit',  'Rent',      1.0, 'test.png', 0),
          (1, '2025-01-07', 'BigBasket',       3240, 'debit',  'Groceries', 1.0, 'test.png', 0),
          (1, '2025-01-08', 'Swiggy',           645, 'debit',  'Food',      1.0, 'test.png', 0),
          (1, '2025-01-12', 'Amazon',          2499, 'debit',  'Shopping',  1.0, 'test.png', 0),
          (1, '2025-01-25', 'SBI EMI',        18500, 'debit',  'EMI',       1.0, 'test.png', 0),
          (2, '2025-02-03', 'Salary Credit',  85000, 'credit', 'Salary',    1.0, 'test2.png',0),
          (2, '2025-02-04', 'Rent Payment',   22000, 'debit',  'Rent',      1.0, 'test2.png',0),
          (2, '2025-02-09', 'BigBasket',       4100, 'debit',  'Groceries', 1.0, 'test2.png',0),
          (2, '2025-02-22', 'Amazon',         34999, 'debit',  'Shopping',  1.0, 'test2.png',0),
          (2, '2025-02-25', 'SBI EMI',        18500, 'debit',  'EMI',       1.0, 'test2.png',0),
          (2, '2025-02-14', 'Zomato',           847, 'debit',  'Food',      1.0, 'test2.png',0),
          (2, '2025-02-14', 'Zomato',           847, 'debit',  'Food',      1.0, 'test2.png',0);
    """)
    conn.commit()
    conn.close()
    yield


def test_net_worth():
    result = analytics.net_worth()
    # assets = 350000 + 100000 + 10000 = 460000
    # liabilities = 28000 + 185000 = 213000
    # net worth = 247000
    assert result["net_worth"] == pytest.approx(247000, rel=0.01)
    assert result["assets"]    == pytest.approx(460000, rel=0.01)
    assert result["liabilities"] == pytest.approx(213000, rel=0.01)
    assert "₹" in result["formatted"]


def test_total_balance():
    result = analytics.total_balance()
    # bank + wallet = 350000 + 100000 + 10000 = 460000
    assert result["total_balance"] == pytest.approx(460000, rel=0.01)


def test_spending_by_category_all():
    # Use a fixed cutoff that covers our 2025 fixture data
    from unittest.mock import patch
    from datetime import date
    with patch('app.analytics.date') as mock_date:
        mock_date.today.return_value = date(2025, 3, 31)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = analytics.spending_by_category("last_90_days")
    cats = result["categories"]
    assert "Rent"      in cats
    assert "Groceries" in cats
    assert "Food"      in cats
    assert cats["Rent"] == pytest.approx(44000, rel=0.01)  # 22000 * 2


def test_monthly_trend():
    trend = analytics.monthly_trend()
    assert len(trend) >= 1
    jan = next((m for m in trend if m["month"] == "2025-01"), None)
    if jan:
        assert jan["income"] == pytest.approx(85000, rel=0.01)


def test_savings_rate():
    from unittest.mock import patch
    from datetime import date
    with patch('app.analytics.date') as mock_date:
        mock_date.today.return_value = date(2025, 3, 31)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = analytics.savings_rate()
    assert result["income"]   > 0, f"Income was 0: {result}"
    assert result["spending"] > 0
    assert 0 < result["rate_percent"] < 100


def test_inr_formatting():
    from app.analytics import _fmt_inr
    assert _fmt_inr(245000) == "₹2,45,000.00"
    assert _fmt_inr(1000)   == "₹1,000.00"
    assert _fmt_inr(500)    == "₹500.00"
