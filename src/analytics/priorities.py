"""Explainable, deterministic ordering for retail issues requiring attention."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database.connection import get_connection
    from analytics.overstock import analyze_all_overstock
    from analytics.sales_anomalies import analyze_all_sales_anomalies
    from analytics.stockout import analyze_all_stockout
else:
    from ..database.connection import get_connection
    from .overstock import analyze_all_overstock
    from .sales_anomalies import analyze_all_sales_anomalies
    from .stockout import analyze_all_stockout


PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def build_priorities(connection) -> list[dict[str, object]]:
    """Combine measured stock, demand, and sales-change signals into sorted issues."""
    priorities: list[dict[str, object]] = []
    for item in analyze_all_stockout(connection):
        if item["risk_level"] == "HIGH":
            urgent = bool(item["lead_time_exceeds_coverage"])
            priorities.append({
                "priority_level": "CRITICAL" if urgent else "HIGH",
                "store_id": item["store_id"], "product_id": item["product_id"],
                "issue_type": "STOCKOUT_RISK",
                "reason": "Supplier lead time exceeds remaining coverage." if urgent else "Days of cover are below 3 days.",
                "supporting_metrics": item,
            })
        elif item["risk_level"] == "MEDIUM":
            priorities.append({
                "priority_level": "MEDIUM", "store_id": item["store_id"], "product_id": item["product_id"],
                "issue_type": "STOCKOUT_RISK", "reason": "Days of cover are between 3 and 7 days.",
                "supporting_metrics": item,
            })
    for item in analyze_all_overstock(connection):
        if item["overstock_status"] in {"OVERSTOCK", "ZERO_SALES_WITH_STOCK"}:
            priorities.append({
                "priority_level": "LOW", "store_id": item["store_id"], "product_id": item["product_id"],
                "issue_type": item["overstock_status"], "reason": item["reason"], "supporting_metrics": item,
            })
    for item in analyze_all_sales_anomalies(connection):
        if item["anomaly_type"] in {"SALES_SPIKE", "SALES_DROP"}:
            priorities.append({
                "priority_level": "MEDIUM", "store_id": "ALL_STORES", "product_id": item["product_id"],
                "issue_type": item["anomaly_type"], "reason": "Measured 30-day revenue change requires investigation.",
                "supporting_metrics": item,
            })
    return sorted(priorities, key=lambda item: (PRIORITY_RANK[item["priority_level"]], item["store_id"], item["product_id"], item["issue_type"]))


def main() -> None:
    """Run a compact deterministic demo against the seeded database."""
    with get_connection() as connection:
        priorities = build_priorities(connection)
    print(f"Generated {len(priorities)} deterministic priority records.")


if __name__ == "__main__":
    main()
