"""HTML snippets used on more than one page."""

import re

from .config import COLORS, fail
from .featured import Story
from .icons import ICONS
from .images import dims, media, square_thumb, thumb
from .ledger import Ledger, Record
from .people import Person, is_lab_member
from .text import esc, md

AUTHOR_LIMIT = 12   # longer author lists are shortened to the first 11 + last


def section_title(text: str, level: int = 2, id_: str | None = None) -> str:
    """Heading with the site's decorative rule."""
    i = f' id="{id_}"' if id_ else ""
    return f'<h{level} class="cm-section-title"{i}><span>{esc(text)}</span></h{level}>'


def author_list(authors: list[str], lab: set[str]) -> str:
    """Comma-separated authors, lab members highlighted, long lists shortened."""
    out = [f'<span class="cm-author--lab">{esc(a)}</span>' if is_lab_member(a, lab) else esc(a)
           for a in authors]
    if len(out) > AUTHOR_LIMIT:
        hidden = len(out) - AUTHOR_LIMIT + 1
        return ", ".join(out[: AUTHOR_LIMIT - 1]) + f', <span class="cm-more">… +{hidden} more</span>, ' + out[-1]
    return ", ".join(out)


def badges(rec: Record) -> str:
    """Preprint / In press / Open access badges."""
    out = []
    if rec.get("status") == "preprint":
        out.append('<span class="cm-badge cm-badge--preprint">Preprint</span>')
    elif rec.get("status") == "in_press":
        out.append('<span class="cm-badge">In press</span>')
    if rec.get("open_access_status") in {"gold", "hybrid", "green", "bronze"}:
        out.append('<span class="cm-badge cm-badge--oa" title="Open access">Open access</span>')
    return "".join(out)


def citation(rec: Record, lab: set[str], ledger: Ledger, story_url: str | None = None,
             abstract: bool = False, heading: str = "h3") -> str:
    """A publication: title, authors, venue/year/DOI, preprint and story links,
    and (optionally) a collapsible abstract."""
    doi = rec["doi"]
    links = []
    pre = ledger.preprint_of(rec)
    if pre:
        links.append(f'<a href="https://doi.org/{esc(pre["doi"])}">Preprint</a>')
    if story_url:
        links.append(f'<a href="{story_url}">Read more</a>')
    year = f' · {rec["year"]}' if rec.get("year") else ""
    parts = [
        f'<{heading} class="cm-pub__title"><a href="https://doi.org/{esc(doi)}">{esc(rec["title"])}</a></{heading}>',
        f'<p class="cm-pub__authors">{author_list(rec["authors"], lab)}</p>',
        f'<p class="cm-pub__venue"><em>{esc(rec.get("venue") or "")}</em>{year}'
        f' · <a class="cm-doi" href="https://doi.org/{esc(doi)}">doi:{esc(doi)}</a> {badges(rec)}</p>',
    ]
    if links:
        parts.append(f'<p class="cm-pub__links">{" · ".join(links)}</p>')
    if abstract and rec.get("abstract"):
        parts.append(f'<details class="cm-pub__abstract"><summary>Abstract</summary><p>{esc(rec["abstract"])}</p></details>')
    return "\n".join(parts)


def feature_card(story: Story) -> str:
    """Picture card linking to a featured paper's page (venue name when no picture)."""
    pub = story["pubs"][0]
    pic = (media(story["image"], story["title"], 700) if story["image"]
           else f'<span class="cm-card__placeholder">{esc(pub.get("venue") or "")}</span>')
    return (f'<a class="cm-card" href="portfolio/{story["slug"]}/">'
            f'<div class="cm-card__media">{pic}</div>'
            f'<p class="cm-card__title">{esc(story["title"])}</p>'
            f'<p class="cm-card__meta">{esc(pub.get("venue") or "")} · {pub.get("year")} {badges(pub)}</p></a>')


def logo_row(items: list[Record]) -> str:
    """Row of linked logos (funders); an item with `logo: null` is shown as its name."""
    def content(it: Record) -> str:
        if it["logo"] is None:
            return f'<span class="cm-logos__text">{esc(it["name"])}</span>'
        src = thumb(it["logo"], 400)
        return f'<img src="{src}"{dims(src)} alt="{esc(it["name"])}" loading="lazy">'
    lis = "".join(f'<li><a href="{esc(it["url"])}" title="{esc(it["name"])}">{content(it)}</a></li>' for it in items)
    return f'<ul class="cm-logos">{lis}</ul>'


def tile(color: str, media_html: str, body_html: str, media_right: bool = False) -> str:
    """Coloured two-column block (picture + text) used on Research and Software."""
    if color not in COLORS:
        fail(f"tile colour {color!r} is not one of {sorted(COLORS)}")
    side = " cm-tile--right" if media_right else ""
    media_part = f'<div class="cm-tile__media">{media_html}</div>' if media_html else ""
    text_only = "" if media_html else " cm-tile--text"
    return (f'<section class="cm-tile cm-tile--{color}{side}{text_only}">'
            f'{media_part}<div class="cm-tile__body">{body_html}</div></section>')


# (profile key, icon, how to build the URL from the value)
PROFILE_LINKS = [
    ("email", "mail", lambda v: f"mailto:{v}"),
    ("orcid", "orcid", lambda v: v if v.startswith("http") else f"https://orcid.org/{v}"),
    ("scholar", "scholar", str),
    ("github", "github", str),
    ("bluesky", "bluesky", str),
    ("website", "web", str),
]


def person_card(m: Person) -> str:
    """Member photo (or initials), name, current role, bio and profile links."""
    if m.get("photo"):
        img = square_thumb(m["photo"], 480, m.get("photo_position", "top"))
        pic = f'<img src="{img}" alt="{esc(m["name"])}" width="480" height="480" loading="lazy">'
    else:
        initials = "".join(w[0] for w in m["name"].split()[:2]).upper()
        pic = f'<span class="cm-person__initials" aria-hidden="true">{esc(initials)}</span>'
    links = "".join(f'<a href="{esc(url(m[key]))}" aria-label="{esc(m["name"])} – {key}">{ICONS[icon]}</a>'
                    for key, icon, url in PROFILE_LINKS if m.get(key))
    link_html = f'<span class="cm-person__links">{links}</span>' if links else ""
    bio = f'<span class="cm-person__bio">{md(m["bio"], inline=True)}</span>' if m.get("bio") else ""
    return (f'<li class="cm-person" id="{esc(m["slug"])}"><figure>{pic}'
            f'<figcaption><span class="cm-person__name">{esc(m["name"])}</span>'
            f'<span class="cm-person__role">{esc(m["role"])}</span>{bio}{link_html}</figcaption></figure></li>')


def one_line(text: str, limit: int) -> str:
    """Whitespace collapsed to single spaces; longer text is cut at the last
    word that fits and ends with "…" (at most `limit` characters)."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
