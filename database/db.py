import os
import sqlite3
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

# (day of current month, category, amount, description)
SEED_EXPENSES = [
    (2, "Food", 45.50, "Weekly groceries"),
    (4, "Transport", 15.00, "Metro card top-up"),
    (6, "Bills", 120.00, "Electricity bill"),
    (9, "Health", 30.00, "Pharmacy"),
    (12, "Entertainment", 18.99, "Movie tickets"),
    (16, "Shopping", 65.25, "New shoes"),
    (20, "Food", 22.75, "Dinner with friends"),
    (25, "Other", 10.00, None),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    date        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email.strip().lower(), generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# Checked when the email is unknown, so that path takes about as long as a
# real password check and reveals nothing about which emails exist.
_DUMMY_HASH = generate_password_hash("unused-placeholder-password")


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    if user_id is None:
        return None
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def verify_user(email, password):
    """Return the matching user's id, name and email, or None."""
    row = get_user_by_email(email)
    if row is None:
        check_password_hash(_DUMMY_HASH, password)
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        today = date.today()
        rows = [
            (
                user_id,
                amount,
                category,
                date(today.year, today.month, day).isoformat(),
                description,
            )
            for day, category, amount, description in SEED_EXPENSES
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
