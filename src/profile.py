"""Profile handling for MBM Mod Loader.

A profile is a named list of mods, stored as a JSON file in the config folder.
The user may keep several profile files, but only one is loaded in the
application at a time.

Each profile also records the application version that wrote it, so a future
version can detect (and migrate) configs made by an older one.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import lang
from config import get_config_dir
from installed_mod import InstalledMod
from version import APP_VERSION

DEFAULT_PROFILE_NAME = "default"


@dataclass
class Profile:
    """An in-memory profile, backed by a JSON file on disk."""

    name: str
    app_version: str
    game_folder_path: str = ""
    mods: list[InstalledMod] = field(default_factory=list)
    favorite: bool = False
    path: Path = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "app_version": self.app_version,
            "favorite": self.favorite,
            "game_folder_path": self.game_folder_path,
            "mods": [{"name": m.name} for m in self.mods],
        }

    @classmethod
    def from_dict(cls, data: dict, path: Path) -> "Profile":
        mods = [
            InstalledMod(name=m["name"])
            for m in data.get("mods", [])
            if isinstance(m, dict) and "name" in m
        ]
        return cls(
            name=data.get("name", path.stem),
            app_version=data.get("app_version", "unknown"),
            game_folder_path=data.get("game_folder_path", ""),
            mods=mods,
            favorite=data.get("favorite", False),
            path=path,
        )

    def save(self) -> None:
        """Write the profile to its JSON file."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


def list_profiles(logger: logging.Logger = None) -> list:
    """Return every valid profile found in the config folder.

    A file counts as valid if it is JSON that parses into an object. Malformed
    files are skipped (and logged as a warning when a logger is given).
    """
    profiles = []
    for path in get_config_dir().glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
            profiles.append(Profile.from_dict(data, path))
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            if logger:
                logger.warning(f"Skipping invalid profile '{path.name}': {exc}")
    return profiles


def toggle_favorite(path: Path, logger: logging.Logger = None) -> bool:
    """Toggle the favorite flag of the profile at ``path``.

    - If it was the favorite, it becomes non-favorite (the file is updated).
    - If it was not, it becomes the favorite and every other profile is set to
      non-favorite (at most one favorite can exist; zero is allowed).

    Returns the profile's new favorite state.
    """
    path = Path(path).resolve()
    profiles = list_profiles(logger)
    target = next((p for p in profiles if p.path.resolve() == path), None)
    if target is None:
        return False

    if target.favorite:
        target.favorite = False
        target.save()
        if logger:
            logger.info(f"Unset favorite: '{target.name}' ({path.name})")
        return False

    # Make this the sole favorite; clear the flag on all others.
    for prof in profiles:
        should_be = prof.path.resolve() == path
        if prof.favorite != should_be:
            prof.favorite = should_be
            prof.save()
    if logger:
        logger.info(f"Set favorite: '{target.name}' ({path.name})")
    return True


def sanitize_name(name: str) -> str:
    """Normalize a user-entered profile name (trim and collapse whitespace)."""
    return " ".join(name.split())


def create_profile(name: str, logger: logging.Logger = None) -> Profile:
    """Create a new profile file initialized with the default content.

    The new profile is never the favorite (the existing favorite, if any, is
    left untouched). Raises ValueError on an empty/invalid name and
    FileExistsError if a profile with that name already exists.
    """
    name = sanitize_name(name)
    if not name:
        raise ValueError(lang.t("errors.profile_name_empty"))
    if any(c in name for c in r'\/:*?"<>|'):
        raise ValueError(lang.t("errors.profile_name_invalid_chars"))

    path = get_config_dir() / f"{name}.json"
    if path.exists():
        raise FileExistsError(lang.t("errors.profile_already_exists").format(name=name))

    profile = Profile(name=name, app_version=APP_VERSION, favorite=False, path=path)
    profile.save()
    if logger:
        logger.info(f"Created profile: '{name}' ({path.name})")
    return profile


def _create_default_profile() -> Profile:
    """Build a fresh default profile and write it to disk."""
    path = get_config_dir() / f"{DEFAULT_PROFILE_NAME}.json"
    profile = Profile(name=DEFAULT_PROFILE_NAME, app_version=APP_VERSION,
                      favorite=True, path=path)
    profile.save()
    return profile


def load_profile(logger: logging.Logger) -> Profile:
    """Load the active profile, creating the default one if none exist.

    - Empty folder: create a new default profile, log that it was created,
      then load it.
    - One or more profiles: load the one the user marked as favorite; if none
      is marked, fall back to the most recently edited file. Either way, log
      the application version stored in it.
    """
    profiles = list_profiles(logger)

    if not profiles:
        profile = _create_default_profile()
        logger.info(f"No profile found - created new default profile: {profile.path.name}")
        return profile

    # Choose the favorite (or the latest edited).
    favorites = [p for p in profiles if p.favorite]
    if favorites:
        # If several are marked favorite, prefer the most recently edited.
        profile = max(favorites, key=lambda p: p.path.stat().st_mtime)
        reason = "favorite"
    else:
        profile = max(profiles, key=lambda p: p.path.stat().st_mtime)
        reason = "latest edited"

    logger.info(
        f"Loaded {reason} profile '{profile.name}' ({profile.path.name}) "
        f"made with application version {profile.app_version}"
    )
    return profile
