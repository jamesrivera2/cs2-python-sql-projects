"""
Library Book Manager
====================
A command-line application for tracking books, members, and checkouts.
Demonstrates: foreign keys, date handling, JOIN queries, and OOP with a DB backend.
"""

import sqlite3
from datetime import date, timedelta


LOAN_DAYS = 14   # default checkout period


# ─────────────────────────────────────────────
# Database layer
# ─────────────────────────────────────────────

def get_connection(db_path: str = "library.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # enforce FK constraints
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            title     TEXT    NOT NULL,
            author    TEXT    NOT NULL,
            isbn      TEXT    UNIQUE NOT NULL,
            copies    INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS members (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );

        -- One row per active checkout; deleted on return
        CREATE TABLE IF NOT EXISTS checkouts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id     INTEGER NOT NULL REFERENCES books(id),
            member_id   INTEGER NOT NULL REFERENCES members(id),
            checked_out TEXT    NOT NULL,   -- ISO date string
            due_date    TEXT    NOT NULL
        );
    """)
    conn.commit()


# ─────────────────────────────────────────────
# Book operations
# ─────────────────────────────────────────────

def add_book(conn: sqlite3.Connection, title: str, author: str, isbn: str, copies: int = 1) -> int:
    cur = conn.execute(
        "INSERT INTO books (title, author, isbn, copies) VALUES (?, ?, ?, ?)",
        (title, author, isbn, copies)
    )
    conn.commit()
    print(f"  ✓ Added '{title}' by {author} (isbn={isbn}, copies={copies})")
    return cur.lastrowid


def available_copies(conn: sqlite3.Connection, book_id: int) -> int:
    """Return the number of copies not currently checked out."""
    book = conn.execute("SELECT copies FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        return 0
    checked_out = conn.execute(
        "SELECT COUNT(*) FROM checkouts WHERE book_id = ?", (book_id,)
    ).fetchone()[0]
    return book["copies"] - checked_out


def search_books(conn: sqlite3.Connection, keyword: str) -> None:
    """Search books by title or author (case-insensitive)."""
    keyword = f"%{keyword}%"
    rows = conn.execute(
        """
        SELECT id, title, author, isbn, copies FROM books
        WHERE title LIKE ? OR author LIKE ?
        ORDER BY title
        """,
        (keyword, keyword)
    ).fetchall()

    if not rows:
        print("  No books matched your search.")
        return

    print(f"\n  {'ID':<5} {'Title':<35} {'Author':<20} {'Avail'}")
    print("  " + "-" * 65)
    for r in rows:
        avail = available_copies(conn, r["id"])
        print(f"  {r['id']:<5} {r['title']:<35} {r['author']:<20} {avail}/{r['copies']}")


# ─────────────────────────────────────────────
# Member operations
# ─────────────────────────────────────────────

def add_member(conn: sqlite3.Connection, name: str, email: str) -> int:
    cur = conn.execute(
        "INSERT INTO members (name, email) VALUES (?, ?)", (name, email)
    )
    conn.commit()
    print(f"  ✓ Registered member '{name}'")
    return cur.lastrowid


# ─────────────────────────────────────────────
# Checkout / return operations
# ─────────────────────────────────────────────

def checkout_book(conn: sqlite3.Connection, member_id: int, book_id: int) -> bool:
    """Check out a book if a copy is available. Returns True on success."""
    if available_copies(conn, book_id) < 1:
        print("  ✗ No copies available for checkout.")
        return False

    today    = date.today().isoformat()
    due_date = (date.today() + timedelta(days=LOAN_DAYS)).isoformat()

    conn.execute(
        "INSERT INTO checkouts (book_id, member_id, checked_out, due_date) VALUES (?, ?, ?, ?)",
        (book_id, member_id, today, due_date)
    )
    conn.commit()
    print(f"  ✓ Checked out book {book_id} to member {member_id}. Due: {due_date}")
    return True


def return_book(conn: sqlite3.Connection, checkout_id: int) -> bool:
    """Return a book by deleting its checkout record."""
    row = conn.execute(
        "SELECT id FROM checkouts WHERE id = ?", (checkout_id,)
    ).fetchone()

    if not row:
        print(f"  ✗ No active checkout with id={checkout_id}")
        return False

    conn.execute("DELETE FROM checkouts WHERE id = ?", (checkout_id,))
    conn.commit()
    print(f"  ✓ Book returned (checkout id={checkout_id})")
    return True


def active_checkouts(conn: sqlite3.Connection) -> None:
    """List all currently checked-out books with member info and overdue status."""
    rows = conn.execute(
        """
        SELECT c.id, b.title, m.name, c.checked_out, c.due_date
        FROM checkouts c
        JOIN books   b ON b.id = c.book_id
        JOIN members m ON m.id = c.member_id
        ORDER BY c.due_date
        """
    ).fetchall()

    if not rows:
        print("  No books currently checked out.")
        return

    today = date.today().isoformat()
    print(f"\n  {'CK ID':<7} {'Book':<30} {'Member':<20} {'Due':<12} {'Status'}")
    print("  " + "-" * 75)
    for r in rows:
        status = "OVERDUE" if r["due_date"] < today else "OK"
        print(f"  {r['id']:<7} {r['title']:<30} {r['name']:<20} {r['due_date']:<12} {status}")


def member_history(conn: sqlite3.Connection, member_id: int) -> None:
    """Show all active loans for one member."""
    member = conn.execute(
        "SELECT name FROM members WHERE id = ?", (member_id,)
    ).fetchone()

    if not member:
        print(f"  No member with id={member_id}")
        return

    rows = conn.execute(
        """
        SELECT c.id, b.title, b.author, c.due_date
        FROM checkouts c
        JOIN books b ON b.id = c.book_id
        WHERE c.member_id = ?
        """,
        (member_id,)
    ).fetchall()

    print(f"\n  Loans for {member['name']}:")
    if not rows:
        print("  No active loans.")
        return
    for r in rows:
        print(f"    [{r['id']}] '{r['title']}' by {r['author']} — due {r['due_date']}")


# ─────────────────────────────────────────────
# Demo / entry point
# ─────────────────────────────────────────────

def main() -> None:
    conn = get_connection()
    initialize_db(conn)

    print("\n=== Library Book Manager Demo ===\n")

    # Add books
    print("-- Adding books --")
    b1 = add_book(conn, "Clean Code",                    "Robert C. Martin", "9780132350884", copies=2)
    b2 = add_book(conn, "The Pragmatic Programmer",      "David Thomas",     "9780135957059", copies=1)
    b3 = add_book(conn, "Introduction to Algorithms",   "Cormen et al.",    "9780262046305", copies=3)

    # Add members
    print("\n-- Adding members --")
    m1 = add_member(conn, "Diana Prince",  "diana@email.com")
    m2 = add_member(conn, "Bruce Wayne",   "bruce@email.com")
    m3 = add_member(conn, "Clark Kent",    "clark@email.com")

    # Checkouts
    print("\n-- Checking out books --")
    ck1 = checkout_book(conn, m1, b1)
    ck2 = checkout_book(conn, m2, b1)   # second copy
    ck3 = checkout_book(conn, m2, b2)
    checkout_book(conn, m3, b2)   # should fail — only 1 copy

    # Active checkouts
    print("\n-- Active checkouts --")
    active_checkouts(conn)

    # Member history
    print("\n-- Member history: Bruce Wayne --")
    member_history(conn, m2)

    # Search
    print("\n-- Search: 'code' --")
    search_books(conn, "code")

    # Return
    print("\n-- Returning a book --")
    # Find the checkout id for Diana's copy of b1
    row = conn.execute(
        "SELECT id FROM checkouts WHERE member_id = ? AND book_id = ?", (m1, b1)
    ).fetchone()
    if row:
        return_book(conn, row["id"])

    print("\n-- Active checkouts after return --")
    active_checkouts(conn)

    conn.close()


if __name__ == "__main__":
    main()
