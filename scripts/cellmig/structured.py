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

from .config import LAB_FOUNDED, SITE_URL
from .featured import Story
from .ledger import Record
from .people import Person, leader
from .text import full_date, md

LAB_ID = f"{SITE_URL}#lab"
Json = dict[str, Any]


def to_json(data: Json) -> str:
    """JSON for a <script type="application/ld+json"> block ("</" escaped)."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def plain(markdown_text: str | None) -> str:
    """Markdown -> plain text on one line (for descriptions)."""
    text = re.sub(r"<[^>]+>", "", md(markdown_text or ""))   # paragraphs keep their newline
    return " ".join(html.unescape(text).split())


def _person_links(m: Person) -> list[str]:
    """Profile URLs of a person (ORCID, Scholar, GitHub, Bluesky, website)."""
    orcid = m.get("orcid")
    links = [orcid if orcid and orcid.startswith("http") else (f"https://orcid.org/{orcid}" if orcid else None),
             m.get("scholar"), m.get("github"), m.get("bluesky"), m.get("website")]
    return [link for link in links if link]


def _org(a: Record) -> Json:
    return {"@type": "Organization", "name": a["name"], "url": a["url"]}


def support_funders(support: list[Record]) -> list[Record]:
    """The direct funders of current support (ledger.support_list groups), once each."""
    return list({f["funder"]: f for g in support for f in g["logos"]}.values())


def organization(site: Record, affiliations: list[Record], members: list[Person], logo: str,
                 leader_bio: str, support: list[Record]) -> Json:
    """The lab: name, founding year, address and contact, leader (with
    affiliations and profiles), and how it relates to each affiliation
    (data/site.yaml `relation`: parent -> parentOrganization, member ->
    memberOf, leader -> only the leader's affiliation)."""
    lead = leader(members)
    by_relation = {r: [_org(a) for a in affiliations if a["relation"] == r] for r in ("parent", "member")}
    return {
        "@context": "https://schema.org",
        "@type": "ResearchOrganization",
        "@id": LAB_ID,
        "name": site["name"],
        "alternateName": "Jacquemet Lab",
        "url": SITE_URL,
        "logo": SITE_URL + logo,
        "description": site["intro"],
        "foundingDate": str(LAB_FOUNDED),
        "address": ", ".join(site["contact"]["address"][1:]),
        "email": lead["email"],
        "contactPoint": {"@type": "ContactPoint", "contactType": "enquiries", "email": lead["email"],
                         "url": f"{SITE_URL}join-us/"},
        "parentOrganization": by_relation["parent"],
        "memberOf": by_relation["member"],
        "funder": [_org(f) for f in support_funders(support)],   # current grants (things_done)
        "founder": {
            "@type": "Person",
            "@id": f"{SITE_URL}#{lead['slug']}",
            "name": lead["name"],
            "jobTitle": lead["role"],
            "description": leader_bio,
            "affiliation": [{"@type": "Organization", "name": a["organization"]} for a in affiliations],
            "sameAs": _person_links(lead),
        },
        "sameAs": [s["url"] for s in site["social"] if s["url"].startswith("http")],
    }


def _date(story_date: str | None, year: int) -> str:
    """ISO date when known to the day, else the year (Scholar tags accept a
    full date or a year)."""
    return full_date(story_date) or str(year)


def article(story: Story, page_url: str, image: Json | None) -> Json:
    """A featured paper as a ScholarlyArticle, with breadcrumbs; `image` is its
    picture as an ImageObject with its rights (rights.image_object)."""
    pub = story["pubs"][0]
    work: Json = {
        "@type": "ScholarlyArticle",
        "@id": f"{page_url}#article",
        "headline": pub["title"],
        "name": pub["title"],
        "author": [{"@type": "Person", "name": a} for a in pub["authors"]],
        "isPartOf": {"@type": "Periodical", "name": pub["venue"]},
        "identifier": {"@type": "PropertyValue", "propertyID": "DOI", "value": pub["doi"]},
        "sameAs": f"https://doi.org/{pub['doi']}",
        "url": page_url,
        "abstract": " ".join(story["summary"].split()),
        # No sourceOrganization: being listed on the lab's site does not make
        # the current lab the paper's source (featured papers go back to before
        # the lab was founded). Organisations come only from provenance data
        # (things_done#142, once it exists); the authors are the claim made here.
    }
    if full_date(story["date"]):   # only full dates: no year- or month-only values
        work["datePublished"] = story["date"]
    if image:
        work["image"] = image
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
    tags += [["citation_author", a] for a in pub["authors"]]
    tags += [["citation_publication_date", _date(story["date"], story["year"]).replace("-", "/")],
             ["citation_journal_title", pub["venue"]],
             ["citation_doi", pub["doi"]]]
    return [t for t in tags if t[1]]


def item_list(name: str, items: list[Json], description: str | None = None) -> Json:
    """schema.org ItemList of the given items, in order."""
    extra = {"description": description} if description else {}
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, **extra,
            "itemListElement": [{"@type": "ListItem", "position": i, "item": item}
                                for i, item in enumerate(items, 1)]}


def publication_item(rec: Record, date: str | None) -> Json:
    """A publication as a short ScholarlyArticle; datePublished only when
    `date` (Ledger.dates) is known to the day, never a bare month or year."""
    item: Json = {"@type": "ScholarlyArticle", "name": rec["title"],
                  "author": [{"@type": "Person", "name": a} for a in rec["authors"]],
                  "isPartOf": {"@type": "Periodical", "name": rec["venue"]},
                  "sameAs": f"https://doi.org/{rec['doi']}"}
    if full_date(date):
        item["datePublished"] = date
    return item


def software_item(s: Record, anchor_url: str) -> Json:
    """A software project as SoftwareSourceCode. The lab is a `contributor`:
    some projects are the lab's own, others were built with partners, and
    the ledger does not record who the authors are."""
    item: Json = {"@type": "SoftwareSourceCode", "name": s["title"], "url": anchor_url,
                  "description": plain(s.get("text")), "contributor": {"@id": LAB_ID}}
    item["codeRepository"] = s["github"]
    item["citation"] = [f"https://doi.org/{r['doi']}" for r in s["papers"]]
    return item


def dataset_item(d: Record, papers: list[Record]) -> Json:
    """A dataset as schema.org Dataset, with the lab as `contributor` (many
    datasets are shared with collaborators), citing its papers (Ledger.dataset_papers)."""
    item: Json = {"@type": "Dataset", "name": d["title"], "url": d["repository_url"],
                  "description": plain(d["description"]), "contributor": {"@id": LAB_ID}}
    if d.get("archive_doi"):
        item["identifier"] = f"https://doi.org/{d['archive_doi']}"
    item["citation"] = [f"https://doi.org/{r['doi']}" for r in papers]
    return item


def person_item(m: Person) -> Json:
    """A lab member as schema.org Person."""
    item: Json = {"@type": "Person", "name": m["name"], "jobTitle": m["role"],
                  "memberOf": {"@id": LAB_ID}, "url": f"{SITE_URL}lab-members/#{m['slug']}"}
    links = _person_links(m)
    if links:
        item["sameAs"] = links
    return item
