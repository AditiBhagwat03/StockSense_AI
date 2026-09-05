"""Deterministic API orchestration for analytics, policy evidence, and Gemini."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fastapi import APIRouter

if __package__ in (None, "", "api"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from analytics.overstock import analyze_all_overstock
    from analytics.priorities import build_priorities
    from analytics.sales_anomalies import analyze_all_sales_anomalies
    from analytics.stockout import analyze_all_stockout
    from database.connection import get_connection
    from llm.responder import respond_to_question
    from rag.retriever import retrieve_policy
    from api.schemas import CopilotRequest, CopilotResponse
else:
    from ..analytics.overstock import analyze_all_overstock
    from ..analytics.priorities import build_priorities
    from ..analytics.sales_anomalies import analyze_all_sales_anomalies
    from ..analytics.stockout import analyze_all_stockout
    from ..database.connection import get_connection
    from ..llm.responder import respond_to_question
    from ..rag.retriever import retrieve_policy
    from .schemas import CopilotRequest, CopilotResponse


router = APIRouter(prefix="/api", tags=["copilot"])


def detect_topic(question: str) -> str | None:
    """Map supported retail questions to deterministic analytics without using Gemini."""
    text = question.lower()
    if any(term in text for term in ("reallocation", "transfer", "move inventory", "between store", "between stores")):
        return "reallocation"
    if any(term in text for term in ("priority", "priorities", "needs attention", "need attention")):
        return "priorities"
    if any(term in text for term in ("overstock", "excess stock", "too much stock")):
        return "overstock"
    if any(term in text for term in ("sales spike", "spike", "sales increase", "sales growth", "increase")):
        return "sales_anomaly"
    if any(term in text for term in ("sales drop", "sales decrease", "sales decline", "drop", "decrease", "decline")):
        return "sales_anomaly"
    if any(term in text for term in ("replenishment", "supplier", "lead time")):
        return "supplier"
    if any(term in text for term in ("stock-out", "stockout", "running out", "low stock", "stock coverage", "stocking out")):
        return "stockout"
    return None


def _stockout_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)
    attention = [item for item in assessments if item["risk_level"] in {"HIGH", "MEDIUM", "WATCH"}]
    return {"topic": "stockout", "at_risk_assessments": attention, "assessments_evaluated": len(assessments)}


def _overstock_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_overstock(connection)
    flagged = [item for item in assessments if item["overstock_status"] != "NORMAL"]
    return {"topic": "overstock", "flagged_assessments": flagged, "assessments_evaluated": len(assessments)}


def _sales_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_sales_anomalies(connection)
    flagged = [item for item in assessments if item["anomaly_type"] in {"SALES_SPIKE", "SALES_DROP"}]
    return {"topic": "sales_anomaly", "flagged_assessments": flagged, "assessments_evaluated": len(assessments)}


def _supplier_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)
    urgent = [item for item in assessments if item["lead_time_exceeds_coverage"] is True]
    suppliers = [
        {"supplier_id": row[0], "supplier_name": row[1], "lead_time_days": row[2]}
        for row in connection.execute(
            "SELECT supplier_id, supplier_name, lead_time_days FROM suppliers ORDER BY supplier_id"
        )
    ]
    return {"topic": "supplier_replenishment", "supplier_lead_times": suppliers, "lead_time_coverage_alerts": urgent}


def _reallocation_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)
    shortage_products = {item["product_id"] for item in assessments if item["risk_level"] == "HIGH"}
    exposures: dict[str, list[dict[str, object]]] = {}
    for product_id in sorted(shortage_products):
        rows = connection.execute(
            """SELECT store_id, current_stock, reorder_level, target_stock
               FROM inventory WHERE product_id = ? ORDER BY store_id""",
            (product_id,),
        )
        exposures[product_id] = [
            {"store_id": row[0], "current_stock": row[1], "reorder_level": row[2], "target_stock": row[3]}
            for row in rows
        ]
    shortage_assessments = [item for item in assessments if item["risk_level"] == "HIGH"]
    return {"topic": "reallocation", "shortage_assessments": shortage_assessments, "inventory_by_shortage_product": exposures}


def collect_verified_facts(connection: sqlite3.Connection, topic: str) -> dict[str, object]:
    """Call only the existing deterministic analytics or parameterized local SQLite queries."""
    if topic == "stockout":
        return _stockout_facts(connection)
    if topic == "overstock":
        return _overstock_facts(connection)
    if topic == "sales_anomaly":
        return _sales_facts(connection)
    if topic == "priorities":
        return {"topic": "priorities", "priority_items": build_priorities(connection)}
    if topic == "supplier":
        return _supplier_facts(connection)
    if topic == "reallocation":
        return _reallocation_facts(connection)
    return {}


def _unsupported_response() -> dict[str, object]:
    return {
        "answer": "This question could not be confidently mapped to the available retail analytics.",
        "key_facts": [],
        "recommendation": "Ask about stock-out risk, overstock, sales changes, priorities, suppliers, replenishment, or inter-store reallocation.",
        "evidence": [],
        "limitations": ["No verified analytics topic or policy evidence was selected for this question."],
        "status": "error",
    }


@router.post("/copilot", response_model=CopilotResponse)
def copilot(request: CopilotRequest) -> dict[str, object]:
    """Return a Gemini explanation constrained to verified analytics and retrieved policy evidence."""
    topic = detect_topic(request.question)
    if topic is None:
        return _unsupported_response()
    try:
        with get_connection() as connection:
            verified_facts = collect_verified_facts(connection, topic)
        policy_evidence = retrieve_policy(request.question, limit=5)
        return respond_to_question(request.question, verified_facts, policy_evidence)
    except (sqlite3.Error, OSError):
        return {
            "answer": "Verified retail data could not be read at this time.",
            "key_facts": [],
            "recommendation": "Try again after the local database is available.",
            "evidence": [],
            "limitations": ["The local analytics data source was unavailable."],
            "status": "error",
        }
