# database.py
# SQLite setup for the Student Registry project.
import sqlite3

DB_NAME = "students.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # users table -> login / register / forgot password
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            otp_code TEXT,
            otp_expires_at TEXT
        )
        """
    )

    # students table -> the actual registry data
    # each row is tied to the user (user_id) who added it, so users only
    # ever see the students they themselves created.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            roll_number TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, roll_number)
        )
        """
    )

    conn.commit()
    conn.close()
