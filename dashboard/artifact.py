"""Startup loading of the dashboard's DuckDB artifact.

The public deploy (Streamlit Community Cloud) does not ship the DuckDB file in
its repository. The file lives in a **private** Hugging Face Dataset and is
fetched on first run with a read-only token, then reused for the life of the
process.

The local path is resolved by :func:`artifact_path`:

* ``DASHBOARD_DUCKDB_PATH`` -- an explicit local file, for development;
* otherwise ``<cache dir>/<HF_DATASET_FILENAME>`` where the cache dir is the
  system temp directory (or ``DASHBOARD_DUCKDB_CACHE_DIR`` when set).

When the file is absent, :func:`ensure_duckdb_artifact` downloads it from the
dataset named by ``HF_DATASET_REPO``. The token comes from ``HF_TOKEN``
(environment or ``st.secrets``); it is passed to ``huggingface_hub`` as a keyword
argument and is never logged, echoed, or embedded in an error message.

``huggingface_hub`` is imported lazily inside the download helper so importing
the dashboard never requires it (see ``test_import_isolation``).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Final

import streamlit as st

from dashboard.settings import get_setting

#: Default file name inside the Hugging Face Dataset.
DEFAULT_FILENAME: Final[str] = "dashboard.duckdb"

#: Sub-directory created under the system temp directory for the cached artifact.
DEFAULT_CACHE_SUBDIR: Final[str] = "iran-macro-dashboard"


class ArtifactUnavailableError(RuntimeError):
    """Raised when the dashboard's DuckDB artifact cannot be made available."""


def _cache_dir() -> Path:
    """Return the directory the downloaded artifact is cached under."""
    override = get_setting("DASHBOARD_DUCKDB_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(tempfile.gettempdir()) / DEFAULT_CACHE_SUBDIR


def artifact_path() -> Path:
    """Return the local path the dashboard expects the DuckDB file at."""
    override = get_setting("DASHBOARD_DUCKDB_PATH")
    if override:
        return Path(override).expanduser()
    filename = get_setting("HF_DATASET_FILENAME", DEFAULT_FILENAME) or DEFAULT_FILENAME
    return _cache_dir() / filename


def _download_artifact(target: Path) -> Path:
    """Fetch the artifact from the configured private dataset into ``target``.

    The download lands in a staging file that is atomically renamed into place,
    so a partial or interrupted transfer is never mistaken for a valid artifact
    by the next run.
    """
    repo_id = get_setting("HF_DATASET_REPO")
    if not repo_id:
        msg = "No DuckDB file and no HF_DATASET_REPO configured; cannot load the dashboard data."
        raise ArtifactUnavailableError(msg)

    filename = get_setting("HF_DATASET_FILENAME", DEFAULT_FILENAME) or DEFAULT_FILENAME
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        msg = "huggingface_hub is not installed; cannot download the dashboard data."
        raise ArtifactUnavailableError(msg) from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f"{target.name}.part")
    try:
        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            token=get_setting("HF_TOKEN"),
            cache_dir=str(target.parent / "hf-cache"),
        )
        shutil.copyfile(downloaded, staging)
        staging.replace(target)
    except Exception as exc:
        # The token is passed to huggingface_hub as a keyword argument and is
        # never interpolated into this message, so the error cannot leak it.
        staging.unlink(missing_ok=True)
        msg = (
            f"Could not download {filename!r} from the configured dataset "
            f"({type(exc).__name__})."
        )
        raise ArtifactUnavailableError(msg) from exc
    return target


def _ensure_artifact() -> Path:
    """Return a local DuckDB path, downloading it when absent (uncached core)."""
    path = artifact_path()
    if path.is_file():
        return path
    if get_setting("DASHBOARD_DUCKDB_PATH"):
        msg = f"DASHBOARD_DUCKDB_PATH points at a missing file: {path}"
        raise ArtifactUnavailableError(msg)
    return _download_artifact(path)


@st.cache_resource(show_spinner="Downloading dashboard data...")
def ensure_duckdb_artifact() -> Path:
    """Return the local DuckDB path, downloading it once per process.

    ``st.cache_resource`` keeps the download to a single run for the lifetime of
    the Streamlit process: the returned path is a resource, not per-run data.
    """
    return _ensure_artifact()
