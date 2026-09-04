"""Seed the STOCKSENSE AI SQLite database from the committed CSV files."""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from connection import DATABASE_PATH, get_connection
    from models import create_schema
else:
    from .connection import DATABASE_PATH, get_connection
    from .models import create_schema


DATA_DIR = PROJECT_ROOT / "data"
EXPECTED_COUNTS = {
    "stores": 4,
    "suppliers": 4,
    "products": 40,
    "sales": 14_400,
    "inventory": 160,
}


def read_csv_rows(filename: str) -> list[dict[str, str]]:
    """Read a source CSV without modifying it."""
    with (DATA_DIR / filename).open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def clear_seeded_data(connection: sqlite3.Connection) -> None:
    """Clear child tables first, making repeated seed runs deterministic."""
    for table in ("sales", "inventory", "products", "stores", "suppliers"):
        connection.execute(f"DELETE FROM {table}")
    connection.execute("DELETE FROM sqlite_sequence WHERE name IN ('sales', 'inventory')")


def seed_database(connection: sqlite3.Connection) -> None:
    """Create tables and load all CSV rows inside one transaction."""
    stores = read_csv_rows("stores.csv")
    suppliers = read_csv_rows("suppliers.csv")
    products = read_csv_rows("products.csv")
    sales = read_csv_rows("sales.csv")
    inventory = read_csv_rows("inventory.csv")

    with connection:
        create_schema(connection)
        clear_seeded_data(connection)

        print(f"Seeding stores: {len(stores)} records")
        connection.executemany(
            "INSERT INTO stores (store_id, store_name, city, store_type) VALUES (?, ?, ?, ?)",
            [(row["store_id"], row["store_name"], row["city"], row["store_type"]) for row in stores],
        )
        print(f"Seeding suppliers: {len(suppliers)} records")
        connection.executemany(
            "INSERT INTO suppliers (supplier_id, supplier_name, lead_time_days) VALUES (?, ?, ?)",
            [(row["supplier_id"], row["supplier_name"], int(row["lead_time_days"])) for row in suppliers],
        )
        print(f"Seeding products: {len(products)} records")
        connection.executemany(
            "INSERT INTO products (product_id, product_name, category, price, supplier_id) VALUES (?, ?, ?, ?, ?)",
            [(row["product_id"], row["product_name"], row["category"], float(row["price"]), row["supplier_id"]) for row in products],
        )
        print(f"Seeding sales: {len(sales)} records")
        connection.executemany(
            "INSERT INTO sales (date, store_id, product_id, units_sold, revenue) VALUES (?, ?, ?, ?, ?)",
            [(row["date"], row["store_id"], row["product_id"], int(row["units_sold"]), float(row["revenue"])) for row in sales],
        )
        print(f"Seeding inventory: {len(inventory)} records")
        connection.executemany(
            """INSERT INTO inventory
               (store_id, product_id, current_stock, reorder_level, target_stock, last_restock_date, supplier_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    row["store_id"], row["product_id"], int(row["current_stock"]),
                    int(row["reorder_level"]), int(row["target_stock"]),
                    row["last_restock_date"], row["supplier_id"],
                )
                for row in inventory
            ],
        )


def validate_database(connection: sqlite3.Connection) -> bool:
    """Validate row counts, relationships, foreign keys, and revenue integrity."""
    print("\nSTOCKSENSE AI DATABASE VALIDATION")
    print("---------------------------------")
    print(f"database path: {DATABASE_PATH}")
    passed = DATABASE_PATH.exists()
    print(f"database file exists: {'PASS' if passed else 'FAIL'}")

    for table, expected in EXPECTED_COUNTS.items():
        actual = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        status = actual == expected
        passed = passed and status
        print(f"{table}: {actual}/{expected} {'PASS' if status else 'FAIL'}")

    duplicate_primary_ids = sum(
        connection.execute(f"SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM {table}").fetchone()[0]
        for table, column in (("stores", "store_id"), ("suppliers", "supplier_id"), ("products", "product_id"))
    )
    relationship_errors = connection.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM products p LEFT JOIN suppliers su ON p.supplier_id = su.supplier_id WHERE su.supplier_id IS NULL) +
          (SELECT COUNT(*) FROM sales sa LEFT JOIN stores st ON sa.store_id = st.store_id WHERE st.store_id IS NULL) +
          (SELECT COUNT(*) FROM sales sa LEFT JOIN products p ON sa.product_id = p.product_id WHERE p.product_id IS NULL) +
          (SELECT COUNT(*) FROM inventory i LEFT JOIN stores st ON i.store_id = st.store_id WHERE st.store_id IS NULL) +
          (SELECT COUNT(*) FROM inventory i LEFT JOIN products p ON i.product_id = p.product_id WHERE p.product_id IS NULL) +
          (SELECT COUNT(*) FROM inventory i LEFT JOIN suppliers su ON i.supplier_id = su.supplier_id WHERE su.supplier_id IS NULL)
        """
    ).fetchone()[0]
    foreign_key_violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    revenue_errors = connection.execute(
        """SELECT COUNT(*)
           FROM sales sa JOIN products p ON sa.product_id = p.product_id
           WHERE ABS(sa.revenue - (sa.units_sold * p.price)) > 0.000001"""
    ).fetchone()[0]

    for label, errors in (
        ("duplicate primary IDs", duplicate_primary_ids),
        ("relationship errors", relationship_errors),
        ("foreign key violations", foreign_key_violations),
        ("revenue validation errors", revenue_errors),
    ):
        status = errors == 0
        passed = passed and status
        print(f"{label}: {errors} {'PASS' if status else 'FAIL'}")
    print(f"DATABASE SEEDING: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    with get_connection() as connection:
        seed_database(connection)
        if not validate_database(connection):
            raise RuntimeError("Database seeding validation failed")


if __name__ == "__main__":
    main()
