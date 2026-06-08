# Movie Database

A Python application for browsing, rating, and querying a personal movie collection with SQLite.

## Learning Goals
- Many-to-many relationships: movies ↔ genres via a junction table
- SQL `VIEW` for simplifying complex repeated queries
- `GROUP_CONCAT` for aggregating related rows into a single column
- Subqueries and JOIN across four tables
- LEFT JOIN for optional relationships (unrated movies still appear)

## Schema

```
movies              genres            movie_genres (junction)
──────              ──────            ──────────────────────
id (PK)             id (PK)           movie_id (FK)
title               name (UNIQUE)     genre_id (FK)
year
director
runtime_min           ratings
description           ───────
                      id (PK)
                      movie_id (FK)
                      score
                      review
                      rated_on
```

**View:** `movie_summary` — joins all tables, aggregates avg rating and genres into one row per movie.

## How to Run

```bash
python movie_db.py
```

No external packages required.

## Extension Ideas (for students)
1. Add an `actors` table and another many-to-many relationship (`movie_actors`)
2. Add a watchlist feature: a `want_to_watch` table separate from rated movies
3. Implement a recommendation engine using `WHERE genre IN (...)` subqueries
4. Add pagination to `all_movies()` using `LIMIT` and `OFFSET`
5. Build a REST API on top using Flask, returning JSON responses
