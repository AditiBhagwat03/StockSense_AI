"""Deterministic stock-out risk calculations using the SQLite database."""

from __future__ import annotations

import sqlite3


RECENT_DAYS = 30
MIN_MEANINGFUL_SALES_DAYS = 14


def _latest_date(connection: sqlite3.Connection) -> str | None:
    return connection.execute("SELECT MAX(date) FROM sales").fetchone()[0]


def analyze_stockout(
    connection: sqlite3.Connection, store_id: str, product_id: str
) -> dict[str, object] | None:
    """Return a transparent stock-out assessment for one store-product pair."""
    latest_date = _latest_date(connection)
    if latest_date is None:
        return None
    row = connection.execute(
        """
        SELECT i.store_id, i.product_id, i.current_stock, i.supplier_id,
               su.lead_time_days,
               COALESCE(SUM(CASE WHEN sa.date BETWEEN DATE(?, '-29 days') AND ?
                                 THEN sa.units_sold ELSE 0 END), 0) AS recent_units,
               COUNT(DISTINCT CASE WHEN sa.date BETWEEN DATE(?, '-29 days') AND ?
                                     AND sa.units_sold > 0 THEN sa.date END) AS meaningful_sales_days
        FROM inventory i
        JOIN suppliers su ON su.supplier_id = i.supplier_id
        LEFT JOIN sales sa ON sa.store_id = i.store_id AND sa.product_id = i.product_id
        WHERE i.store_id = ? AND i.product_id = ?
        GROUP BY i.store_id, i.product_id
        """,
        (latest_date, latest_date, latest_date, latest_date, store_id, product_id),
    ).fetchone()
    if row is None:
        return None

    result = {
        "store_id": row[0], "product_id": row[1], "current_stock": row[2],
        "supplier_id": row[3], "supplier_lead_time_days": row[4],
        "recent_units_sold": row[5], "meaningful_sales_days": row[6],
        "average_daily_sales": None, "days_of_cover": None,
        "risk_level": "INSUFFICIENT_DATA", "lead_time_exceeds_coverage": None,
    }
    if row[6] < MIN_MEANINGFUL_SALES_DAYS:
        return result

    average_daily_sales = row[5] / row[6]
    days_of_cover = row[2] / average_daily_sales if average_daily_sales else None
    if days_of_cover is None:
        risk_level = "INSUFFICIENT_DATA"
    elif days_of_cover > 14:
        risk_level = "HEALTHY"
    elif days_of_cover >= 7:
        risk_level = "WATCH"
    elif days_of_cover >= 3:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    result.update(
        average_daily_sales=average_daily_sales,
        days_of_cover=days_of_cover,
        risk_level=risk_level,
        lead_time_exceeds_coverage=row[4] > days_of_cover,
    )
    return result


def analyze_all_stockout(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return stock-out assessments for every inventory record."""
    pairs = connection.execute("SELECT store_id, product_id FROM inventory ORDER BY store_id, product_id").fetchall()
    return [result for store_id, product_id in pairs if (result := analyze_stockout(connection, store_id, product_id))]
