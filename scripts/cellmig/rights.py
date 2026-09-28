"""Copyright and credit of the images the site shows (#28).

data/media.yaml is the single source: one entry per image file (path,
type, rights, creators or owner or source). The website code is MIT
licensed (LICENSE); images are not: each keeps the rights recorded here.

  rights: all-rights-reserved   lab or personal work; credit "© creators"
          third-party           journal covers, logos, publisher figures:
                                their owners' rights (`source` names them)
          CC-BY-4.0 / CC0-1.0   only by an explicit decision for that file
          unknown               not yet established: no credit is shown and
                                no licence is ever implied

Every local image the build uses is recorded (images.source(), media()) and
check_all_recorded() stops the build if one has no entry. Nothing here is
inferred: a creator is only listed when it is public (e.g. a caption credit).
"""

from functools import cache
from typing import Any

from .config import DATA, fail, load

RIGHTS = ("all-rights-reserved", "third-party", "CC-BY-4.0", "CC0-1.0", "unknown")
OPEN_LICENCES = {"CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
                 "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/"}
TYPES = ("microscopy", "photo", "portrait", "journal-cover", "paper-figure", "logo", "software-media")
KEYS = {"path", "type", "rights", "creators", "owner", "source", "source_url"}
Entry = dict[str, Any]
_used: set[str] = set()


@cache
def registry() -> dict[str, Entry]:
    """data/media.yaml by path, checked."""
    out: dict[str, Entry] = {}
    for e in load(DATA / "media.yaml")["media"]:
        where = f"data/media.yaml ({e.get('path')})"
        if set(e) - KEYS:
            fail(f"{where}: unknown keys {sorted(set(e) - KEYS)}")
        if e.get("type") not in TYPES or e.get("rights") not in RIGHTS:
            fail(f"{where}: type must be one of {TYPES} and rights one of {RIGHTS}")
        if e["rights"] == "third-party" and not e.get("source"):
            fail(f"{where}: third-party material needs `source` (whose it is)")
        if e["rights"] == "third-party" and (e.get("creators") or e.get("owner")):
            fail(f"{where}: third-party material is not the lab's: no creators/owner")
        if e["rights"] in ("all-rights-reserved", *OPEN_LICENCES) and not (e.get("creators") or e.get("owner")):
            fail(f"{where}: {e['rights']} needs `creators` (or `owner`); use `unknown` when they are not known")
        if e["path"] in out:
            fail(f"{where}: listed twice")
        out[e["path"]] = e
    return out


def use(site_path: str) -> None:
    """Record that the site shows this local file."""
    _used.add(site_path)


def entry(site_path: str) -> Entry:
    """The rights entry of an image the site shows."""
    e = registry().get(site_path)
    if e is None:
        fail(f"data/media.yaml: add an entry (path, type, rights) for {site_path}; "
             "use rights: unknown if its copyright is not established")
    return e


def credit(site_path: str) -> str:
    """Public credit line ("© Emilia Peuhu and Guillaume Jacquemet",
    "Cover © the publisher"), or "" when unknown."""
    e = entry(site_path)
    if e["rights"] == "unknown":
        return ""
    if e["type"] == "journal-cover":   # the caption names the journal; the cover is its publisher's
        return "Cover © the publisher"
    who = e.get("creators") or [e.get("owner") or e["source"]]
    return "© " + " and ".join([", ".join(who[:-1]), who[-1]] if len(who) > 1 else who)


def image_object(site_path: str, url: str) -> dict[str, Any]:
    """schema.org ImageObject with the rights that are established: creator
    and creditText when known, copyrightNotice, and a licence URL only for an
    open licence (never for all-rights-reserved, third-party or unknown)."""
    e = entry(site_path)
    item: dict[str, Any] = {"@type": "ImageObject", "contentUrl": url}
    if e.get("creators"):
        item["creator"] = [{"@type": "Person", "name": n} for n in e["creators"]]
    text = credit(site_path)
    if text:
        item["creditText"] = text.split("© ", 1)[1]
        item["copyrightNotice"] = text
    if e["rights"] in OPEN_LICENCES:
        item["license"] = OPEN_LICENCES[e["rights"]]
    return item


def check_all_recorded() -> None:
    """Every local image the site used has an entry (and an unused entry is a
    leftover to remove)."""
    missing = sorted(p for p in _used if p not in registry())
    if missing:
        fail(f"data/media.yaml: no rights entry for {len(missing)} image(s) the site shows: {missing[:8]}"
             f"{' ...' if len(missing) > 8 else ''}; add them (rights: unknown if not established)")
    unused = sorted(set(registry()) - _used)
    if unused:
        fail(f"data/media.yaml: entries for images the site no longer shows, remove them: {unused[:8]}")
