"""Streamlit Community Cloud entrypoint.

Community Cloud runs ``streamlit run`` from the repository root and adds the
entrypoint's directory to ``sys.path``. Keeping this file at the root therefore
makes both the ``dashboard`` and ``src`` packages importable; a subdirectory
entrypoint would only put its own directory on the path and ``import dashboard``
would fail. The application itself lives in :mod:`dashboard.app`; this file only
boots it.
"""

from dashboard.app import main

main()
