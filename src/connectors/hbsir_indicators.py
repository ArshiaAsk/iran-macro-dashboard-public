"""HBSIR indicator id constants (dependency-light).

The dashboard's Welfare & Survey page renders HBSIR series by id
(``dashboard/page_view.py``), but it must not import the survey parser
(:mod:`src.connectors.hbsir_parser`), which pulls numpy/pandas and the ORM
schema. This module is the shared, standard-library-only home for the ids and
the poverty-line multiplier; :mod:`src.connectors.hbsir_parser` imports them
back, so its public surface and behavior are unchanged.
"""

GINI_INDICATOR = "HBSIR.GINI"
POVERTY_INDICATOR = "HBSIR.POVERTY.RATE"
DECILE_INDICATOR_PREFIX = "HBSIR.INCOME.DECILE.D"
DECILE_COUNT = 10
DECILE_INDICATORS = tuple(
    f"{DECILE_INDICATOR_PREFIX}{index}" for index in range(1, DECILE_COUNT + 1)
)
DEFAULT_INDICATORS = (GINI_INDICATOR, POVERTY_INDICATOR, *DECILE_INDICATORS)

DEFAULT_POVERTY_LINE_K = 0.5
