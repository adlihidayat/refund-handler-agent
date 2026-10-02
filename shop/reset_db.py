import os
from shop.db import get_db_connection, init_db

def seed_data(db_path=None):
    if db_path:
        init_db(db_path)
        conn = get_db_connection(db_path)
    else:
        init_db()
        conn = get_db_connection()
        
    cursor = conn.cursor()

    orders_data = [
        # (id, customer_name, customer_email, item_name, price_paid, order_date, delivery_date, status, shipping_address)
        (1042, "Alice Smith", "alice@example.com", "Headphones", 60.00, "2026-09-15", "2026-09-20", "Delivered", "101 Main St, Anytown"),
        (1043, "Bob Johnson", "bob@example.com", "Smart Watch", 100.00, "2026-09-16", "2026-09-22", "Delivered", "202 Oak St, Anytown"),
        (1077, "Charlie Brown", "charlie@example.com", "Monitor Stand", 240.00, "2026-09-18", "2026-09-22", "Delivered", "303 Pine St, Anytown"),
        (1080, "Diana Prince", "diana@example.com", "Mechanical Keyboard", 45.00, "2026-08-10", "2026-08-15", "Delivered", "404 Elm St, Anytown"),
        (1085, "Eve Polastri", "eve@example.com", "Wireless Mouse", 30.00, "2026-09-22", "2026-09-27", "Delivered", "505 Maple St, Anytown"),
        (1090, "Frank Castle", "frank@example.com", "Ergonomic Monitor", 200.00, "2026-09-20", "2026-09-24", "Delivered", "606 Cedar St, Anytown"),
        (1095, "Grace Hopper", "grace@example.com", "Desk Lamp", 50.00, "2026-09-21", "2026-09-25", "Delivered", "707 Birch St, Anytown"),
        (1100, "Hank Pym", "hank@example.com", "USB-C Cable", 60.00, "2026-09-25", "2026-09-28", "Delivered", "808 Walnut St, Anytown"),
        (1105, "Ivy Pepper", "ivy@example.com", "USB Hub", 75.00, "2026-09-22", "2026-09-26", "Delivered", "909 Spruce St, Anytown"),
        (1110, "Jack Ryan", "jack@example.com", "Portable Speaker", 80.00, "2026-09-23", "2026-09-27", "Delivered", "1010 Ash St, Anytown"),
        (1120, "Karen Page", "karen@example.com", "Ergonomic Chair", 150.00, "2026-09-30", None, "Processing", "123 Old St, Cityville")
    ]

    for order in orders_data:
        cursor.execute("""
            INSERT INTO orders (id, customer_name, customer_email, item_name, price_paid, order_date, delivery_date, status, shipping_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, order)

    payments_data = [
        # (order_id, payment_reference, amount, payment_date)
        (1042, "PAY-1042-1", 60.00, "2026-09-15"),
        # Double charge for 1043: 2 payments of $50 each
        (1043, "PAY-1043-1", 50.00, "2026-09-16"),
        (1043, "PAY-1043-2", 50.00, "2026-09-16"),
        (1077, "PAY-1077-1", 240.00, "2026-09-18"),
        (1080, "PAY-1080-1", 45.00, "2026-08-10"),
        (1085, "PAY-1085-1", 30.00, "2026-09-22"),
        (1090, "PAY-1090-1", 200.00, "2026-09-20"),
        (1095, "PAY-1095-1", 50.00, "2026-09-21"),
        (1100, "PAY-1100-1", 60.00, "2026-09-25"),
        (1105, "PAY-1105-1", 75.00, "2026-09-22"),
        (1110, "PAY-1110-1", 80.00, "2026-09-23"),
        (1120, "PAY-1120-1", 150.00, "2026-09-30")
    ]

    for pay in payments_data:
        cursor.execute("""
            INSERT INTO payments (order_id, payment_reference, amount, payment_date)
            VALUES (?, ?, ?, ?)
        """, pay)

    # Past refund for Eve (1085): $30 already refunded
    cursor.execute("""
        INSERT INTO refunds (order_id, payment_id, amount, reason, created_at)
        VALUES (1085, 6, 30.00, 'Previous damaged item claim', '2026-09-28 10:00:00')
    """)

    conn.commit()
    conn.close()
    print("Database reset and seed data loaded.")

if __name__ == "__main__":
    seed_data()
