"""/llms.txt and /llms-full.txt: the site as plain Markdown for LLMs.

llms.txt follows the llmstxt.org convention: a title, a one-line summary,
then links to the main pages and papers. llms-full.txt has the content
itself (people, research, papers with abstracts, software, datasets, talks)
so a model can read the lab in one file. Both are rebuilt from the same data
as the pages on every build.
"""

from datetime import date

from .config import DATA, DOCS, SITE_URL, load
from .featured import Story
from .ledger import Ledger, Record, software_list
from .people import Person
from .previews import preview_text
from .profile import month_year, recent_talks
from .structured import plain

PAGES = [  # (title, path) in the order of the menu
    ("Research", "research/"), ("Featured research", "featured-research/"), ("Publications", "publications/"),
    ("Software", "software/"), ("Datasets", "datasets/"), ("Lab members", "lab-members/"),
    ("Lab in numbers", "lab-in-numbers/"), ("Gallery", "gallery/"), ("Online talks", "online-lectures/"),
    ("About us", "about-us/"), ("ZeroCostDL4Mic", "image-analysis/"), ("News", "news/"), ("Join us", "join-us/"),
]


def _cite(rec: Record) -> str:
    """"Venue, year. doi:..." for a publication."""
    return f"{rec.get('venue') or ''}, {rec['year']}. https://doi.org/{rec['doi']}"


def llms_txt(site: Record, featured: list[Story]) -> str:
    """The short llms.txt: summary, main pages, featured papers."""
    lines = [f"# {site['name']} (Jacquemet Lab)", "", f"> {preview_text('index')}", "", site["intro"], "",
             "## Pages", ""]
    lines += [f"- [{title}]({SITE_URL}{path}): {preview_text(path.strip('/'))}" for title, path in PAGES]
    lines += ["", "## Featured papers", ""]
    lines += [f"- [{s['title']}]({SITE_URL}portfolio/{s['slug']}/): {_cite(s['pubs'][0])}" for s in featured]
    lines += ["", "## Optional", "",
              f"- [Everything above as one Markdown file]({SITE_URL}llms-full.txt): people, research, "
              "papers with abstracts, software, datasets and talks",
              f"- [RSS feed of featured papers]({SITE_URL}feed.xml)", ""]
    return "\n".join(lines)


def _people(members: list[Person]) -> list[str]:
    """People section: current members (current role), alumni (all roles)."""
    out = ["## People", "", "### Current members", ""]
    out += [f"- {m['name']}, {m['role']}" for m in members if m["status"] == "current"]
    out += ["", "### Alumni", ""]
    out += [f"- {m['name']}: {', '.join(m['roles'])}" for m in members if m["status"] == "alumni"]
    return out + [""]


def llms_full(site: Record, featured: list[Story], ledger: Ledger, members: list[Person],
              affiliations: list[Record]) -> str:
    """The long llms-full.txt with the site's content."""
    research = load(DATA / "research.yaml")
    out = [f"# {site['name']} (Jacquemet Lab)", "", f"> {preview_text('index')}", "", site["intro"], "",
           f"Website: {SITE_URL}", f"Address: {', '.join(site['contact']['address'])}", "",
           "## Affiliations", ""]
    out += [f"- {a['organization']} ({a['title']})" for a in affiliations]
    prof = ledger.profile
    out += ["", f"## Group leader: {prof['name']}", "", prof["short_bio"], ""]
    for heading, key in (("Positions", "appointments"), ("Editorial roles", "editorial"),
                         ("Service and leadership", "service")):
        out += [f"### {heading}", "", *(f"- {r['title']}, {r['organization']}" for r in prof.get(key) or []), ""]
    out += ["### Education", "", *(f"- {e['degree']}, {e['organization']}" + (f" ({str(e['end_date'])[:4]})" if e.get("end_date") else "")
                                   for e in prof["education"]), ""]
    out += _people(members)
    out += ["## Research", ""]
    for t in research["themes"]:
        out += [f"### {t['title']}", "", *(plain(x) for x in t.get("text") or []), ""]
    out += ["## Featured papers", "", "Papers where Guillaume Jacquemet is (co-)corresponding author.", ""]
    for s in featured:
        pub = s["pubs"][0]
        out += [f"### {s['title']}", "", f"{', '.join(pub.get('authors') or [])}. {_cite(pub)}",
                f"Page: {SITE_URL}portfolio/{s['slug']}/", "", " ".join(s["summary"].split()), ""]
    out += ["## All publications", ""]
    out += [f"- {r['title']}. {', '.join(r.get('authors') or [])}. {_cite(r)}"
            + (" (preprint)" if r.get("status") == "preprint" else "") for r in ledger.grouped()]
    out += ["", "## Software", ""]
    for s in software_list(ledger):
        code = f" Code: {s['github']}" if s.get("github") else ""
        out += [f"- {s['title']}" + (f" ({s['year']})" if s.get("year") else "") + f": {plain(s.get('text'))}{code}"]
    out += ["", "## Datasets", ""]
    out += [f"- {d['title']}: {d.get('description') or ''} {d['repository_url']}" for d in ledger.datasets]
    out += ["", "## Talks (last two years)", ""]
    out += [f"- {month_year(t['date'])}: {t['title']}" + "".join(f", {x}" for x in (t.get("event_name"), t.get("location")) if x)
            for t in recent_talks(ledger, date.today())]
    out += ["", "## Recorded talks", ""]
    for t in load(DATA / "talks.yaml"):
        link = f"https://www.youtube.com/watch?v={t['youtube']}" if t.get("youtube") else f"https://vimeo.com/{t['vimeo']}"
        out += [f"- {t['title']}" + "".join(f", {x}" for x in (t.get("event"), t.get("year")) if x) + f". {link}"]
    return "\n".join(out) + "\n"


def write_llms(site: Record, featured: list[Story], ledger: Ledger, members: list[Person],
               affiliations: list[Record]) -> None:
    """Write docs/llms.txt and docs/llms-full.txt (copied to the site root)."""
    (DOCS / "llms.txt").write_text(llms_txt(site, featured), encoding="utf-8")
    (DOCS / "llms-full.txt").write_text(llms_full(site, featured, ledger, members, affiliations), encoding="utf-8")
