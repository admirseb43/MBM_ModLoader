"""Language string loader for MBM Mod Loader.

Call load() once at startup. Use t() anywhere to retrieve a localized string.
Keys use dot notation matching the JSON structure (e.g. "errors.invalid_folder_title").
"""

import json
from pathlib import Path

LANG_DIR = Path(__file__).resolve().parent.parent / "language"

_strings: dict = {}


def load(lang_name: str = "eng") -> None:
    """Load the given language file into memory."""
    global _strings
    with open(LANG_DIR / f"{lang_name}.json", encoding="utf-8") as f:
        _strings = json.load(f)


def t(key: str) -> str:
    """Return the string for a dot-separated key (e.g. 'buttons.ok')."""
    node = _strings
    for part in key.split("."):
        node = node[part]
    return str(node)
