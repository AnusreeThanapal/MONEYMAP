"""
MoneyMap database initialisation.
Creates SQLite DB with all tables on startup.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "moneymap.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            type        TEXT    NOT NULL CHECK(type IN ('bank','wallet','card','loan','investment','insurance')),
            balance     REAL    NOT NULL DEFAULT 0,
            source      TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id   INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
            date         TEXT    NOT NULL,
            merchant     TEXT    NOT NULL,
            amount       REAL    NOT NULL CHECK(amount >= 0),
            direction    TEXT    NOT NULL CHECK(direction IN ('debit','credit')),
            category     TEXT    NOT NULL DEFAULT 'Other',
            confidence   REAL    NOT NULL DEFAULT 1.0,
            source_file  TEXT,
            needs_review INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_txn_date       ON transactions(date);
        CREATE INDEX IF NOT EXISTS idx_txn_account    ON transactions(account_id);
        CREATE INDEX IF NOT EXISTS idx_txn_category   ON transactions(category);

        CREATE TABLE IF NOT EXISTS goals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            target_amount REAL    NOT NULL,
            months        INTEGER NOT NULL,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS anomaly_explanations (
            key  TEXT PRIMARY KEY,
            text TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def reset_db():
    conn = get_db()
    conn.executescript("""
        DELETE FROM transactions;
        DELETE FROM accounts;
        DELETE FROM goals;
        DELETE FROM anomaly_explanations;
    """)
    conn.commit()
    conn.close()
