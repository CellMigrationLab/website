"""Machine-readable descriptions of pages, for search engines and LLMs.

- JSON-LD (schema.org): the lab as a ResearchOrganization with its leader
  and affiliations (on every page, via overrides/partials/cm-jsonld.html),
  each featured paper as a ScholarlyArticle with breadcrumbs, and the
  publications, software, datasets and people pages as lists.
- Google Scholar / Highwire tags (citation_title, citation_author, ...) on
  each featured-paper page.

Everything is built from data already used for the pages; nothing here is
entered by hand.
"""

import html
import json
import re
from typing import Any

from .config import SITE_URL
from .featured import Story
from .ledger import Record
from .people import Person
from .text import md

LAB_ID = f"{SITE_URL}#lab"
Json = dict[str, Any]


def to_json(data: Json) -> str:
    """JSON for a <script type="application/ld+json"> block ("</" escaped)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def plain(markdown_text: str | None) -> str:
    """Markdown -> plain text on one line (for descriptions)."""
    text = re.sub(r"<[^>]+>", " ", md(markdown_text or ""))
    return " ".join(html.unescape(text).split())


def _person_links(m: Person) -> list[str]:
    """Profile URLs of a person (ORCID, Scholar, GitHub, Bluesky, website)."""
    orcid = m.get("orcid")
    links = [orcid if orcid and orcid.startswith("http") else (f"https://orcid.org/{orcid}" if orcid else None),
             m.get("scholar"), m.get("github"), m.get("bluesky"), m.get("website")]
    return [link for link in links if link]


def organization(site: Record, affiliations: list[Record], members: list[Person], logo: str) -> Json:
    """The lab: name, address, leader (with affiliations and profiles), parent
    organisations and social links."""
    leader = next(m for m in members if m["group"] == "pi" and m["status"] == "current")
    return {
        "@context": "https://schema.org",
        "@type": "ResearchOrganization",
        "@id": LAB_ID,
        "name": site["name"],
        "alternateName": "Jacquemet Lab",
        "url": SITE_URL,
        "logo": SITE_URL + logo,
        "description": site["intro"],
        "address": ", ".join(site["contact"]["address"][1:]),
        "parentOrganization": [{"@type": "Organization", "name": a["name"], "url": a["url"]} for a in affiliations],
        "founder": {
            "@type": "Person",
            "@id": f"{SITE_URL}#{leader['slug']}",
            "name": leader["name"],
            "jobTitle": leader["role"],
            "affiliation": [{"@type": "Organization", "name": a["organization"]} for a in affiliations],
            "sameAs": _person_links(leader),
        },
        "sameAs": [s["url"] for s in site["social"] if s["url"].startswith("http")],
    }


def _date(story_date: str | None, year: int) -> str:
    """ISO date when known, else the year."""
    return story_date or str(year)


def article(story: Story, page_url: str, image_url: str | None) -> Json:
    """A featured paper as a ScholarlyArticle, with breadcrumbs."""
    pub = story["pubs"][0]
    work: Json = {
        "@type": "ScholarlyArticle",
        "@id": f"{page_url}#article",
        "headline": pub["title"],
        "name": pub["title"],
        "author": [{"@type": "Person", "name": a} for a in pub.get("authors") or []],
        "datePublished": _date(story["date"], story["year"]),
        "isPartOf": {"@type": "Periodical", "name": pub.get("venue") or ""},
        "identifier": {"@type": "PropertyValue", "propertyID": "DOI", "value": pub["doi"]},
        "sameAs": f"https://doi.org/{pub['doi']}",
        "url": page_url,
        "abstract": " ".join(story["summary"].split()),
        "sourceOrganization": {"@id": LAB_ID},
    }
    if image_url:
        work["image"] = image_url
    crumbs = [("Home", SITE_URL), ("Featured research", f"{SITE_URL}featured-research/"), (pub["title"], page_url)]
    return {"@context": "https://schema.org", "@graph": [work, {
        "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u}
                            for i, (n, u) in enumerate(crumbs, 1)]}]}


def scholar_tags(story: Story) -> list[list[str]]:
    """[name, content] pairs of Google Scholar (Highwire) meta tags for the
    story's main paper."""
    pub = story["pubs"][0]
    tags = [["citation_title", pub["title"]]]
    tags += [["citation_author", a] for a in pub.get("authors") or []]
    tags += [["citation_publication_date", _date(story["date"], story["year"]).replace("-", "/")],
             ["citation_journal_title", pub.get("venue") or ""],
             ["citation_doi", pub["doi"]]]
    return [t for t in tags if t[1]]


def item_list(name: str, items: list[Json]) -> Json:
    """schema.org ItemList of the given items, in order."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name,
            "itemListElement": [{"@type": "ListItem", "position": i, "item": item}
                                for i, item in enumerate(items, 1)]}


def publication_item(rec: Record) -> Json:
    """A publication as a short ScholarlyArticle."""
    return {"@type": "ScholarlyArticle", "name": rec["title"],
            "author": [{"@type": "Person", "name": a} for a in rec.get("authors") or []],
            "datePublished": str(rec["year"]), "isPartOf": {"@type": "Periodical", "name": rec.get("venue") or ""},
            "sameAs": f"https://doi.org/{rec['doi']}"}


def software_item(s: Record, anchor_url: str) -> Json:
    """A software project as SoftwareSourceCode."""
    item: Json = {"@type": "SoftwareSourceCode", "name": s["title"], "url": anchor_url,
                  "description": plain(s.get("text")), "author": {"@id": LAB_ID}}
    if s.get("github"):
        item["codeRepository"] = s["github"]
    if s["dois"]:
        item["citation"] = [f"https://doi.org/{d}" for d in s["dois"]]
    return item


def dataset_item(d: Record) -> Json:
    """A dataset as schema.org Dataset."""
    item: Json = {"@type": "Dataset", "name": d["title"], "url": d["repository_url"],
                  "description": d.get("description") or d["title"], "creator": {"@id": LAB_ID}}
    if d.get("archive_doi"):
        item["identifier"] = f"https://doi.org/{d['archive_doi']}"
    if d.get("related_publication_dois"):
        item["citation"] = [f"https://doi.org/{x}" for x in d["related_publication_dois"]]
    return item


def person_item(m: Person) -> Json:
    """A lab member as schema.org Person."""
    item: Json = {"@type": "Person", "name": m["name"], "jobTitle": m["role"],
                  "memberOf": {"@id": LAB_ID}, "url": f"{SITE_URL}lab-members/#{m['slug']}"}
    links = _person_links(m)
    if links:
        item["sameAs"] = links
    return item
