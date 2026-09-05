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

    if any(
        term in text
        for term in (
            "reallocation",
            "transfer",
            "move inventory",
            "between store",
            "between stores",
        )
    ):
        return "reallocation"

    if any(
        term in text
        for term in (
            "priority",
            "priorities",
            "needs attention",
            "need attention",
        )
    ):
        return "priorities"

    if any(
        term in text
        for term in (
            "overstock",
            "excess stock",
            "too much stock",
        )
    ):
        return "overstock"

    if any(
        term in text
        for term in (
            "sales spike",
            "spike",
            "sales increase",
            "sales growth",
            "increase",
        )
    ):
        return "sales_anomaly"

    if any(
        term in text
        for term in (
            "sales drop",
            "sales decrease",
            "sales decline",
            "drop",
            "decrease",
            "decline",
        )
    ):
        return "sales_anomaly"

    if any(
        term in text
        for term in (
            "replenishment",
            "supplier",
            "lead time",
        )
    ):
        return "supplier"

    if any(
        term in text
        for term in (
            "stock-out",
            "stockout",
            "running out",
            "low stock",
            "stock coverage",
            "stocking out",
        )
    ):
        return "stockout"

    return None


def _stockout_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)

    attention = [
        item
        for item in assessments
        if item["risk_level"] in {"HIGH", "MEDIUM", "WATCH"}
    ]

    return {
        "topic": "stockout",
        "at_risk_assessments": attention,
        "assessments_evaluated": len(assessments),
    }


def _overstock_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_overstock(connection)

    flagged = [
        item
        for item in assessments
        if item["overstock_status"] != "NORMAL"
    ]

    return {
        "topic": "overstock",
        "flagged_assessments": flagged,
        "assessments_evaluated": len(assessments),
    }


def _sales_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_sales_anomalies(connection)

    flagged = [
        item
        for item in assessments
        if item["anomaly_type"] in {"SALES_SPIKE", "SALES_DROP"}
    ]

    return {
        "topic": "sales_anomaly",
        "flagged_assessments": flagged,
        "assessments_evaluated": len(assessments),
    }


def _supplier_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)

    urgent = [
        item
        for item in assessments
        if item["lead_time_exceeds_coverage"] is True
    ]

    suppliers = [
        {
            "supplier_id": row[0],
            "supplier_name": row[1],
            "lead_time_days": row[2],
        }
        for row in connection.execute(
            """
            SELECT supplier_id, supplier_name, lead_time_days
            FROM suppliers
            ORDER BY supplier_id
            """
        )
    ]

    return {
        "topic": "supplier_replenishment",
        "supplier_lead_times": suppliers,
        "lead_time_coverage_alerts": urgent,
    }


def _reallocation_facts(connection: sqlite3.Connection) -> dict[str, object]:
    assessments = analyze_all_stockout(connection)

    shortage_products = {
        item["product_id"]
        for item in assessments
        if item["risk_level"] == "HIGH"
    }

    exposures: dict[str, list[dict[str, object]]] = {}

    for product_id in sorted(shortage_products):
        rows = connection.execute(
            """
            SELECT store_id, current_stock, reorder_level, target_stock
            FROM inventory
            WHERE product_id = ?
            ORDER BY store_id
            """,
            (product_id,),
        )

        exposures[product_id] = [
            {
                "store_id": row[0],
                "current_stock": row[1],
                "reorder_level": row[2],
                "target_stock": row[3],
            }
            for row in rows
        ]

    shortage_assessments = [
        item
        for item in assessments
        if item["risk_level"] == "HIGH"
    ]

    return {
        "topic": "reallocation",
        "shortage_assessments": shortage_assessments,
        "inventory_by_shortage_product": exposures,
    }


def collect_verified_facts(
    connection: sqlite3.Connection,
    topic: str,
) -> dict[str, object]:
    """Call only the existing deterministic analytics or parameterized local SQLite queries."""

    if topic == "stockout":
        return _stockout_facts(connection)

    if topic == "overstock":
        return _overstock_facts(connection)

    if topic == "sales_anomaly":
        return _sales_facts(connection)

    if topic == "priorities":
        return {
            "topic": "priorities",
            "priority_items": build_priorities(connection),
        }

    if topic == "supplier":
        return _supplier_facts(connection)

    if topic == "reallocation":
        return _reallocation_facts(connection)

    return {}


def _unsupported_response() -> dict[str, object]:
    return {
        "answer": (
            "This question could not be confidently mapped to "
            "the available retail analytics."
        ),
        "key_facts": [],
        "recommendation": (
            "Ask about stock-out risk, overstock, sales changes, "
            "priorities, suppliers, replenishment, or inter-store reallocation."
        ),
        "evidence": [],
        "limitations": [
            "No verified analytics topic or policy evidence was selected for this question."
        ],
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
            verified_facts = collect_verified_facts(
                connection,
                topic,
            )

        policy_evidence = retrieve_policy(
            request.question,
            limit=5,
        )

        return respond_to_question(
            request.question,
            verified_facts,
            policy_evidence,
        )

    except (sqlite3.Error, OSError):
        return {
            "answer": "Verified retail data could not be read at this time.",
            "key_facts": [],
            "recommendation": (
                "Try again after the local database is available."
            ),
            "evidence": [],
            "limitations": [
                "The local analytics data source was unavailable."
            ],
            "status": "error",
        }


@router.get("/dashboard")
def dashboard() -> dict[str, object]:
    """Return verified dashboard data for the frontend."""

    try:
        with get_connection() as connection:
            total_products = connection.execute(
                "SELECT COUNT(*) FROM products"
            ).fetchone()[0]

            stockout_assessments = analyze_all_stockout(connection)
            overstock_assessments = analyze_all_overstock(connection)
            sales_assessments = analyze_all_sales_anomalies(connection)
            priorities = build_priorities(connection)

            # Lookup product names from the local database.
            products = {
                row[0]: row[1]
                for row in connection.execute(
                    """
                    SELECT product_id, product_name
                    FROM products
                    """
                )
            }

            # Lookup store names from the local database.
            stores = {
                row[0]: row[1]
                for row in connection.execute(
                    """
                    SELECT store_id, store_name
                    FROM stores
                    """
                )
            }

            # Lookup supplier information from the local database.
            suppliers = {
                row[0]: {
                    "supplier_name": row[1],
                    "lead_time_days": row[2],
                }
                for row in connection.execute(
                    """
                    SELECT supplier_id, supplier_name, lead_time_days
                    FROM suppliers
                    """
                )
            }

        low_stock = [
            item
            for item in stockout_assessments
            if item["risk_level"] in {"HIGH", "MEDIUM", "WATCH"}
        ]

        # Enrich stock-out assessments with verified database information.
        enriched_stockout = []

        for item in low_stock:
            supplier = suppliers.get(
                item["supplier_id"],
                {},
            )

            enriched_stockout.append(
                {
                    **item,

                    "product_name": products.get(
                        item["product_id"],
                        item["product_id"],
                    ),

                    "store_name": stores.get(
                        item["store_id"],
                        item["store_id"],
                    ),

                    "supplier_name": supplier.get(
                        "supplier_name",
                        item["supplier_id"],
                    ),

                    # Fixed: the stock-out analytics object does not
                    # contain lead_time_days. Use the supplier lookup.
                    "supplier_lead_time": supplier.get(
                        "lead_time_days",
                        "N/A",
                    ),

                    "review_message": (
                        "Immediate replenishment review"
                        if item["risk_level"] == "HIGH"
                        else "Monitor and review replenishment"
                    ),
                }
            )

        overstock = [
            item
            for item in overstock_assessments
            if item["overstock_status"] != "NORMAL"
        ]

        sales_changes = [
            item
            for item in sales_assessments
            if item["anomaly_type"] in {"SALES_SPIKE", "SALES_DROP"}
        ]

        return {
            "total_products": total_products,
            "low_stock_count": len(low_stock),
            "overstock_count": len(overstock),
            "sales_changes_count": len(sales_changes),
            "stockout": enriched_stockout,
            "sales_changes": sales_changes,
            "priorities": priorities,
            "status": "success",
        }

    except sqlite3.Error:
        return {
            "total_products": 0,
            "low_stock_count": 0,
            "overstock_count": 0,
            "sales_changes_count": 0,
            "stockout": [],
            "sales_changes": [],
            "priorities": [],
            "status": "error",
        }