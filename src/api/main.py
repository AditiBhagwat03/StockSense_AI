"""FastAPI application entry point for STOCKSENSE AI."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

if __package__ in (None, "", "api"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database.connection import get_connection
    from api.routes import router
else:
    from ..database.connection import get_connection
    from .routes import router


app = FastAPI(title="STOCKSENSE AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)


@app.get("/")
def root() -> dict[str, str]:
    """Return a minimal service identity response."""
    return {"service": "STOCKSENSE AI", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    """Verify that a short-lived local SQLite connection can be opened."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Local database is unavailable.") from error
    return {"service": "STOCKSENSE AI", "status": "healthy"}
