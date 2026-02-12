"""Interactive DuckDB shell connected to the dbt dev database.

Launches a REPL with the dev.duckdb database pre-connected, showing
available schemas and tables. Useful for ad-hoc queries against
the dbt-managed data warehouse.

Usage:
    uv run python scripts/shell.py
"""
from pathlib import Path

import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "dev.duckdb"


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Run 'make build' first to create the database.")
        return

    con = duckdb.connect(str(DB_PATH))
    print(f"Connected to {DB_PATH.name}")
    print()

    # Show schemas
    schemas = con.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
        ORDER BY schema_name
    """).fetchall()
    print(f"Schemas: {', '.join(s[0] for s in schemas)}")

    # Show tables per schema
    for (schema_name,) in schemas:
        tables = con.execute(f"""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = '{schema_name}'
            ORDER BY table_name
        """).fetchall()
        if tables:
            table_list = ", ".join(f"{t[0]} ({t[1][:5].lower()})" for t in tables)
            print(f"  {schema_name}: {table_list}")

    print()
    print("Type SQL queries. Press Ctrl+C or type 'exit' to quit.")
    print()

    while True:
        try:
            query = input("dbt> ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "\\q"):
                break
            result = con.execute(query)
            df = result.fetchdf()
            if len(df) > 0:
                print(df.to_string())
            else:
                print("(0 rows)")
            print()
        except KeyboardInterrupt:
            print()
            break
        except Exception as e:
            print(f"Error: {e}")
            print()

    con.close()
    print("Disconnected.")


if __name__ == "__main__":
    main()
