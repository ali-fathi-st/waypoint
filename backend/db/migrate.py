"""
Apply database migrations: every .sql file in db/migrations/, in name order,
each exactly once.

    python -m db.migrate            apply new migrations to DATABASE_URL
    python -m db.migrate --test     same, on TEST_DATABASE_URL
    python -m db.migrate --reset    DELETE EVERYTHING, then apply all (dev only)

Applied files are recorded in the schema_migrations table, so running this
again only applies new files. Never edit a migration that has already been
applied; add a new numbered file instead (002_..., 003_...).
"""

import argparse
from pathlib import Path

import psycopg

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(database_url: str, reset: bool = False) -> list[str]:
    """Apply pending migrations. Returns the file names applied."""
    applied_now = []
    with psycopg.connect(database_url) as conn:
        if reset:
            conn.execute("DROP SCHEMA public CASCADE")
            conn.execute("CREATE SCHEMA public")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        done = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            sql = path.read_text(encoding="utf-8")
            if not sql.strip() or all(line.strip().startswith("--") for line in sql.splitlines() if line.strip()):
                raise SystemExit(f"{path.name} has no SQL yet. Write it first (docs/09, step 2a).")
            try:
                conn.execute(sql)
            except psycopg.Error as error:
                raise SystemExit(f"{path.name} failed:\n{error}") from error
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test", action="store_true", help="use TEST_DATABASE_URL")
    parser.add_argument("--reset", action="store_true", help="drop everything first (development only)")
    args = parser.parse_args()
    settings = get_settings()
    applied = migrate(settings.test_database_url if args.test else settings.database_url, reset=args.reset)
    print("Applied: " + ", ".join(applied) if applied else "Already up to date.")


if __name__ == "__main__":
    main()
