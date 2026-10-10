"""Declarative navigation registry for the dashboard information architecture.

The registry is plain data. ``st.Page`` objects are built from it inside the
running Streamlit entrypoint (``dashboard/app.py``), never at import time: outside
a script run ``st.Page`` silently degrades to a stub
(see ``docs/phase-7.1/wave-0-spike.md``). ``PageSpec.path`` is stored relative to
this package, and :func:`page_script_path` turns it into an absolute path so the
pages resolve the same whether the entrypoint is ``dashboard/app.py`` (local) or
the root-level ``streamlit_app.py`` used by the public deploy.

Sidebar labels are not stored here. Each page's nav label and in-page title are
both resolved from the string catalog (``nav.<key>`` / ``page.<key>``) so a
literal cannot survive outside ``dashboard/i18n.py`` and the two cannot drift.
Group names are stable keys for the same reason (``group.<key>``).

Owned domains mirror the Phase 7.1 plan: the all-domain views (Overview,
Comparison & Correlation, Data Catalog) own no domain, and every other page owns
exactly the domains it renders. ``economy`` is a dead domain and is never
claimed. The Welfare & Survey page owns ``welfare`` (split out of the old
Trade/Welfare/Energy page), the Market page owns ``market`` and the Labor page
owns ``labor`` (SCI's quarterly unemployment rate), so every plan domain has
exactly one owner.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: Directory holding this module and the ``pages/`` scripts.
DASHBOARD_DIR: Final[Path] = Path(__file__).resolve().parent

GROUP_OVERVIEW_ANALYSIS: Final[str] = "overview_analysis"
GROUP_DOMAINS: Final[str] = "domains"

GROUPS: Final[tuple[str, ...]] = (GROUP_OVERVIEW_ANALYSIS, GROUP_DOMAINS)
"""Sidebar section keys in display order; every page belongs to exactly one.

The Persian section labels live in ``dashboard/i18n.py`` as ``group.<key>``.
"""


@dataclass(frozen=True, slots=True)
class PageSpec:
    """One dashboard page: routing and ownership metadata.

    ``key`` is the stable per-page identifier and the i18n namespace: the nav
    label is ``nav.<key>`` and the in-page title is ``page.<key>``.
    """

    key: str
    path: str
    icon: str
    group: str
    domains: tuple[str, ...] = ()
    is_default: bool = False


PAGES: Final[tuple[PageSpec, ...]] = (
    PageSpec(
        key="overview",
        path="pages/1_Overview.py",
        icon=":material/overview:",
        group=GROUP_OVERVIEW_ANALYSIS,
        is_default=True,
    ),
    PageSpec(
        key="correlation",
        path="pages/6_Correlation.py",
        icon=":material/compare_arrows:",
        group=GROUP_OVERVIEW_ANALYSIS,
    ),
    PageSpec(
        key="catalog",
        path="pages/7_Data_Catalog.py",
        icon=":material/menu_book:",
        group=GROUP_OVERVIEW_ANALYSIS,
    ),
    PageSpec(
        key="inflation",
        path="pages/2_Inflation.py",
        icon=":material/show_chart:",
        group=GROUP_DOMAINS,
        domains=("inflation",),
    ),
    PageSpec(
        key="gdp",
        path="pages/3_GDP_Economy.py",
        icon=":material/analytics:",
        group=GROUP_DOMAINS,
        domains=("gdp",),
    ),
    PageSpec(
        key="trade_energy",
        path="pages/4_Trade_Welfare_Energy.py",
        icon=":material/swap_horiz:",
        group=GROUP_DOMAINS,
        domains=("trade", "energy"),
    ),
    PageSpec(
        key="welfare",
        path="pages/8_Welfare_Survey.py",
        icon=":material/home:",
        group=GROUP_DOMAINS,
        domains=("welfare",),
    ),
    PageSpec(
        key="fx_gold",
        path="pages/5_FX_Gold.py",
        icon=":material/currency_exchange:",
        group=GROUP_DOMAINS,
        domains=("fx", "gold"),
    ),
    PageSpec(
        key="market",
        path="pages/9_Market.py",
        icon=":material/trending_up:",
        group=GROUP_DOMAINS,
        domains=("market",),
    ),
    PageSpec(
        key="labor",
        path="pages/10_Labor.py",
        icon=":material/work:",
        group=GROUP_DOMAINS,
        domains=("labor",),
    ),
)
"""Dashboard pages in sidebar order, grouped by :data:`GROUPS`."""


def page_script_path(spec: PageSpec) -> Path:
    """Return the absolute path of ``spec``'s script file.

    ``st.Page`` and ``st.page_link`` resolve a relative path against Streamlit's
    "main script" directory, which is the repository root under the public-deploy
    entrypoint (``streamlit_app.py``) but ``dashboard/`` locally. Resolving
    against :data:`DASHBOARD_DIR` makes both entrypoints find the same files.

    Examples:
        >>> page_script_path(PAGES[0]).name
        '1_Overview.py'
    """
    return DASHBOARD_DIR / spec.path


def page_for_domain(domain: str) -> PageSpec | None:
    """Return the page that owns ``domain``, or ``None`` when unowned.

    Ownership is declared once in :data:`PAGES`, so the Overview's per-domain
    links and the domain-coverage test read the same declaration.

    Examples:
        >>> page_for_domain("inflation").key
        'inflation'
        >>> page_for_domain("economy") is None
        True
    """
    for spec in PAGES:
        if domain in spec.domains:
            return spec
    return None
