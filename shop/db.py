import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")

def get_db_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS payments")
    cursor.execute("DROP TABLE IF EXISTS refunds")
    cursor.execute("DROP TABLE IF EXISTS address_updates")
    
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            item_name TEXT NOT NULL,
            price_paid REAL NOT NULL,
            order_date TEXT NOT NULL,
            delivery_date TEXT,
            status TEXT NOT NULL,
            shipping_address TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            payment_reference TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            payment_id INTEGER,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE address_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            old_address TEXT NOT NULL,
            new_address TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
