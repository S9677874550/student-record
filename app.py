# app.py
# Entry point. Run with: python app.py
# Serves the frontend template + static files, and mounts the Student API.
import re
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import init_db, get_db
from routes.students import students_bp
from sms import send_otp_sms

app = Flask(__name__)
app.secret_key = "student_registry_secret_key_2026"

# ---------------- validation helpers ----------------
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
PHONE_RE = re.compile(r"^[0-9]{10}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@gmail\.com$")


# ---------------- auth guard ----------------
@app.before_request
def require_login():
    # routes that don't need an active session
    allowed_routes = ("login", "register", "forgot_password", "verify_otp", "reset_password", "static")
    if request.endpoint is None:
        return
    if request.endpoint in allowed_routes or request.endpoint.startswith("static"):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login"))


# ---------------- login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)


# ---------------- register (create new user) ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ---- validation ----
        if not USERNAME_RE.match(username):
            error = "Username must be 3-20 characters (letters, numbers, underscore only)"
        elif not PHONE_RE.match(phone):
            error = "Phone number must contain exactly 10 digits"
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid @gmail.com address"
        elif len(password) < 6:
            error = "Password must be at least 6 characters"
        elif password != confirm_password:
            error = "Password and Confirm Password do not match"

        if not error:
            db = get_db()
            existing_username = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            existing_phone = db.execute(
                "SELECT id FROM users WHERE phone = ?", (phone,)
            ).fetchone()

            if existing_username:
                error = "Username already exists"
            elif existing_phone:
                error = "Phone number already registered"

            if not error:
                hashed_password = generate_password_hash(password)
                db.execute(
                    "INSERT INTO users (username, phone, email, password) VALUES (?, ?, ?, ?)",
                    (username, phone, email, hashed_password),
                )
                db.commit()
                db.close()
                flash("Account created successfully. Please login.")
                return redirect(url_for("login"))
            db.close()

    return render_template("register.html", error=error)


# ---------------- forgot password : STEP 1 - request OTP ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()

        if not PHONE_RE.match(phone):
            error = "Enter a valid 10-digit phone number"
        else:
            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE phone = ?", (phone,)
            ).fetchone()

            if not user:
                error = "Phone number not registered"
            else:
                otp = f"{random.randint(0, 999999):06d}"
                otp_hash = generate_password_hash(otp)
                expires_at = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

                db.execute(
                    "UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE phone = ?",
                    (otp_hash, expires_at, phone),
                )
                db.commit()
                send_otp_sms(phone, otp)

                # remember which phone is going through reset, for the next 2 steps
                session["reset_phone"] = phone
                session["otp_verified"] = False

                flash("An OTP has been sent to your phone number.")
                db.close()
                return redirect(url_for("verify_otp"))
            db.close()

    return render_template("forgot_password.html", error=error)


# ---------------- forgot password : STEP 2 - verify OTP ----------------
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    phone = session.get("reset_phone")
    if not phone:
        return redirect(url_for("forgot_password"))

    error = None
    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()

        if not user or not user["otp_code"]:
            error = "No OTP request found. Please request a new OTP."
        elif datetime.utcnow() > datetime.fromisoformat(user["otp_expires_at"]):
            error = "OTP expired. Please request a new one."
        elif not check_password_hash(user["otp_code"], entered_otp):
            error = "Invalid OTP. Please try again."
        else:
            # OTP correct - clear it so it can't be reused, mark verified
            db.execute(
                "UPDATE users SET otp_code = NULL, otp_expires_at = NULL WHERE phone = ?",
                (phone,),
            )
            db.commit()
            db.close()
            session["otp_verified"] = True
            return redirect(url_for("reset_password"))
        db.close()

    return render_template("verify_otp.html", error=error, phone=phone)


# ---------------- forgot password : STEP 3 - set new password ----------------
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    phone = session.get("reset_phone")
    if not phone or not session.get("otp_verified"):
        return redirect(url_for("forgot_password"))

    error = None
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(new_password) < 6:
            error = "New password must be at least 6 characters"
        elif new_password != confirm_password:
            error = "Password and Confirm Password do not match"
        else:
            hashed_password = generate_password_hash(new_password)
            db = get_db()
            db.execute(
                "UPDATE users SET password = ? WHERE phone = ?",
                (hashed_password, phone),
            )
            db.commit()
            db.close()

            # clear the reset session
            session.pop("reset_phone", None)
            session.pop("otp_verified", None)

            flash("Password changed successfully. Please login again.")
            return redirect(url_for("login"))

    return render_template("reset_password.html", error=error)


# ---------------- logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- Register the API blueprint ----------------
app.register_blueprint(students_bp)


@app.route("/")
def index():
    return render_template("index.html", username=session.get("username"))


if __name__ == "__main__":
    init_db()  # creates students.db + tables (users, students) on first run
    print("Student Registry running at http://localhost:5000")
    app.run(debug=True, port=5000)
