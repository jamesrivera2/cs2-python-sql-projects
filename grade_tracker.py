"""
Student Grade Tracker
=====================
A command-line application for managing students, courses, and grades.
Demonstrates: SQLite with Python, CRUD operations, basic data aggregation.
"""

import sqlite3


# ─────────────────────────────────────────────
# Database setup
# ─────────────────────────────────────────────

def get_connection(db_path: str = "grades.db") -> sqlite3.Connection:
    """Create (or open) the SQLite database and return a connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # lets us access columns by name
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT    NOT NULL,
            email   TEXT    UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS courses (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            code    TEXT    UNIQUE NOT NULL,
            title   TEXT    NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3
        );

        CREATE TABLE IF NOT EXISTS grades (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            course_id  INTEGER NOT NULL REFERENCES courses(id),
            score      REAL    NOT NULL CHECK(score BETWEEN 0 AND 100),
            UNIQUE(student_id, course_id)
        );
    """)
    conn.commit()


# ─────────────────────────────────────────────
# Student operations
# ─────────────────────────────────────────────

def add_student(conn: sqlite3.Connection, name: str, email: str) -> int:
    """Insert a new student and return their id."""
    cur = conn.execute(
        "INSERT INTO students (name, email) VALUES (?, ?)", (name, email)
    )
    conn.commit()
    print(f"  ✓ Added student '{name}' (id={cur.lastrowid})")
    return cur.lastrowid


def list_students(conn: sqlite3.Connection) -> None:
    """Print all students."""
    rows = conn.execute("SELECT id, name, email FROM students ORDER BY name").fetchall()
    if not rows:
        print("  No students found.")
        return
    print(f"\n  {'ID':<5} {'Name':<25} {'Email'}")
    print("  " + "-" * 55)
    for r in rows:
        print(f"  {r['id']:<5} {r['name']:<25} {r['email']}")


# ─────────────────────────────────────────────
# Course operations
# ─────────────────────────────────────────────

def add_course(conn: sqlite3.Connection, code: str, title: str, credits: int = 3) -> int:
    """Insert a new course and return its id."""
    cur = conn.execute(
        "INSERT INTO courses (code, title, credits) VALUES (?, ?, ?)",
        (code, title, credits)
    )
    conn.commit()
    print(f"  ✓ Added course '{code}: {title}' ({credits} credits)")
    return cur.lastrowid


def list_courses(conn: sqlite3.Connection) -> None:
    """Print all courses."""
    rows = conn.execute(
        "SELECT id, code, title, credits FROM courses ORDER BY code"
    ).fetchall()
    if not rows:
        print("  No courses found.")
        return
    print(f"\n  {'ID':<5} {'Code':<10} {'Title':<30} {'Credits'}")
    print("  " + "-" * 55)
    for r in rows:
        print(f"  {r['id']:<5} {r['code']:<10} {r['title']:<30} {r['credits']}")


# ─────────────────────────────────────────────
# Grade operations
# ─────────────────────────────────────────────

def record_grade(
    conn: sqlite3.Connection,
    student_id: int,
    course_id: int,
    score: float
) -> None:
    """Insert or replace a grade for a student in a course."""
    conn.execute(
        """
        INSERT INTO grades (student_id, course_id, score)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id, course_id) DO UPDATE SET score = excluded.score
        """,
        (student_id, course_id, score)
    )
    conn.commit()
    print(f"  ✓ Recorded score {score} for student {student_id} in course {course_id}")


def score_to_letter(score: float) -> str:
    """Convert a numeric score to a letter grade."""
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"


def student_report(conn: sqlite3.Connection, student_id: int) -> None:
    """Print a grade report for one student, including weighted GPA."""
    student = conn.execute(
        "SELECT name, email FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if not student:
        print(f"  No student with id={student_id}")
        return

    rows = conn.execute(
        """
        SELECT c.code, c.title, c.credits, g.score
        FROM grades g
        JOIN courses c ON c.id = g.course_id
        WHERE g.student_id = ?
        ORDER BY c.code
        """,
        (student_id,)
    ).fetchall()

    print(f"\n  Report for: {student['name']} ({student['email']})")
    print("  " + "=" * 55)

    if not rows:
        print("  No grades recorded yet.")
        return

    total_points = 0.0
    total_credits = 0

    print(f"  {'Code':<10} {'Title':<25} {'Cr':<4} {'Score':<8} {'Grade'}")
    print("  " + "-" * 55)

    for r in rows:
        letter = score_to_letter(r['score'])
        print(f"  {r['code']:<10} {r['title']:<25} {r['credits']:<4} {r['score']:<8.1f} {letter}")
        total_points  += r['score'] * r['credits']
        total_credits += r['credits']

    weighted_avg = total_points / total_credits if total_credits else 0
    print("  " + "-" * 55)
    print(f"  Weighted average: {weighted_avg:.2f}  ({score_to_letter(weighted_avg)})")
    print(f"  Total credits:    {total_credits}")


def class_summary(conn: sqlite3.Connection, course_id: int) -> None:
    """Print statistics for a course."""
    course = conn.execute(
        "SELECT code, title FROM courses WHERE id = ?", (course_id,)
    ).fetchone()

    if not course:
        print(f"  No course with id={course_id}")
        return

    stats = conn.execute(
        """
        SELECT COUNT(*) AS enrolled,
               AVG(score) AS avg_score,
               MIN(score) AS min_score,
               MAX(score) AS max_score
        FROM grades
        WHERE course_id = ?
        """,
        (course_id,)
    ).fetchone()

    print(f"\n  {course['code']}: {course['title']}")
    print("  " + "=" * 40)
    print(f"  Enrolled:  {stats['enrolled']}")
    if stats['enrolled']:
        print(f"  Average:   {stats['avg_score']:.2f}")
        print(f"  High:      {stats['max_score']:.2f}")
        print(f"  Low:       {stats['min_score']:.2f}")


# ─────────────────────────────────────────────
# Demo / entry point
# ─────────────────────────────────────────────

def main() -> None:
    conn = get_connection()
    initialize_db(conn)

    print("\n=== Student Grade Tracker Demo ===\n")

    # Add students
    print("-- Adding students --")
    s1 = add_student(conn, "Alice Johnson", "alice@university.edu")
    s2 = add_student(conn, "Bob Martinez",  "bob@university.edu")
    s3 = add_student(conn, "Carol Chen",    "carol@university.edu")

    # Add courses
    print("\n-- Adding courses --")
    c1 = add_course(conn, "CS101", "Intro to Programming", credits=3)
    c2 = add_course(conn, "CS201", "Data Structures",      credits=4)
    c3 = add_course(conn, "MATH150","Calculus I",           credits=4)

    # Record grades
    print("\n-- Recording grades --")
    record_grade(conn, s1, c1, 92.5)
    record_grade(conn, s1, c2, 87.0)
    record_grade(conn, s1, c3, 95.0)

    record_grade(conn, s2, c1, 78.0)
    record_grade(conn, s2, c2, 65.5)

    record_grade(conn, s3, c1, 88.0)
    record_grade(conn, s3, c2, 91.0)
    record_grade(conn, s3, c3, 74.0)

    # Reports
    print("\n-- Student reports --")
    student_report(conn, s1)
    student_report(conn, s2)

    print("\n-- Course summary --")
    class_summary(conn, c2)

    print("\n-- All students --")
    list_students(conn)

    print("\n-- All courses --")
    list_courses(conn)

    conn.close()


if __name__ == "__main__":
    main()
