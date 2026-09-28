"""The home page (docs/index.md, rendered with overrides/home.html)."""

from .components import citation, feature_card, logo_row, section_title
from .config import HOME_FEATURED, UNCAPTIONED_ALT
from .featured import Story, story_by_doi
from .images import media
from .ledger import Ledger, Record
from .news import KIND_LABELS, NewsItem, date_label
from .page import Page
from .previews import preview
from .text import esc

LATEST_PAPERS = 5
LATEST_NEWS = 4


def band(b: Record) -> str:
    """Full-width picture between sections."""
    cap = f'<figcaption>{esc(b["caption"])}</figcaption>' if b.get("caption") else ""
    return f'<figure class="cm-band">{media(b["image"], b.get("caption") or UNCAPTIONED_ALT, 2400, sizes="100vw")}{cap}</figure>'


def latest_news(news: list[NewsItem]) -> str:
    """The newest news items that are not papers (papers have their own list)."""
    items = [n for n in news if n["kind"] not in ("paper", "preprint")][:LATEST_NEWS]
    rows = "".join(f'<li><span class="cm-talklist__date">{esc(date_label(n))}</span><span>'
                   f'<span class="cm-badge cm-news__kind">{KIND_LABELS[n["kind"]]}</span> {n["html"]}</span></li>'
                   for n in items)
    return (f'{section_title("Latest news")}<ul class="cm-talklist cm-news cm-news--home">{rows}</ul>'
            '<p class="cm-more-link"><a href="news/">All news</a></p>')


def page_home(site: Record, featured: list[Story], ledger: Ledger, lab: set[str],
              affiliations: list[Record], funding: list[Record], news: list[NewsItem]) -> None:
    """Hero, newest featured papers, latest papers and news, affiliations,
    funders; data/site.yaml `bands` (two pictures) go between the sections."""
    hero, bands = site["hero"], site["bands"]
    welcome = f'<p class="cm-hero__welcome">{esc(site["welcome"])}</p>' if site.get("welcome") else ""
    p = Page("index.md", template="home.html", title="Home", head_title=f'{site["name"]} – {site["motto"].rstrip(".")}',
             **preview("index"))
    p.add(
        '<section class="cm-hero">',
        '<div class="cm-hero__text">',
        f'<h1 class="cm-hero__title">{esc(site["tagline"])}</h1>',
        welcome,
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
    p.add("</ol>", '<p class="cm-more-link"><a href="publications/">All publications</a></p>', latest_news(news))

    p.add(band(bands[1]), section_title("Affiliations"), logo_row(affiliations),
          section_title("Funding"), logo_row(funding))
    p.write()
