"""Configuration storage and base path helpers for MBM Mod Loader.

Two path roots exist:
  _bundle_dir()  — read-only bundled data (assets, language, data).
                   Points to sys._MEIPASS when frozen, project root otherwise.
  _app_dir()     — writable runtime directories (configs, logs, downloads).
                   Always the directory containing the exe / main.py.
"""

import sys
from pathlib import Path

CONFIG_DIR_NAME = "_mbm_ml_configs"


def _bundle_dir() -> Path:
    """Root for bundled read-only data files."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _app_dir() -> Path:
    """Root for runtime writable directories (next to the exe)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_config_dir() -> Path:
    """Return the config directory, creating it if missing."""
    config_dir = _app_dir() / CONFIG_DIR_NAME
    config_dir.mkdir(exist_ok=True)
    return config_dir
