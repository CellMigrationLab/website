"""Featured research grid, one page per featured paper, and all publications."""


from .components import citation, feature_card, one_line
from .config import edit_url
from .featured import Story, story_by_doi
from .images import media
from .ledger import Ledger, Record, software_list
from .page import Page
from .text import esc, slugify


def page_featured(featured: list[Story], unlisted: list[Story], ledger: Ledger, lab: set[str]) -> None:
    """docs/featured-research.md (the grid) and docs/portfolio/<slug>.md for each
    story; unlisted stories get their page too (old addresses) but no grid card."""
    p = Page("featured-research.md", title="Featured Research", edit_url=edit_url("data/featured.yaml"),
             description="Our main papers: every paper led by the Cell Migration Lab, with its abstract.")
    p.add("# Featured Research",
          '<p class="cm-lead">Papers led by our lab, newest first. See <a href="publications/">all our publications</a>.</p>',
          '<div class="cm-cards cm-cards--grid">', *(feature_card(s) for s in featured), "</div>")
    p.write()
    software = software_list(ledger)
    for i, story in enumerate(featured):
        page_story(story, featured, i, ledger, lab, software)
    for story in unlisted:
        page_story(story, [story], 0, ledger, lab, software)


def _related(story: Story, ledger: Ledger, software: list[Record]) -> str:
    """Aside listing software and datasets linked to any version of the story's papers."""
    dois = set().union(*(ledger.family_dois(d) for d in story["papers"]))
    tools = [s for s in software if {d.lower() for d in s["dois"]} & dois]
    data = [d for d in ledger.datasets if {x.lower() for x in d.get("related_publication_dois") or []} & dois]
    if not (tools or data):
        return ""
    out = ['<aside class="cm-related">']
    if tools:
        out.append("<h2>Software</h2><ul>")
        out += [f'<li><a href="software/#{slugify(s["title"])}">{esc(s["title"])}</a>'
                + (f' · <a href="{esc(s["github"])}">code</a>' if s.get("github") else "") + "</li>" for s in tools]
        out.append("</ul>")
    if data:
        out.append("<h2>Data</h2><ul>")
        out += [f'<li><a href="{esc(d["repository_url"])}">{esc(d["title"])}</a></li>' for d in data]
        out.append("</ul>")
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
    p = Page(f"portfolio/{story['slug']}.md", title=story["title"], edit_url=edit_url("data/featured.yaml"),
             description=one_line(story["summary"], 300),
             image=image if image and not image.endswith(".gif") else None)
    p.add(f'# {esc(story["title"])}')
    if image:
        p.add(f'<figure class="cm-story__media">{media(image, story["title"], 1600, eager=True, sizes="(max-width: 900px) 100vw, 900px")}</figure>')
    p.add(*(f'<div class="cm-story__cite cm-pub">{citation(rec, lab, ledger, heading="p")}</div>' for rec in story["pubs"]))
    p.add(*(f"<p>{esc(para.strip())}</p>" for para in story["summary"].splitlines() if para.strip()))
    main = story["pubs"][0]
    buttons = [f'<a class="cm-button" href="https://doi.org/{esc(main["doi"])}">Read the paper</a>']
    pre = ledger.preprint_of(main)
    if pre:
        buttons.append(f'<a class="cm-button cm-button--ghost" href="https://doi.org/{esc(pre["doi"])}">Preprint</a>')
    p.add(f'<p class="cm-story__links">{" ".join(buttons)}</p>')
    p.add(_related(story, ledger, software), _pager(stories, i))
    p.write()


def page_publications(ledger: Ledger, featured: list[Story], lab: set[str]) -> None:
    """docs/publications.md: every publication by year, with search and filters
    (filtering itself is done in the browser by cellmig.js)."""
    records = ledger.grouped()
    stories = story_by_doi(featured, ledger)
    years = sorted({r["year"] for r in records}, reverse=True)
    n_pre = sum(1 for r in records if r.get("status") == "preprint")
    p = Page("publications.md", title="Publications",
             description="All publications and preprints of the Cell Migration Lab, updated automatically.")
    p.add("# Publications",
          f'<p class="cm-lead">{len(records)} papers and preprints, newest first. Lab members are '
          '<span class="cm-author--lab">highlighted</span>; preprints are merged with their journal version.</p>',
          '<form class="cm-filter" data-cm-filter role="search" onsubmit="return false">',
          '<label class="cm-visually-hidden" for="pub-search">Search publications</label>',
          '<input id="pub-search" type="search" placeholder="Search title, author, journal…" data-cm-search>',
          '<div class="cm-filter__chips" role="group" aria-label="Show">',
          '<button type="button" class="is-active" data-cm-kind="">All</button>',
          '<button type="button" data-cm-kind="published">Peer-reviewed</button>',
          f'<button type="button" data-cm-kind="preprint">Preprints ({n_pre})</button>',
          "</div>",
          '<p class="cm-filter__count" data-cm-count aria-live="polite"></p>',
          "</form>")
    for y in years:
        p.add(f'<section class="cm-year" data-cm-year><h2 id="y{y}">{y}</h2><ol class="cm-pubs">')
        for rec in (r for r in records if r["year"] == y):
            story = stories.get(rec["doi"].lower())
            link = f"portfolio/{story['slug']}/" if story else None
            kind = "preprint" if rec.get("status") == "preprint" else "published"
            text = " ".join([rec["title"], *(rec.get("authors") or []), rec.get("venue") or "", rec["doi"]]).lower()
            p.add(f'<li class="cm-pub" data-kind="{kind}" data-search="{esc(text)}">'
                  f'{citation(rec, lab, ledger, link, abstract=True)}</li>')
        p.add("</ol></section>")
    p.add('<p class="cm-small cm-source">This list is generated from our '
          '<em>things_done</em> activity ledger and updates automatically when a paper is added. '
          'Also on <a href="https://scholar.google.com/citations?user=dnBWtfsAAAAJ&hl=en">Google Scholar</a> and '
          '<a href="https://orcid.org/0000-0002-9286-920X">ORCID</a>.</p>')
    p.write()
