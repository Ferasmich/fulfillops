# Python packages

`runtime.txt` records the application dependencies installed in the Python 3.12 virtual environment. `development.txt` includes those packages plus pytest, HTTPX and Ruff. Install with `python -m pip install -r requirements/development.txt` for local work, or `runtime.txt` for application-only use.

These are pinned pip-freeze snapshots, not hash-verified cross-platform lock files. Clean image installation and security scanning remain later work.
