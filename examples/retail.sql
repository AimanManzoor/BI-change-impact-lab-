CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, region TEXT);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, amount DECIMAL(12,2));

CREATE VIEW order_summary AS
SELECT customer_id, SUM(amount) AS total_amount FROM orders GROUP BY customer_id;

CREATE VIEW regional_sales AS
SELECT c.region, SUM(s.total_amount) AS total_amount
FROM order_summary s JOIN customers c ON s.customer_id = c.customer_id
GROUP BY c.region;

CREATE VIEW customer_directory AS
SELECT customer_id, region FROM customers;
