"""
Raw SQLite database layer — no ORM dependency.
Upgrade path: swap with SQLAlchemy when deploying to Postgres.
"""
import sqlite3
import os
from flask import g, current_app

# ─── Connection ───────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
        g.db.execute('PRAGMA journal_mode = WAL')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ─── Schema ───────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    push_subscription TEXT,
    notifications_enabled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '📦',
    color TEXT DEFAULT '#D3D3D3',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('credit','debit')),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    description TEXT,
    date TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT DEFAULT 'manual',
    external_transaction_id TEXT,
    sync_status TEXT DEFAULT 'synced',
    is_duplicate INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_txn_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_txn_type ON transactions(type);
"""

DEFAULT_CATEGORIES = [
    ('Food & Dining',  '🍔', '#FF6B6B'),
    ('Transport',      '🚗', '#4ECDC4'),
    ('Shopping',       '🛍️', '#45B7D1'),
    ('Entertainment',  '🎬', '#96CEB4'),
    ('Health',         '💊', '#FFEAA7'),
    ('Utilities',      '💡', '#DDA0DD'),
    ('Savings',        '💰', '#98FB98'),
    ('Gift',           '🎁', '#FFB347'),
    ('Salary',         '💼', '#87CEEB'),
    ('Freelance',      '💻', '#F0E68C'),
    ('Investment',     '📈', '#90EE90'),
    ('Miscellaneous',  '📦', '#D3D3D3'),
]


def init_db(db_path):
    """Create schema and seed default data."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Seed global categories
    for name, icon, color in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, icon, color) VALUES (?,?,?)",
            (name, icon, color)
        )
    conn.commit()
    conn.close()


# ─── Row Helpers ──────────────────────────────────────────

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    return [dict(r) for r in rows]
