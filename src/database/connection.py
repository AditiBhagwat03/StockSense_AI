"""SQLite connection helpers."""

from pathlib import Path
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "stocksense.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection with SQLite foreign-key enforcement enabled."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
