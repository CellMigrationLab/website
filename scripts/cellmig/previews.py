"""Link previews: what a pasted link to a page shows (title, text, picture).

Everything comes from data/previews.yaml; see the comments at its top. Pages
ask for their entry with preview("research"); at the end of the build,
check_all_used() stops the build if an entry matched no page.
"""

from functools import cache
from typing import Any

from .config import DATA, fail, load

ENTRY_KEYS = {"title", "description", "image"}
_used: set[str] = set()


@cache
def _data() -> dict[str, Any]:
    """data/previews.yaml, checked: every entry has a description and an image."""
    data = load(DATA / "previews.yaml")
    for key, entry in (data.get("pages") or {}).items():
        unknown = set(entry) - ENTRY_KEYS
        if unknown:
            fail(f"data/previews.yaml ({key}): unknown keys {sorted(unknown)}")
        if not entry.get("description") or not entry.get("image"):
            fail(f"data/previews.yaml ({key}): needs a description and an image")
    if not data.get("paper_image"):
        fail("data/previews.yaml: paper_image is missing")
    return data


def preview(key: str) -> dict[str, str]:
    """Page metadata for the page `key` (its path without .md): description,
    image and, when set, share_title. The build stops if there is no entry."""
    entry = (_data().get("pages") or {}).get(key)
    if not entry:
        fail(f"data/previews.yaml: add an entry for the page '{key}'")
    _used.add(key)
    out = {"description": " ".join(entry["description"].split()), "image": entry["image"]}
    if entry.get("title"):
        out["share_title"] = entry["title"]
    return out


def preview_text(key: str) -> str:
    """The description of page `key` (for llms.txt); the build stops if the
    page has no entry."""
    entry = (_data().get("pages") or {}).get(key)
    if not entry:
        fail(f"data/previews.yaml: add an entry for the page '{key}'")
    return " ".join(entry["description"].split())


def paper_image() -> str:
    """Preview picture for a featured paper that has no picture of its own."""
    return _data()["paper_image"]


def check_all_used() -> None:
    """Stop the build if data/previews.yaml has entries that match no page."""
    unused = sorted(set(_data().get("pages") or {}) - _used)
    if unused:
        fail(f"data/previews.yaml: no page called {unused} (typo, or a removed page?)")
