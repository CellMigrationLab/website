"""Featured research grid, one page per featured paper, and all publications."""


from . import rights
from .components import PAPERS, PREPRINT_LINK, citation, feature_card, one_line, orcid_url, section_nav
from .config import LAB_FOUNDED, SITE_URL, edit_url
from .featured import Story, story_by_doi
from .images import media
from .ledger import Ledger, Record, software_list
from .page import Page
from .people import Person
from .previews import paper_image, preview
from .structured import article, item_list, publication_item, scholar_tags, to_json
from .text import esc, slugify


def page_featured(featured: list[Story], ledger: Ledger, lab: set[str]) -> None:
    """docs/featured-research.md (the grid) and docs/portfolio/<slug>.md for each story."""
    p = Page("featured-research.md", title="Featured research", menu="publications/", edit_url=edit_url("data/featured.yaml"),
             **preview("featured-research"))
    p.add("# Featured research", section_nav(PAPERS, "Featured research"),
          '<div class="cm-cards cm-cards--grid">', *(feature_card(s) for s in featured), "</div>")
    p.write()
    software = software_list(ledger)
    for i, story in enumerate(featured):
        page_story(story, featured, i, ledger, lab, software)


def _related(story: Story, ledger: Ledger, software: list[Record]) -> str:
    """Aside listing software and datasets linked to any version of the story's
    papers; each heading and its list share one grid cell."""
    dois = set().union(*(ledger.family_dois(d) for d in story["papers"]))
    tools = [s for s in software if {d.lower() for d in s["dois"]} & dois]
    data = [d for d in ledger.datasets if {x.lower() for x in d.get("related_publication_dois") or []} & dois]
    if not (tools or data):
        return ""
    out = ['<aside class="cm-related">']
    if tools:
        out.append("<div><h2>Software</h2><ul>")
        out += [f'<li><a href="software/#{slugify(s["title"])}">{esc(s["title"])}</a>'
                + (f' · <a href="{esc(s["github"])}">code</a>' if s.get("github") else "") + "</li>" for s in tools]
        out.append("</ul></div>")
    if data:
        out.append("<div><h2>Data</h2><ul>")
        out += [f'<li><a href="{esc(d["repository_url"])}">{esc(d["title"])}</a></li>' for d in data]
        out.append("</ul></div>")
    out.append("</aside>")
    return "".join(out)


def _pager(stories: list[Story], i: int) -> str:
    """Links to the newer and older featured papers."""
    nav = []
    if i > 0:
        s = stories[i - 1]
        nav.append(f'<a class="cm-pager__prev" href="portfolio/{s["slug"]}/"><span>Newer</span>{esc(s["title"])}</a>')
    if i + 1 < len(stories):
        s = stories[i + 1]
        nav.append(f'<a class="cm-pager__next" href="portfolio/{s["slug"]}/"><span>Older</span>{esc(s["title"])}</a>')
    return f'<nav class="cm-pager" aria-label="More featured research">{"".join(nav)}</nav>'


def page_story(story: Story, stories: list[Story], i: int, ledger: Ledger, lab: set[str],
               software: list[Record]) -> None:
    """docs/portfolio/<slug>.md: picture, citation(s), abstract, links, related
    software/data, and newer/older navigation within `stories`."""
    image = story["image"]
    p = Page(f"portfolio/{story['slug']}.md", title=story["title"], menu="publications/", edit_url=edit_url("data/featured.yaml"),
             description=one_line(story["summary"], 300),
             image=image or paper_image(), og_type="article")
    picture = rights.image_object(image or paper_image(), SITE_URL + p.meta["image"])   # the preview picture
    p.meta["jsonld"] = to_json(article(story, p.url, picture))
    p.meta["citation"] = scholar_tags(story)
    p.add(f'# {esc(story["title"])}')
    # Lead section (#21): the picture beside the citation and summary on wide
    # screens (about 38% / 62%), above them with a capped height on narrow ones.
    text = "".join([*(f'<div class="cm-story__cite cm-pub">{citation(rec, lab, ledger, heading="p")}</div>'
                      for rec in story["pubs"]),
                    *(f"<p>{esc(para.strip())}</p>" for para in story["summary"].splitlines() if para.strip())])
    credit = rights.credit(image) if image else ""
    pic = (f'<figure class="cm-story__media">{media(image, story["alt"], 1000, eager=True, sizes="(max-width: 760px) 100vw, 360px")}'
           f'{f"<figcaption>{esc(credit)}</figcaption>" if credit else ""}</figure>' if image else "")
    p.add(f'<div class="cm-story__lead{"" if image else " cm-story__lead--text"}">{pic}<div class="cm-story__text">{text}</div></div>')
    main = story["pubs"][0]
    buttons = [f'<a class="cm-button" href="https://doi.org/{esc(main["doi"])}">Read the paper</a>']
    pre = ledger.preprint_of(main)
    if pre:
        buttons.append(f'<a class="cm-button cm-button--ghost" href="https://doi.org/{esc(pre["doi"])}">{PREPRINT_LINK}</a>')
    p.add(f'<p class="cm-story__links">{" ".join(buttons)}</p>')
    p.add(_related(story, ledger, software), _pager(stories, i))
    p.write()


def publication_filter_kind(rec: Record) -> str:
    """Browser-filter category: peer review is an explicit ledger fact, not inferred from status."""
    if rec.get("status") == "preprint":
        return "preprint"
    return "peer-reviewed" if rec.get("peer_reviewed") is True else "other"


def page_publications(ledger: Ledger, featured: list[Story], lab: set[str], leader: Person) -> None:
    """docs/publications.md: every publication by year, with search and filters
    (filtering itself is done in the browser by cellmig.js)."""
    records = ledger.grouped()
    stories = story_by_doi(featured, ledger)
    years = sorted({r["year"] for r in records}, reverse=True)
    n_pre = sum(1 for r in records if r.get("status") == "preprint")
    p = Page("publications.md", title="Publications", **preview("publications"))
    p.meta["jsonld"] = to_json(item_list(
        "Publications of Guillaume Jacquemet and the Cell Migration Lab",
        [publication_item(r, ledger.dates.get(r["doi"].lower())) for r in records],
        f"All publications of Guillaume Jacquemet, who founded the Cell Migration Lab in {LAB_FOUNDED}; "
        f"papers before {LAB_FOUNDED} are from his PhD and postdoctoral work."))
    p.add("# Publications", section_nav(PAPERS, "All publications"),
          f'<p class="cm-lead">{len(records)} papers and preprints, newest first. Authors directly associated with the lab are '
          '<span class="cm-author--lab">highlighted</span>; preprints are merged with their journal version.</p>',
          '<form class="cm-filter" data-cm-filter="publications" role="search" onsubmit="return false">',
          '<label class="cm-visually-hidden" for="pub-search">Search publications</label>',
          '<input id="pub-search" type="search" placeholder="Search title, author, journal…" data-cm-search>',
          '<div class="cm-filter__chips" role="group" aria-label="Show">',
          '<button type="button" class="is-active" data-cm-kind="">All</button>',
          '<button type="button" data-cm-kind="peer-reviewed">Peer-reviewed</button>',
          f'<button type="button" data-cm-kind="preprint">Preprints ({n_pre})</button>',
          "</div>",
          '<p class="cm-filter__count" data-cm-count aria-live="polite"></p>',
          "</form>")
    for y in years:
        p.add(f'<section class="cm-year" data-cm-group><h2 id="y{y}">{y}</h2><ol class="cm-pubs">')
        for rec in (r for r in records if r["year"] == y):
            story = stories.get(rec["doi"].lower())
            link = f"portfolio/{story['slug']}/" if story else None
            kind = publication_filter_kind(rec)
            text = " ".join([rec["title"], *(rec["authors"]), rec["venue"], rec["doi"]]).lower()
            p.add(f'<li class="cm-pub" data-kind="{kind}" data-search="{esc(text)}">'
                  f'{citation(rec, lab, ledger, link, abstract=True)}</li>')
        p.add("</ol></section>")
    p.add('<p class="cm-small cm-source">'
          f'Also on <a href="{esc(ledger.metrics["scholar_url"])}">Google Scholar</a> and '
          f'<a href="{esc(orcid_url(leader["orcid"]))}">ORCID</a>.</p>')
    p.write()
