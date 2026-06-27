"""MBM Mod Loader — root entry point.

Adds src/ to sys.path then delegates to src/main.py.
This file is registered as __main__ by Python, so importing 'main' below
resolves to src/main.py without conflict.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mainui import main  # noqa: E402 — resolves to src/mainui.py

if __name__ == "__main__":
    main()
