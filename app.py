import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, abort, redirect, render_template, request, url_for

app = Flask(__name__)

PRODUCTS = {
    "Goat Meat": 1000, "Beef Ribs": 500, "Beef Side": 680,
    "Fresh Chicken": 750, "Premium Pork": 650, "Farm Sausages": 600,
}
PORTIONS = {"0.5": "500 g", "1": "1 kg", "2": "2 kg", "5": "5 kg"}
WHATSAPP_NUMBER = "254759924416"


def database_path():
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    return Path(app.instance_path) / "orders.db"


def get_database():
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_database() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL, email TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL, location TEXT NOT NULL,
                product TEXT NOT NULL, portion_kg REAL NOT NULL, portion_label TEXT NOT NULL,
                quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL, total_price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'New', created_at TEXT NOT NULL
            )
        """)
        columns = {column[1] for column in connection.execute("PRAGMA table_info(orders)")}
        if "email" not in columns:
            connection.execute("ALTER TABLE orders ADD COLUMN email TEXT NOT NULL DEFAULT ''")


initialize_database()


def product_from_query(value):
    normalized = (value or "").replace("-", " ").casefold().strip()
    return next((product for product in PRODUCTS if product.casefold() == normalized), "")


def require_admin(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        password = os.environ.get("ADMIN_PASSWORD")
        username = os.environ.get("ADMIN_USERNAME", "admin")
        credentials = request.authorization
        if not password:
            return Response("Set ADMIN_PASSWORD before opening the admin dashboard.", status=503)
        if not credentials or credentials.username != username or credentials.password != password:
            return Response("Admin login required.", status=401,
                            headers={"WWW-Authenticate": 'Basic realm="Blessy Admin"'})
        return view(*args, **kwargs)
    return wrapped_view


@app.get("/")
def home():
    return render_template("index.html")


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "GET":
        return render_template("order.html", products=PRODUCTS, portions=PORTIONS,
                               selected_product=product_from_query(request.args.get("product")),
                               form={}, error=None)

    form = request.form
    product, portion_value = form.get("product", ""), form.get("portion", "")
    customer_name, email, phone, location = (form.get("customer_name", "").strip(), form.get("email", "").strip(),
                                             form.get("phone", "").strip(), form.get("location", "").strip())
    try:
        quantity = int(form.get("quantity", "0"))
    except ValueError:
        quantity = 0

    error = None
    if product not in PRODUCTS:
        error = "Choose a product from the list."
    elif portion_value not in PORTIONS:
        error = "Choose a meat size."
    elif not customer_name or not email or not phone or not location:
        error = "Please enter your name, email, phone number, and delivery location."
    elif quantity < 1 or quantity > 100:
        error = "Quantity must be between 1 and 100."
    if error:
        return render_template("order.html", products=PRODUCTS, portions=PORTIONS,
                               selected_product=product, form=form, error=error), 400

    portion_kg, unit_price = float(portion_value), PRODUCTS[product]
    total_price = round(unit_price * portion_kg * quantity)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with get_database() as connection:
        cursor = connection.execute("""
            INSERT INTO orders (customer_name, email, phone, location, product, portion_kg, portion_label,
                                quantity, unit_price, total_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_name, email, phone, location, product, portion_kg, PORTIONS[portion_value],
              quantity, unit_price, total_price, created_at))
        order_id = cursor.lastrowid
    return redirect(url_for("order_confirmation", order_id=order_id))


@app.get("/order/<int:order_id>/confirmation")
def order_confirmation(order_id):
    with get_database() as connection:
        saved_order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if saved_order is None:
        abort(404)
    message = (f"New Blessy order #{saved_order['id']}%0A"
               f"Customer: {saved_order['customer_name']}%0A"
               f"Email: {saved_order['email']}%0A"
               f"Phone: {saved_order['phone']}%0A"
               f"Delivery: {saved_order['location']}%0A"
               f"Order: {saved_order['quantity']} × {saved_order['portion_label']} {saved_order['product']}%0A"
               f"Total: Ksh {saved_order['total_price']:,}")
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(message, safe='%')}"
    return render_template("confirmation.html", order=saved_order, whatsapp_url=whatsapp_url)


@app.get("/admin/orders")
@require_admin
def admin_orders():
    with get_database() as connection:
        orders = connection.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template("admin_orders.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True)
