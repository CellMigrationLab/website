"""HTML snippets used on more than one page."""

import re

from .config import FITS, TILE_SURFACES, fail
from .featured import Story
from .icons import ICONS
from .images import image_size, media, square_thumb, thumb
from .ledger import Ledger, Record
from .people import Person, is_lab_member
from .text import esc, md

AUTHOR_LIMIT = 12   # longer author lists are shortened to the first 11 + last


def section_title(text: str, level: int = 2, id_: str | None = None) -> str:
    """Heading with the site's decorative rule."""
    i = f' id="{id_}"' if id_ else ""
    return f'<h{level} class="cm-section-title"{i}><span>{esc(text)}</span></h{level}>'


# Sibling pages shown as a row under a page title; each page belongs to one
# main-menu item (Page `menu`), which stays highlighted on all of them.
RESEARCH = [("Research", "research/"), ("Online talks", "online-lectures/")]
SOFTWARE_DATA = [("Software", "software/"), ("Datasets", "datasets/")]
PAPERS = [("Featured research", "featured-research/"), ("All publications", "publications/")]


def section_nav(links: list[tuple[str, str]], current: str) -> str:
    """Row of buttons to sibling pages (e.g. Software, Datasets), styled like the
    Research page's buttons: `current` is the filled one, marked, not linked."""
    return '<nav class="cm-section-nav" aria-label="Section">' + " ".join(
        f'<span class="cm-button" aria-current="page">{esc(title)}</span>' if title == current
        else f'<a class="cm-button cm-button--ghost" href="{url}">{esc(title)}</a>'
        for title, url in links) + "</nav>"


# Link from a journal paper to its preprint: worded as an action, so it is not
# read as a status (the "Preprint" badge is only for records that are preprints).
PREPRINT_LINK = "Read the associated preprint"


def author_list(authors: list[str], lab: set[str]) -> str:
    """Comma-separated authors, long lists shortened. Authors directly associated
    with the lab, now or in the past, are highlighted on every paper: the
    highlight does not depend on the paper's year or on when they were in the lab."""
    out = [f'<span class="cm-author--lab">{esc(a)}</span>' if is_lab_member(a, lab) else esc(a)
           for a in authors]
    if len(out) > AUTHOR_LIMIT:
        hidden = len(out) - AUTHOR_LIMIT   # AUTHOR_LIMIT - 1 first authors and the last one are shown
        return ", ".join(out[: AUTHOR_LIMIT - 1]) + f', <span class="cm-more">… +{hidden} more</span>, ' + out[-1]
    return ", ".join(out)


# things_done open_access_status values that mean free to read (from OpenAlex);
# closed and unknown get no badge.
OPEN_ACCESS = {"gold", "diamond", "hybrid", "green", "bronze"}
OA_BADGE = '<span class="cm-badge cm-badge--oa" title="Open access">Open access</span>'


def oa_badge(rec: Record) -> str:
    """The Open access badge, or "" for a closed or unknown record."""
    return OA_BADGE if rec.get("open_access_status") in OPEN_ACCESS else ""


def badges(rec: Record) -> str:
    """Preprint / In press / Open access badges."""
    out = []
    if rec.get("status") == "preprint":
        out.append('<span class="cm-badge cm-badge--preprint">Preprint</span>')
    elif rec.get("status") == "in_press":
        out.append('<span class="cm-badge">In press</span>')
    return "".join(out) + oa_badge(rec)


# How a paper is mentioned. Two forms, the same everywhere:
# - citation(): the full reference (Publications, featured paper pages), with
#   authors, DOI and all badges (Preprint, In press, Open access);
# - the short forms below (cards, Research, Software, Datasets): the journal in
#   italics, " · ", the year, and only the Open access badge (a preprint shows
#   as one by its venue, bioRxiv).
def venue_year(rec: Record) -> str:
    """<em>Journal</em> · 2026"""
    return f'<em class="cm-venue">{esc(rec["venue"])}</em> · {rec["year"]}'


def paper_link(rec: Record) -> str:
    """Short reference without the title: the journal and year, linked to the DOI."""
    return f'<a href="https://doi.org/{esc(rec["doi"])}">{venue_year(rec)}</a>{oa_badge(rec)}'


def paper_ref(rec: Record) -> str:
    """Short reference with the title: the title linked to the DOI, then journal and year."""
    return (f'<a href="https://doi.org/{esc(rec["doi"])}">{esc(rec["title"])}</a> '
            f'<span class="cm-ref__meta">{venue_year(rec)}</span>{oa_badge(rec)}')


def citation(rec: Record, lab: set[str], ledger: Ledger, story_url: str | None = None,
             abstract: bool = False, heading: str = "h3") -> str:
    """A publication: title, authors, venue/year/DOI, preprint and story links,
    and (optionally) a collapsible abstract."""
    doi = rec["doi"]
    links = []
    pre = ledger.preprint_of(rec)
    if pre:
        links.append(f'<a href="https://doi.org/{esc(pre["doi"])}">{PREPRINT_LINK}</a>')
    if story_url:
        links.append(f'<a href="{story_url}">Read more</a>')
    parts = [
        f'<{heading} class="cm-pub__title"><a href="https://doi.org/{esc(doi)}">{esc(rec["title"])}</a></{heading}>',
        f'<p class="cm-pub__authors">{author_list(rec["authors"], lab)}</p>',
        f'<p class="cm-pub__venue">{venue_year(rec)}'
        f' · <a class="cm-doi" href="https://doi.org/{esc(doi)}">doi:{esc(doi)}</a>{badges(rec)}</p>',
    ]
    if links:
        parts.append(f'<p class="cm-pub__links">{" · ".join(links)}</p>')
    if abstract and "abstract" in rec:   # the sync leaves it out when things_done has none yet
        parts.append(f'<details class="cm-pub__abstract"><summary>Abstract</summary><p>{esc(rec["abstract"])}</p></details>')
    return "\n".join(parts)


def feature_card(story: Story) -> str:
    """Picture card linking to a featured paper's page (venue name when no picture)."""
    pub = story["pubs"][0]
    pic = (media(story["image"], story["title"], 700) if story["image"]
           else f'<span class="cm-card__placeholder">{esc(pub["venue"])}</span>')
    return (f'<a class="cm-card" href="portfolio/{story["slug"]}/">'
            f'<div class="cm-card__media{" cm-fit-contain" if story["fit"] == "contain" else ""}">{pic}</div>'
            f'<p class="cm-card__title">{esc(story["title"])}</p>'
            f'<p class="cm-card__meta">{venue_year(pub)}{oa_badge(pub)}</p></a>')


# Logo sizes (CSS px): every logo gets about the same visual area, so a wide
# word mark and a square seal look equally heavy (#20); within the slot limits.
LOGO_AREA, LOGO_MAX_W, LOGO_MAX_H = 6400, 170, 76


def logo_size(width: int, height: int, scale: float = 1.0) -> tuple[int, int]:
    """Display size of a logo with this intrinsic size: equal area within the
    slot, aspect ratio kept; `scale` (an optical correction) is applied last."""
    ratio = width / height
    h = min(LOGO_MAX_H, (LOGO_AREA / ratio) ** 0.5)
    w = h * ratio
    if w > LOGO_MAX_W:
        w, h = LOGO_MAX_W, LOGO_MAX_W / ratio
    return round(w * scale), round(h * scale)


def _logo(it: Record) -> str:
    """A linked logo (data/site.yaml entry: name, url, logo, optional `scale`
    for artwork with unusual whitespace); `logo: null` shows the name."""
    if it["logo"] is None:
        inner = f'<span class="cm-logos__text">{esc(it["name"])}</span>'
    else:
        src = thumb(it["logo"], 400)
        size = image_size(src)
        if not size:
            fail(f"data/site.yaml: logo {it['logo']} has no size (an SVG needs width and height attributes)")
        w, h = logo_size(*size, it.get("scale", 1.0))
        inner = f'<img src="{src}" width="{w}" height="{h}" alt="{esc(it["name"])}" loading="lazy">'
    return f'<a href="{esc(it["url"])}" title="{esc(it["name"])}">{inner}</a>'


def logo_row(items: list[Record]) -> str:
    """Row of linked logos (affiliations, research support)."""
    return '<ul class="cm-logos">' + "".join(f"<li>{_logo(it)}</li>" for it in items) + "</ul>"


def support_row(groups: list[Record]) -> str:
    """Current research support (ledger.support_list) as one row of logos,
    all sized alike: each group's funders, then the logos of its programmes
    (a programme's `scheme` mark first). Programmes without a logo, and a
    joint award's co-funders, are named in llms-full.txt, not here."""
    items = []
    for g in groups:
        items += g["logos"]
        for p in g["programmes"] + ([g["title"]] if g["title"] else []):
            items += [p["scheme"]] if "scheme" in p else []
            items += [p] if p["logo"] is not None else []
    return logo_row(items)

def tile(index: int, media_html: str, body_html: str, fit: str | None = None, picture_right_first: bool = False) -> str:
    """Two-column block (picture + text) used on Research and Software (#25):
    the surface follows TILE_SURFACES in turn by `index`; the picture side
    alternates (starting on the right with `picture_right_first`); `fit:
    contain` shows a logo or drawing whole instead of filling the tile."""
    if fit is not None and fit not in FITS:
        fail(f"media fit {fit!r} is not one of {sorted(FITS)}")
    surface = TILE_SURFACES[index % len(TILE_SURFACES)]
    side = " cm-tile--right" if (index + picture_right_first) % 2 == 1 else ""
    media_part = f'<div class="cm-tile__media{" cm-fit-contain" if fit == "contain" else ""}">{media_html}</div>' if media_html else ""
    text_only = "" if media_html else " cm-tile--text"
    return (f'<section class="cm-tile cm-tile--{surface}{side}{text_only}">'
            f'{media_part}<div class="cm-tile__body">{body_html}</div></section>')


# (profile key, icon, how to build the URL from the value)
def orcid_url(value: str) -> str:
    """ORCID link from an iD ("0000-...") or a full URL."""
    return value if value.startswith("http") else f"https://orcid.org/{value}"


PROFILE_LINKS = [
    ("email", "mail", lambda v: f"mailto:{v}"),
    ("orcid", "orcid", orcid_url),
    ("scholar", "scholar", str),
    ("github", "github", str),
    ("bluesky", "bluesky", str),
    ("website", "web", str),
]


def person_card(m: Person, profile_url: str | None = None) -> str:
    """Member photo (or initials), name, current role, bio and profile links.
    With `profile_url` (the group leader's profile on About us), the photo and
    the name link there; the profile icons stay separate links."""
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
    name = esc(m["name"])
    if profile_url:
        pic = f'<a class="cm-person__profile" href="{profile_url}" aria-label="{name}: profile">{pic}</a>'
        name = f'<a href="{profile_url}">{name}</a>'
    return (f'<li class="cm-person" id="{esc(m["slug"])}"><figure>{pic}'
            f'<figcaption><span class="cm-person__name">{name}</span>'
            f'<span class="cm-person__role">{esc(m["role"])}</span>{bio}{link_html}</figcaption></figure></li>')


# The last card of the members grid: an invitation to join, shaped like a member's card.
JOIN_CARD = ('<li class="cm-person cm-person--join"><a href="join-us/"><figure>'
             '<span class="cm-person__initials" aria-hidden="true">+</span>'
             '<figcaption><span class="cm-person__name">This could be you</span>'
             '<span class="cm-person__role">Join us</span></figcaption></figure></a></li>')


def one_line(text: str, limit: int) -> str:
    """Whitespace collapsed to single spaces; longer text is cut at the last
    word that fits and ends with "…" (at most `limit` characters)."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
