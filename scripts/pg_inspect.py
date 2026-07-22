#!/usr/bin/env python3
"""Inspect km-agent Postgres tables (list, peek, run SQL).

Uses the same ``KMA_DB_*`` / ``DB_*`` env as the app via ``kma.db.build_db_url``.
Read-only by default (SELECT / WITH / SHOW / EXPLAIN); pass ``--write`` for other SQL.

Examples:

  uv run python scripts/pg_inspect.py tables
  uv run python scripts/pg_inspect.py tables --schema public

  uv run python scripts/pg_inspect.py peek public.kma_knowledge --limit 10

  uv run python scripts/pg_inspect.py sql --query "SELECT count(*) FROM kma_knowledge"

  uv run python scripts/pg_inspect.py sql --file scripts/sql/count_knowledge.sql
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import Engine, Result  # noqa: E402

from kma.db import build_db_url  # noqa: E402

_CELL_MAX = 120
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LEADING_COMMENT = re.compile(
    r"""(?xs)
    ^(?:\s|--[^\n]*\n|/\*.*?\*/)*
    """
)


def _connection_banner(db_url: str) -> str:
    parsed = urlparse(db_url)
    host = parsed.hostname or "?"
    port = parsed.port or 5432
    db = (parsed.path or "/").lstrip("/") or "?"
    user = parsed.username or "?"
    return f"connecting: {user}@{host}:{port}/{db}"


def _make_engine() -> Engine:
    return create_engine(build_db_url())


def _quote_ident(name: str) -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"invalid SQL identifier: {name!r}")
    return f'"{name}"'


def _qualify_table(table: str) -> str:
    """Validate ``schema.table`` or ``table`` and return a quoted FROM target."""
    parts = table.split(".")
    if len(parts) == 1:
        return _quote_ident(parts[0])
    if len(parts) == 2:
        return f"{_quote_ident(parts[0])}.{_quote_ident(parts[1])}"
    raise ValueError(f"expected table or schema.table, got: {table!r}")


def _first_keyword(sql: str) -> str:
    body = _LEADING_COMMENT.sub("", sql).lstrip()
    if not body:
        return ""
    return body.split(None, 1)[0].upper()


def _assert_read_only(sql: str, *, allow_write: bool) -> None:
    if allow_write:
        return
    kw = _first_keyword(sql)
    if not kw:
        return
    if kw not in {"SELECT", "WITH", "SHOW", "EXPLAIN"}:
        raise ValueError(
            f"refusing non-read-only statement starting with {kw!r} "
            "(pass --write to allow)"
        )


def _split_statements(sql: str) -> list[str]:
    """Split on ``;``, drop empty / comment-only chunks."""
    parts: list[str] = []
    for chunk in sql.split(";"):
        stripped = chunk.strip()
        if not stripped:
            continue
        if not _first_keyword(stripped):
            continue
        parts.append(stripped)
    return parts


def _fmt_cell(value: Any) -> str:
    if value is None:
        return "NULL"
    text_val = str(value).replace("\t", " ").replace("\n", "\\n")
    if len(text_val) > _CELL_MAX:
        return text_val[: _CELL_MAX - 3] + "..."
    return text_val


def _print_result(result: Result) -> None:
    if result.returns_rows:
        keys = list(result.keys())
        print("\t".join(keys))
        rows = result.fetchall()
        for row in rows:
            print("\t".join(_fmt_cell(v) for v in row))
        print(f"-- {len(rows)} row(s)")
    else:
        print(f"-- ok (rowcount={result.rowcount})")


def _run_sql(engine: Engine, sql: str, *, allow_write: bool) -> None:
    statements = _split_statements(sql)
    if not statements:
        print("error: no SQL statements to run", file=sys.stderr)
        raise SystemExit(1)
    for stmt in statements:
        _assert_read_only(stmt, allow_write=allow_write)
    connect = engine.begin if allow_write else engine.connect
    with connect() as conn:
        for stmt in statements:
            result = conn.execute(text(stmt))
            _print_result(result)

def cmd_tables(engine: Engine, schema: str | None) -> None:
    sql = """
        SELECT table_schema AS schema, table_name AS "table"
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
    """
    params: dict[str, str] = {}
    if schema:
        sql += " AND table_schema = :schema"
        params["schema"] = schema
    sql += " ORDER BY table_schema, table_name"
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        _print_result(result)


def cmd_peek(engine: Engine, table: str, limit: int) -> None:
    if limit < 1:
        raise ValueError("--limit must be >= 1")
    qualified = _qualify_table(table)
    # Identifiers are validated; limit is an int — safe to interpolate.
    sql = f"SELECT * FROM {qualified} LIMIT {int(limit)}"
    _run_sql(engine, sql, allow_write=False)


def cmd_sql(
    engine: Engine,
    *,
    query: str | None,
    file: Path | None,
    allow_write: bool,
) -> None:
    chunks: list[str] = []
    if query:
        chunks.append(query)
    if file is not None:
        path = file.resolve()
        if not path.is_file():
            print(f"error: SQL file not found: {path}", file=sys.stderr)
            raise SystemExit(1)
        chunks.append(path.read_text(encoding="utf-8"))
    if not chunks:
        print("error: provide --query and/or --file", file=sys.stderr)
        raise SystemExit(1)
    _run_sql(engine, "\n;\n".join(chunks), allow_write=allow_write)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_tables = sub.add_parser("tables", help="List base tables via information_schema")
    p_tables.add_argument(
        "--schema",
        default=None,
        help="Filter to one schema (e.g. public or kma)",
    )

    p_peek = sub.add_parser("peek", help="SELECT * FROM table LIMIT N")
    p_peek.add_argument("table", help="Table name or schema.table")
    p_peek.add_argument("--limit", type=int, default=20, help="Row limit (default 20)")

    p_sql = sub.add_parser("sql", help="Run inline SQL and/or a .sql file")
    p_sql.add_argument("--query", "-q", default=None, help="SQL string")
    p_sql.add_argument("--file", "-f", type=Path, default=None, help="Path to .sql file")
    p_sql.add_argument(
        "--write",
        action="store_true",
        help="Allow non-SELECT statements (INSERT/UPDATE/DDL/…)",
    )

    args = parser.parse_args()
    db_url = build_db_url()
    print(_connection_banner(db_url), file=sys.stderr)

    engine = _make_engine()
    try:
        if args.command == "tables":
            cmd_tables(engine, args.schema)
        elif args.command == "peek":
            cmd_peek(engine, args.table, args.limit)
        elif args.command == "sql":
            cmd_sql(
                engine,
                query=args.query,
                file=args.file,
                allow_write=args.write,
            )
        else:
            parser.error(f"unknown command: {args.command}")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 — surface DB errors cleanly for CLI
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
