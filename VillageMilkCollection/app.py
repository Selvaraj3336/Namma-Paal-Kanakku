from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = "milk_secret_key"


def get_db():
    return sqlite3.connect("milk.db")


def login_required():
    return "user_id" in session


# ── Root ─────────────────────────────────────────────────────
@app.route("/")
def home():
    return redirect("/login")


# ── Register ─────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        phone    = request.form["phone"]
        password = request.form["password"]

        conn   = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (phone, password) VALUES (?, ?)",
                (phone, password)
            )
            conn.commit()
            conn.close()
            return redirect("/login")
        except Exception:
            conn.close()
            return render_template("register.html", error="Phone number already registered.")

    return render_template("register.html")


# ── Login ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone    = request.form["phone"]
        password = request.form["password"]

        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE phone = ? AND password = ?",
            (phone, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["phone"]   = user[1]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid phone number or password.")

    return render_template("login.html")


# ── Logout ────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── Dashboard ─────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()

    # Total Customers
    cursor.execute(
        "SELECT COUNT(*) FROM customers WHERE user_id=?",
        (session["user_id"],)
    )
    total_customers = cursor.fetchone()[0]

    # Total Milk
    cursor.execute(
        "SELECT SUM(litre) FROM milk_entries WHERE user_id=?",
        (session["user_id"],)
    )
    result = cursor.fetchone()
    total_milk = result[0] if result[0] is not None else 0

    # Total Revenue
    cursor.execute("""
        SELECT SUM(milk_entries.litre * customers.rate)
        FROM milk_entries
        JOIN customers ON milk_entries.customer_id = customers.id
        WHERE milk_entries.user_id = ?
    """, (session["user_id"],))
    result = cursor.fetchone()
    total_revenue = result[0] if result[0] is not None else 0

    conn.close()

    return render_template(
        "dashboard.html",
        total_customers=total_customers,
        total_milk=total_milk,
        total_revenue=total_revenue
    )


# ── Customers ─────────────────────────────────────────────────
@app.route("/customers")
def customers():
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM customers WHERE user_id=?",
        (session["user_id"],)
    )
    data = cursor.fetchall()
    conn.close()

    return render_template("customers.html", customers=data)


# ── Add Customer ──────────────────────────────────────────────
@app.route("/add_customer", methods=["GET", "POST"])
def add_customer():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        name    = request.form["name"]
        mobile  = request.form["mobile"]
        address = request.form["address"]
        rate    = request.form["rate"]

        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO customers (user_id, name, mobile, address, rate)
               VALUES (?, ?, ?, ?, ?)""",
            (session["user_id"], name, mobile, address, rate)
        )
        conn.commit()
        conn.close()
        return redirect("/customers")

    return render_template("add_customer.html")


# ── Edit Customer ─────────────────────────────────────────────
@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name    = request.form["name"]
        mobile  = request.form["mobile"]
        address = request.form["address"]
        rate    = request.form["rate"]

        cursor.execute("""
            UPDATE customers
            SET name=?, mobile=?, address=?, rate=?
            WHERE id=? AND user_id=?
        """, (name, mobile, address, rate, id, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect("/customers")

    # GET — fetch existing data
    cursor.execute(
        "SELECT * FROM customers WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )
    customer = cursor.fetchone()
    conn.close()

    return render_template("edit_customer.html", customer=customer)


# ── Delete Customer ───────────────────────────────────────────
@app.route("/delete_customer/<int:id>")
def delete_customer(id):
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM customers WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/customers")


# ── Milk Entry ────────────────────────────────────────────────
@app.route("/milk_entry", methods=["GET", "POST"])
def milk_entry():
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        customer_id  = request.form["customer_id"]
        entry_date   = request.form["entry_date"]
        session_name = request.form["session"]
        litre        = float(request.form["litre"])

        cursor.execute("""
            INSERT INTO milk_entries (user_id, customer_id, entry_date, session, litre)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], customer_id, entry_date, session_name, litre))
        conn.commit()
        conn.close()
        return redirect("/entries")

    # GET — include rate for live amount preview
    cursor.execute(
        "SELECT id, name, rate FROM customers WHERE user_id=?",
        (session["user_id"],)
    )
    customers = cursor.fetchall()
    conn.close()

    return render_template("milk_entry.html", customers=customers)


# ── Entries (Daily Records) ───────────────────────────────────
@app.route("/entries")
def entries():
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            milk_entries.id,
            customers.name,
            milk_entries.entry_date,
            milk_entries.session,
            milk_entries.litre
        FROM milk_entries
        JOIN customers ON milk_entries.customer_id = customers.id
        WHERE milk_entries.user_id = ?
        ORDER BY milk_entries.entry_date DESC, milk_entries.id DESC
    """, (session["user_id"],))
    data = cursor.fetchall()
    conn.close()

    return render_template("entries.html", entries=data)


# ── WhatsApp ──────────────────────────────────────────────────
@app.route("/send_whatsapp/<int:id>")
def send_whatsapp(id):
    if not login_required():
        return redirect("/login")

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT customers.name, customers.mobile,
               milk_entries.entry_date, milk_entries.session, milk_entries.litre
        FROM milk_entries
        JOIN customers ON milk_entries.customer_id = customers.id
        WHERE milk_entries.id = ?
    """, (id,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return redirect("/entries")

    name, mobile, date, session_name, litre = data

    message = (
        f"Hello {name}\n\n"
        f"Date: {date}\n"
        f"Session: {session_name}\n"
        f"Milk Collected: {litre} Litre\n\n"
        f"Thank You"
    )
    whatsapp_url = f"https://wa.me/91{mobile}?text={quote(message)}"
    return redirect(whatsapp_url)


# ── Monthly Report ────────────────────────────────────────────
@app.route("/monthly_report", methods=["GET", "POST"])
def monthly_report():
    if not login_required():
        return redirect("/login")

    report         = []
    selected_month = ""
    selected_year  = ""

    if request.method == "POST":
        selected_month = request.form["month"]
        selected_year  = request.form["year"]

        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                customers.name,
                customers.mobile,
                SUM(CASE WHEN milk_entries.session='Morning' THEN milk_entries.litre ELSE 0 END) AS morning_total,
                SUM(CASE WHEN milk_entries.session='Evening' THEN milk_entries.litre ELSE 0 END) AS evening_total,
                SUM(milk_entries.litre) AS total_litre,
                customers.rate
            FROM milk_entries
            JOIN customers ON milk_entries.customer_id = customers.id
            WHERE milk_entries.user_id = ?
              AND strftime('%m', milk_entries.entry_date) = ?
              AND strftime('%Y', milk_entries.entry_date) = ?
            GROUP BY customers.id
        """, (session["user_id"], selected_month, selected_year))
        report = cursor.fetchall()
        conn.close()

    return render_template(
        "monthly_report.html",
        report=report,
        selected_month=selected_month,
        selected_year=selected_year
    )


if __name__ == "__main__":
    app.run(debug=True)
