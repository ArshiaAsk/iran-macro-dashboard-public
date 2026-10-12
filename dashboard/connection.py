"""Streamlit-specific database connection management.

The read-only backend is chosen by ``DASHBOARD_DB_URL`` (environment or
``st.secrets``): a ``duckdb://`` URL opens the exported DuckDB file used by the
public deploy, while anything else -- or nothing -- keeps the PostgreSQL /
TimescaleDB development workflow exactly as before.

When ``DASHBOARD_DB_URL`` is unset, a DuckDB backend is selected instead when a
local file (``DASHBOARD_DUCKDB_PATH``) or a private Hugging Face Dataset
(``HF_DATASET_REPO``) is configured; :mod:`dashboard.artifact` fetches and caches
that file. With neither set, the PostgreSQL configuration is used unchanged.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from dashboard.artifact import ArtifactUnavailableError, ensure_duckdb_artifact
from dashboard.diagnostics import (
    STAGE_DUCKDB_OPEN_FAILED,
    STAGE_QUERY_FAILED,
    STAGE_SECRETS_MISSING,
    log_failure,
)
from dashboard.repository import DashboardRepository
from dashboard.settings import get_setting, is_public_bundle
from src.database.connection import DatabaseConnection
from src.utils.config import get_config

#: URL scheme that selects the DuckDB backend.
DUCKDB_SCHEME = "duckdb"


class DuckDBConnection:
    """Read-only session factory over a DuckDB export file."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: Engine = create_engine(
            database_url,
            connect_args={"read_only": True},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Yield a request-scoped session, rolling back on error."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Return True when the DuckDB file can be queried.

        A failure here is the file failing to open read-only (missing, corrupt,
        or written by an incompatible DuckDB version). It is recorded with the
        ``duckdb-open-failed`` stage so the cause is visible in the Cloud log
        rather than only as the sidebar's offline dot.
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:
            log_failure(STAGE_DUCKDB_OPEN_FAILED, exc)
            return False
        return True

    def close(self) -> None:
        """Dispose of the engine's connection pool."""
        self.engine.dispose()


def _duckdb_url(path: Path | str) -> str:
    """Build a ``duckdb://`` SQLAlchemy URL for a local file path."""
    return f"{DUCKDB_SCHEME}:///{Path(path).expanduser().resolve()}"


def _duckdb_artifact_url() -> str | None:
    """Return a DuckDB URL when a local file or its source is configured.

    Both the explicit local path (development) and the private-dataset download
    resolve through :func:`dashboard.artifact.ensure_duckdb_artifact`, which
    raises :class:`dashboard.artifact.ArtifactUnavailableError` when the file is
    missing and cannot be fetched.
    """
    if not (get_setting("DASHBOARD_DUCKDB_PATH") or get_setting("HF_DATASET_REPO")):
        return None
    return _duckdb_url(ensure_duckdb_artifact())


def database_url() -> str:
    """Resolve the dashboard database URL.

    Precedence: an explicit ``DASHBOARD_DB_URL`` (any backend), then a DuckDB
    artifact (a local ``DASHBOARD_DUCKDB_PATH`` or a downloaded private-dataset
    file), then the PostgreSQL configuration used by local development.

    In the generated public bundle the PostgreSQL driver is not shipped, so a
    missing DuckDB source is a configuration error rather than a PostgreSQL
    fallback: it is reported with the friendly startup message (stage
    ``secrets-missing``) instead of an unhandled driver import error.
    """
    override = get_setting("DASHBOARD_DB_URL")
    if override:
        return override
    duckdb_url = _duckdb_artifact_url()
    if duckdb_url:
        return duckdb_url
    if is_public_bundle():
        detail = (
            "public bundle has no DuckDB source configured "
            "(DASHBOARD_DUCKDB_PATH and HF_DATASET_REPO are both unset)"
        )
        log_failure(STAGE_SECRETS_MISSING, detail=detail)
        raise ArtifactUnavailableError(detail, stage=STAGE_SECRETS_MISSING)
    return get_config().database.url


def _is_duckdb(url: str) -> bool:
    """True when the URL selects the DuckDB backend."""
    return url.split(":", 1)[0] == DUCKDB_SCHEME


@st.cache_resource(show_spinner="Connecting to database...")
def get_connection() -> DatabaseConnection | DuckDBConnection:
    """Create one cached connection for the dashboard process.

    A ``duckdb://`` ``DASHBOARD_DB_URL`` selects the read-only DuckDB export;
    otherwise the PostgreSQL/TimescaleDB connection is used unchanged.
    """
    url = database_url()
    if _is_duckdb(url):
        return DuckDBConnection(url)
    return DatabaseConnection(database_url=url)


@contextmanager
def repository_session() -> Generator[DashboardRepository, None, None]:
    """Yield a repository bound to a request-scoped database session.

    A query failure is recorded with the ``query-failed`` stage before it is
    re-raised, so a page's generic error state still leaves the cause in the
    Cloud log. An :class:`ArtifactUnavailableError` passes through unchanged: it
    is a startup failure the artifact loader has already recorded.
    """
    try:
        with get_connection().get_session() as session:
            yield DashboardRepository(session)
    except ArtifactUnavailableError:
        raise
    except Exception as exc:
        log_failure(STAGE_QUERY_FAILED, exc)
        raise
