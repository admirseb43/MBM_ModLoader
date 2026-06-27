import json
import re
import urllib.error
import urllib.request


def get_releases(url_repo: str) -> list[str]:
    """Return all release tag names from a GitHub repository URL.

    Raises ValueError if the URL is not a recognizable GitHub URL.
    Raises urllib.error.URLError / HTTPError on network or HTTP failures.
    """
    match = re.search(r"github\.com/([^/]+/[^/?#]+)", url_repo)
    if not match:
        raise ValueError(f"Not a GitHub URL: {url_repo}")
    slug = match.group(1).rstrip("/")
    api_url = f"https://api.github.com/repos/{slug}/releases"
    req = urllib.request.Request(api_url, headers={"User-Agent": "MBM-ModLoader/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return [r["tag_name"] for r in json.loads(resp.read().decode())]
