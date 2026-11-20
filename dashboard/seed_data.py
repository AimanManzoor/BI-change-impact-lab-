import sqlite3
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DB_PATH = ROOT / "reports/generated/retail_demo.sqlite"
SCHEMA_PATH = ROOT / "examples/retail.sql"

# Create the database directory
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Initialize reproducible synthetic data
random.seed(42)

REGIONS = ["North", "South", "East", "West", "Central"]

customers = [
    (i, random.choice(REGIONS))
    for i in range(1, 501)
]

orders = [
    (
        i,
        random.randint(1, 500),
        round(random.uniform(10, 2500), 2)
    )
    for i in range(1, 5001)
]

with sqlite3.connect(DB_PATH) as conn:

    # Initialize tables and views if the database is new
    table_exists = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'customers'
    """).fetchone()

    if not table_exists:
        conn.executescript(SCHEMA_PATH.read_text())
        print("Database schema initialized.")

    conn.executemany("""
        INSERT OR IGNORE INTO customers
        (customer_id, region)
        VALUES (?, ?)
    """, customers)

    conn.executemany("""
        INSERT OR IGNORE INTO orders
        (order_id, customer_id, amount)
        VALUES (?, ?, ?)
    """, orders)

    conn.commit()

    print("Synthetic retail data generated successfully.")

    print("Total customers:",
          conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0])

    print("Total orders:",
          conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0])