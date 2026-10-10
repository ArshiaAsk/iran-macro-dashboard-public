"""Visibility rules for the public (Streamlit Community Cloud) deploy.

When ``DASHBOARD_PUBLIC_MODE`` is on, the Market and FX & Gold pages are hidden
-- from the sidebar, from the Overview's per-domain links, and from direct URL
access (the page modules refuse to render) -- and data downloads are disabled
(see :mod:`dashboard.components.exports`).

The rules are pure given ``is_public_mode()``; the page registry itself
(:data:`dashboard.navigation.PAGES`) is never mutated.
"""

from __future__ import annotations

from typing import Final

import streamlit as st

from dashboard.i18n import t
from dashboard.navigation import PAGES, PageSpec, page_for_domain
from dashboard.settings import is_public_mode

#: Pages hidden in public mode, by registry key.
PUBLIC_HIDDEN_PAGE_KEYS: Final[frozenset[str]] = frozenset({"market", "fx_gold"})


def hidden_page_keys() -> frozenset[str]:
    """Return the hidden page keys for the current mode (empty when not public)."""
    return PUBLIC_HIDDEN_PAGE_KEYS if is_public_mode() else frozenset()


def visible_pages(*, public_mode: bool | None = None) -> tuple[PageSpec, ...]:
    """Return the pages to register, in registry order.

    Args:
        public_mode: Force a mode (tests); defaults to the live setting.
    """
    is_public = is_public_mode() if public_mode is None else public_mode
    if not is_public:
        return PAGES
    return tuple(spec for spec in PAGES if spec.key not in PUBLIC_HIDDEN_PAGE_KEYS)


def visible_page_for_domain(domain: str) -> PageSpec | None:
    """Return the page that owns ``domain``, or ``None`` when it is hidden.

    Wraps :func:`dashboard.navigation.page_for_domain` so the Overview's
    per-domain links never point at a page the public deploy does not serve.
    """
    owner = page_for_domain(domain)
    if owner is not None and owner.key in hidden_page_keys():
        return None
    return owner


def require_page_visible(key: str) -> None:
    """Stop a page's render when it is hidden in public mode.

    Called at the top of a hidden page module so a direct URL access cannot
    bypass the navigation filter.
    """
    if key in hidden_page_keys():
        st.error(t("note.public_page_hidden"))
        st.stop()
