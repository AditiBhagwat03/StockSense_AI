"""FastAPI application entry point for STOCKSENSE AI."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if __package__ in (None, "", "api"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database.connection import get_connection
    from api.routes import router
else:
    from ..database.connection import get_connection
    from .routes import router


# Project root: STOCKSENSE AI/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = FastAPI(title="STOCKSENSE AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)

# Serve frontend CSS, JavaScript and other static files.
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


@app.get("/")
def frontend() -> FileResponse:
    """Serve the STOCKSENSE AI dashboard."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Verify that a short-lived local SQLite connection can be opened."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error as error:
        raise HTTPException(
            status_code=503,
            detail="Local database is unavailable.",
        ) from error

    return {
        "service": "STOCKSENSE AI",
        "status": "healthy",
    }