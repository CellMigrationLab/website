"""The home page (docs/index.md, rendered with overrides/home.html)."""

from .components import citation, feature_card, logo_row, section_title
from .config import HOME_FEATURED, UNCAPTIONED_ALT
from .featured import Story, story_by_doi
from .images import media
from .ledger import Ledger, Record
from .page import Page
from .previews import preview
from .text import esc

LATEST_PAPERS = 5


def band(b: Record) -> str:
    """Full-width picture between sections."""
    cap = f'<figcaption>{esc(b["caption"])}</figcaption>' if b.get("caption") else ""
    return f'<figure class="cm-band">{media(b["image"], b.get("caption") or UNCAPTIONED_ALT, 2400, sizes="100vw")}{cap}</figure>'


def page_home(site: Record, featured: list[Story], ledger: Ledger, lab: set[str],
              affiliations: list[Record], funding: list[Record]) -> None:
    """Hero, newest featured papers, latest papers, affiliations, funders;
    data/site.yaml `bands` (two pictures) go between the sections."""
    hero, bands = site["hero"], site["bands"]
    p = Page("index.md", template="home.html", title="Home", head_title=f'{site["name"]} – {site["motto"].rstrip(".")}',
             **preview("index"))
    p.add(
        '<section class="cm-hero">',
        '<div class="cm-hero__text">',
        f'<h1 class="cm-hero__title">{esc(site["tagline"])}</h1>',
        f'<p class="cm-hero__welcome">{esc(site["welcome"])}</p>',
        "</div>",
        f'<figure class="cm-hero__image">{media(hero["image"], hero.get("caption") or UNCAPTIONED_ALT, 2400, eager=True, sizes="100vw")}</figure>',
        "</section>",
        f'<p class="cm-intro">{esc(site["intro"])}</p>',
    )
    p.add(section_title("Featured research", id_="featured"), '<div class="cm-cards cm-cards--home">',
          *(feature_card(s) for s in featured[:HOME_FEATURED]),
          "</div>", f'<p class="cm-more-link"><a href="featured-research/">All featured research ({len(featured)})</a></p>')
    p.add(band(bands[0]))

    stories = story_by_doi(featured, ledger)
    p.add(section_title("Latest papers"), '<ol class="cm-pubs cm-pubs--compact">')
    for rec in ledger.grouped()[:LATEST_PAPERS]:
        story = stories.get(rec["doi"].lower())
        link = f"portfolio/{story['slug']}/" if story else None
        p.add(f'<li class="cm-pub">{citation(rec, lab, ledger, link)}</li>')
    p.add("</ol>", '<p class="cm-more-link"><a href="publications/">All publications</a></p>')

    p.add(band(bands[1]), section_title("Affiliations"), logo_row(affiliations),
          section_title("Funding"), logo_row(funding))
    p.write()
