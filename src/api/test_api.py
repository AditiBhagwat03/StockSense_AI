"""HTTP-level validation for the STOCKSENSE AI FastAPI backend."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

if __package__ in (None, "", "api"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from api.main import app
else:
    from .main import app


client = TestClient(app)


def run_validation() -> bool:
    print("STOCKSENSE AI FASTAPI HTTP VALIDATION")
    print("------------------------------------")

    overall = True

        # 1. Root endpoint
    response = client.get("/")
    passed = (
        response.status_code == 200
        and "text/html" in response.headers.get("content-type", "")
        and "STOCKSENSE AI" in response.text
    )
    print(f"GET /: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    # 2. Health endpoint
    response = client.get("/health")
    passed = response.status_code == 200 and response.json().get("status") == "healthy"
    print(f"GET /health: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    # 3. Valid copilot request
    response = client.post(
        "/api/copilot",
        json={"question": "Which products are at risk of stock-out?"},
    )
    passed = response.status_code == 200
    print(f"POST /api/copilot valid request: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    # 4. Verify response structure
    if response.status_code == 200:
        data = response.json()
        required_fields = {
            "answer",
            "key_facts",
            "recommendation",
            "evidence",
            "limitations",
            "status",
        }
        passed = required_fields.issubset(data.keys())
    else:
        passed = False

    print(f"Copilot response schema: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    # 5. Empty question should be rejected
    response = client.post(
        "/api/copilot",
        json={"question": ""},
    )
    passed = response.status_code == 422
    print(f"Empty question rejected: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    # 6. Unsupported question should be controlled
    response = client.post(
        "/api/copilot",
        json={"question": "What is the weather today?"},
    )

    if response.status_code == 200:
        data = response.json()
        passed = data.get("status") == "error"
    else:
        passed = False

    print(f"Unsupported question controlled: {'PASS' if passed else 'FAIL'}")
    overall = overall and passed

    print("------------------------------------")
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")

    return overall


if __name__ == "__main__":
    raise SystemExit(0 if run_validation() else 1)