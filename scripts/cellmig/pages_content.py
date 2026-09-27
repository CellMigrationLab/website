"""Pages built mostly from the website's own files: Research, Software, Datasets,
Gallery, Online talks, and the hand-written pages in content/."""

import re
from datetime import date

import yaml

from .components import section_title, tile
from .config import (
    CONTENT,
    DATA,
    DATASET_TYPES,
    OTHER_DATA,
    UNCAPTIONED_ALT,
    edit_url,
    fail,
    load,
)
from .images import lite_video, media, thumb
from .ledger import Ledger, Record, software_list
from .page import Page
from .previews import preview
from .profile import talks_section, teaching_section
from .structured import dataset_item, item_list, software_item, to_json
from .text import esc, is_external, md, slugify, year_of

BROWSE_PUBLICATIONS = '<a class="cm-button" href="publications/">Browse all our publications</a>'


def _theme(t: Record, ledger: Ledger) -> str:
    """Text of one research theme: title, lead, paragraphs, selected papers, credit."""
    body = [f'<h2 id="{slugify(t["title"])}">{esc(t["title"])}</h2>']
    if t.get("lead"):
        body.append(f'<p class="cm-tile__lead">{md(t["lead"], inline=True)}</p>')
    body += [md(x) for x in t.get("text") or []]
    papers = [ledger.published_version(ledger.require(d, f"data/research.yaml ({t['title']})"))
              for d in t.get("papers") or []]
    if papers:
        body.append('<p class="cm-tile__label">Selected papers</p><ul class="cm-tile__papers">')
        body += [f'<li><a href="https://doi.org/{esc(r["doi"])}">{esc(r["title"])}</a>'
                 f' <span>{esc(r.get("venue") or "")}, {r["year"]}</span></li>' for r in papers]
        body.append("</ul>")
    if t.get("credit"):
        body.append(f'<p class="cm-tile__credit">{esc(t["credit"])}</p>')
    return "\n".join(body)


def page_research(ledger: Ledger) -> None:
    """docs/research.md from data/research.yaml: videos, then one tile per theme."""
    research = load(DATA / "research.yaml")
    p = Page("research.md", title="Research", edit_url=edit_url("data/research.yaml"), **preview("research"))
    p.add("# Research", '<p class="cm-lead">Our research interests</p>', '<div class="cm-videos">')
    p.add(*(f'<figure>{lite_video(v.get("youtube"), v.get("vimeo"), v["title"], v.get("start"))}'
            f'<figcaption>{esc(v["title"])}</figcaption></figure>' for v in research.get("videos") or []))
    p.add("</div>", '<div class="cm-wide">')
    for i, t in enumerate(research["themes"]):
        p.add(tile(t["color"], media(t.get("image"), t.get("credit", ""), 1000), _theme(t, ledger), media_right=i % 2 == 1))
    p.add("</div>", f'<p class="cm-cta">{BROWSE_PUBLICATIONS}</p>')
    p.write()


def _software_body(s: Record) -> str:
    """Text of one software tile: title (year), description, links."""
    title = f'{s["title"]} ({s["year"]})' if s.get("year") else s["title"]
    text = md(s.get("text") or "").replace("<p>", '<p class="cm-dropcap">', 1)
    links = []
    paper = s.get("paper") or (f'https://doi.org/{s["dois"][0]}' if s["dois"] else None)
    if paper:
        links.append(f'<a href="{esc(paper)}">Read our paper</a>')
    if s.get("github"):
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
    p.add("# Software", '<p class="cm-lead">Here are the software we have developed or contributed to. '
          'Looking for data? See <a href="datasets/">our datasets, models and materials</a>.</p>', '<div class="cm-wide">')
    for i, s in enumerate(projects):
        pic = media(s.get("video") or s.get("image"), f'{s["title"]} logo' if s.get("image") else "", 900)
        p.add(tile(s.get("color", "light"), pic, _software_body(s), media_right=i % 2 == 0))
    p.add("</div>", f'<p class="cm-cta">{BROWSE_PUBLICATIONS} '
          '<a class="cm-button cm-button--ghost" href="https://github.com/CellMigrationLab">CellMigrationLab on GitHub</a></p>')
    p.write()


def _dataset(d: Record, ledger: Ledger) -> str:
    """One dataset: title, tags, description, year, archive DOI and papers."""
    refs = []
    for doi in d.get("related_publication_dois") or []:
        rec = ledger.get(doi)
        label = f'{rec.get("venue")}, {rec["year"]}' if rec else f"doi:{doi}"   # paper not in the ledger
        refs.append(f'<a href="https://doi.org/{esc(doi)}">{esc(label)}</a>')
    tags = "".join(f'<span class="cm-badge">{esc(t)}</span>' for t in d.get("dataset_tags") or [] if t in ("model-zoo", "dl-ready"))
    archive = d.get("archive_doi")
    archive_html = (f' · <a href="https://doi.org/{esc(archive)}">doi:{esc(archive)}</a>'
                    if archive and archive not in d["repository_url"] else "")
    return (f'<li><a class="cm-datasets__title" href="{esc(d["repository_url"])}">{esc(d["title"])}</a>{tags}'
            f'<p>{esc(d.get("description") or "")}</p>'
            f'<p class="cm-small">{year_of(d.get("start_date")) or ""}{archive_html}'
            f'{" · Paper: " + ", ".join(refs) if refs else ""}</p></li>')


def page_datasets(ledger: Ledger, site: Record) -> None:
    """docs/datasets.md: shared resources (data/site.yaml), then datasets by type."""
    p = Page("datasets.md", title="Datasets", **preview("datasets"))
    p.meta["jsonld"] = to_json(item_list("Datasets shared by the Cell Migration Lab",
                                         [dataset_item(d) for d in ledger.datasets]))
    p.add("# Datasets",
          '<p class="cm-lead">We share our data. Here are the datasets, models and materials that accompany our papers. '
          'The tools we build are on <a href="software/">Software</a>.</p>')
    p.add('<ul class="cm-resources">', *(
        f'<li><a href="{esc(r["url"])}"><strong>{esc(r["title"])}</strong><span>{esc(r.get("text", ""))}</span></a></li>'
        for r in site["resources"]), "</ul>")
    groups: dict[str, list[Record]] = {}
    for d in ledger.datasets:
        groups.setdefault(DATASET_TYPES.get(str(d.get("dataset_type") or "").lower(), OTHER_DATA), []).append(d)
    order = [g for g in [*dict.fromkeys(DATASET_TYPES.values()), OTHER_DATA] if g in groups]
    p.add('<nav class="cm-toc-inline">' + " · ".join(
        f'<a href="#{slugify(g)}">{esc(g)} ({len(groups[g])})</a>' for g in order) + "</nav>")
    for g in order:
        p.add(f'<h2 id="{slugify(g)}">{esc(g)}</h2>', '<ul class="cm-datasets">',
              *(_dataset(d, ledger) for d in groups[g]), "</ul>")
    p.add('<p class="cm-small cm-source">Generated from our <em>things_done</em> activity ledger; updates automatically.</p>')
    p.write()


def page_gallery() -> None:
    """docs/gallery.md from data/gallery.yaml: journal covers and images (lightbox)."""
    gallery = load(DATA / "gallery.yaml")
    p = Page("gallery.md", title="Gallery", edit_url=edit_url("data/gallery.yaml"), **preview("gallery"))
    p.add("# Gallery", section_title("Journal covers"), '<ul class="cm-covers">')
    for c in gallery["covers"]:
        cap = esc(c.get("caption", ""))
        p.add(f'<li><a href="{thumb(c["image"], 1600)}" data-cm-lightbox data-caption="{cap}">'
              f'{media(c["image"], c.get("caption", ""), 500)}</a><span>{cap}</span></li>')
    p.add("</ul>", section_title("Images"), '<ul class="cm-gallery">')
    for g in gallery["images"]:
        p.add(f'<li><a href="{thumb(g["image"], 2000)}" data-cm-lightbox data-caption="{esc(g.get("caption", ""))}">'
              f'{media(g["image"], g.get("caption") or UNCAPTIONED_ALT, 600)}</a></li>')
    p.add("</ul>")
    p.write()


def page_talks(ledger: Ledger, today: date) -> None:
    """docs/online-lectures.md: recorded talks (data/talks.yaml), then recent
    talks and this year's teaching from things_done."""
    p = Page("online-lectures.md", title="Online talks", edit_url=edit_url("data/talks.yaml"),
             **preview("online-lectures"))
    p.add("# Online talks", '<div class="cm-talks">')
    for t in load(DATA / "talks.yaml"):
        meta = " · ".join(str(x) for x in (t.get("event"), t.get("year")) if x)
        p.add(f'<figure class="cm-talk">{lite_video(t.get("youtube"), t.get("vimeo"), t["title"], t.get("start"))}'
              f'<figcaption><strong>{esc(t["title"])}</strong><span>{esc(meta)}</span></figcaption></figure>')
    p.add("</div>", talks_section(ledger, today), teaching_section(ledger, today))
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
    p.add(_local_images(m.group(2).strip()), extra)
    p.write()


MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)(\{[^}]*\})?")


def _local_images(markdown_text: str) -> str:
    """Markdown images of files under docs/ -> resized, lazy <img> with width,
    height and srcset (like every generated page); external images unchanged."""
    def repl(m: re.Match) -> str:
        alt, path = m.group(1), m.group(2)
        if is_external(path):
            return m.group(0)
        return media(path, alt, 900, sizes="(max-width: 900px) 100vw, 900px")
    return MD_IMAGE.sub(repl, markdown_text)
