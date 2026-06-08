"""
Movie Database
==============
Browse, rate, and query a personal movie collection.
Demonstrates: many-to-many relationships, subqueries, views, and full-text search.
"""

import sqlite3


# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

def get_connection(db_path: str = "movies.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """Create tables and a convenience view."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS movies (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            year         INTEGER NOT NULL,
            director     TEXT    NOT NULL,
            runtime_min  INTEGER,
            description  TEXT
        );

        CREATE TABLE IF NOT EXISTS genres (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        -- Many-to-many: a movie can have multiple genres
        CREATE TABLE IF NOT EXISTS movie_genres (
            movie_id INTEGER NOT NULL REFERENCES movies(id),
            genre_id INTEGER NOT NULL REFERENCES genres(id),
            PRIMARY KEY (movie_id, genre_id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL REFERENCES movies(id),
            score    REAL    NOT NULL CHECK(score BETWEEN 1 AND 10),
            review   TEXT,
            rated_on TEXT    NOT NULL
        );

        -- A view that joins everything together for easy querying
        CREATE VIEW IF NOT EXISTS movie_summary AS
        SELECT
            m.id,
            m.title,
            m.year,
            m.director,
            m.runtime_min,
            ROUND(AVG(r.score), 1)  AS avg_rating,
            COUNT(r.id)             AS rating_count,
            GROUP_CONCAT(g.name, ', ') AS genres
        FROM movies m
        LEFT JOIN ratings     r  ON r.movie_id = m.id
        LEFT JOIN movie_genres mg ON mg.movie_id = m.id
        LEFT JOIN genres       g  ON g.id = mg.genre_id
        GROUP BY m.id;
    """)
    conn.commit()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_or_create_genre(conn: sqlite3.Connection, name: str) -> int:
    """Return the genre id, inserting if it doesn't exist."""
    row = conn.execute("SELECT id FROM genres WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO genres (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


# ─────────────────────────────────────────────
# Movie operations
# ─────────────────────────────────────────────

def add_movie(
    conn: sqlite3.Connection,
    title:       str,
    year:        int,
    director:    str,
    genres:      list[str],
    runtime_min: int | None = None,
    description: str | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO movies (title, year, director, runtime_min, description) VALUES (?,?,?,?,?)",
        (title, year, director, runtime_min, description)
    )
    movie_id = cur.lastrowid

    # Link genres
    for genre_name in genres:
        genre_id = get_or_create_genre(conn, genre_name)
        conn.execute(
            "INSERT OR IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?,?)",
            (movie_id, genre_id)
        )

    conn.commit()
    genre_str = ", ".join(genres)
    print(f"  ✓ Added '{title}' ({year}) [{genre_str}]")
    return movie_id


def rate_movie(
    conn: sqlite3.Connection,
    movie_id: int,
    score:    float,
    review:   str = "",
    rated_on: str = "2025-01-01",
) -> None:
    if not (1 <= score <= 10):
        raise ValueError("Score must be between 1 and 10")
    conn.execute(
        "INSERT INTO ratings (movie_id, score, review, rated_on) VALUES (?,?,?,?)",
        (movie_id, score, review, rated_on)
    )
    conn.commit()
    print(f"  ✓ Rated movie {movie_id}: {score}/10")


# ─────────────────────────────────────────────
# Query operations
# ─────────────────────────────────────────────

def all_movies(conn: sqlite3.Connection) -> None:
    """Display all movies from the summary view."""
    rows = conn.execute(
        "SELECT * FROM movie_summary ORDER BY avg_rating DESC NULLS LAST"
    ).fetchall()

    print(f"\n  {'Title':<35} {'Year':<6} {'Rating':<8} {'Genres'}")
    print("  " + "-" * 80)
    for r in rows:
        rating_str = f"{r['avg_rating']}/10" if r["avg_rating"] else "unrated"
        genres_str = r["genres"] or "—"
        print(f"  {r['title']:<35} {r['year']:<6} {rating_str:<8} {genres_str}")


def movies_by_genre(conn: sqlite3.Connection, genre_name: str) -> None:
    """List movies in a given genre."""
    rows = conn.execute(
        """
        SELECT ms.*
        FROM movie_summary ms
        JOIN movie_genres mg ON mg.movie_id = ms.id
        JOIN genres       g  ON g.id = mg.genre_id
        WHERE g.name LIKE ?
        ORDER BY ms.avg_rating DESC
        """,
        (f"%{genre_name}%",)
    ).fetchall()

    print(f"\n  Movies in genre '{genre_name}':")
    if not rows:
        print("  None found.")
        return
    for r in rows:
        rating_str = f"{r['avg_rating']}/10" if r["avg_rating"] else "unrated"
        print(f"    {r['title']} ({r['year']}) — {rating_str}")


def top_rated(conn: sqlite3.Connection, n: int = 5) -> None:
    """Show top-N rated movies (requires at least 1 rating)."""
    rows = conn.execute(
        """
        SELECT * FROM movie_summary
        WHERE rating_count > 0
        ORDER BY avg_rating DESC
        LIMIT ?
        """,
        (n,)
    ).fetchall()

    print(f"\n  Top {n} rated movies:")
    for i, r in enumerate(rows, 1):
        print(f"  {i}. {r['title']} ({r['year']}) — {r['avg_rating']}/10 ({r['rating_count']} rating(s))")


def director_stats(conn: sqlite3.Connection) -> None:
    """Show statistics grouped by director."""
    rows = conn.execute(
        """
        SELECT
            m.director,
            COUNT(DISTINCT m.id)  AS movies,
            ROUND(AVG(r.score),1) AS avg_rating
        FROM movies m
        LEFT JOIN ratings r ON r.movie_id = m.id
        GROUP BY m.director
        ORDER BY avg_rating DESC NULLS LAST
        """
    ).fetchall()

    print(f"\n  {'Director':<25} {'Movies':<8} {'Avg Rating'}")
    print("  " + "-" * 45)
    for r in rows:
        rating_str = str(r["avg_rating"]) if r["avg_rating"] else "—"
        print(f"  {r['director']:<25} {r['movies']:<8} {rating_str}")


def search(conn: sqlite3.Connection, keyword: str) -> None:
    """Search movies by title or description keyword."""
    rows = conn.execute(
        """
        SELECT id, title, year, director FROM movies
        WHERE title LIKE ? OR description LIKE ?
        """,
        (f"%{keyword}%", f"%{keyword}%")
    ).fetchall()

    print(f"\n  Search results for '{keyword}':")
    if not rows:
        print("  No results.")
        return
    for r in rows:
        print(f"    [{r['id']}] {r['title']} ({r['year']}) — {r['director']}")


# ─────────────────────────────────────────────
# Demo / entry point
# ─────────────────────────────────────────────

def main() -> None:
    conn = get_connection()
    initialize_db(conn)

    print("\n=== Movie Database Demo ===\n")

    # Add movies
    print("-- Adding movies --")
    m1 = add_movie(conn, "Inception",             2010, "Christopher Nolan",
                   ["Sci-Fi", "Thriller"], 148,
                   "A thief who steals corporate secrets through dream-sharing technology.")

    m2 = add_movie(conn, "The Shawshank Redemption", 1994, "Frank Darabont",
                   ["Drama"], 142,
                   "Two imprisoned men bond over years, finding solace through decency.")

    m3 = add_movie(conn, "Interstellar",          2014, "Christopher Nolan",
                   ["Sci-Fi", "Drama"], 169,
                   "A team of explorers travel through a wormhole in space.")

    m4 = add_movie(conn, "Pulp Fiction",          1994, "Quentin Tarantino",
                   ["Crime", "Drama"], 154,
                   "The lives of two mob hitmen intertwine in four tales of violence.")

    m5 = add_movie(conn, "The Dark Knight",       2008, "Christopher Nolan",
                   ["Action", "Thriller"], 152,
                   "Batman faces the Joker, a criminal mastermind who revels in chaos.")

    # Rate movies
    print("\n-- Rating movies --")
    rate_movie(conn, m1, 9.0, "Mind-bending and visually stunning", "2025-01-10")
    rate_movie(conn, m1, 8.5, "Great concept, maybe 30 mins too long", "2025-02-14")
    rate_movie(conn, m2, 9.8, "One of the greatest films ever made", "2025-01-15")
    rate_movie(conn, m3, 8.8, "Visually gorgeous, emotionally powerful", "2025-03-01")
    rate_movie(conn, m4, 9.2, "Tarantino at his absolute best", "2025-01-20")
    rate_movie(conn, m5, 9.5, "Heath Ledger is unforgettable", "2025-02-28")
    rate_movie(conn, m5, 9.0, "Peak superhero cinema", "2025-03-10")

    # Queries
    print("\n-- All movies (sorted by rating) --")
    all_movies(conn)

    print("\n-- Top 3 rated --")
    top_rated(conn, 3)

    print("\n-- Movies by genre: Sci-Fi --")
    movies_by_genre(conn, "Sci-Fi")

    print("\n-- Director stats --")
    director_stats(conn)

    print("\n-- Search: 'dream' --")
    search(conn, "dream")

    conn.close()


if __name__ == "__main__":
    main()
