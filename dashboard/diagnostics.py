"""Startup diagnostics for the public deploy.

The public deploy can fail before any page renders: the DuckDB artifact is
downloaded from a private Hugging Face Dataset at startup, and any problem there
is reported to the viewer with one generic, bilingual message
(``error.artifact_unavailable``). The *reason* must therefore be recoverable from
the Cloud logs alone.

This module is that log channel. For every startup failure it records:

* a stable **stage marker** -- one of :data:`STAGE_SECRETS_MISSING`,
  :data:`STAGE_DOWNLOAD_FAILED`, :data:`STAGE_FILE_NOT_FOUND`,
  :data:`STAGE_DUCKDB_OPEN_FAILED`, :data:`STAGE_QUERY_FAILED`;
* the exception **class name** (never a traceback -- an uncaught failure already
  renders one; these are the failures the generic message hides);
* a **sanitised** message.

It also records which configuration *names* are present or absent. Values are
never logged, and a token length or prefix is never logged either: presence is
the only fact written.

Everything goes to ``stdout`` through the standard :mod:`logging` module -- the
stream Streamlit Community Cloud captures -- and every message is passed through
:func:`src.utils.sanitize.sanitize_text` with the live ``HF_TOKEN`` value as an
exact-match secret, so a credential cannot reach the log even if a library
embeds it in an exception message.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Final

from dashboard.settings import get_setting
from src.utils.sanitize import sanitize_text

#: Logger name; ``dashboard.startup`` is the one line to grep for in Cloud logs.
LOGGER_NAME: Final[str] = "dashboard.startup"

STAGE_SECRETS_MISSING: Final[str] = "secrets-missing"
STAGE_DOWNLOAD_FAILED: Final[str] = "download-failed"
STAGE_FILE_NOT_FOUND: Final[str] = "file-not-found"
STAGE_DUCKDB_OPEN_FAILED: Final[str] = "duckdb-open-failed"
STAGE_QUERY_FAILED: Final[str] = "query-failed"

#: The stage markers, exported so a caller (and the tests) can enumerate them.
STAGES: Final[tuple[str, ...]] = (
    STAGE_SECRETS_MISSING,
    STAGE_DOWNLOAD_FAILED,
    STAGE_FILE_NOT_FOUND,
    STAGE_DUCKDB_OPEN_FAILED,
    STAGE_QUERY_FAILED,
)

#: Configuration names whose *presence* is logged. These are the settings the
#: public deploy needs; a missing name is the first thing to check in the logs.
TRACKED_SETTINGS: Final[tuple[str, ...]] = (
    "HF_DATASET_REPO",
    "HF_DATASET_FILENAME",
    "HF_TOKEN",
)

#: The one tracked setting whose value is a credential. Only its value is passed
#: to the sanitiser (as an exact-match secret); it is never logged.
SECRET_SETTING: Final[str] = "HF_TOKEN"


class _StdoutHandler(logging.StreamHandler[Any]):
    """A stdout handler tagged so it is installed at most once per process."""


def _logger() -> logging.Logger:
    """Return the diagnostics logger, wiring a stdout handler on first use.

    Community Cloud captures ``stdout``; the handler is added once per process
    (detected by its type, so no module-level flag is needed). ``propagate`` is
    left at its default (``True``) so the record is still visible to any root
    handler a test runner installs, while the logger's own handler guarantees the
    Cloud log line.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(handler, _StdoutHandler) for handler in logger.handlers):
        handler = _StdoutHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def sanitize(message: str) -> str:
    """Redact credentials from a free-text message.

    The live ``HF_TOKEN`` value is passed as an exact-match secret, so it is
    removed wherever it appears; ``sanitize_text`` also removes ``key=value``
    credentials and ``Authorization: Bearer`` headers.
    """
    return sanitize_text(message, secrets=[get_setting(SECRET_SETTING)])


def log_settings_presence() -> None:
    """Log which tracked setting NAMES are present or absent.

    Only the names are written -- never a value, a token length, or a token
    prefix.
    """
    present = [name for name in TRACKED_SETTINGS if get_setting(name)]
    absent = [name for name in TRACKED_SETTINGS if not get_setting(name)]
    _logger().info(
        "startup config: present=%s absent=%s",
        ",".join(present) or "-",
        ",".join(absent) or "-",
    )


def log_failure(stage: str, exc: BaseException | None = None, *, detail: str | None = None) -> None:
    """Log one startup failure with its stage marker, class name and message.

    Args:
        stage: One of :data:`STAGES`; recorded verbatim so a log search is exact.
        exc: The caught exception. Its class name is logged; the message is
            sanitised. May be ``None`` when the failure has no exception (for
            example a missing setting).
        detail: An explicit message to use instead of ``str(exc)``. Sanitised the
            same way.
    """
    exc_name = type(exc).__name__ if exc is not None else "-"
    raw = detail if detail is not None else (str(exc) if exc is not None else "")
    _logger().error("stage=%s exception=%s message=%s", stage, exc_name, sanitize(raw))
