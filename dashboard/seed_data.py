import sqlite3
import random
from pathlib import Path

# Database location
DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports/generated/retail_demo.sqlite"
)

# Reproducible synthetic data
random.seed(42)

REGIONS = ["North", "South", "East", "West", "Central"]

NUM_CUSTOMERS = 500
NUM_ORDERS = 5000

# Generate synthetic customers
customers = [
    (customer_id, random.choice(REGIONS))
    for customer_id in range(1, NUM_CUSTOMERS + 1)
]

# Generate synthetic orders
orders = [
    (
        order_id,
        random.randint(1, NUM_CUSTOMERS),
        round(random.uniform(10, 2500), 2)
    )
    for order_id in range(1, NUM_ORDERS + 1)
]

# Ensure the database exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

if not DB_PATH.is_file():

    schema_path = (
        Path(__file__).resolve().parents[1]
        / "examples/retail.sql"
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_path.read_text())

    print("Retail database initialized successfully.")

# Insert synthetic data
with sqlite3.connect(DB_PATH) as conn:

    conn.executemany(
        """
        INSERT OR IGNORE INTO customers
        (customer_id, region)
        VALUES (?, ?)
        """,
        customers
    )

    conn.executemany(
        """
        INSERT OR IGNORE INTO orders
        (order_id, customer_id, amount)
        VALUES (?, ?, ?)
        """,
        orders
    )

    conn.commit()

    customer_count = conn.execute(
        "SELECT COUNT(*) FROM customers"
    ).fetchone()[0]

    order_count = conn.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    print("Synthetic retail data generated successfully.")
    print(f"Total customers: {customer_count}")
    print(f"Total orders: {order_count}")
    print(f"Database: {DB_PATH}")