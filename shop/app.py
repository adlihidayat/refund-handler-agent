import os
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from shop.db import get_db_connection

app = Flask(__name__)
app.secret_key = "shop_backoffice_secret_key_demo"

# Base HTML Template
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Shop Back Office</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f4f6f9; color: #333; }
        header { background: #1e293b; color: #fff; padding: 15px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
        header a { color: #38bdf8; text-decoration: none; margin-left: 15px; font-weight: bold; }
        .container { background: #fff; padding: 20px; margin-top: 20px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; }
        input[type="text"], input[type="number"], input[type="password"] { padding: 8px; width: 300px; border: 1px solid #cbd5e1; border-radius: 4px; }
        button, input[type="submit"] { background: #2563eb; color: #fff; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #1d4ed8; }
        .alert { padding: 10px; border-radius: 4px; margin-bottom: 15px; }
        .alert-error { background: #fee2e2; color: #991b1b; }
        .alert-success { background: #dcfce7; color: #166534; }
        .card { border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <header>
        <div><strong>Fake Shop Back Office</strong></div>
        <div>
            {% if session.get('user') %}
                <span>Logged in as <strong>{{ session['user'] }}</strong></span>
                <a href="{{ url_for('orders_list') }}">Orders</a>
                <a href="{{ url_for('refunds_list') }}">Refunds Log</a>
                <a href="{{ url_for('logout') }}">Logout</a>
            {% endif %}
        </div>
    </header>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<h2>Admin Login</h2>
<form method="POST" action="{{ url_for('login') }}" id="login-form">
    <p>
        <label>Username:</label><br>
        <input type="text" name="username" id="username" required value="admin">
    </p>
    <p>
        <label>Password:</label><br>
        <input type="password" name="password" id="password" required value="password123">
    </p>
    <p>
        <input type="submit" id="submit-login" value="Login">
    </p>
</form>
""")

ORDERS_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<h2>Customer Orders</h2>
<form method="GET" action="{{ url_for('orders_list') }}" id="search-form">
    <input type="text" name="q" id="search-input" placeholder="Search by order ID, name, or email..." value="{{ query }}">
    <button type="submit" id="search-button">Search</button>
</form>
<table>
    <thead>
        <tr>
            <th>Order ID</th>
            <th>Customer Name</th>
            <th>Email</th>
            <th>Item</th>
            <th>Paid</th>
            <th>Status</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
        {% for order in orders %}
        <tr>
            <td>#{{ order.id }}</td>
            <td>{{ order.customer_name }}</td>
            <td>{{ order.customer_email }}</td>
            <td>{{ order.item_name }}</td>
            <td>${{ '%.2f'|format(order.price_paid) }}</td>
            <td>{{ order.status }}</td>
            <td><a href="{{ url_for('order_detail', order_id=order.id) }}" id="view-order-{{ order.id }}">View Details</a></td>
        </tr>
        {% else %}
        <tr><td colspan="7">No orders found.</td></tr>
        {% endfor %}
    </tbody>
</table>
""")

ORDER_DETAIL_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<h2>Order Details #{{ order.id }}</h2>
<div class="card">
    <p><strong>Customer:</strong> {{ order.customer_name }} ({{ order.customer_email }})</p>
    <p><strong>Item:</strong> {{ order.item_name }}</p>
    <p><strong>Price Paid:</strong> ${{ '%.2f'|format(order.price_paid) }}</p>
    <p><strong>Order Date:</strong> {{ order.order_date }}</p>
    <p><strong>Delivery Date:</strong> {{ order.delivery_date or 'Not Delivered' }}</p>
    <p><strong>Order Status:</strong> {{ order.status }}</p>
    <p><strong>Shipping Address:</strong> <span id="current-address">{{ order.shipping_address }}</span></p>
</div>

<h3>Payments Record</h3>
<table>
    <thead>
        <tr>
            <th>Payment ID</th>
            <th>Reference</th>
            <th>Amount</th>
            <th>Payment Date</th>
        </tr>
    </thead>
    <tbody>
        {% for payment in payments %}
        <tr>
            <td>#{{ payment.id }}</td>
            <td>{{ payment.payment_reference }}</td>
            <td>${{ '%.2f'|format(payment.amount) }}</td>
            <td>{{ payment.payment_date }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<h3>Past Refunds</h3>
<table>
    <thead>
        <tr>
            <th>Refund ID</th>
            <th>Amount</th>
            <th>Reason</th>
            <th>Date</th>
        </tr>
    </thead>
    <tbody>
        {% for refund in refunds %}
        <tr>
            <td>#{{ refund.id }}</td>
            <td>${{ '%.2f'|format(refund.amount) }}</td>
            <td>{{ refund.reason }}</td>
            <td>{{ refund.created_at }}</td>
        </tr>
        {% else %}
        <tr><td colspan="4">No past refunds for this order.</td></tr>
        {% endfor %}
    </tbody>
</table>

<h3>Issue Refund</h3>
<div class="card">
    <form method="POST" action="{{ url_for('process_refund', order_id=order.id) }}" id="refund-form">
        <p>
            <label>Refund Amount ($):</label><br>
            <input type="number" step="0.01" name="amount" id="refund-amount" required placeholder="0.00">
        </p>
        <p>
            <label>Reason for Refund:</label><br>
            <input type="text" name="reason" id="refund-reason" required placeholder="Damaged item, double charge, etc.">
        </p>
        <p>
            <button type="submit" id="submit-refund-button">Submit Refund</button>
        </p>
    </form>
</div>

<h3>Update Shipping Address</h3>
<div class="card">
    <form method="POST" action="{{ url_for('update_address', order_id=order.id) }}" id="address-form">
        <p>
            <label>New Shipping Address:</label><br>
            <input type="text" name="new_address" id="new-address-input" required placeholder="123 New Street...">
        </p>
        <p>
            <button type="submit" id="submit-address-button">Update Address</button>
        </p>
    </form>
</div>
""")

REFUNDS_LOG_TEMPLATE = BASE_TEMPLATE.replace("{% block content %}{% endblock %}", """
<h2>Processed Refunds Log</h2>
<table>
    <thead>
        <tr>
            <th>Refund ID</th>
            <th>Order ID</th>
            <th>Amount</th>
            <th>Reason</th>
            <th>Processed Date</th>
        </tr>
    </thead>
    <tbody>
        {% for refund in refunds %}
        <tr>
            <td>#{{ refund.id }}</td>
            <td><a href="{{ url_for('order_detail', order_id=refund.order_id) }}">Order #{{ refund.order_id }}</a></td>
            <td>${{ '%.2f'|format(refund.amount) }}</td>
            <td>{{ refund.reason }}</td>
            <td>{{ refund.created_at }}</td>
        </tr>
        {% else %}
        <tr><td colspan="5">No refunds processed yet.</td></tr>
        {% endfor %}
    </tbody>
</table>
""")

def login_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == 'admin' and pwd == 'password123':
            session['user'] = user
            flash("Logged in successfully.", "success")
            return redirect(url_for('orders_list'))
        else:
            flash("Invalid credentials.", "error")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for('login'))

@app.route('/expire_session')
def expire_session():
    session.clear()
    return "Session expired", 200

@app.route('/')
@app.route('/orders')
@login_required
def orders_list():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    if query:
        orders = conn.execute("""
            SELECT * FROM orders 
            WHERE CAST(id AS TEXT) LIKE ? OR customer_name LIKE ? OR customer_email LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
    else:
        orders = conn.execute("SELECT * FROM orders ORDER BY id ASC").fetchall()
    conn.close()
    return render_template_string(ORDERS_TEMPLATE, orders=orders, query=query)

@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "error")
        return redirect(url_for('orders_list'))
        
    payments = conn.execute("SELECT * FROM payments WHERE order_id = ?", (order_id,)).fetchall()
    refunds = conn.execute("SELECT * FROM refunds WHERE order_id = ? ORDER BY id DESC", (order_id,)).fetchall()
    conn.close()
    return render_template_string(ORDER_DETAIL_TEMPLATE, order=order, payments=payments, refunds=refunds)

@app.route('/orders/<int:order_id>/refund', methods=['POST'])
@login_required
def process_refund(order_id):
    amount_str = request.form.get('amount')
    reason = request.form.get('reason', '').strip()
    
    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        flash("Invalid refund amount.", "error")
        return redirect(url_for('order_detail', order_id=order_id))
        
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "error")
        return redirect(url_for('orders_list'))

    # Calculate total payments & previous refunds
    total_paid_row = conn.execute("SELECT SUM(amount) as total FROM payments WHERE order_id = ?", (order_id,)).fetchone()
    total_paid = total_paid_row['total'] or 0.0

    total_refunded_row = conn.execute("SELECT SUM(amount) as total FROM refunds WHERE order_id = ?", (order_id,)).fetchone()
    total_refunded = total_refunded_row['total'] or 0.0

    max_allowed = total_paid - total_refunded

    if amount <= 0:
        conn.close()
        flash("Refund amount must be greater than $0.", "error")
        return redirect(url_for('order_detail', order_id=order_id))

    if amount > max_allowed + 0.001:  # small floating point tolerance
        conn.close()
        flash(f"Refund denied: Amount ${amount:.2f} exceeds maximum remaining refundable amount (${max_allowed:.2f}).", "error")
        return redirect(url_for('order_detail', order_id=order_id))

    import datetime
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO refunds (order_id, payment_id, amount, reason, created_at)
        VALUES (?, NULL, ?, ?, ?)
    """, (order_id, amount, reason, created_at))
    conn.commit()
    conn.close()

    flash(f"Successfully processed refund of ${amount:.2f} for Order #{order_id}.", "success")
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/orders/<int:order_id>/address', methods=['POST'])
@login_required
def update_address(order_id):
    new_address = request.form.get('new_address', '').strip()
    if not new_address:
        flash("Address cannot be empty.", "error")
        return redirect(url_for('order_detail', order_id=order_id))
        
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Order not found.", "error")
        return redirect(url_for('orders_list'))

    old_address = order['shipping_address']
    conn.execute("UPDATE orders SET shipping_address = ? WHERE id = ?", (new_address, order_id))
    
    import datetime
    updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO address_updates (order_id, old_address, new_address, updated_at)
        VALUES (?, ?, ?, ?)
    """, (order_id, old_address, new_address, updated_at))
    
    conn.commit()
    conn.close()

    flash(f"Successfully updated shipping address for Order #{order_id} to '{new_address}'.", "success")
    return redirect(url_for('order_detail', order_id=order_id))

@app.route('/refunds')
@login_required
def refunds_list():
    conn = get_db_connection()
    refunds = conn.execute("SELECT * FROM refunds ORDER BY id DESC").fetchall()
    conn.close()
    return render_template_string(REFUNDS_LOG_TEMPLATE, refunds=refunds)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
