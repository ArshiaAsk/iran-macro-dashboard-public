"""Dialect portability helpers for the ORM schema and queries.

The platform is authored against PostgreSQL + TimescaleDB, but the read-only
dashboard can also run against a DuckDB export of three Gold/metadata tables
(see ``scripts/export_dashboard_db.py``). Two constructs are not portable:

- ``postgresql.JSONB`` -- DuckDB stores JSON as its own ``JSON`` type;
- ``.astext`` JSON access -- a PostgreSQL-only operator.

This module supplies a JSON type that resolves to ``JSONB`` on PostgreSQL and
to the dialect's JSON elsewhere, and a :func:`json_text` expression builder that
extracts an object key as text on both backends.
"""

from typing import Any, cast

from sqlalchemy import JSON, String, func, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import TypeDecorator


class PortableJSON(TypeDecorator[object]):
    """JSON column that is ``JSONB`` on PostgreSQL and ``JSON`` elsewhere.

    The PostgreSQL ``JSONB`` type keeps the platform's existing storage and
    indexing behavior unchanged; every other backend (DuckDB) gets its native
    JSON type. ``cache_ok`` is set because the type has no per-instance state.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]  # signature fixed by SQLAlchemy
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


def json_text(column: Any, key: str, *, dialect_name: str) -> ColumnElement[str]:
    """Return an expression extracting ``key`` from a JSON column as text.

    PostgreSQL uses the ``->>`` operator (defined for both ``json`` and
    ``jsonb``; ``json_extract_path_text`` is json-only and rejects a ``jsonb``
    argument). DuckDB uses ``json_extract_string`` with a JSON path. Both yield
    SQL NULL when the key is absent, so a missing ``derived_from`` stays NULL
    and the dashboard treats the row as a base series.

    Args:
        column: The JSON column expression (an ORM attribute or a ``Column``).
        key: The top-level object key to extract.
        dialect_name: ``session.get_bind().dialect.name``.

    Returns:
        A text expression, NULL when the key is absent.
    """
    if dialect_name == "duckdb":
        return func.json_extract_string(column, f"$.{key}")
    # ``return_type=String`` types the extraction as text (so an ``IN`` binds
    # plain strings, not JSON) and ``literal(..., String)`` forces the key to a
    # text bind parameter: without it the ``->>`` right operand inherits the
    # column's JSON type and PostgreSQL rejects ``jsonb ->> jsonb``.
    return cast(
        ColumnElement[str],
        column.op("->>", return_type=String)(literal(key, String)),
    )
