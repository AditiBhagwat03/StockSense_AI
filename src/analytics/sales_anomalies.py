"""Measured 30-day product sales-change detection without causal inference."""

from __future__ import annotations

import sqlite3


MIN_MEANINGFUL_SALES_DAYS = 14


def analyze_sales_anomaly(connection: sqlite3.Connection, product_id: str) -> dict[str, object] | None:
    """Compare the most recent 30 days with the preceding 30 days for a product."""
    latest_date = connection.execute("SELECT MAX(date) FROM sales").fetchone()[0]
    if latest_date is None:
        return None
    row = connection.execute(
        """
        SELECT
          COALESCE(SUM(CASE WHEN date BETWEEN DATE(?, '-29 days') AND ? THEN units_sold ELSE 0 END), 0),
          COALESCE(SUM(CASE WHEN date BETWEEN DATE(?, '-29 days') AND ? THEN revenue ELSE 0 END), 0),
          COALESCE(SUM(CASE WHEN date BETWEEN DATE(?, '-59 days') AND DATE(?, '-30 days') THEN units_sold ELSE 0 END), 0),
          COALESCE(SUM(CASE WHEN date BETWEEN DATE(?, '-59 days') AND DATE(?, '-30 days') THEN revenue ELSE 0 END), 0),
          COUNT(DISTINCT CASE WHEN date BETWEEN DATE(?, '-59 days') AND ? AND units_sold > 0 THEN date END)
        FROM sales WHERE product_id = ?
        """,
        (latest_date,) * 10 + (product_id,),
    ).fetchone()
    if row is None:
        return None
    current_units, current_revenue, previous_units, previous_revenue, meaningful_days = row
    result = {
        "product_id": product_id, "current_30d_units": current_units,
        "previous_30d_units": previous_units, "current_30d_revenue": current_revenue,
        "previous_30d_revenue": previous_revenue, "meaningful_sales_days": meaningful_days,
        "percentage_change": None, "anomaly_type": "INSUFFICIENT_DATA",
    }
    if meaningful_days < MIN_MEANINGFUL_SALES_DAYS or previous_revenue == 0:
        return result
    change = ((current_revenue - previous_revenue) / previous_revenue) * 100
    anomaly_type = "SALES_SPIKE" if change >= 30 else "SALES_DROP" if change <= -30 else "NORMAL"
    result.update(percentage_change=change, anomaly_type=anomaly_type)
    return result


def analyze_all_sales_anomalies(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return sales-change assessments for all products."""
    product_ids = [row[0] for row in connection.execute("SELECT product_id FROM products ORDER BY product_id")]
    return [result for product_id in product_ids if (result := analyze_sales_anomaly(connection, product_id))]
