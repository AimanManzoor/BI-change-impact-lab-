import sqlite3
from pathlib import Path
from contextlib import closing

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse



app = FastAPI(title="BI Retail Intelligence API")

DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports/generated/retail_demo.sqlite"
)


def get_connection():
    conn = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def home():
    return {
        "message": "BI Retail Intelligence API is running"
    }


@app.get("/api/regions")
def get_regions():

    with closing(get_connection()) as conn:
        rows = conn.execute("""
            SELECT DISTINCT region
            FROM customers
            ORDER BY region
        """).fetchall()

    return [row["region"] for row in rows]


@app.get("/api/kpis")
def get_kpis(region: str = "All"):

    query = """
        SELECT
            COUNT(DISTINCT c.customer_id) AS total_customers,
            COUNT(o.order_id) AS total_orders,
            ROUND(COALESCE(SUM(o.amount), 0), 2) AS total_sales,
            ROUND(AVG(o.amount), 2) AS average_order_value
        FROM customers c
        LEFT JOIN orders o
            ON c.customer_id = o.customer_id
    """

    params = []

    if region != "All":
        query += " WHERE c.region = ?"
        params.append(region)

    with closing(get_connection()) as conn:
        row = conn.execute(query, params).fetchone()

    return dict(row)


@app.get("/api/regional-sales")
def get_regional_sales(region: str = "All"):

    query = """
        SELECT
            region,
            ROUND(total_amount, 2) AS total_sales
        FROM regional_sales
    """

    params = []

    if region != "All":
        query += " WHERE region = ?"
        params.append(region)

    query += " ORDER BY total_sales DESC"

    with closing(get_connection()) as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


@app.get("/api/customer-sales")
def get_customer_sales(region: str = "All"):

    query = """
        SELECT
            s.customer_id,
            c.region,
            ROUND(s.total_amount, 2) AS total_sales
        FROM order_summary s
        JOIN customers c
            ON s.customer_id = c.customer_id
    """

    params = []

    if region != "All":
        query += " WHERE c.region = ?"
        params.append(region)

    query += " ORDER BY total_sales DESC LIMIT 10"

    with closing(get_connection()) as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]

STATIC_DIR = Path(__file__).resolve().parent / "static"

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")