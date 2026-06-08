"""
Personal Expense Tracker
========================
Track income and expenses by category, generate spending summaries,
and export reports to CSV.
Demonstrates: OOP design, SQLite, aggregate queries, csv module, argparse.
"""

import argparse
import csv
import sqlite3
from datetime import date
from io import StringIO


# ─────────────────────────────────────────────
# Data model (simple value objects)
# ─────────────────────────────────────────────

class Transaction:
    """Represents a single income or expense record."""

    TYPES = {"income", "expense"}

    def __init__(
        self,
        tx_id:    int,
        tx_type:  str,
        category: str,
        amount:   float,
        note:     str,
        tx_date:  str,
    ) -> None:
        if tx_type not in self.TYPES:
            raise ValueError(f"tx_type must be one of {self.TYPES}")
        if amount <= 0:
            raise ValueError("amount must be positive")

        self.tx_id    = tx_id
        self.tx_type  = tx_type
        self.category = category
        self.amount   = amount
        self.note     = note
        self.tx_date  = tx_date

    def __repr__(self) -> str:
        sign = "+" if self.tx_type == "income" else "-"
        return (
            f"[{self.tx_id}] {self.tx_date} | {sign}${self.amount:>8.2f} "
            f"| {self.category:<15} | {self.note}"
        )


# ─────────────────────────────────────────────
# Repository (all DB logic lives here)
# ─────────────────────────────────────────────

class ExpenseRepository:
    """Handles all database operations for the expense tracker."""

    def __init__(self, db_path: str = "expenses.db") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                type     TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT    NOT NULL,
                amount   REAL    NOT NULL CHECK(amount > 0),
                note     TEXT    DEFAULT '',
                tx_date  TEXT    NOT NULL
            )
        """)
        self.conn.commit()

    def add(
        self,
        tx_type:  str,
        category: str,
        amount:   float,
        note:     str = "",
        tx_date:  str | None = None,
    ) -> Transaction:
        tx_date = tx_date or date.today().isoformat()
        # Validate via the data model before inserting
        temp = Transaction(0, tx_type, category, amount, note, tx_date)

        cur = self.conn.execute(
            "INSERT INTO transactions (type, category, amount, note, tx_date) VALUES (?,?,?,?,?)",
            (temp.tx_type, temp.category, temp.amount, temp.note, temp.tx_date)
        )
        self.conn.commit()
        temp.tx_id = cur.lastrowid
        return temp

    def get_all(self, tx_type: str | None = None) -> list[Transaction]:
        if tx_type:
            rows = self.conn.execute(
                "SELECT * FROM transactions WHERE type = ? ORDER BY tx_date DESC", (tx_type,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM transactions ORDER BY tx_date DESC"
            ).fetchall()
        return [Transaction(tx_id=r["id"], tx_type=r["type"], category=r["category"], amount=r["amount"], note=r["note"], tx_date=r["tx_date"]) for r in rows]

    def delete(self, tx_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # ── Aggregation queries ────────────────────

    def summary(self) -> dict:
        """Return total income, total expenses, and net balance."""
        row = self.conn.execute("""
            SELECT
                SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expenses
            FROM transactions
        """).fetchone()
        income   = row["total_income"]   or 0.0
        expenses = row["total_expenses"] or 0.0
        return {
            "income":   income,
            "expenses": expenses,
            "balance":  income - expenses,
        }

    def by_category(self, tx_type: str = "expense") -> list[dict]:
        """Return spending/income totals grouped by category, descending."""
        rows = self.conn.execute("""
            SELECT category, SUM(amount) AS total, COUNT(*) AS count
            FROM transactions
            WHERE type = ?
            GROUP BY category
            ORDER BY total DESC
        """, (tx_type,)).fetchall()
        return [dict(r) for r in rows]

    def monthly_totals(self) -> list[dict]:
        """Return income and expense totals grouped by YYYY-MM."""
        rows = self.conn.execute("""
            SELECT
                SUBSTR(tx_date, 1, 7) AS month,
                SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expenses
            FROM transactions
            GROUP BY month
            ORDER BY month
        """).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()


# ─────────────────────────────────────────────
# Report / display helpers
# ─────────────────────────────────────────────

def print_summary(repo: ExpenseRepository) -> None:
    s = repo.summary()
    print(f"\n  {'Income:':12} ${s['income']:>10.2f}")
    print(f"  {'Expenses:':12} ${s['expenses']:>10.2f}")
    print(f"  {'Balance:':12} ${s['balance']:>10.2f}")


def print_category_breakdown(repo: ExpenseRepository, tx_type: str = "expense") -> None:
    rows = repo.by_category(tx_type)
    label = tx_type.capitalize()
    print(f"\n  {label} by category:")
    print(f"  {'Category':<20} {'Total':>10}  {'# Txns'}")
    print("  " + "-" * 40)
    for r in rows:
        print(f"  {r['category']:<20} ${r['total']:>9.2f}  {r['count']}")


def print_monthly(repo: ExpenseRepository) -> None:
    rows = repo.monthly_totals()
    print(f"\n  {'Month':<10} {'Income':>10}  {'Expenses':>10}  {'Net':>10}")
    print("  " + "-" * 45)
    for r in rows:
        net = r["income"] - r["expenses"]
        print(f"  {r['month']:<10} ${r['income']:>9.2f}  ${r['expenses']:>9.2f}  ${net:>9.2f}")


def export_csv(repo: ExpenseRepository) -> str:
    """Return CSV string of all transactions."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "type", "category", "amount", "note", "date"])
    for tx in repo.get_all():
        writer.writerow([tx.tx_id, tx.tx_type, tx.category, tx.amount, tx.note, tx.tx_date])
    return buf.getvalue()


# ─────────────────────────────────────────────
# Demo / entry point
# ─────────────────────────────────────────────

def main() -> None:
    repo = ExpenseRepository()

    print("\n=== Personal Expense Tracker Demo ===\n")

    # Seed some data
    print("-- Adding transactions --")
    transactions = [
        ("income",  "Salary",        3200.00, "August paycheck",  "2025-08-01"),
        ("income",  "Freelance",      450.00, "Web project",      "2025-08-10"),
        ("expense", "Rent",          1100.00, "August rent",      "2025-08-01"),
        ("expense", "Groceries",      180.50, "Weekly shop",      "2025-08-03"),
        ("expense", "Utilities",       75.00, "Electric bill",    "2025-08-05"),
        ("expense", "Dining Out",      62.30, "Dinner with team", "2025-08-07"),
        ("expense", "Groceries",      145.00, "Weekly shop",      "2025-08-10"),
        ("expense", "Entertainment",   29.99, "Streaming sub",    "2025-08-11"),
        ("income",  "Salary",        3200.00, "September pay",    "2025-09-01"),
        ("expense", "Rent",          1100.00, "September rent",   "2025-09-01"),
        ("expense", "Dining Out",      88.75, "Birthday dinner",  "2025-09-14"),
        ("expense", "Transport",       55.00, "Gas",              "2025-09-18"),
    ]

    for tx_type, cat, amt, note, dt in transactions:
        tx = repo.add(tx_type, cat, amt, note, dt)
        sign = "+" if tx_type == "income" else "-"
        print(f"  {sign}${amt:>8.2f}  {cat}")

    # Summary
    print("\n-- Balance summary --")
    print_summary(repo)

    # Category breakdown
    print("\n-- Expense breakdown by category --")
    print_category_breakdown(repo, "expense")

    print("\n-- Income breakdown by category --")
    print_category_breakdown(repo, "income")

    # Monthly totals
    print("\n-- Monthly totals --")
    print_monthly(repo)

    # All transactions
    print("\n-- Recent transactions (all) --")
    for tx in repo.get_all():
        print(f"  {tx}")

    # CSV export
    print("\n-- CSV export (first 3 lines) --")
    csv_data = export_csv(repo)
    for line in csv_data.splitlines()[:4]:
        print(f"  {line}")

    repo.close()


if __name__ == "__main__":
    main()
