"""Research outputs: the RSS feed of new papers, preprints, software and
datasets (#22), generated from things_done, never written by hand.

Items (since OUTPUTS_SINCE):
  - papers published and preprints posted (publications)
  - new software (software registry)
  - new datasets (datasets registry)
Talks, events, funding and positions are not research outputs and are not
included.

Dates are shown only as precisely as the ledger knows them: papers have a
day when the preprint-lag report has one, else only a year; dates on
1 January come from CV-style records and are treated as the year.
"""

from typing import Any

from .featured import Story, story_by_doi
from .ledger import Ledger, software_list
from .text import esc, slugify, year_of

OUTPUTS_SINCE = "2024-01-01"
ResearchOutput = dict[str, Any]

KIND_LABELS = {"paper": "Paper", "preprint": "Preprint", "software": "Software", "dataset": "Dataset"}


def _precision(date: str) -> str:
    """How precisely a ledger date is known: "day", "month" or "year"."""
    parts = str(date).split("-")
    if len(parts) == 1 or parts[1:] == ["01", "01"]:
        return "year"
    return "month" if len(parts) == 2 else "day"


def _item(date: str, kind: str, title: str, html: str, url: str, precision: str | None = None) -> ResearchOutput:
    """One output; `url` is where it links in the feed (site path or absolute)."""
    return {"date": str(date), "precision": precision or _precision(date), "kind": kind,
            "title": title, "html": html, "url": url}


def _papers(ledger: Ledger, featured: list[Story]) -> list[ResearchOutput]:
    """Journal papers (day date from the lag report when known) and preprints
    not yet published."""
    stories = story_by_doi(featured, ledger)
    preprint_dates = {str(p["preprint_doi"]).lower(): p["preprint_date"] for p in ledger.lag_pairs
                      if p["preprint_date_precision"] == "day"}
    out = []
    for rec in ledger.grouped():
        story = stories.get(rec["doi"].lower())
        url = f"portfolio/{story['slug']}/" if story else f"https://doi.org/{rec['doi']}"
        link = f'<a href="{url}">{esc(rec["title"])}</a>'
        if rec["status"] == "preprint":
            date = preprint_dates.get(rec["doi"].lower())
            out.append(_item(date or str(rec["year"]), "preprint", rec["title"],
                             f"New preprint on {esc(rec['venue'])}: {link}", url, "day" if date else "year"))
        else:
            date = ledger.dates.get(rec["doi"].lower())
            out.append(_item(date or str(rec["year"]), "paper", rec["title"],
                             f"New paper in <em>{esc(rec['venue'])}</em>: {link}", url, "day" if date else "year"))
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
    """Research outputs since OUTPUTS_SINCE, newest first; within a year,
    items with a known month come before items known only to the year."""
    items = _papers(ledger, featured) + _software(ledger) + _datasets(ledger)
    items = [i for i in items
             if i["date"][:4] >= OUTPUTS_SINCE[:4] and (i["precision"] == "year" or i["date"] >= OUTPUTS_SINCE)]
    items.sort(key=lambda i: (i["date"][:4], i["precision"] != "year", i["date"]), reverse=True)
    return items
