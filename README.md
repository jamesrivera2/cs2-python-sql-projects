# Library Book Manager

A command-line Python application for tracking library books, member registrations, and checkouts using SQLite.

## Learning Goals
- Multi-table relational design with foreign key constraints
- Using `PRAGMA foreign_keys = ON` in SQLite
- Date arithmetic with Python's `datetime` module
- JOIN queries across three tables
- Business logic layered on top of database operations (availability check)

## Schema

```
books              members            checkouts
─────              ───────            ─────────
id (PK)            id (PK)            id (PK)
title              name               book_id   (FK → books)
author             email (UNIQUE)     member_id (FK → members)
isbn (UNIQUE)                         checked_out  (ISO date)
copies                                due_date     (ISO date)
```

## How to Run

```bash
python library.py
```

No external packages required.

## Extension Ideas (for students)
1. Add a `loan_history` table to keep a permanent record of past checkouts (instead of deleting on return)
2. Add a late-fee calculator based on the number of days overdue
3. Implement a command-line interface with `argparse` or `cmd.Cmd`
4. Add a `reservations` table so members can queue for unavailable books
5. Write pytest tests that use an in-memory SQLite database (`:memory:`)
