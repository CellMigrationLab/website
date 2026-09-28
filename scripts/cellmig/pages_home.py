"""The home page (docs/index.md, rendered with overrides/home.html)."""

from . import rights
from .components import feature_card, section_title, support_row
from .config import HOME_FEATURED, UNCAPTIONED_ALT
from .featured import AREAS, Story
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


def page_home(site: Record, featured: list[Story], funding: list[Record]) -> None:
    """Hero, the newest featured papers of each area (biology, then methods),
    and current research support; data/site.yaml `bands` (two pictures) go
    between the sections."""
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
    for i, (area, name) in enumerate(AREAS.items()):
        if i:
            p.add(band(bands[0]))   # a picture between the two groups
        p.add(section_title(f"Featured research: {name.lower()}", id_=area), '<div class="cm-cards cm-cards--home">',
              *(feature_card(s) for s in [s for s in featured if s["area"] == area][:HOME_FEATURED]), "</div>")
    p.add(f'<p class="cm-more-link"><a href="featured-research/">All featured research ({len(featured)})</a>'
          ' · <a href="publications/">All publications</a></p>',
          band(bands[1]), section_title("Current research support", id_="funding"), support_row(funding))
    p.write()
