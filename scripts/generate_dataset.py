"""Generate the deterministic STOCKSENSE AI hackathon dataset and policies."""

from __future__ import annotations

import csv
import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
DATA_DIR = ROOT / "data"
POLICY_DIR = DATA_DIR / "policies"
RNG = random.Random(42)

STORES = [
    ("S001", "Central Store", "Aurangabad", "High Traffic"),
    ("S002", "Mall Store", "Aurangabad", "Mall"),
    ("S003", "Highway Store", "Aurangabad", "Highway"),
    ("S004", "City Store", "Aurangabad", "Standard"),
]
SUPPLIERS = [
    ("SUP01", "TechSource Distributors", 5),
    ("SUP02", "Prime Electronics Supply", 7),
    ("SUP03", "Metro Wholesale", 4),
    ("SUP04", "DigitalMart Supply", 6),
]
PRODUCTS = [
    ("P001", "Wireless Mouse", "Computer Peripherals", 899, "SUP01"),
    ("P002", "Mechanical Keyboard", "Computer Peripherals", 2499, "SUP01"),
    ("P003", "USB-C Hub", "Computer Peripherals", 1799, "SUP02"),
    ("P004", "Bluetooth Speaker", "Audio", 2999, "SUP02"),
    ("P005", "Smart Watch", "Smart Devices", 4499, "SUP03"),
    ("P006", "Wireless Earbuds", "Audio", 3499, "SUP03"),
    ("P007", "Power Bank", "Mobile Accessories", 1599, "SUP04"),
    ("P008", "USB-C Cable", "Mobile Accessories", 499, "SUP04"),
    ("P009", "Phone Stand", "Accessories", 699, "SUP01"),
    ("P010", "Webcam", "Computer Peripherals", 2299, "SUP02"),
    ("P011", "Laptop Sleeve", "Accessories", 1299, "SUP01"),
    ("P012", "Wireless Charger", "Mobile Accessories", 1499, "SUP04"),
    ("P013", "Gaming Mouse Pad", "Accessories", 799, "SUP02"),
    ("P014", "HDMI Cable", "Computer Peripherals", 699, "SUP01"),
    ("P015", "Smart Fitness Tracker", "Smart Devices", 2999, "SUP03"),
    ("P016", "Noise Cancelling Headphones", "Audio", 5999, "SUP03"),
    ("P017", "Laptop Cooling Pad", "Computer Peripherals", 1899, "SUP02"),
    ("P018", "Screen Protector", "Mobile Accessories", 399, "SUP04"),
    ("P019", "Bluetooth Keyboard", "Computer Peripherals", 2199, "SUP01"),
    ("P020", "Old Bluetooth Headset", "Audio", 1999, "SUP03"),
    ("P021", "Portable SSD 1TB", "Computer Peripherals", 7499, "SUP02"),
    ("P022", "USB Flash Drive 64GB", "Computer Peripherals", 699, "SUP01"),
    ("P023", "Car Phone Mount", "Accessories", 899, "SUP04"),
    ("P024", "Smart Plug", "Smart Devices", 1199, "SUP03"),
    ("P025", "Wi-Fi Extender", "Smart Devices", 2699, "SUP02"),
    ("P026", "Laptop Stand", "Accessories", 1699, "SUP01"),
    ("P027", "Type-C Adapter", "Mobile Accessories", 599, "SUP04"),
    ("P028", "Gaming Headset", "Audio", 3999, "SUP03"),
    ("P029", "Action Camera Mount", "Accessories", 1399, "SUP02"),
    ("P030", "Smart LED Bulb", "Smart Devices", 899, "SUP03"),
    ("P031", "Wireless Presenter", "Computer Peripherals", 1299, "SUP01"),
    ("P032", "Phone Ring Light", "Mobile Accessories", 999, "SUP04"),
    ("P033", "Desktop Speakers", "Audio", 2799, "SUP02"),
    ("P034", "Cable Organizer", "Accessories", 449, "SUP01"),
    ("P035", "Tablet Stylus", "Mobile Accessories", 1899, "SUP04"),
    ("P036", "Smart Door Sensor", "Smart Devices", 1599, "SUP03"),
    ("P037", "Ethernet Cable", "Computer Peripherals", 549, "SUP02"),
    ("P038", "Travel Adapter", "Mobile Accessories", 1999, "SUP04"),
    ("P039", "Mini Tripod", "Accessories", 1099, "SUP01"),
    ("P040", "Bluetooth Tracker", "Smart Devices", 1799, "SUP03"),
]

POLICIES = {
"inventory_policy.txt": """POLICY ID: INV-001\nTITLE: Inventory Status Classification\n\nPurpose:\nDefine how inventory coverage is interpreted.\n\nStock coverage is calculated as:\nDays of Cover = Current Stock / Average Daily Sales\n\nClassification:\nHealthy: More than 14 days of coverage.\nWatch: 7 to 14 days of coverage.\nMedium Risk: 3 to less than 7 days of coverage.\nHigh Risk: Less than 3 days of coverage.\n\nIf average daily sales cannot be reliably calculated\nbecause insufficient sales history is available, the\nsystem must not assign a stock-out risk level.\n\nThe system must show the data used for every\ninventory classification.\n""",
"replenishment_policy.txt": """POLICY ID: REP-001\nTITLE: Replenishment Review\n\nA product should be reviewed for replenishment when\nprojected stock coverage is below the supplier lead time.\n\nPriority should increase when the product is already\nclassified as high stock-out risk.\n\nThe recommended replenishment quantity should consider:\n\n1. Current stock\n2. Recent average sales\n3. Target stock level\n4. Supplier lead time\n\nThe system must present the assumptions used to\ncalculate any suggested replenishment quantity.\n\nThe system must not claim that a purchase order has\nbeen placed or that stock will definitely arrive.\n""",
"stockout_policy.txt": """POLICY ID: STO-001\nTITLE: Stock-Out Risk\n\nA product is considered high priority when its estimated\ndays of stock coverage is below 3 days.\n\nIf the product's supplier lead time is greater than its\nremaining stock coverage, replenishment should be\nreviewed immediately.\n\nIf sufficient sales history is unavailable, the system\nmust state that stock-out risk cannot be reliably\nestimated.\n\nThe system must never guarantee that a product will\nsell out on a specific date.\n""",
"overstock_policy.txt": """POLICY ID: OVS-001\nTITLE: Overstock Identification\n\nA product may be flagged for overstock review when\nits inventory coverage exceeds 21 weeks based on\nrecent average weekly sales.\n\nProducts with zero sales during the review period\nshould also be flagged for inventory review when\nstock remains available.\n\nAn overstock flag does not automatically mean that the\nproduct should be discounted.\n\nThe system should recommend reviewing purchasing,\ninventory allocation, or promotional options rather than\nautomatically selecting a discount.\n""",
"sales_anomaly_policy.txt": """POLICY ID: ANM-001\nTITLE: Sales Change Detection\n\nCompare the current 30-day sales period with the\nprevious 30-day period.\n\nA change of 30 percent or more in either direction\nshould be flagged for investigation.\n\nIncrease of 30 percent or more:\nSALES SPIKE\n\nDecrease of 30 percent or more:\nSALES DROP\n\nThe system should report the measured change and\nthe underlying sales values.\n\nA sales anomaly does not establish its cause.\n\nThe system must not invent explanations when the\navailable data does not contain causal information.\n""",
"reallocation_policy.txt": """POLICY ID: REL-001\nTITLE: Inter-Store Stock Review\n\nWhen a store has high stock-out risk for a product,\nthe system may check other stores for available stock.\n\nIf another store has sufficient inventory and lower\nsales demand, inter-store reallocation may be suggested\nfor human review.\n\nThe system must show:\n\n1. Store with the shortage\n2. Current stock at that store\n3. Sales rate at that store\n4. Candidate source store\n5. Available stock at the source store\n6. Reason for the recommendation\n\nThe system must not claim that stock has been moved.\nAny reallocation recommendation requires human approval.\n""",
}


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def allocate_total(sales, product_id, start_day, total, store_cycle=("S001", "S002", "S003", "S004"), period=30):
    """Place one-unit transactions deterministically across a date/store period."""
    for offset in range(total):
        day_index = start_day + offset % period
        store_id = store_cycle[offset % len(store_cycle)]
        sales[(day_index, store_id, product_id)] += 1


def build_sales(dates):
    sales = defaultdict(int)
    store_factor = {"S001": 1.30, "S002": 1.08, "S003": 0.78, "S004": 1.00}
    special = {"P001", "P002", "P004", "P005", "P006", "P015", "P020"}
    for day_index, current_date in enumerate(dates):
        for product_index, (product_id, _, _, _, _) in enumerate(PRODUCTS, start=1):
            if product_id in special:
                continue
            for store_id, *_ in STORES:
                base = 1 + (product_index % 4)
                weekend = 1 if current_date.weekday() >= 5 and product_index % 3 else 0
                trend = 1 if product_index % 7 == 0 and day_index >= 60 else 0
                noise = RNG.choice((-1, 0, 0, 0, 1))
                units = max(0, round(base * store_factor[store_id] / 2) + weekend + trend + noise)
                sales[(day_index, store_id, product_id)] = units

    # Explicit demand and anomaly scenarios. Totals are deliberately auditable.
    allocate_total(sales, "P001", 60, 186, ("S001",))          # 6.2/day at Central Store
    allocate_total(sales, "P001", 60, 75, ("S002",))
    allocate_total(sales, "P001", 60, 42, ("S003",))
    allocate_total(sales, "P001", 60, 54, ("S004",))
    allocate_total(sales, "P002", 60, 144, ("S002",))          # 4.8/day at Mall Store
    allocate_total(sales, "P004", 62, 32, ("S003",), 28)       # 8/week over final 28 days
    allocate_total(sales, "P005", 0, 10)                         # previous 30 days: Rs 44,990
    allocate_total(sales, "P005", 30, 10)
    allocate_total(sales, "P005", 60, 17)                        # latest 30 days: Rs 76,483 (+70.0%)
    allocate_total(sales, "P006", 0, 16)
    allocate_total(sales, "P006", 30, 16)                        # previous 30 days: Rs 55,984
    allocate_total(sales, "P006", 60, 9)                         # latest 30 days: Rs 31,491 (-43.8%)
    allocate_total(sales, "P015", 83, 12, period=7)              # meaningful history on seven days only
    allocate_total(sales, "P020", 20, 18)                        # no sales in latest 30 days

    rows = []
    prices = {product[0]: product[3] for product in PRODUCTS}
    for day_index, current_date in enumerate(dates):
        for store_id, *_ in STORES:
            for product_id, *_ in PRODUCTS:
                units = sales[(day_index, store_id, product_id)]
                rows.append((current_date.isoformat(), store_id, product_id, units, units * prices[product_id]))
    return rows


def build_inventory(dates):
    records = []
    product_supplier = {product[0]: product[4] for product in PRODUCTS}
    overrides = {
        ("S001", "P001"): 14, ("S002", "P001"): 72, ("S003", "P001"): 48, ("S004", "P001"): 51,
        ("S002", "P002"): 35, ("S003", "P004"): 240,
    }
    for store_index, (store_id, *_ ) in enumerate(STORES):
        for product_index, (product_id, *_rest) in enumerate(PRODUCTS, start=1):
            stock = overrides.get((store_id, product_id), 30 + ((product_index * 11 + store_index * 7) % 70))
            if product_id == "P020":
                stock = 85 + store_index * 5
            if product_id == "P010":
                stock = 60 + store_index * 4
            reorder = max(8, stock // 3)
            target = max(stock + 20, reorder * 3)
            restock = dates[-1] - timedelta(days=3 + ((product_index + store_index) % 18))
            records.append((store_id, product_id, stock, reorder, target, restock.isoformat(), product_supplier[product_id]))
    return records


def read_csv(name):
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate():
    stores, products, suppliers = read_csv("stores.csv"), read_csv("products.csv"), read_csv("suppliers.csv")
    sales, inventory = read_csv("sales.csv"), read_csv("inventory.csv")
    required = {
        "stores.csv": {"store_id", "store_name", "city", "store_type"},
        "products.csv": {"product_id", "product_name", "category", "price", "supplier_id"},
        "suppliers.csv": {"supplier_id", "supplier_name", "lead_time_days"},
        "sales.csv": {"date", "store_id", "product_id", "units_sold", "revenue"},
        "inventory.csv": {"store_id", "product_id", "current_stock", "reorder_level", "target_stock", "last_restock_date", "supplier_id"},
    }
    for filename, columns in required.items():
        assert (DATA_DIR / filename).exists() and columns <= set(read_csv(filename)[0])
    assert len(stores) == 4 and len(products) == 40 and len(suppliers) == 4 and len(inventory) == 160
    assert len({r["store_id"] for r in stores}) == 4 and len({r["product_id"] for r in products}) == 40 and len({r["supplier_id"] for r in suppliers}) == 4
    store_ids, product_ids, supplier_ids = ({r["store_id"] for r in stores}, {r["product_id"] for r in products}, {r["supplier_id"] for r in suppliers})
    prices = {r["product_id"]: int(r["price"]) for r in products}
    assert all(r["store_id"] in store_ids and r["product_id"] in product_ids and int(r["units_sold"]) >= 0 and int(r["revenue"]) == int(r["units_sold"]) * prices[r["product_id"]] for r in sales)
    assert all(r["store_id"] in store_ids and r["product_id"] in product_ids and r["supplier_id"] in supplier_ids and all(int(r[key]) >= 0 for key in ("current_stock", "reorder_level", "target_stock")) for r in inventory)
    dates = sorted({r["date"] for r in sales})
    assert len(dates) == 90 and dates[-1] == "2026-09-03"
    def units(product, store=None, last_days=30):
        period = set(dates[-last_days:])
        return sum(int(r["units_sold"]) for r in sales if r["product_id"] == product and r["date"] in period and (store is None or r["store_id"] == store))
    def stock(product, store):
        return int(next(r["current_stock"] for r in inventory if r["product_id"] == product and r["store_id"] == store))
    p001_cover = stock("P001", "S001") / (units("P001", "S001") / 30)
    p004_weeks = stock("P004", "S003") / (units("P004", "S003", 28) / 4)
    p005_change = (units("P005") - sum(int(r["units_sold"]) for r in sales if r["product_id"] == "P005" and r["date"] in set(dates[30:60]))) / sum(int(r["units_sold"]) for r in sales if r["product_id"] == "P005" and r["date"] in set(dates[30:60])) * 100
    previous_p006 = sum(int(r["units_sold"]) for r in sales if r["product_id"] == "P006" and r["date"] in set(dates[30:60]))
    p006_change = (units("P006") - previous_p006) / previous_p006 * 100
    meaningful_p015_days = len({r["date"] for r in sales if r["product_id"] == "P015" and int(r["units_sold"]) > 0})
    assert 2.2 <= p001_cover <= 2.4 and 29 <= p004_weeks <= 31 and 68 <= p005_change <= 72 and -46 <= p006_change <= -42
    assert meaningful_p015_days <= 7 and units("P020") == 0 and all(stock("P020", s[0]) > 0 for s in STORES)
    assert stock("P001", "S001") == 14 and min(stock("P001", s) for s in ("S002", "S003", "S004")) >= 48
    assert len(list(POLICY_DIR.glob("*.txt"))) == 6
    return p001_cover, p004_weeks, p005_change, p006_change, meaningful_p015_days


def main():
    DATA_DIR.mkdir(exist_ok=True)
    POLICY_DIR.mkdir(exist_ok=True)
    dates = [date(2026, 9, 3) - timedelta(days=89 - index) for index in range(90)]
    write_csv(DATA_DIR / "stores.csv", ("store_id", "store_name", "city", "store_type"), STORES)
    write_csv(DATA_DIR / "suppliers.csv", ("supplier_id", "supplier_name", "lead_time_days"), SUPPLIERS)
    write_csv(DATA_DIR / "products.csv", ("product_id", "product_name", "category", "price", "supplier_id"), PRODUCTS)
    sales = build_sales(dates)
    write_csv(DATA_DIR / "sales.csv", ("date", "store_id", "product_id", "units_sold", "revenue"), sales)
    inventory = build_inventory(dates)
    write_csv(DATA_DIR / "inventory.csv", ("store_id", "product_id", "current_stock", "reorder_level", "target_stock", "last_restock_date", "supplier_id"), inventory)
    for filename, content in POLICIES.items():
        (POLICY_DIR / filename).write_text(content, encoding="utf-8")
    p001, p004, p005, p006, p015 = validate()
    print("DATASET GENERATION COMPLETE\n")
    print("Stores: 4\nProducts: 40\nSuppliers: 4\nInventory records: 160\nSales records: 14,400\nPolicy documents: 6\n")
    print("VALIDATION:")
    for message in ("Foreign keys valid", "Revenue calculations valid", "90-day period valid", "P001 stock-out scenario detected", "P004 overstock scenario detected", "P005 sales spike scenario detected", "P006 sales drop scenario detected", "P015 insufficient-data scenario detected", "P020 zero-sales scenario detected", "P001 inter-store imbalance detected"):
        print(f"✓ {message}")
    print(f"\nScenario metrics: P001 cover={p001:.2f} days; P004 cover={p004:.1f} weeks; P005 change={p005:.1f}%; P006 change={p006:.1f}%; P015 meaningful days={p015}")


if __name__ == "__main__":
    main()
