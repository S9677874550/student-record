# routes/students.py
# Student CRUD API with full backend validation.
# Every student row is tied to the logged-in user (user_id), so each
# user only ever sees / edits / deletes the students they themselves added.
import re
from flask import Blueprint, request, jsonify, session

from database import get_db

students_bp = Blueprint("students", __name__, url_prefix="/api/students")

# ---------------- validation patterns ----------------
ROLL_RE = re.compile(r"^[0-9]+$")
NAME_RE = re.compile(r"^[A-Za-z ]+$")
DEPT_RE = re.compile(r"^[A-Za-z& ]+$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@gmail\.com$")
PHONE_RE = re.compile(r"^[0-9]{10}$")


def validate_student(data):
    """Returns an error message string, or None if valid."""
    roll_number = str(data.get("roll_number", "")).strip()
    name = str(data.get("name", "")).strip()
    department = str(data.get("department", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()

    if not roll_number or not ROLL_RE.fullmatch(roll_number):
        return "Roll Number must contain only numbers"
    if not name or not NAME_RE.fullmatch(name):
        return "Name must contain only letters"
    if not department or not DEPT_RE.fullmatch(department):
        return "Department must contain only letters (and '&' if needed)"
    if not email or not EMAIL_RE.fullmatch(email):
        return "Enter a valid @gmail.com address"
    if not phone or not PHONE_RE.fullmatch(phone):
        return "Phone number must be exactly 10 digits"
    return None


# ---------------- GET all students (only the current user's) ----------------
@students_bp.route("", methods=["GET"])
def get_students():
    user_id = session["user_id"]
    db = get_db()
    rows = db.execute(
        "SELECT * FROM students WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    db.close()
    return jsonify([dict(row) for row in rows])


# ---------------- ADD a student (tagged to the current user) ----------------
@students_bp.route("", methods=["POST"])
def add_student():
    user_id = session["user_id"]
    data = request.get_json(force=True, silent=True) or {}

    error = validate_student(data)
    if error:
        return jsonify({"error": error}), 400

    db = get_db()
    existing = db.execute(
        "SELECT id FROM students WHERE roll_number = ? AND user_id = ?",
        (str(data["roll_number"]).strip(), user_id),
    ).fetchone()

    if existing:
        db.close()
        return jsonify({"error": "Roll Number already exists"}), 400

    db.execute(
        """INSERT INTO students (user_id, roll_number, name, department, email, phone)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            str(data["roll_number"]).strip(),
            data["name"].strip(),
            data["department"].strip(),
            data["email"].strip(),
            data["phone"].strip(),
        ),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Student added successfully"}), 201


# ---------------- GET a single student (for pre-filling the edit form) ----------------
@students_bp.route("/<int:student_id>", methods=["GET"])
def get_student(student_id):
    user_id = session["user_id"]
    db = get_db()
    row = db.execute(
        "SELECT * FROM students WHERE id = ? AND user_id = ?", (student_id, user_id)
    ).fetchone()
    db.close()

    if not row:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(dict(row))


# ---------------- UPDATE a student (only if it belongs to the current user) ----------------
@students_bp.route("/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    user_id = session["user_id"]
    data = request.get_json(force=True, silent=True) or {}

    error = validate_student(data)
    if error:
        return jsonify({"error": error}), 400

    db = get_db()

    # make sure this student belongs to the logged-in user
    owned = db.execute(
        "SELECT id FROM students WHERE id = ? AND user_id = ?", (student_id, user_id)
    ).fetchone()
    if not owned:
        db.close()
        return jsonify({"error": "Student not found"}), 404

    # roll number shouldn't clash with another one of THIS user's students
    existing = db.execute(
        "SELECT id FROM students WHERE roll_number = ? AND user_id = ? AND id != ?",
        (str(data["roll_number"]).strip(), user_id, student_id),
    ).fetchone()
    if existing:
        db.close()
        return jsonify({"error": "Roll Number already exists"}), 400

    db.execute(
        """UPDATE students
           SET roll_number = ?, name = ?, department = ?, email = ?, phone = ?
           WHERE id = ? AND user_id = ?""",
        (
            str(data["roll_number"]).strip(),
            data["name"].strip(),
            data["department"].strip(),
            data["email"].strip(),
            data["phone"].strip(),
            student_id,
            user_id,
        ),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Student updated successfully"})


# ---------------- DELETE a student (only if it belongs to the current user) ----------------
@students_bp.route("/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    user_id = session["user_id"]
    db = get_db()
    db.execute(
        "DELETE FROM students WHERE id = ? AND user_id = ?", (student_id, user_id)
    )
    db.commit()
    db.close()
    return jsonify({"message": "Student deleted successfully"})
