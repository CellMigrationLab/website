"""Featured research: every paper on which Guillaume is (co-)corresponding author.

The flag comes from the ledger (`me.corresponding_author`, copied as
`corresponding: true`, on the paper or any of its versions). data/featured.yaml
only adds a picture and a page address per paper, plus two switches:
`show: true` features a paper that is not corresponding-author and
`hide: true` un-features one.

Entries in data/featured.yaml that end up not featured still get their page
(old WordPress /portfolio/<slug>/ addresses keep working), but are not listed.
"""

from typing import Any

from .config import DATA, fail, load
from .ledger import Ledger, Record
from .text import slugify

Story = dict[str, Any]

ENTRY_KEYS = {"doi", "image", "slug", "also", "show", "hide"}


def _entries(ledger: Ledger) -> dict[str, Record]:
    """data/featured.yaml entries, keyed by the DOI of the journal version."""
    out = {}
    for e in load(DATA / "featured.yaml") or []:
        unknown = set(e) - ENTRY_KEYS
        if unknown:
            fail(f"data/featured.yaml ({e.get('doi')}): unknown keys {sorted(unknown)}")
        if e.get("show") and e.get("hide"):
            fail(f"data/featured.yaml ({e['doi']}): 'show' and 'hide' together")
        rec = ledger.require(e["doi"], "data/featured.yaml")
        for d in e.get("also") or []:
            ledger.require(d, f"data/featured.yaml ({e['doi']}, also)")
        key = ledger.published_version(rec)["doi"].lower()
        if key in out:
            fail(f"data/featured.yaml: {e['doi']} and {out[key]['doi']} are the same paper")
        out[key] = e
    return out


def _story(ledger: Ledger, main: Record, entry: Record, pos: int) -> Story:
    """A featured item: the paper (plus any `also` papers) and its presentation."""
    pubs = [main] + [ledger.published_version(ledger.get(d)) for d in entry.get("also") or []]
    family = [main, *ledger.related(main)]
    return {
        "papers": [main["doi"], *(entry.get("also") or [])],
        "pubs": pubs,
        "image": entry.get("image"),
        "title": main["title"],
        "slug": entry.get("slug") or slugify(main["title"])[:90],
        "year": int(main["year"]),
        # Day-precision journal date when the lag report has one, else None.
        "date": next((ledger.dates[r["doi"].lower()] for r in family if r["doi"].lower() in ledger.dates), None),
        "summary": "\n\n".join(p["abstract"] for p in pubs if p.get("abstract")),
        "pos": pos,
    }


def load_featured(ledger: Ledger) -> tuple[list[Story], list[Story]]:
    """(featured, unlisted): featured papers newest first, and the entries of
    data/featured.yaml that are not featured (they keep their old page).

    Order: year, then the exact date where known (papers with no known date
    come after dated ones of the same year), then ledger order."""
    entries = _entries(ledger)
    featured, used = [], set()
    for pos, main in enumerate(ledger.grouped()):
        key = main["doi"].lower()
        entry = entries.get(key, {})
        corresponding = any(r.get("corresponding") for r in [main, *ledger.related(main)])
        if (corresponding and not entry.get("hide")) or entry.get("show"):
            featured.append(_story(ledger, main, entry, pos))
            used.add(key)
    featured.sort(key=lambda s: (-s["year"], s["date"] is None, _neg(s["date"]), s["pos"]))
    unlisted = [_story(ledger, ledger.get(k), e, 1000 + i)
                for i, (k, e) in enumerate(entries.items()) if k not in used]
    return featured, unlisted


def _neg(date: str | None) -> tuple[int, ...]:
    """Sort key that orders ISO dates newest first."""
    return tuple(-int(x) for x in date.split("-")) if date else ()


def story_by_doi(featured: list[Story], ledger: Ledger) -> dict[str, Story]:
    """Lower-case DOI (any version of any paper of a story) -> its story."""
    out: dict[str, Story] = {}
    for story in featured:
        for doi in story["papers"]:
            for d in ledger.family_dois(doi):
                out.setdefault(d, story)
    return out
