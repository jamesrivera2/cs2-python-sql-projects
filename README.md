# Student Grade Tracker

A command-line Python application that manages students, courses, and grades using SQLite.

## Learning Goals
- Connecting to and querying a SQLite database with Python's `sqlite3` module
- Designing a normalized relational schema (students → grades ← courses)
- CRUD operations: INSERT, SELECT, UPDATE via `ON CONFLICT`
- Aggregation queries: `AVG`, `MIN`, `MAX`, `COUNT`
- Joining multiple tables and computing a weighted average in Python

## Schema

```
students          courses            grades
─────────         ───────            ──────
id (PK)           id (PK)            id (PK)
name              code (UNIQUE)      student_id (FK)
email (UNIQUE)    title              course_id  (FK)
                  credits            score
```

## How to Run

```bash
python grade_tracker.py
```

No external packages required — only the Python standard library.

## Extension Ideas (for students)
1. Add a command-line menu so a user can interactively add students/grades
2. Export a student's report to a `.csv` file
3. Add a `semesters` table so grades are tracked per semester
4. Write unit tests for `score_to_letter()` and `student_report()`
