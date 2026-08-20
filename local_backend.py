"""
Local (offline) storage for activities, used when the user hasn't signed
in to Google -- or chooses not to. Plain sqlite3 (not QSqlDatabase) so it
can be freely opened/closed alongside the Google backend without Qt driver
connection-name headaches.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "activities.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def ensure_ready():
    """Create the DB file/table if needed. Call once at startup to fail early and clearly."""
    _connect().close()


def read_activities():
    """Return rows as [[id, name, date], ...] in insertion order."""
    conn = _connect()
    try:
        cur = conn.execute("SELECT id, name, date FROM activities ORDER BY id")
        return [[str(row[0]), row[1], row[2]] for row in cur.fetchall()]
    finally:
        conn.close()


def append_activity(name, date):
    conn = _connect()
    try:
        conn.execute("INSERT INTO activities (name, date) VALUES (?, ?)", (name, date))
        conn.commit()
    finally:
        conn.close()


def delete_activity_by_id(activity_id):
    conn = _connect()
    try:
        conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        conn.commit()
    finally:
        conn.close()


def clear_all_activities():
    conn = _connect()
    try:
        conn.execute("DELETE FROM activities")
        conn.commit()
    finally:
        conn.close()
