from __future__ import annotations

from pathlib import Path

import psycopg

from fleettrack.config import DATABASE_URL

ROOT = Path(__file__).resolve().parents[1]


def apply_sql(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, prepare=False)
        conn.commit()
    print(f"Applied {path.relative_to(ROOT)}")


def main() -> None:
    apply_sql(ROOT / "sql" / "schema.sql")
    for migration in sorted((ROOT / "sql" / "migrations").glob("*.sql")):
        apply_sql(migration)
    apply_sql(ROOT / "sql" / "data.sql")


if __name__ == "__main__":
    main()
