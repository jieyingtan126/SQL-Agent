import os
from dotenv import load_dotenv
import sqlite3
import random
from datetime import datetime, timedelta

load_dotenv()

db_path = os.getenv("DATABASE_URL")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Clean start
cursor.executescript("""
DROP TABLE IF EXISTS Order_Items;
DROP TABLE IF EXISTS Orders;
DROP TABLE IF EXISTS Products;
DROP TABLE IF EXISTS Customers;

CREATE TABLE Customers (customer_id INTEGER PRIMARY KEY, name TEXT, gender TEXT, city TEXT);
CREATE TABLE Products (product_id INTEGER PRIMARY KEY, name TEXT, price REAL, category TEXT);
CREATE TABLE Orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date DATE);
CREATE TABLE Order_Items (item_id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER);
""")

# 2. Insert 10 Customers
customers = [
    ('Amelia Rossi', 'Female', 'Paris'), 
    ('Bob Smith', 'Male', 'New York'), 
    ('Charlie Case', 'Male', 'London'), 
    ('Darren Whitaker', 'Male', 'Melbourne'), 
    ('Edward Norton', 'Male', 'Berlin'), 
    ('Fiona Gallagher', 'Female', 'Paris'), 
    ('Gabriel Novak', 'Male', 'New York'), 
    ('Hannah Abbott', 'Female', 'London'), 
    ('Ian Wright', 'Male', 'London'), 
    ('Jasmine Patel', 'Female', 'Melbourne')
]
cursor.executemany("INSERT INTO Customers (name, gender, city) VALUES (?, ?, ?)", customers)

# 3. Insert 20 Products
categories = ['Electronics', 'Home Office', 'Apparel']
product_data = [
    ('Mechanical Keyboard', 120.0, 'Electronics'), ('Gaming Mouse', 60.0, 'Electronics'),
    ('32-inch Monitor', 350.0, 'Electronics'), ('USB-C Hub', 45.0, 'Electronics'),
    ('Webcam 4K', 95.0, 'Electronics'), ('Standing Desk', 450.0, 'Home Office'),
    ('Ergonomic Chair', 299.0, 'Home Office'), ('Desk Mat', 25.0, 'Home Office'),
    ('LED Desk Lamp', 35.0, 'Home Office'), ('Notebook', 12.0, 'Home Office'),
    ('Cotton T-Shirt', 20.0, 'Apparel'), ('Hoodie', 55.0, 'Apparel'),
    ('Canvas Tote', 15.0, 'Apparel'), ('Baseball Cap', 22.0, 'Apparel'),
    ('Wool Socks', 12.0, 'Apparel'), ('Wireless Earbuds', 150.0, 'Electronics'),
    ('External SSD', 110.0, 'Electronics'), ('Power Bank', 40.0, 'Electronics'),
    ('Coffee Mug', 18.0, 'Home Office'), ('Water Bottle', 25.0, 'Home Office')
]
cursor.executemany("INSERT INTO Products (name, price, category) VALUES (?, ?, ?)", product_data)

# 4. Insert 30 Orders & 50 Items
for i in range(1, 31):
    cust_id = random.randint(1, 10)
    order_date = (datetime.now() - timedelta(days=random.randint(0, 60))).strftime('%Y-%m-%d')
    cursor.execute("INSERT INTO Orders (customer_id, order_date) VALUES (?, ?)", (cust_id, order_date))
    order_id = cursor.lastrowid
    
    # Add 1-3 items per order
    for _ in range(random.randint(1, 3)):
        prod_id = random.randint(1, 20)
        qty = random.randint(1, 2)
        cursor.execute("INSERT INTO Order_Items (order_id, product_id, quantity) VALUES (?, ?, ?)", (order_id, prod_id, qty))

conn.commit()
conn.close()
print("E-commerce DB populated")