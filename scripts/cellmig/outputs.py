"""Research outputs: the RSS feed of new papers, preprints, software and
datasets (#22), generated from things_done, never written by hand.

Items (since OUTPUTS_SINCE):
  - papers published and preprints posted (publications)
  - new software (software registry)
  - new datasets (datasets registry)
Talks, events, funding and positions are not research outputs and are not
included.

Each item's date is cut to what the ledger knows (text.known_date): papers
and preprints have the day or month from the preprint-lag report, else only
the year; other dates on 1 January come from CV-style records and are
treated as the year. Nothing downstream fills in a missing month or day.
"""

from typing import Any

from .featured import Story, story_by_doi
from .ledger import Ledger, software_list
from .text import esc, known_date, precision_of, slugify, year_of

OUTPUTS_SINCE = "2024-01-01"
ResearchOutput = dict[str, Any]

KIND_LABELS = {"paper": "Paper", "preprint": "Preprint", "software": "Software", "dataset": "Dataset"}


def _precision(date: str) -> str:
    """How precisely a CV-style ledger date is known: "day", "month" or "year"."""
    parts = str(date).split("-")
    if len(parts) == 1 or parts[1:] == ["01", "01"]:
        return "year"
    return "month" if len(parts) == 2 else "day"


def _item(date: str, kind: str, title: str, html: str, url: str, precision: str | None = None) -> ResearchOutput:
    """One output; `date` is cut to `precision` (guessed from the date when
    not given); `url` is where it links in the feed (site path or absolute)."""
    date = known_date(date, precision or _precision(date))
    return {"date": date, "precision": precision_of(date), "kind": kind,
            "title": title, "html": html, "url": url}


def _papers(ledger: Ledger, featured: list[Story]) -> list[ResearchOutput]:
    """Journal papers and preprints not yet published, dated as far as the
    lag report knows (else the year)."""
    stories = story_by_doi(featured, ledger)
    preprint_dates = {str(p["preprint_doi"]).lower(): known_date(p["preprint_date"], p["preprint_date_precision"])
                      for p in ledger.lag_pairs if p["preprint_date_precision"] != "year"}
    out = []
    for rec in ledger.grouped():
        story = stories.get(rec["doi"].lower())
        url = f"portfolio/{story['slug']}/" if story else f"https://doi.org/{rec['doi']}"
        link = f'<a href="{url}">{esc(rec["title"])}</a>'
        preprint = rec["status"] == "preprint"
        date = (preprint_dates if preprint else ledger.dates).get(rec["doi"].lower()) or str(rec["year"])
        text = f"New preprint on {esc(rec['venue'])}" if preprint else f"New paper in <em>{esc(rec['venue'])}</em>"
        out.append(_item(date, "preprint" if preprint else "paper", rec["title"], f"{text}: {link}", url,
                         precision_of(date)))   # explicit: a lag-report day may be 1 January
    return out


def _software(ledger: Ledger) -> list[ResearchOutput]:
    """New software projects (year known from the registry)."""
    return [_item(str(s["year"]), "software", s["title"],
                  f'New software: <a href="software/#{slugify(s["title"])}">{esc(s["title"])}</a>',
                  f"software/#{slugify(s['title'])}", "year")
            for s in software_list(ledger) if s.get("year")]


def _datasets(ledger: Ledger) -> list[ResearchOutput]:
    """New datasets, linked to their repository (start_date is required)."""
    return [_item(str(d["start_date"]), "dataset", d["title"],
                  f'New dataset: <a href="{d["repository_url"]}">{esc(d["title"])}</a>', d["repository_url"])
            for d in ledger.datasets if year_of(d["start_date"])]


def build_outputs(ledger: Ledger, featured: list[Story]) -> list[ResearchOutput]:
    """Research outputs since OUTPUTS_SINCE (compared as far as each date is
    known), newest first; within a year or month, the less precise dates come
    after the more precise ones (text.known_date)."""
    items = _papers(ledger, featured) + _software(ledger) + _datasets(ledger)
    items = [i for i in items if i["date"] >= OUTPUTS_SINCE[:len(i["date"])]]
    items.sort(key=lambda i: i["date"], reverse=True)   # stable: ties keep the order above
    return items
