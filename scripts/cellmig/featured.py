"""Featured research: every paper on which Guillaume is (co-)corresponding author.

The flag comes from the ledger (`me.corresponding_author`, copied as
`corresponding: true`, on the paper or any of its versions). data/featured.yaml
only adds a picture and a page address per paper; `hide: true` un-features a
paper. An entry for a paper that is not corresponding-author stops the build
(old addresses of removed pages are redirected in mkdocs.yml).
"""

import re
from typing import Any

from .config import DATA, FITS, fail, load
from .ledger import Ledger, Record
from .text import slugify

Story = dict[str, Any]

ENTRY_KEYS = {"doi", "image", "slug", "also", "hide", "summary", "fit", "area"}
# What a featured paper is mainly about; the home page shows the newest of
# each in its own group (config.HOME_FEATURED each). Required on every paper.
AREAS = {"biology": "Biology", "methods": "Methods and tools"}


def _entries(ledger: Ledger) -> dict[str, Record]:
    """data/featured.yaml entries, keyed by the DOI of the journal version."""
    out = {}
    for e in load(DATA / "featured.yaml") or []:
        unknown = set(e) - ENTRY_KEYS
        if unknown:
            fail(f"data/featured.yaml ({e.get('doi')}): unknown keys {sorted(unknown)}")
        rec = ledger.require(e["doi"], "data/featured.yaml")
        for d in e.get("also") or []:
            ledger.require(d, f"data/featured.yaml ({e['doi']}, also)")
        key = ledger.published_version(rec)["doi"].lower()
        if key in out:
            fail(f"data/featured.yaml: {e['doi']} and {out[key]['doi']} are the same paper")
        out[key] = e
    return out


SLUG_LENGTH = 90
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def _title_slug(title: str) -> str:
    """Page address from a title, at most SLUG_LENGTH characters, cut at a word."""
    slug = slugify(title)
    return slug if len(slug) <= SLUG_LENGTH else slug[:SLUG_LENGTH + 1].rsplit("-", 1)[0]


def _fit(entry: Record) -> str:
    """How the card shows the picture: cover (fill the square) unless `fit: contain`."""
    fit = entry.get("fit", "cover")
    if fit not in FITS:
        fail(f"data/featured.yaml ({entry['doi']}): fit must be one of {sorted(FITS)}")
    return fit


def _summary(main: Record, pubs: list[Record], entry: Record) -> str:
    """The text of a featured page: `summary:` in data/featured.yaml, else
    the papers' abstracts. A paper with no abstract (an editorial, say) needs
    a summary: the build stops otherwise."""
    text = entry.get("summary") or "\n\n".join(p["abstract"] for p in pubs if "abstract" in p)
    if not text.strip():
        fail(f"featured paper {main['doi']} has no abstract in things_done; add `summary:` for it to data/featured.yaml")
    return text


def _story(ledger: Ledger, main: Record, entry: Record) -> Story:
    """A featured item: the paper (plus any `also` papers) and its presentation."""
    pubs = [main] + [ledger.published_version(ledger.get(d)) for d in entry.get("also") or []]
    family = [main, *ledger.related(main)]
    return {
        "papers": [main["doi"], *(entry.get("also") or [])],
        "pubs": pubs,
        "image": entry.get("image"),
        "fit": _fit(entry),
        "area": entry.get("area"),
        "title": main["title"],
        "slug": entry.get("slug") or _title_slug(main["title"]),
        "year": int(main["year"]),
        # Journal date as far as the lag report knows it (Ledger.dates), else None.
        "date": next((ledger.dates[r["doi"].lower()] for r in family if r["doi"].lower() in ledger.dates), None),
        "summary": _summary(main, pubs, entry),
    }


def load_featured(ledger: Ledger) -> list[Story]:
    """Featured papers, newest first.

    Order: as Ledger.grouped: year, then the date as far as it is known
    (papers with no known date come after dated ones of the same year), then
    ledger order."""
    entries = _entries(ledger)
    featured, used = [], set()
    for main in ledger.grouped():
        key = main["doi"].lower()
        entry = entries.get(key, {})
        if any(r.get("corresponding") for r in [main, *ledger.related(main)]):
            used.add(key)
            if not entry.get("hide"):
                featured.append(_story(ledger, main, entry))
    stray = [e["doi"] for k, e in entries.items() if k not in used]
    if stray:
        fail(f"data/featured.yaml: not corresponding-author papers in the ledger, remove them: {stray}")
    no_area = [s["papers"][0] for s in featured if s["area"] not in AREAS]
    if no_area:
        fail(f"data/featured.yaml: give these featured papers an `area` ({' or '.join(AREAS)}): {no_area}")
    bad = [s["slug"] for s in featured if not SLUG.fullmatch(s["slug"])]
    if bad:
        fail(f"data/featured.yaml: slugs must be lower-case words joined by '-': {bad}")
    dupes = sorted({s["slug"] for s in featured if sum(t["slug"] == s["slug"] for t in featured) > 1})
    if dupes:
        fail(f"featured papers share a page address {dupes}; give one a `slug:` in data/featured.yaml")
    featured.sort(key=lambda s: s["date"] or "", reverse=True)   # stable: ties keep ledger order
    featured.sort(key=lambda s: (-s["year"], s["date"] is None))
    return featured


def story_by_doi(featured: list[Story], ledger: Ledger) -> dict[str, Story]:
    """Lower-case DOI (any version of any paper of a story) -> its story."""
    out: dict[str, Story] = {}
    for story in featured:
        for doi in story["papers"]:
            for d in ledger.family_dois(doi):
                out.setdefault(d, story)
    return out
