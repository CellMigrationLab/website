"""The home page (docs/index.md, rendered with overrides/home.html)."""

from . import rights
from .components import feature_card, logo_row, section_title, support_row
from .config import HOME_FEATURED, UNCAPTIONED_ALT
from .featured import Story
from .images import media
from .ledger import Record
from .page import Page
from .previews import preview
from .text import esc


def band(b: Record) -> str:
    """Full-width picture between sections."""
    text = " ".join(x for x in (b.get("caption"), rights.credit(b["image"])) if x)
    cap = f'<figcaption>{esc(text)}</figcaption>' if text else ""
    return f'<figure class="cm-band">{media(b["image"], b.get("caption") or UNCAPTIONED_ALT, 2400, sizes="100vw")}{cap}</figure>'


def page_home(site: Record, featured: list[Story], affiliations: list[Record], funding: list[Record]) -> None:
    """Hero, newest featured papers, affiliations and current research
    support; data/site.yaml `bands` (two pictures) go between the sections."""
    hero, bands = site["hero"], site["bands"]
    p = Page("index.md", template="home.html", title="Home", head_title=f'{site["name"]} – {site["motto"].rstrip(".")}',
             **preview("index"))
    p.add(
        '<section class="cm-hero">',
        '<div class="cm-hero__text">',
        f'<h1 class="cm-hero__title">{esc(site["tagline"])}</h1>',
        "</div>",
        f'<figure class="cm-hero__image">{media(hero["image"], hero.get("caption") or UNCAPTIONED_ALT, 2400, eager=True, sizes="100vw")}</figure>',
        "</section>",
        f'<p class="cm-intro">{esc(site["intro"])}</p>',
    )
    p.add(section_title("Featured research", id_="featured"), '<div class="cm-cards cm-cards--home">',
          *(feature_card(s) for s in featured[:HOME_FEATURED]),
          "</div>", f'<p class="cm-more-link"><a href="featured-research/">All featured research ({len(featured)})</a>'
          ' · <a href="publications/">All publications</a></p>')
    p.add(band(bands[0]), section_title("Affiliations"), logo_row(affiliations), band(bands[1]),
          section_title("Current research support", id_="funding"), support_row(funding))
    p.write()
