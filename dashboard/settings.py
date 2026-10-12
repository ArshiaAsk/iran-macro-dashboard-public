"""Runtime settings resolved from environment variables or Streamlit secrets.

The public deploy is configured entirely through Streamlit's secrets
(``st.secrets``) while local development uses environment variables / ``.env``.
This module is the one place that reads either, so the backend switch, the
public-mode flag and the Hugging Face token are resolved consistently and no
caller touches ``st.secrets`` directly.

Public mode is **fail-safe**: the generated public bundle defaults to public
even if ``DASHBOARD_PUBLIC_MODE`` is missing or misspelled, and the internal
build can only be reached there through the explicit ``DASHBOARD_INTERNAL_MODE``
opt-in. The main repository keeps internal as its default so local development
is unchanged.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

import streamlit as st

#: Values that turn a boolean setting on.
_TRUTHY = frozenset({"1", "true", "yes", "on"})

#: Marker module shipped only by the generated public bundle. Its presence flips
#: the public-mode default, so the bundle stays public even when the mode
#: variable is absent or malformed. Kept in sync with
#: :data:`scripts.build_public_bundle.PUBLIC_BUNDLE_MARKER`.
BUNDLE_MARKER_MODULE = "dashboard._public_bundle"


def _is_public_bundle() -> bool:
    """True when the running code is the generated public-deploy bundle.

    Detected by the presence of the bundle's marker module, never by an
    environment variable -- an unset or mistyped variable must not be able to
    turn the public deploy back into the internal one.
    """
    try:
        return importlib.util.find_spec(BUNDLE_MARKER_MODULE) is not None
    except ModuleNotFoundError:  # pragma: no cover - parent package always importable here
        return False


#: Resolved once at import: the module set of a process does not change.
_IS_PUBLIC_BUNDLE_DEFAULT: bool = _is_public_bundle()


def is_public_bundle() -> bool:
    """True when the running code is the generated public-deploy bundle.

    The bundle ships no PostgreSQL driver, so the backend resolver uses this to
    treat a missing DuckDB source as a configuration error (reported with the
    friendly startup message) instead of falling back to PostgreSQL.
    """
    return _IS_PUBLIC_BUNDLE_DEFAULT


def get_setting(name: str, default: str | None = None) -> str | None:
    """Return a setting from the environment, else Streamlit secrets, else default.

    The environment wins so a local shell (or an AppTest) can override a
    deployed secret. ``st.secrets`` may be unconfigured (no ``secrets.toml``),
    in which case reading it raises; that is treated as "unset" rather than an
    error, because most local runs have no secrets file at all.
    """
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    try:
        secret: Any = st.secrets[name]
    except Exception:
        return default
    return str(secret)


def _truthy_setting(name: str) -> bool:
    """True when ``name`` is set to one of the recognised truthy tokens."""
    value = get_setting(name, "") or ""
    return value.strip().lower() in _TRUTHY


def is_public_mode() -> bool:
    """True when the dashboard should serve the public (restricted) build.

    Resolution order, most explicit first:

    1. ``DASHBOARD_PUBLIC_MODE`` truthy -- public, in both builds.
    2. ``DASHBOARD_INTERNAL_MODE`` truthy -- internal; the only opt-in that can
       override the public bundle's default.
    3. The build's default: public inside the generated bundle, internal in the
       main repository.

    A missing or malformed ``DASHBOARD_PUBLIC_MODE`` therefore leaves the public
    bundle public and the development checkout internal.
    """
    if _truthy_setting("DASHBOARD_PUBLIC_MODE"):
        return True
    if _truthy_setting("DASHBOARD_INTERNAL_MODE"):
        return False
    return _IS_PUBLIC_BUNDLE_DEFAULT
