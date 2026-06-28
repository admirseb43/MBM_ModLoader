import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config import _bundle_dir
from mod_descriptor import ModDescriptor

DB_PATH = _bundle_dir() / "data" / "mod_database.json"


@dataclass
class ModDatabase:
    version: str
    last_edited: str
    mods: list[ModDescriptor] = field(default_factory=list)

    @staticmethod
    def load() -> "ModDatabase":
        with open(DB_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        mods = [ModDescriptor(**m) for m in raw.get("mods", [])]
        return ModDatabase(
            version=raw.get("version", "1.0.0"),
            last_edited=raw.get("last_edited", ""),
            mods=mods,
        )

    def save(self) -> None:
        self.last_edited = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = {
            "version": self.version,
            "last_edited": self.last_edited,
            "mods": [asdict(m) for m in self.mods],
        }
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
