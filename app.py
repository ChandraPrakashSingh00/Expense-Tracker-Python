import os
import re
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_category_totals,
    get_db,
    get_expense_totals,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# SQLite's datetime('now') is UTC; Spendly users are in India
IST_OFFSET = timedelta(hours=5, minutes=30)

with app.app_context():
    init_db()
    seed_db()


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = get_user_by_id(user_id) if user_id is not None else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ------------------------------------------------------------------ #
# Template filters                                                    #
# ------------------------------------------------------------------ #

@app.template_filter("inr")
def format_inr(amount):
    # Indian digit grouping: 1234567.5 -> ₹12,34,567.50
    rupees, paise = f"{amount:.2f}".split(".")
    if len(rupees) > 3:
        head, tail = rupees[:-3], rupees[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        groups.insert(0, head)
        rupees = ",".join(groups) + "," + tail
    return f"₹{rupees}.{paise}"


@app.template_filter("date_label")
def format_date(value):
    # Accepts a date or a "YYYY-MM-DD..." string -> "5 Sep 2026"
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    return f"{value.day} {value:%b %Y}"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    duplicate_error = "An account with this email already exists."
    error = None
    if not (name and email and password):
        error = "Please fill in all fields."
    elif not EMAIL_RE.fullmatch(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif get_user_by_email(email):
        error = duplicate_error
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = duplicate_error

    if error:
        return render_template("register.html", error=error, name=name, email=email)

    flash("Account created. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("profile"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not (email and password):
        return render_template("login.html", error="Please fill in all fields.", email=email)

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session.clear()
    session["user_id"] = user["id"]
    flash(f"Welcome back, {user['name'].split()[0]}!", "success")
    return redirect(url_for("profile"))


@app.route("/terms-and-conditions")
def terms():
    return render_template("terms.html")


@app.route("/privacy-policy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():
    user = g.user
    name_parts = user["name"].split()
    initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper()
    joined = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S") + IST_OFFSET

    today = date.today()
    month_start = today.replace(day=1)
    next_month_start = (month_start + timedelta(days=32)).replace(day=1)

    return render_template(
        "profile.html",
        initials=initials,
        member_since=joined.date(),
        month_label=f"{today:%B %Y}",
        all_time=get_expense_totals(user["id"]),
        this_month=get_expense_totals(
            user["id"], month_start.isoformat(), next_month_start.isoformat()
        ),
        categories=get_category_totals(user["id"]),
        recent=get_recent_expenses(user["id"]),
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
