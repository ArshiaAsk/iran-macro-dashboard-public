# Iran Macroeconomic Dashboard — public deploy

A read-only, Persian (RTL) Streamlit dashboard over a set of derived and
aggregated Iranian macroeconomic indicators. This repository is the **minimal
deploy bundle**: only the dashboard, the `src` modules it imports, and a pinned
`requirements.txt`. It contains no data, no tests, and none of the collection
stack.

The dashboard reads a single DuckDB file that is **downloaded at startup** from a
private Hugging Face Dataset using a read-only token. The file itself is never
committed here.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit it
streamlit run streamlit_app.py
```

To develop against a local export instead of the dataset, point the app at the
file directly:

```bash
DASHBOARD_DUCKDB_PATH=/path/to/dashboard.duckdb streamlit run streamlit_app.py
```

## Configuration

| Setting | Purpose |
| --- | --- |
| `DASHBOARD_PUBLIC_MODE` | `1` forces public mode. Optional in this bundle, which already defaults to public. |
| `DASHBOARD_INTERNAL_MODE` | `1` is the explicit opt-in to the internal build from this bundle (Market and FX & Gold visible, downloads on). |
| `HF_DATASET_REPO` | Private Hugging Face Dataset id, e.g. `user/iran-macro-dashboard-data`. |
| `HF_DATASET_FILENAME` | File name inside the dataset (default `dashboard.duckdb`). |
| `HF_TOKEN` | Read-only token with access to that dataset. Never logged. |
| `DASHBOARD_DUCKDB_PATH` | Local file override for development (skips the download). |
| `DASHBOARD_DB_URL` | Explicit backend override, e.g. `duckdb:////abs/path.duckdb`. |

Values are read from the environment first, then Streamlit secrets.

## Public mode is fail-safe

This bundle ships `dashboard/_public_bundle.py`, which flips the mode default to
**public**: downloads are disabled and the Market and FX & Gold pages are hidden
even if `DASHBOARD_PUBLIC_MODE` is missing or misspelled. Running the internal
build from this bundle requires the explicit `DASHBOARD_INTERNAL_MODE=1` opt-in.
The main project repository does not ship that marker, so its development default
stays internal.

## Data attribution and licence

The dashboard presents **derived and aggregated indicators**. Underlying data
remain subject to each source's terms and are **not relicensed** by this project.
Sources include the World Bank, the IMF, the U.S. Energy Information
Administration (EIA), TGJU, the Statistical Center of Iran (SCI), the Tehran
Stock Exchange (TSETMC), and the Iran Household Budget Survey (HBSIR). Please
consult each source for its own terms of use.

## Licence

The **source code** in this repository is released under the MIT Licence — see
`LICENSE`. The **data** the dashboard displays is not covered by that licence and
remains subject to the terms of its original publishers.

The bundled Vazirmatn font (`static/Vazirmatn.ttf`) is licensed under the SIL
Open Font Licence; its licence text ships alongside it at `static/OFL.txt`.
Streamlit serves the `static/` folder next to the entrypoint (`streamlit_app.py`)
at `app/static/...`, which is where the theme's `[[theme.fontFaces]]` URL points.

## Regenerating this bundle

This directory is generated from the main project repository by
`scripts/build_public_bundle.py`. Edit the main repository and regenerate; do not
edit the bundle in place.
