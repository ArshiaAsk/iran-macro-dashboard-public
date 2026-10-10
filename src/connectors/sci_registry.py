"""SCI publication/canonical-indicator registry (dependency-light).

This module holds the SCI indicator registry as **plain data**: the unit and
frequency constants, the :class:`SciPublication` and
:class:`SciCanonicalIndicator` value types, and the two registry mappings. It
imports nothing but the standard library.

Why it exists: the dashboard renders SCI-derived series from this registry
(``dashboard/page_view.py``) but must not drag the scraper's browser/network
stack (playwright, requests, bs4, xlrd, openpyxl) into a read-only deploy. The
scraper (:mod:`src.connectors.sci_scraper`) and the parser
(:mod:`src.connectors.sci_parser`) import these names back from here, so their
public surface is unchanged and no ETL behavior moves.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NamedTuple

UNIT_INDEX = "index"
UNIT_PERCENT = "percent"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_QUARTERLY = "quarterly"


class SciPublication(NamedTuple):
    """
    One SCI publication and how to parse it.

    The first five fields mirror the plan's ``(indicator_id, name, domain,
    frequency, base_year)`` registry tuple; the rest make the entry actionable
    (where the file lives, which parser reads it, which series it contains).

    For a single-series workbook ``indicator_id`` is the series id. For a
    multi-series workbook (the decile publication) it is the **prefix** and
    ``series_ids`` enumerates the ten members.
    """

    indicator_id: str
    name: str
    domain: str
    frequency: str
    base_year: int | None
    path: str
    parser: str
    unit: str | None = UNIT_INDEX
    base_year_gregorian: int | None = None
    has_base_year_changes: bool = False
    base_years: tuple[int, ...] | None = None
    series_ids: tuple[str, ...] = ()
    parser_options: Mapping[str, Any] = {}
    via_browser: bool = False

    @property
    def member_ids(self) -> tuple[str, ...]:
        """Every series id this publication carries (one for single series)."""
        return self.series_ids or (self.indicator_id,)


# Publication slug -> metadata + file location. Paths/URLs are the real ones
# captured in Task 1 (tests/fixtures/sci/_capture.json); every base year is
# explicit in the file, never inferred from values.
SCI_INDICATOR_REGISTRY: dict[str, SciPublication] = {
    "cpi_national": SciPublication(
        indicator_id="SCI.CPI.NATIONAL.B2021",
        name="CPI - national (all households), base 1400=2021",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        base_year=1400,
        base_year_gregorian=2021,
        path="/Portals/0/Statistics/ts_national_140505-14050618165053.xlsx",
        parser="cpi_excel",
        unit=UNIT_INDEX,
        has_base_year_changes=True,
        base_years=(2016, 2021),
    ),
    "cpi_urban": SciPublication(
        indicator_id="SCI.CPI.URBAN.B2021",
        name="CPI - urban households, base 1400=2021",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        base_year=1400,
        base_year_gregorian=2021,
        path="/Portals/0/Statistics/ts_urban_140505-14050618165804.xlsx",
        parser="cpi_excel",
        unit=UNIT_INDEX,
        has_base_year_changes=True,
        base_years=(2016, 2021),
    ),
    "cpi_rural": SciPublication(
        indicator_id="SCI.CPI.RURAL.B2021",
        name="CPI - rural households, base 1400=2021",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        base_year=1400,
        base_year_gregorian=2021,
        path="/Portals/0/Statistics/ts_rural-140505-14050618165248.xlsx",
        parser="cpi_excel",
        unit=UNIT_INDEX,
        has_base_year_changes=True,
        base_years=(2016, 2021),
    ),
    "cpi_base1395": SciPublication(
        indicator_id="SCI.CPI.URBAN.B2016",
        name="CPI - urban households, base 1395=2016",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        base_year=1395,
        base_year_gregorian=2016,
        path="/Portals/0/Statistics/ts_cpi_1395=100-14040208113537.xlsx",
        parser="cpi_excel",
        unit=UNIT_INDEX,
        has_base_year_changes=True,
        base_years=(2016, 2021),
        # جدول 3 is the tidy long sheet (1361-01 … 1401-01). The wide جدول 1 only
        # starts at 1381-01 -- the same first period as the 1400-base workbooks --
        # so it offers no older history for the 1395->1400 splice to rescale.
        parser_options={"sheet": "جدول 3"},
    ),
    "cpi_decile": SciPublication(
        indicator_id="SCI.CPI.DECILE.B2021",
        name="CPI by household expenditure decile, base 1400=2021",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        base_year=1400,
        base_year_gregorian=2021,
        path="/Portals/0/Statistics/ts_decile_140505-14050618164745.xlsx",
        parser="cpi_decile_excel",
        unit=UNIT_INDEX,
        series_ids=tuple(f"SCI.CPI.DECILE.B2021.D{n}" for n in range(1, 11)),
    ),
    "unemployment_spring_1405": SciPublication(
        indicator_id="SCI.UNEMPLOYMENT.QUARTERLY",
        name="Unemployment rate (labour force survey, quarterly)",
        domain="labor",
        frequency=FREQUENCY_QUARTERLY,
        base_year=None,
        path="/Portals/0/Statistics/ne_niruye_kar_1405-01-14050525163749.xls",
        parser="unemployment_excel",
        unit=UNIT_PERCENT,
        parser_options={"jalali_year": 1405, "season": "بهار"},
    ),
}

DEFAULT_PUBLICATIONS: tuple[str, ...] = tuple(SCI_INDICATOR_REGISTRY)


@dataclass(frozen=True)
class SciCanonicalIndicator:
    """
    A chain-linked series built from one or more published base-year segments.

    The canonical id is what the catalog marks active and what Gold publishes;
    the ``B<year>`` segment ids stay in Silver and are seeded inactive.
    """

    indicator_id: str
    name: str
    domain: str
    frequency: str
    unit: str | None
    segment_ids: tuple[str, ...]
    base_years: tuple[int, ...]

    @property
    def has_base_year_changes(self) -> bool:
        """True when more than one published base must be linked."""
        return len(self.segment_ids) > 1


# Canonical CPI series and the published base-year segments that feed them.
# Only 1395 (2016) and 1400 (2021) are published (Task 1 finding), so a real
# multi-base link exists only for the urban series; the others carry one segment
# and link as a passthrough.
SCI_CANONICAL_INDICATORS: dict[str, SciCanonicalIndicator] = {
    "SCI.CPI.NATIONAL": SciCanonicalIndicator(
        indicator_id="SCI.CPI.NATIONAL",
        name="CPI - national (all households), chain-linked",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        unit=UNIT_INDEX,
        segment_ids=("SCI.CPI.NATIONAL.B2021",),
        base_years=(2021,),
    ),
    "SCI.CPI.URBAN": SciCanonicalIndicator(
        indicator_id="SCI.CPI.URBAN",
        name="CPI - urban households, chain-linked",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        unit=UNIT_INDEX,
        segment_ids=("SCI.CPI.URBAN.B2016", "SCI.CPI.URBAN.B2021"),
        base_years=(2016, 2021),
    ),
    "SCI.CPI.RURAL": SciCanonicalIndicator(
        indicator_id="SCI.CPI.RURAL",
        name="CPI - rural households, chain-linked",
        domain="inflation",
        frequency=FREQUENCY_MONTHLY,
        unit=UNIT_INDEX,
        segment_ids=("SCI.CPI.RURAL.B2021",),
        base_years=(2021,),
    ),
}
