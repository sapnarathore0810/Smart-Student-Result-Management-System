"""Smart Student Result Management System.

This Flask app stores student results in SQLite and provides:
- add/update/delete records
- search by roll number
- automatic total, percentage, grade, and pass/fail calculation

It is intentionally kept simple and beginner-friendly.
"""

import sqlite3
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "students.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "student-result-portal-secret-key"
app.config["DATABASE"] = str(DATABASE_PATH)


def get_db() -> sqlite3.Connection:
    """Return the current SQLite connection or create a new one."""

    if "db" not in g:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_: Exception | None) -> None:
    """Close the SQLite connection after each request."""

    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create the students table if it does not exist."""

    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL UNIQUE,
            subject1 INTEGER NOT NULL,
            subject2 INTEGER NOT NULL,
            subject3 INTEGER NOT NULL,
            total_marks INTEGER NOT NULL,
            percentage REAL NOT NULL,
            grade TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


with app.app_context():
    init_db()


def calculate_grade(percentage: float) -> str:
    """Return grade from percentage."""

    if percentage >= 75:
        return "A"
    if percentage >= 50:
        return "B"
    return "C"


def calculate_status(percentage: float) -> str:
    """Return Pass or Fail from percentage."""

    return "Pass" if percentage >= 40 else "Fail"


def parse_mark(value: str) -> int | None:
    """Convert submitted marks to integer if possible."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_student_form(form: dict[str, str]) -> tuple[list[str], dict[str, object]]:
    """Validate form input and return errors plus cleaned values."""

    errors: list[str] = []
    cleaned: dict[str, object] = {
        "student_name": form.get("student_name", "").strip(),
        "roll_number": form.get("roll_number", "").strip(),
        "subject1": parse_mark(form.get("subject1", "")),
        "subject2": parse_mark(form.get("subject2", "")),
        "subject3": parse_mark(form.get("subject3", "")),
    }

    if not cleaned["student_name"]:
        errors.append("Student name is required.")
    if not cleaned["roll_number"]:
        errors.append("Roll number is required.")

    for index, key in enumerate(("subject1", "subject2", "subject3"), start=1):
        value = cleaned[key]
        if value is None:
            errors.append(f"Subject {index} marks must be a number.")
        elif value < 0 or value > 100:
            errors.append(f"Subject {index} marks must be between 0 and 100.")

    if errors:
        return errors, cleaned

    subject1 = int(cleaned["subject1"])
    subject2 = int(cleaned["subject2"])
    subject3 = int(cleaned["subject3"])
    total_marks = subject1 + subject2 + subject3
    percentage = round((total_marks / 300) * 100, 2)

    cleaned.update(
        {
            "subject1": subject1,
            "subject2": subject2,
            "subject3": subject3,
            "total_marks": total_marks,
            "percentage": percentage,
            "grade": calculate_grade(percentage),
            "status": calculate_status(percentage),
        }
    )
    return errors, cleaned


def fetch_all_students() -> list[sqlite3.Row]:
    """Return all student rows."""

    db = get_db()
    cursor = db.execute("SELECT * FROM students ORDER BY id DESC")
    return cursor.fetchall()


def fetch_student_by_id(student_id: int) -> sqlite3.Row | None:
    """Return one student by ID."""

    db = get_db()
    cursor = db.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    return cursor.fetchone()


def fetch_student_by_roll(roll_number: str) -> sqlite3.Row | None:
    """Return one student by roll number."""

    db = get_db()
    cursor = db.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number,))
    return cursor.fetchone()


def blank_form_data() -> dict[str, object]:
    """Return default form values for the home page."""

    return {
        "student_name": "",
        "roll_number": "",
        "subject1": "",
        "subject2": "",
        "subject3": "",
        "total_marks": 0,
        "percentage": 0.0,
        "grade": "C",
        "status": "Fail",
    }


def render_home(
    *,
    form_data: dict[str, object] | None = None,
    editing_student_id: int | None = None,
    errors: list[str] | None = None,
) -> str:
    """Render the home page with current table data."""

    return render_template(
        "index.html",
        students=fetch_all_students(),
        form_data=form_data or blank_form_data(),
        editing_student_id=editing_student_id,
        errors=errors or [],
    )


@app.route("/")
def index() -> str:
    """Show the home page and load an edit form when requested."""

    edit_id = request.args.get("edit_id", type=int)
    if edit_id is not None:
        student = fetch_student_by_id(edit_id)
        if student is None:
            flash("Student record not found.", "error")
            return redirect(url_for("index"))

        form_data = {
            "student_name": student["student_name"],
            "roll_number": student["roll_number"],
            "subject1": student["subject1"],
            "subject2": student["subject2"],
            "subject3": student["subject3"],
            "total_marks": student["total_marks"],
            "percentage": student["percentage"],
            "grade": student["grade"],
            "status": student["status"],
        }
        return render_home(form_data=form_data, editing_student_id=student["id"])

    return render_home()


@app.route("/save", methods=["POST"])
def save_student() -> str:
    """Insert or update a student record."""

    student_id = request.form.get("student_id", type=int)
    form_values = {
        "student_name": request.form.get("student_name", "").strip(),
        "roll_number": request.form.get("roll_number", "").strip(),
        "subject1": request.form.get("subject1", "").strip(),
        "subject2": request.form.get("subject2", "").strip(),
        "subject3": request.form.get("subject3", "").strip(),
    }

    errors, cleaned = validate_student_form(form_values)
    if errors:
        return render_home(
            form_data={
                **form_values,
                "total_marks": 0,
                "percentage": 0.0,
                "grade": "C",
                "status": "Fail",
            },
            editing_student_id=student_id,
            errors=errors,
        )

    db = get_db()
    existing_roll = db.execute(
        "SELECT id FROM students WHERE roll_number = ?",
        (cleaned["roll_number"],),
    ).fetchone()

    if existing_roll is not None and (student_id is None or existing_roll["id"] != student_id):
        return render_home(
            form_data={
                **form_values,
                "total_marks": cleaned["total_marks"],
                "percentage": cleaned["percentage"],
                "grade": cleaned["grade"],
                "status": cleaned["status"],
            },
            editing_student_id=student_id,
            errors=["Roll number already exists. Please use a different roll number."],
        )

    if student_id is None:
        db.execute(
            """
            INSERT INTO students
            (student_name, roll_number, subject1, subject2, subject3, total_marks, percentage, grade, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cleaned["student_name"],
                cleaned["roll_number"],
                cleaned["subject1"],
                cleaned["subject2"],
                cleaned["subject3"],
                cleaned["total_marks"],
                cleaned["percentage"],
                cleaned["grade"],
                cleaned["status"],
            ),
        )
        db.commit()
        flash("Student record added successfully.", "success")
    else:
        db.execute(
            """
            UPDATE students
            SET student_name = ?,
                roll_number = ?,
                subject1 = ?,
                subject2 = ?,
                subject3 = ?,
                total_marks = ?,
                percentage = ?,
                grade = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                cleaned["student_name"],
                cleaned["roll_number"],
                cleaned["subject1"],
                cleaned["subject2"],
                cleaned["subject3"],
                cleaned["total_marks"],
                cleaned["percentage"],
                cleaned["grade"],
                cleaned["status"],
                student_id,
            ),
        )
        db.commit()
        flash("Student record updated successfully.", "success")

    return redirect(url_for("index"))


@app.route("/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id: int) -> str:
    """Delete a student record."""

    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    flash("Student record deleted successfully.", "success")
    return redirect(url_for("index"))


@app.route("/search")
def search() -> str:
    """Search a student by roll number."""

    roll_number = request.args.get("roll_number", "").strip()
    student = None
    message = None

    if roll_number:
        student = fetch_student_by_roll(roll_number)
        if student is None:
            message = "No student record was found for that roll number."

    return render_template(
        "search.html",
        roll_number=roll_number,
        student=student,
        message=message,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
