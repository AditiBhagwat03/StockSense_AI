"""Deterministic overstock calculations using recent weekly sales."""

from __future__ import annotations

import sqlite3


RECENT_DAYS = 28


def _latest_date(connection: sqlite3.Connection) -> str | None:
    return connection.execute("SELECT MAX(date) FROM sales").fetchone()[0]


def analyze_overstock(
    connection: sqlite3.Connection, store_id: str, product_id: str
) -> dict[str, object] | None:
    """Return the 28-day/4-week overstock assessment for a store-product pair."""
    latest_date = _latest_date(connection)
    if latest_date is None:
        return None
    row = connection.execute(
        """
        SELECT i.store_id, i.product_id, i.current_stock,
               COALESCE(SUM(CASE WHEN sa.date BETWEEN DATE(?, '-27 days') AND ?
                                 THEN sa.units_sold ELSE 0 END), 0) AS recent_units
        FROM inventory i
        LEFT JOIN sales sa ON sa.store_id = i.store_id AND sa.product_id = i.product_id
        WHERE i.store_id = ? AND i.product_id = ?
        GROUP BY i.store_id, i.product_id
        """,
        (latest_date, latest_date, store_id, product_id),
    ).fetchone()
    if row is None:
        return None
    weekly_sales = row[3] / 4
    if weekly_sales == 0 and row[2] > 0:
        status, reason, weeks_of_cover = "ZERO_SALES_WITH_STOCK", "No sales in the latest 28 days while stock remains.", None
    elif weekly_sales and row[2] / weekly_sales > 21:
        status, reason, weeks_of_cover = "OVERSTOCK", "Inventory coverage exceeds 21 weeks.", row[2] / weekly_sales
    else:
        status, reason, weeks_of_cover = "NORMAL", "Inventory coverage does not exceed 21 weeks.", row[2] / weekly_sales if weekly_sales else None
    return {
        "store_id": row[0], "product_id": row[1], "current_stock": row[2],
        "recent_28d_units": row[3], "average_weekly_sales": weekly_sales,
        "weeks_of_cover": weeks_of_cover, "overstock_status": status, "reason": reason,
    }


def analyze_all_overstock(connection: sqlite3.Connection) -> list[dict[str, object]]:
    """Return overstock assessments for every inventory record."""
    pairs = connection.execute("SELECT store_id, product_id FROM inventory ORDER BY store_id, product_id").fetchall()
    return [result for store_id, product_id in pairs if (result := analyze_overstock(connection, store_id, product_id))]
