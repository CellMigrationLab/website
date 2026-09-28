"""/llms.txt and /llms-full.txt: the site as plain Markdown for LLMs.

llms.txt follows the llmstxt.org convention: a title, a one-line summary,
then links to the main pages and papers. llms-full.txt has the content
itself (people, research, papers with abstracts, software, datasets, talks)
so a model can read the lab in one file. Both are rebuilt from the same data
as the pages on every build.
"""

import re
from datetime import date

from .config import CONTENT, DATA, DOCS, LAB_FOUNDED, SITE_URL, load
from .featured import Story
from .ledger import Ledger, Record, software_list
from .page import check_public
from .people import Person, leader
from .previews import preview_text
from .profile import month_year, recent_talks
from .structured import plain

PAGES = [  # (title, path) in the order of the menu
    ("Research", "research/"), ("Featured research", "featured-research/"), ("Publications", "publications/"),
    ("Software", "software/"), ("Datasets", "datasets/"), ("Lab members", "lab-members/"),
    ("Lab in numbers", "lab-in-numbers/"), ("Gallery", "gallery/"), ("Online talks", "online-lectures/"),
    ("About us", "about-us/"), ("News", "news/"), ("Join us", "join-us/"),
]


def _cite(rec: Record) -> str:
    """"Venue, year. doi:..." for a publication."""
    return f"{rec['venue']}, {rec['year']}. https://doi.org/{rec['doi']}"


def leader_email(members: list[Person]) -> str:
    """The group leader's email (data/members/<slug>.yaml)."""
    return leader(members)["email"]


def _join_us_text() -> str:
    """content/join-us.md without its front matter and title (already Markdown)."""
    text = (CONTENT / "join-us.md").read_text(encoding="utf-8").split("---", 2)[2]
    lines = [ln for ln in text.strip().splitlines() if not ln.startswith("# ")]
    text = re.sub(r"<[^>]+>", "", "\n".join(lines)).strip().replace("## ", "### ")
    # site links ("research.md") -> absolute page addresses, as everywhere else in this file
    return re.sub(r"\]\((?!https?:|mailto:)([a-z0-9/-]+)\.md(#[^)]*)?\)",
                  lambda m: f"]({SITE_URL}{m.group(1)}/{m.group(2) or ''})", text) + "\n"


def llms_txt(site: Record, featured: list[Story], members: list[Person]) -> str:
    """The short llms.txt: summary, main pages, featured papers."""
    lines = [f"# {site['name']} (Jacquemet Lab)", "", f"> {preview_text('index')}", "", site["intro"], "",
             "## Pages", ""]
    lines += [f"- [{title}]({SITE_URL}{path}): {preview_text(path.strip('/'))}" for title, path in PAGES]
    lines += ["", "## Featured papers", ""]
    lines += [f"- [{s['title']}]({SITE_URL}portfolio/{s['slug']}/): {_cite(s['pubs'][0])}" for s in featured]
    lines += ["", "## Contact", "",
              f"- Email: {leader_email(members)} (Guillaume Jacquemet, group leader)",
              f"- [How to join the lab]({SITE_URL}join-us/): {preview_text('join-us')}",
              f"- Address: {', '.join(site['contact']['address'])}"]
    lines += ["", "## Optional", "",
              f"- [Everything above as one Markdown file]({SITE_URL}llms-full.txt): people, research, "
              "papers with abstracts, software, datasets and talks",
              f"- [News feed (RSS)]({SITE_URL}feed.xml): papers, talks, events and funding", ""]
    return "\n".join(lines)


def _people(members: list[Person]) -> list[str]:
    """People section: current members (current role), alumni (all roles)."""
    out = ["## People", "", "### Current members", ""]
    out += [f"- {m['name']}, {m['role']}" for m in members if m["status"] == "current"]
    out += ["", "### Alumni", ""]
    out += [f"- {m['name']}: {', '.join(m['roles'])}" for m in members if m["status"] == "alumni"]
    return out + [""]


def _support(support: list[Record]) -> list[str]:
    """Current research support, grouped as on the home page."""
    out = ["## Current research support", ""]
    for g in support:
        names = " and ".join(f["name"] for f in g["logos"])
        if g["title"]:
            cof = f"; programme co-funded by {', '.join(g['cofunders'])}" if g["cofunders"] else ""
            out.append(f"- {g['title']['name']}: joint award from {names}{cof}")
        else:
            out.append(f"- {names}" + "".join(f"; {p['name']}" for p in g["programmes"]))
    return out + [""]


def llms_full(site: Record, featured: list[Story], ledger: Ledger, members: list[Person],
              affiliations: list[Record], support: list[Record]) -> str:
    """The long llms-full.txt with the site's content."""
    research = load(DATA / "research.yaml")
    out = [f"# {site['name']} (Jacquemet Lab)", "", f"> {preview_text('index')}", "", site["intro"], "",
           f"Website: {SITE_URL}", f"Address: {', '.join(site['contact']['address'])}", "",
           "## Affiliations", ""]
    out += [f"- {a['organization']} ({a['title']})" for a in affiliations]
    out += ["", *_support(support)][:-1]
    prof = ledger.profile
    out += ["", f"## Group leader: {prof['name']}", "", prof["short_bio"], ""]
    for heading, key in (("Positions", "appointments"), ("Editorial roles", "editorial"),
                         ("Service and leadership", "service")):
        out += [f"### {heading}", "", *(f"- {r['title']}, {r['organization']}" for r in prof[key]), ""]
    out += ["### Education", "", *(f"- {e['degree']}, {e['organization']}" + (f" ({str(e['end_date'])[:4]})" if e.get("end_date") else "")
                                   for e in prof["education"]), ""]
    out += _people(members)
    out += ["## Research", ""]
    for t in research["themes"]:
        out += [f"### {t['title']}", "", *(plain(x) for x in t.get("text") or []), ""]
    out += ["## Featured papers", "", "Papers where Guillaume Jacquemet is (co-)corresponding author.", ""]
    for s in featured:
        pub = s["pubs"][0]
        out += [f"### {s['title']}", "", f"{', '.join(pub['authors'])}. {_cite(pub)}",
                f"Page: {SITE_URL}portfolio/{s['slug']}/", "", " ".join(s["summary"].split()), ""]
    out += ["## All publications", "",
            f"Publications of Guillaume Jacquemet and the Cell Migration Lab. The lab was founded in {LAB_FOUNDED}; "
            f"papers from before {LAB_FOUNDED} come from his PhD and postdoctoral work.", ""]
    out += [f"- {r['title']}. {', '.join(r['authors'])}. {_cite(r)}"
            + (" (preprint)" if r.get("status") == "preprint" else "") for r in ledger.grouped()]
    out += ["", "## Software", ""]
    for s in software_list(ledger):
        code = f" Code: {s['github']}" if s.get("github") else ""
        out += [f"- {s['title']}" + (f" ({s['year']})" if s.get("year") else "") + f": {plain(s.get('text'))}{code}"]
    out += ["", "## Datasets", ""]
    out += [f"- {d['title']}: {d['description']} {d['repository_url']}" for d in ledger.datasets]
    out += ["", "## Contact", "",
            f"- Email: {ledger.profile['name']}, {leader_email(members)}",
            f"- Address: {', '.join(site['contact']['address'])}",
            f"- How to join: {SITE_URL}join-us/", ""]
    out += ["## Join the lab", "", _join_us_text()]
    out += ["", "## Talks (last two years)", ""]
    out += [f"- {month_year(t['date'])}: {t['title']}" + "".join(f", {x}" for x in (t["event_name"], t.get("location")) if x)
            for t in recent_talks(ledger, date.today())]
    out += ["", "## Recorded talks", ""]
    for t in load(DATA / "talks.yaml"):
        link = f"https://www.youtube.com/watch?v={t['youtube']}" if t.get("youtube") else f"https://vimeo.com/{t['vimeo']}"
        out += [f"- {t['title']}" + "".join(f", {x}" for x in (t.get("event"), t.get("year")) if x) + f". {link}"]
    return "\n".join(out) + "\n"


def write_llms(site: Record, featured: list[Story], ledger: Ledger, members: list[Person],
               affiliations: list[Record], support: list[Record]) -> None:
    """Write docs/llms.txt and docs/llms-full.txt (copied to the site root)."""
    for name, text in (("llms.txt", llms_txt(site, featured, members)),
                       ("llms-full.txt", llms_full(site, featured, ledger, members, affiliations, support))):
        check_public(f"docs/{name}", text)
        (DOCS / name).write_text(text, encoding="utf-8")
