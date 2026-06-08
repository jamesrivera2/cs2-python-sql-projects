# Personal Expense Tracker

A Python application that tracks income and expenses by category, generates spending summaries, and exports reports to CSV.

## Learning Goals
- Object-oriented design: separating data models (`Transaction`) from persistence (`ExpenseRepository`)
- SQL aggregation: `SUM`, `COUNT`, `GROUP BY`, `CASE WHEN`
- String manipulation in SQL: `SUBSTR` for grouping dates by month
- Exporting data with Python's built-in `csv` module
- Validating data at the model layer before writing to the database

## Project Structure

```
expense_tracker/
├── expense_tracker.py   # all code: models, repository, display helpers, demo
└── README.md
```

## How to Run

```bash
python expense_tracker.py
```

No external packages required.

## Key Design Patterns

| Pattern | Where used |
|---|---|
| Repository pattern | `ExpenseRepository` encapsulates all SQL |
| Value object | `Transaction` holds data and validates on construction |
| Separation of concerns | Display helpers are pure functions; no SQL in them |

## Extension Ideas (for students)
1. Add an `argparse` CLI: `python expense_tracker.py add --type expense --category Groceries --amount 45.50`
2. Add a budget per category and warn when the user goes over
3. Plot monthly spending with `matplotlib`
4. Add a `tags` many-to-many relationship to transactions
5. Write a Flask or FastAPI web front-end backed by this repository
