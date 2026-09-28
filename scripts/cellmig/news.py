"""News: lab updates generated from things_done, never written by hand.

Items (since NEWS_SINCE):
  - papers published and preprints posted (publications)
  - keynote and plenary talks (talks)
  - events organised or chaired (conference_organization)
  - new funding (grants: active, awarded or completed)
  - new positions and editorial roles of the group leader (profile)
  - new software (software registry)

Dates are shown only as precisely as the ledger knows them: papers have a
day when the preprint-lag report has one, else only a year; dates on
1 January come from CV-style records and are shown as the year.

The same items feed docs/news.md and the RSS feed (site_files.write_feed).
"""

from typing import Any

from .featured import Story, story_by_doi
from .ledger import Ledger, software_list
from .page import Page
from .previews import preview
from .profile import MONTHS
from .text import esc, slugify

NEWS_SINCE = "2024-01-01"
NewsItem = dict[str, Any]

KIND_LABELS = {"paper": "Paper", "preprint": "Preprint", "keynote": "Keynote", "plenary": "Plenary", "event": "Event",
               "funding": "Funding", "position": "Position", "software": "Software"}


def _precision(date: str) -> str:
    """How precisely a ledger date is known: "day", "month" or "year"."""
    parts = str(date).split("-")
    if len(parts) == 1 or parts[1:] == ["01", "01"]:
        return "year"
    return "month" if len(parts) == 2 else "day"


def date_label(item: NewsItem) -> str:
    """"12 Sep 2026", "Sep 2026" or "2026", as precise as the ledger date."""
    parts = item["date"].split("-")
    if item["precision"] == "year":
        return parts[0]
    month = f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return f"{int(parts[2])} {month}" if item["precision"] == "day" else month


def _item(date: str, kind: str, title: str, html: str, url: str | None, precision: str | None = None) -> NewsItem:
    """One news item; `url` is where it links in the RSS feed (None: the news page)."""
    return {"date": str(date), "precision": precision or _precision(date), "kind": kind,
            "title": title, "html": html, "url": url}


def _papers(ledger: Ledger, featured: list[Story]) -> list[NewsItem]:
    """Journal papers (day date from the lag report when known) and preprints
    not yet published."""
    stories = story_by_doi(featured, ledger)
    preprint_dates = {str(p["preprint_doi"]).lower(): p["preprint_date"] for p in ledger.lag_pairs
                      if p.get("preprint_date_precision") == "day"}
    out = []
    for rec in ledger.grouped():
        story = stories.get(rec["doi"].lower())
        url = f"portfolio/{story['slug']}/" if story else f"https://doi.org/{rec['doi']}"
        link = f'<a href="{url}">{esc(rec["title"])}</a>'
        if rec.get("status") == "preprint":
            date = preprint_dates.get(rec["doi"].lower())
            out.append(_item(date or str(rec["year"]), "preprint", rec["title"],
                             f"New preprint on {esc(rec['venue'])}: {link}", url,
                             "day" if date else "year"))
        else:
            date = ledger.dates.get(rec["doi"].lower())
            out.append(_item(date or str(rec["year"]), "paper", rec["title"],
                             f"New paper in <em>{esc(rec['venue'])}</em>: {link}", url,
                             "day" if date else "year"))
    return out


def _activities(ledger: Ledger) -> list[NewsItem]:
    """Keynotes and plenaries, events organised or chaired."""
    out = [_item(t["date"], t["talk_kind"], t["title"],
                 f'{"Keynote" if t["talk_kind"] == "keynote" else "Plenary talk"} at {esc(t["event_name"])}: '
                 f'“{esc(t["title"])}”', None)
           for t in ledger.talks if t["talk_kind"] in ("keynote", "plenary")]
    out += [_item(e["start_date"], "event", e["event_name"],
                  f'{esc(e["title"])}, {esc(e["event_name"])}' + (f' ({esc(e["location"])})' if e.get("location") else ""),
                  None)
            for e in ledger.events]   # start_date is required in things_done
    return out


def _funding_and_roles(ledger: Ledger) -> list[NewsItem]:
    """New grants (their public titles name the funder) and the group
    leader's positions and editorial roles, current or completed (things_done
    profile `roles`, so a role stays in the news after it ends)."""
    out = [_item(g["start_date"], "funding", g["title"], f'New funding: {esc(g["title"])}', None)
           for g in ledger.grants if g["status"] in ("active", "awarded", "completed")]   # these have dates
    prof = ledger.profile
    out += [_item(r["start_date"], "position", r["title"],
                  f'{esc(prof["name"])}: {esc(r["title"])}, {esc(r["organization"])}', "about-us/#group-leader")
            for r in prof["roles"]]
    return out


def _software(ledger: Ledger) -> list[NewsItem]:
    """New software projects (year known from the registry)."""
    return [_item(str(s["year"]), "software", s["title"],
                  f'New software: <a href="software/#{slugify(s["title"])}">{esc(s["title"])}</a>',
                  f"software/#{slugify(s['title'])}", "year")
            for s in software_list(ledger) if s.get("year")]


def build_news(ledger: Ledger, featured: list[Story]) -> list[NewsItem]:
    """All news items since NEWS_SINCE, newest first; within a year, items
    with a known month come before items known only to the year."""
    items = _papers(ledger, featured) + _activities(ledger) + _funding_and_roles(ledger) + _software(ledger)
    items = [i for i in items if i["date"][:4] >= NEWS_SINCE[:4] and (i["precision"] == "year" or i["date"] >= NEWS_SINCE)]
    items.sort(key=lambda i: (i["date"][:4], i["precision"] != "year", i["date"]), reverse=True)
    return items


def page_news(items: list[NewsItem]) -> None:
    """docs/news.md: news items grouped by year."""
    p = Page("news.md", title="News", **preview("news"))
    p.add("# News", '<p class="cm-lead">What the lab has been up to: papers, preprints, talks, events and '
                    'funding. Also as an <a href="feed.xml">RSS feed</a>.</p>')
    year = None
    for item in items:
        if item["date"][:4] != year:
            if year:
                p.add("</ul>")
            year = item["date"][:4]
            p.add(f'<h2 id="y{year}">{year}</h2>', '<ul class="cm-talklist cm-news">')
        when = "" if item["precision"] == "year" else date_label(item)
        p.add(f'<li><span class="cm-talklist__date">{esc(when)}</span><span>'
              f'<span class="cm-badge cm-news__kind">{KIND_LABELS[item["kind"]]}</span> {item["html"]}</span></li>')
    if year:
        p.add("</ul>")
    p.write()
