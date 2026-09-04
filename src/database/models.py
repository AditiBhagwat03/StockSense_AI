"""SQLite schema definition for STOCKSENSE AI."""

import sqlite3


def create_schema(connection: sqlite3.Connection) -> None:
    """Create all database tables and the small set of useful query indexes."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS stores (
            store_id TEXT PRIMARY KEY,
            store_name TEXT NOT NULL,
            city TEXT NOT NULL,
            store_type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            lead_time_days INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            supplier_id TEXT NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            store_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            units_sold INTEGER NOT NULL,
            revenue REAL NOT NULL,
            FOREIGN KEY (store_id) REFERENCES stores(store_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            current_stock INTEGER NOT NULL,
            reorder_level INTEGER NOT NULL,
            target_stock INTEGER NOT NULL,
            last_restock_date TEXT NOT NULL,
            supplier_id TEXT NOT NULL,
            FOREIGN KEY (store_id) REFERENCES stores(store_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        );

        CREATE INDEX IF NOT EXISTS idx_sales_store_product_date
            ON sales(store_id, product_id, date);
        CREATE INDEX IF NOT EXISTS idx_sales_product_date
            ON sales(product_id, date);
        CREATE INDEX IF NOT EXISTS idx_inventory_store_product
            ON inventory(store_id, product_id);
        """
    )

