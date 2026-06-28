import json
import re
import time
import urllib.error
import urllib.request

_rate_limit_reset: float = 0.0  # Unix timestamp; 0 = not blocked


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    def __init__(self, reset_at: float) -> None:
        self.reset_at = reset_at
        super().__init__(f"GitHub rate limit exceeded, resets at {reset_at}")


def _check_rate_limit() -> None:
    if _rate_limit_reset and time.time() < _rate_limit_reset:
        raise RateLimitError(_rate_limit_reset)


def _raise_if_rate_limited(exc: urllib.error.HTTPError) -> None:
    global _rate_limit_reset
    if exc.code in (403, 429):
        reset_header = exc.headers.get("X-RateLimit-Reset")
        _rate_limit_reset = float(reset_header) if reset_header else time.time() + 3600
        raise RateLimitError(_rate_limit_reset) from exc
    raise exc


def get_all_releases(url_repo: str) -> list[str]:
    """Return every release tag name from a GitHub repository URL."""
    _check_rate_limit()
    match = re.search(r"github\.com/([^/]+/[^/?#]+)", url_repo)
    if not match:
        raise ValueError(f"Not a GitHub URL: {url_repo}")
    slug = match.group(1).rstrip("/")
    api_url = f"https://api.github.com/repos/{slug}/releases"
    req = urllib.request.Request(api_url, headers={"User-Agent": "MBM-ModLoader/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return [r["tag_name"] for r in json.loads(resp.read().decode())]
    except urllib.error.HTTPError as exc:
        _raise_if_rate_limited(exc)


def get_release_asset_url(url_repo: str, tag: str) -> tuple[str, str]:
    """Return (download_url, filename) for the best downloadable asset of a release.

    Prefers .zip assets; falls back to .dll; then any asset.
    Raises ValueError if nothing is found.
    """
    _check_rate_limit()
    match = re.search(r"github\.com/([^/]+/[^/?#]+)", url_repo)
    if not match:
        raise ValueError(f"Not a GitHub URL: {url_repo}")
    slug = match.group(1).rstrip("/")
    api_url = f"https://api.github.com/repos/{slug}/releases/tags/{tag}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "MBM-ModLoader/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            release = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        _raise_if_rate_limited(exc)
    assets = release.get("assets", [])
    for ext in (".zip", ".dll"):
        for a in assets:
            if a["name"].lower().endswith(ext):
                return a["browser_download_url"], a["name"]
    if assets:
        return assets[0]["browser_download_url"], assets[0]["name"]
    raise ValueError(f"No downloadable asset in release '{tag}' for {url_repo}")


def get_releases(url_repo: str) -> list[str]:
    """Return the latest release tag from a GitHub repository URL as a single-item list.

    Returns an empty list if the repository has no releases.
    Raises ValueError if the URL is not a recognizable GitHub URL.
    Raises RateLimitError when GitHub rate limit is exceeded.
    Raises urllib.error.URLError / HTTPError on other network or HTTP failures.
    """
    _check_rate_limit()
    match = re.search(r"github\.com/([^/]+/[^/?#]+)", url_repo)
    if not match:
        raise ValueError(f"Not a GitHub URL: {url_repo}")
    slug = match.group(1).rstrip("/")
    api_url = f"https://api.github.com/repos/{slug}/releases/latest"
    req = urllib.request.Request(api_url, headers={"User-Agent": "MBM-ModLoader/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return [json.loads(resp.read().decode())["tag_name"]]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        _raise_if_rate_limited(exc)
