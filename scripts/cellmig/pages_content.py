"""Pages built mostly from the website's own files: Research, Software, Datasets,
Gallery, Online talks, and the hand-written pages in content/."""

import re

import yaml

from .components import SOFTWARE_DATA, oa_badge, section_nav, section_title, tile
from . import rights
from .config import (
    CONTENT,
    DATA,
    DATASET_TAGS,
    DATASET_TYPES,
    UNCAPTIONED_ALT,
    edit_url,
    fail,
    load,
)
from .images import image_size, lite_video, media, thumb
from .ledger import Ledger, Record, software_list
from .page import Page, new_tab_markdown
from .previews import preview
from .structured import dataset_item, item_list, software_item, to_json
from .text import esc, is_external, md, slugify, year_of

BROWSE_PUBLICATIONS = '<a class="cm-button" href="publications/">Browse all our publications</a>'
# Research page: the papers behind the themes, at the top and the bottom.
FEATURED_RESEARCH = '<a class="cm-button" href="featured-research/">Explore our featured research</a>'


def _theme(t: Record, ledger: Ledger) -> str:
    """Text of one research theme: title, lead, paragraphs, selected papers, credit."""
    body = [f'<h2 id="{slugify(t["title"])}">{esc(t["title"])}</h2>']
    if t.get("lead"):
        body.append(f'<p class="cm-tile__lead">{md(t["lead"], inline=True)}</p>')
    body += [md(x) for x in t.get("text") or []]
    papers = [ledger.published_version(ledger.require(d, f"data/research.yaml ({t['title']})"))
              for d in t.get("papers") or []]
    dois = [r["doi"] for r in papers]
    if len(dois) != len(set(dois)):   # e.g. a preprint and its journal version both listed
        fail(f"data/research.yaml ({t['title']}): a paper is listed twice {sorted({d for d in dois if dois.count(d) > 1})}")
    if papers:
        body.append('<p class="cm-tile__label">Selected papers</p><ul class="cm-tile__papers">')
        body += [f'<li><a href="https://doi.org/{esc(r["doi"])}">{esc(r["title"])}</a>'
                 f' <span>{esc(r["venue"])}, {r["year"]}</span>'
                 f' {oa_badge(r)}</li>' for r in papers]   # a preprint shows as such by its venue (bioRxiv)
        body.append("</ul>")
    caption = " ".join(x for x in (t.get("credit"), rights.credit(t["image"]) if t.get("image") else "") if x)
    if caption:   # `credit` in research.yaml is the caption; the © line comes from data/media.yaml
        body.append(f'<p class="cm-tile__credit">{esc(caption)}</p>')
    return "\n".join(body)


def _no_colour(entry: Record, source: str) -> None:
    """Tiles take their colour from their place (config.TILE_SURFACES)."""
    if "color" in entry:
        fail(f"{source} ({entry.get('title') or entry.get('id')}): remove `color`; "
             "tile colours follow each other down the page")


def page_research(ledger: Ledger) -> None:
    """docs/research.md from data/research.yaml: videos, then one tile per theme."""
    research = load(DATA / "research.yaml")
    p = Page("research.md", title="Research", edit_url=edit_url("data/research.yaml"), **preview("research"))
    papers = f'{FEATURED_RESEARCH} {BROWSE_PUBLICATIONS.replace("cm-button", "cm-button cm-button--ghost", 1)}'
    p.add("# Research", f'<p class="cm-lead">{esc(research["intro"])}</p>', f'<p class="cm-research-links">{papers}</p>',
          '<div class="cm-videos">')
    p.add(*(f'<figure>{lite_video(v.get("youtube"), v.get("vimeo"), v["title"], v.get("start"))}'
            f'<figcaption>{esc(v["title"])}</figcaption></figure>' for v in research.get("videos") or []))
    p.add("</div>", '<div class="cm-wide">')
    for i, t in enumerate(research["themes"]):
        _no_colour(t, "data/research.yaml")
        p.add(tile(i, media(t.get("image"), t.get("credit", ""), 1000), _theme(t, ledger), t.get("fit")))
    p.add("</div>", f'<p class="cm-cta">{papers}</p>')
    p.write()


def _software_body(s: Record) -> str:
    """Text of one software tile: title (year), description, links."""
    title = f'{s["title"]} ({s["year"]})' if s.get("year") else s["title"]
    text = md(s.get("text") or "")
    papers = s["papers"]   # never empty (software_list); journal versions once published
    if len(papers) == 1:
        links = [f'<a href="https://doi.org/{esc(papers[0]["doi"])}">Read our paper</a>']
    else:
        links = ["Read our papers: " + ", ".join(
            f'<a href="https://doi.org/{esc(r["doi"])}">{esc(r["venue"])}, {r["year"]}</a>' for r in papers)]
    host = "GitHub" if "github.com" in s["github"] else "Code"
    links.append(f'<a href="{esc(s["github"])}">Find {esc(s["title"])} on {host}</a>')
    links += [f'<a href="{esc(link["url"])}">{esc(link["label"])}</a>' for link in s.get("links") or []]
    return f'<h2 id="{slugify(s["title"])}">{esc(title)}</h2>{text}<p class="cm-tile__links">{" · ".join(links)}</p>'


def page_software(ledger: Ledger) -> None:
    """docs/software.md: one tile per project (things_done + data/software.yaml)."""
    p = Page("software.md", title="Software", edit_url=edit_url("data/software.yaml"), **preview("software"))
    projects = software_list(ledger)
    p.meta["jsonld"] = to_json(item_list("Software from the Cell Migration Lab", [
        software_item(s, f"{p.url}#{slugify(s['title'])}") for s in projects]))
    p.add("# Software", section_nav(SOFTWARE_DATA, "Software"),
          '<p class="cm-lead">Here are the tools we have developed or contributed to. '
          'Many are designed to make microscopy and image analysis easier to run, reproduce and share. '
          'Looking for example data or trained models? See '
          '<a href="datasets/">our datasets, models and materials</a>.</p>', '<div class="cm-wide">')
    for i, s in enumerate(projects):
        pic = media(s.get("video") or s.get("image"), f'{s["title"]} logo' if s.get("image") else "", 900)
        _no_colour(s, "data/software.yaml")
        p.add(tile(i, pic, _software_body(s), s.get("fit"), picture_right_first=True))   # as before
    p.add("</div>", f'<p class="cm-cta">{BROWSE_PUBLICATIONS} '
          '<a class="cm-button cm-button--ghost" href="https://github.com/CellMigrationLab">CellMigrationLab on GitHub</a></p>')
    p.write()


def _dataset_tag(tag: str, d: Record) -> str:
    """Badge text of a things_done dataset tag; an unknown tag stops the build."""
    if tag not in DATASET_TAGS:
        fail(f"dataset {d['title']!r}: tag {tag!r} has no badge; add it to DATASET_TAGS in scripts/cellmig/config.py")
    return DATASET_TAGS[tag]


def _dataset_type(d: Record) -> str:
    """Section of a dataset; an unknown things_done dataset_type stops the build."""
    if d["dataset_type"] not in DATASET_TYPES:
        fail(f"dataset {d['title']!r}: type {d['dataset_type']!r} has no section; add it to DATASET_TYPES "
             "in scripts/cellmig/config.py")
    return DATASET_TYPES[d["dataset_type"]]


def _dataset(d: Record, ledger: Ledger) -> str:
    """One dataset: title, tags, description, year, archive DOI and papers."""
    refs = [f'<a href="https://doi.org/{esc(rec["doi"])}">{esc(rec["venue"])}, {rec["year"]}</a>'
            for rec in ledger.dataset_papers(d)]
    tags = "".join(f'<span class="cm-badge">{esc(_dataset_tag(t, d))}</span>' for t in d.get("dataset_tags") or [])
    archive = d.get("archive_doi")
    archive_html = (f' · <a href="https://doi.org/{esc(archive)}">doi:{esc(archive)}</a>'
                    if archive and archive not in d["repository_url"] else "")
    return (f'<li><a class="cm-datasets__title" href="{esc(d["repository_url"])}">{esc(d["title"])}</a>{tags}'
            f'<p>{md(d["description"], inline=True)}</p>'
            f'<p class="cm-small">{year_of(d["start_date"])}{archive_html}'
            f'{" · Paper: " + ", ".join(refs) if refs else ""}</p></li>')


def page_datasets(ledger: Ledger, site: Record) -> None:
    """docs/datasets.md: shared resources (data/site.yaml), then datasets by type."""
    p = Page("datasets.md", title="Datasets", menu="software/", **preview("datasets"))
    p.meta["jsonld"] = to_json(item_list("Datasets shared by the Cell Migration Lab",
                                         [dataset_item(d, ledger.dataset_papers(d)) for d in ledger.datasets]))
    p.add("# Datasets", section_nav(SOFTWARE_DATA, "Datasets"),
          '<p class="cm-lead">We share microscopy datasets, trained models and other research data from our work. '
          'Many accompany published papers or provide examples for our image-analysis tools. '
          'Looking for analysis software? See <a href="software/">our software</a>.</p>')
    p.add('<ul class="cm-resources">', *(
        f'<li><a href="{esc(r["url"])}"><strong>{esc(r["title"])}</strong><span>{esc(r.get("text", ""))}</span></a></li>'
        for r in site["resources"]), "</ul>")
    groups: dict[str, list[Record]] = {}
    for d in ledger.datasets:
        groups.setdefault(_dataset_type(d), []).append(d)
    order = [g for g in DATASET_TYPES.values() if g in groups]
    p.add('<nav class="cm-toc-inline">' + " · ".join(
        f'<a href="#{slugify(g)}">{esc(g)} ({len(groups[g])})</a>' for g in order) + "</nav>")
    for g in order:
        p.add(f'<h2 id="{slugify(g)}">{esc(g)}</h2>', '<ul class="cm-datasets">',
              *(_dataset(d, ledger) for d in groups[g]), "</ul>")
    p.write()


GALLERY_ROW = 8.5   # rem: height a gallery row aims for before it is stretched to the full width


def _justified(site_path: str) -> str:
    """Flex sizes of a gallery picture in rows of equal height (#gallery):
    basis and growth both proportional to its aspect ratio, so every picture
    in a row gets the same height and none is cropped. Computed here, not by
    the browser, so the layout is the same in every browser."""
    size = image_size(site_path)
    if not size:
        fail(f"data/gallery.yaml: {site_path} has no size (an SVG needs width and height attributes)")
    ratio = size[0] / size[1]
    return f"flex: {ratio * 100:.1f} 1 {ratio * GALLERY_ROW:.2f}rem"


def page_gallery() -> None:
    """docs/gallery.md from data/gallery.yaml: journal covers and images (lightbox)."""
    gallery = load(DATA / "gallery.yaml")
    p = Page("gallery.md", title="Gallery", edit_url=edit_url("data/gallery.yaml"), **preview("gallery"))
    p.add("# Gallery", section_title("Journal covers"), '<ul class="cm-covers">')
    for c in gallery["covers"]:
        cap = esc(f'{c["caption"]} · {rights.credit(c["image"])}')   # journal and issue (required) · © the journal
        p.add(f'<li><a href="{thumb(c["image"], 1600)}" data-cm-lightbox data-caption="{cap}">'
              f'{media(c["image"], c["caption"], 500)}</a><span>{cap}</span></li>')
    p.add("</ul>", section_title("Images"), '<ul class="cm-gallery">')
    for g in gallery["images"]:
        cap = " ".join(x for x in (g.get("caption"), rights.credit(g["image"])) if x)   # © from data/media.yaml
        p.add(f'<li style="{_justified(g["image"])}"><a href="{thumb(g["image"], 2000)}" data-cm-lightbox data-caption="{esc(cap)}">'
              f'{media(g["image"], g.get("caption") or UNCAPTIONED_ALT, 600)}</a></li>')
    p.add("</ul>")
    p.write()


def page_talks() -> None:
    """docs/online-lectures.md: recorded talks from data/talks.yaml."""
    p = Page("online-lectures.md", title="Online talks", edit_url=edit_url("data/talks.yaml"),
             **preview("online-lectures"))
    p.add("# Online talks", '<div class="cm-talks">')
    for t in load(DATA / "talks.yaml"):
        meta = " · ".join(str(x) for x in (t.get("event"), t.get("year")) if x)
        p.add(f'<figure class="cm-talk">{lite_video(t.get("youtube"), t.get("vimeo"), t["title"], t.get("start"))}'
              f'<figcaption><strong>{esc(t["title"])}</strong><span>{esc(meta)}</span></figcaption></figure>')
    p.add("</div>")
    p.write()


def page_handwritten(name: str, extra: str = "") -> None:
    """docs/<name>.md from the hand-written content/<name>.md (front matter:
    only `title`), with its link preview from data/previews.yaml, an edit link
    to the file in content/, and `extra` (generated HTML) at the end."""
    source = CONTENT / f"{name}.md"
    m = re.match(r"---\n(.*?)\n---\n(.*)", source.read_text(encoding="utf-8"), re.S)
    if not m:
        fail(f"content/{name}.md must start with front matter (---, title: ..., ---)")
    front = yaml.safe_load(m.group(1)) or {}
    if set(front) != {"title"}:
        fail(f"content/{name}.md: front matter must be only `title` "
             "(description and image go in data/previews.yaml)")
    p = Page(f"{name}.md", title=front["title"], edit_url=edit_url(f"content/{name}.md"), **preview(name))
    p.add(new_tab_markdown(_local_images(m.group(2).strip())), extra)
    p.write()


MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)(\{[^}]*\})?")


def _local_images(markdown_text: str) -> str:
    """Markdown images of files under docs/ -> resized, lazy <img> with width,
    height and srcset (like every generated page); external images unchanged."""
    def repl(m: re.Match) -> str:
        alt, path, attrs = m.group(1), m.group(2), m.group(3)
        if is_external(path):
            return m.group(0)
        if attrs:   # would be lost: the <img> is generated (always lazy, with its size)
            fail(f"content/: image {path} has attributes {attrs}; remove them (images are resized and lazy-loaded)")
        return media(path, alt, 900, sizes="(max-width: 900px) 100vw, 900px")
    return MD_IMAGE.sub(repl, markdown_text)
