"""Configuration storage for MBM Mod Loader.

Creates a "_mbm_ml_configs" folder next to the script (only if missing).
"""

from pathlib import Path

CONFIG_DIR_NAME = "_mbm_ml_configs"


def get_config_dir() -> Path:
    """Return the config directory (next to this script), creating it if missing."""
    config_dir = Path(__file__).resolve().parent.parent / CONFIG_DIR_NAME
    config_dir.mkdir(exist_ok=True)
    return config_dir
