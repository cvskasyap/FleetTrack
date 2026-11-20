from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from .config import DATABASE_URL


@contextmanager
def get_connection() -> Iterator[psycopg.Connection[Any]]:
    """Yield a PostgreSQL connection and reliably close it afterwards."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def query_df(sql: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    """Execute a read query using DB-API and return a pandas DataFrame."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return pd.DataFrame(rows)


def execute(sql: str, params: tuple[Any, ...] | None = None) -> int:
    """Execute a write statement and commit; returns affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            count = cur.rowcount
        conn.commit()
        return count


def scalar(sql: str, params: tuple[Any, ...] | None = None) -> Any:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return next(iter(row.values())) if row else None
