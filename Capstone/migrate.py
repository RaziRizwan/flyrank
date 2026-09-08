"""
migrate.py -- a small migration runner. Applies every .sql file in migrations/ in
filename order, tracking what's already been applied in a schema_migrations table so
re-running is a no-op. Run with:  python migrate.py
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def run():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migration_files:
            print("No migration files found in", MIGRATIONS_DIR)
            return

        for path in migration_files:
            if path.name in applied:
                print(f"  skip   {path.name} (already applied)")
                continue
            sql = path.read_text(encoding="utf-8")
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print(f"  apply  {path.name}")

    print("Migrations up to date.")


if __name__ == "__main__":
    run()
