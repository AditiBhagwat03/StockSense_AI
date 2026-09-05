"""Lightweight direct validation for the FastAPI application and orchestration handlers."""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from api.main import app, health, root
    from api.routes import copilot
    from api.schemas import CopilotRequest
else:
    from .main import app, health, root
    from .routes import copilot
    from .schemas import CopilotRequest


def run_validation() -> bool:
    """Validate FastAPI imports, endpoint handlers, request checks, and existing module imports."""
    from src.analytics.priorities import build_priorities
    from src.database.connection import get_connection
    from src.llm.responder import respond_to_question
    from src.rag.retriever import retrieve_policy

    checks: list[tuple[str, bool]] = []
    paths = {route.path for route in app.routes}
    checks.append(("FastAPI app imports", {"/", "/health", "/api/copilot"} <= paths))
    checks.append(("GET /", root() == {"service": "STOCKSENSE AI", "status": "running"}))
    checks.append(("GET /health", health()["status"] == "healthy"))

    valid_response = copilot(CopilotRequest(question="Which products are at high stock-out risk?"))
    checks.append(("POST /api/copilot accepts valid question", {"answer", "key_facts", "recommendation", "evidence", "limitations"} <= valid_response.keys()))
    try:
        CopilotRequest(question="   ")
        empty_rejected = False
    except ValidationError:
        empty_rejected = True
    checks.append(("Empty question rejected", empty_rejected))

    unsupported_response = copilot(CopilotRequest(question="Tell me a joke about the moon."))
    checks.append(("Unsupported question controlled", unsupported_response.get("status") == "error"))
    checks.append(("Steps 6-9 imports", all((get_connection, build_priorities, retrieve_policy, respond_to_question))))

    print("STOCKSENSE AI FASTAPI VALIDATION")
    print("---------------------------------")
    for name, passed in checks:
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    overall = all(passed for _, passed in checks)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    return overall


if __name__ == "__main__":
    if not run_validation():
        raise SystemExit(1)
