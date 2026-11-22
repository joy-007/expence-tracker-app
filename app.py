import os
import secrets
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_db,
    get_user_by_id,
    init_db,
    seed_db,
    verify_user,
)

NAME_MAX = 100
EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 128

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return {"current_user": None}
    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
    return {"current_user": user}


@app.route("/")
def landing():
    return render_template("landing.html")


def _is_valid_email(email):
    if not email or len(email) > EMAIL_MAX:
        return False
    if any(ch.isspace() for ch in email) or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or "." not in domain:
        return False
    return not (domain.startswith(".") or domain.endswith("."))


def _validate_registration(name, email, password):
    """Return the first validation error message, or None if input is valid."""
    if not name:
        return "Name is required."
    if len(name) > NAME_MAX:
        return f"Name must be at most {NAME_MAX} characters."
    if not _is_valid_email(email):
        return "Please enter a valid email address."
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    return None


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("register.html")

    raw_name = request.form.get("name", "")
    raw_email = request.form.get("email", "")
    password = request.form.get("password", "")
    name = raw_name.strip()
    email = raw_email.strip().lower()

    error = _validate_registration(name, email, password)
    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError as exc:
            if "users.email" not in str(exc):
                raise
            error = "An account with that email already exists."

    if error:
        return (
            render_template(
                "register.html", error=error, name=raw_name, email=raw_email
            ),
            400,
        )
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("login.html")

    raw_email = request.form.get("email", "")
    password = request.form.get("password", "")
    email = raw_email.strip().lower()

    if not email or not password:
        error = "Email and password are required."
    else:
        user = verify_user(email, password)
        if user is not None:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("landing"))
        error = "Invalid email or password."

    return render_template("login.html", error=error, email=raw_email), 400


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
