"""Generate the website pages from the files in data/.

    python scripts/build_pages.py     (then: zensical build / zensical serve)

Reads                                   Writes (git-ignored, rebuilt every time)
  data/site.yaml                          docs/index.md             home page
  data/research.yaml                      docs/research.md
  data/members/*.yaml, data/photos/       docs/lab-members.md
  data/software.yaml  + ledger            docs/software.md
  data/featured.yaml + ledger             featured papers on the home page, docs/portfolio/<slug>.md
  data/things_done/publications.yaml      docs/publications.md
  data/things_done/datasets.yaml          docs/datasets.md
  data/gallery.yaml                       docs/gallery.md
  data/talks.yaml                         docs/online-lectures.md
                                          docs/feed.xml, docs/feed/index.html (RSS)
                                          docs/assets/thumbs/  (resized images)

The data in data/things_done/ comes from the things_done ledger and is
updated automatically (scripts/sync_things_done.py); edit the ledger, not
those files. Page addresses match the old WordPress site, so existing links
keep working.
"""

import html
import re
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
THUMBS = "assets/thumbs"
REPO = "https://github.com/CellMigrationLab/website"
SITE_URL = "https://cellmig.org/"

GENERATED = [
    "index.md", "research.md", "lab-members.md", "software.md", "lab-in-numbers.md", "collaborators.md", "featured-research.md",
    "publications.md", "datasets.md", "gallery.md", "online-lectures.md",
    "portfolio", "feed.xml", "feed", THUMBS,
]

COLORS = {"purple", "orange", "blue", "black", "white", "sky", "grey", "mint", "red",
          "green", "amber", "pink", "light"}

ICONS = {
    "bluesky": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.2 3.6C7.9 5.6 10.8 9.7 12 12c1.2-2.3 4.1-6.4 6.8-8.4 1.9-1.4 5.1-2.6 5.1 1 0 .7-.4 6.1-.7 7-.9 3.1-4.1 3.9-6.9 3.4 4.9.8 6.1 3.6 3.4 6.4-5.1 5.2-7.3-1.3-7.9-3-.1-.3-.1-.5-.2-.3 0-.2-.1 0-.2.3-.6 1.7-2.8 8.2-7.9 3-2.7-2.8-1.5-5.6 3.4-6.4-2.8.5-6-.3-6.9-3.4C.5 11.5.1 6 .1 5.4c0-3.6 3.2-2.4 5.1-1.8z"/></svg>',
    "github": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0C17.3 4.3 18.3 4.6 18.3 4.6c.6 1.6.2 2.8.1 3.1.8.8 1.2 1.9 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5z"/></svg>',
    "scholar": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 1 9l4 2.6V17c0 2 3.1 4 7 4s7-2 7-4v-5.4L21 10.3V16h2V9L12 2zm0 16.5c-2.8 0-5-1.3-5-2v-3.6l5 3.2 5-3.2v3.6c0 .7-2.2 2-5 2z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm1 2.4V17h16V7.4l-8 5.3-8-5.3zM5.6 7l6.4 4.3L18.4 7H5.6z"/></svg>',
    "orcid": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1a11 11 0 1 0 0 22 11 11 0 0 0 0-22zM8.3 17.3H6.6V9.1h1.7v8.2zM7.4 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3 1.1h3.1c3 0 4.3 2.1 4.3 4.1 0 2.2-1.7 4.1-4.3 4.1h-3.1V9.1zm1.7 1.5v5.2h1.3c1.9 0 2.7-1.2 2.7-2.6 0-1.3-.8-2.6-2.6-2.6h-1.4z"/></svg>',
    "web": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm6.9 6h-3a15.7 15.7 0 0 0-1.4-3.6A8 8 0 0 1 18.9 8zM12 4c.8 1.2 1.5 2.5 1.9 4h-3.8c.4-1.5 1.1-2.8 1.9-4zM4.3 14a8.2 8.2 0 0 1 0-4h3.4a16.5 16.5 0 0 0 0 4H4.3zm.8 2h3a15.7 15.7 0 0 0 1.4 3.6A8 8 0 0 1 5.1 16zm3-8h-3a8 8 0 0 1 4.4-3.6C8 5.6 7.6 6.8 8.1 8zM12 20c-.8-1.2-1.5-2.5-1.9-4h3.8c-.4 1.5-1.1 2.8-1.9 4zm2.3-6H9.7a14.7 14.7 0 0 1 0-4h4.6a14.7 14.7 0 0 1 0 4zm.3 5.6c.6-1.1 1.1-2.3 1.4-3.6h3a8 8 0 0 1-4.4 3.6zm1.7-5.6a16.5 16.5 0 0 0 0-4h3.4a8.2 8.2 0 0 1 0 4h-3.4z"/></svg>',
}

GROUPS = [
    ("pi", "Group leader"),
    ("staff", "Researchers"),
    ("postdoc", "Postdoctoral researchers"),
    ("phd", "PhD students"),
    ("student", "Students"),
    ("other", "Team"),
]

DATASET_TYPES = [
    ("image", "Image data"),
    ("video", "Image data"),
    ("proteomic", "Proteomic data"),
    ("rna_seq", "Sequencing data"),
    ("sequencing", "Sequencing data"),
    ("model", "Deep learning models"),
]


# --------------------------------------------------------------------------- helpers

def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


MD = markdown.Markdown(extensions=["smarty"])


def md(text, inline=False):
    """Markdown -> HTML. Links like `software/` are site-relative (fixed later by rel())."""
    MD.reset()
    out = MD.convert(str(text or "").strip())
    if inline:
        out = re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)
    return out


def slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def year_of(value):
    m = re.match(r"\d{4}", str(value or ""))
    return int(m.group(0)) if m else None


def is_external(url):
    return bool(re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", str(url), flags=re.I))


class Page:
    """One generated Markdown page. `u()` turns a site path into a relative URL."""

    def __init__(self, path, **meta):
        self.path = path                      # e.g. "portfolio/cdm.md"
        self.meta = {k: v for k, v in meta.items() if v not in (None, "", [])}
        self.parts = []
        # Zensical rewrites href/src in raw HTML as paths relative to the
        # Markdown file; other attributes (srcset, poster) are used as they are, so they
        # must be relative to the page's final URL (directory URLs: one level deeper).
        self.depth_file = path.count("/")
        stem = path[:-3]
        self.depth_url = self.depth_file + (0 if stem == "index" or stem.endswith("/index") else 1)

    def u(self, target, final_url=False):
        target = str(target or "")
        if not target or is_external(target):
            return target
        depth = self.depth_url if final_url else self.depth_file
        return "../" * depth + target.lstrip("/") if depth else (target.lstrip("/") or "./")

    def add(self, *chunks):
        self.parts.extend(chunks)

    def fix_links(self, text):
        """Make href/src values written as site paths ("software/") relative to this page."""
        def repl(m):
            attr, url = m.group(1), m.group(2)
            if is_external(url) or url.startswith(("../", "./")):
                return m.group(0)
            return f'{attr}="{self.u(url, final_url=attr in ("poster", "data-full"))}"'
        def repl_srcset(m):
            items = []
            for part in m.group(1).split(","):
                url, _, size = part.strip().partition(" ")
                items.append(f"{url if is_external(url) else self.u(url, final_url=True)} {size}".strip())
            return f'srcset="{", ".join(items)}"'
        text = re.sub(r'\bsrcset="([^"]*)"', repl_srcset, text)
        return re.sub(r'\b(href|src|poster|data-full)="([^"]*)"', repl, text)

    def write(self):
        out = DOCS / self.path
        out.parent.mkdir(parents=True, exist_ok=True)
        front = yaml.safe_dump(self.meta, allow_unicode=True, sort_keys=False, width=1000).strip()
        body = self.fix_links("\n".join(self.parts))
        out.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")


def edit_url(path):
    return f"{REPO}/edit/main/{path}"


# --------------------------------------------------------------------------- images

_sizes = {}


def image_size(site_path):
    if site_path not in _sizes:
        try:
            with Image.open(DOCS / site_path) as im:
                _sizes[site_path] = ImageOps.exif_transpose(im).size
        except Exception:
            _sizes[site_path] = None
    return _sizes[site_path]


def thumb(site_path, width):
    """Resized WebP copy of an image (made once, kept between builds)."""
    src = DOCS / site_path
    if not src.is_file():
        raise SystemExit(f"Missing image: docs/{site_path}")
    if src.suffix.lower() in (".svg", ".gif"):
        return site_path
    size = image_size(site_path)
    if size and size[0] <= width and src.stat().st_size < 150_000:
        return site_path
    rel = Path(site_path)
    out_rel = f"{THUMBS}/{width}/{rel.with_suffix('.webp').as_posix()}"
    out = DOCS / out_rel
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "transparency" in im.info or im.mode in ("LA", "P") else "RGB")
            im.thumbnail((width, width * 4), Image.LANCZOS)
            im.save(out, "WEBP", quality=82, method=4)
    return out_rel


def square_thumb(site_path, size=480, position="top"):
    """Square crop for member photos."""
    src = DOCS / site_path
    if not src.is_file():
        raise SystemExit(f"Missing image: docs/{site_path}")
    out_rel = f"{THUMBS}/square/{Path(site_path).with_suffix('.webp').as_posix()}"
    out = DOCS / out_rel
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            centering = (0.5, 0.5) if position == "center" else (0.5, 0.25)
            im = ImageOps.fit(im, (size, size), Image.LANCZOS, centering=centering)
            im.save(out, "WEBP", quality=84, method=4)
    return out_rel


def gif_video(site_path):
    """A GIF from WordPress has an MP4 twin in docs/assets/media/gif/ (much smaller)."""
    if not site_path.lower().endswith(".gif"):
        return None
    rel = site_path.split("wp-content/uploads/", 1)[-1]
    mp4 = f"assets/media/gif/{rel[:-4]}.mp4"
    if (DOCS / mp4).is_file():
        poster = mp4[:-4] + ".jpg"
        return mp4, poster if (DOCS / poster).is_file() else None
    return None


def media(site_path, alt="", width=900, cls="", eager=False, sizes=None):
    """<img>, or a silent looping <video> for GIFs, with lazy loading and sizes."""
    if not site_path:
        return ""
    if site_path.lower().endswith(".mp4"):
        poster = site_path[:-4] + ".jpg"
        p = f' poster="{poster}"' if (DOCS / poster).is_file() else ""
        return (f'<video class="{cls}" controls preload="none" playsinline{p}>'
                f'<source src="{site_path}" type="video/mp4"></video>')
    twin = gif_video(site_path)
    if twin:
        mp4, poster = twin
        p = f' poster="{poster}"' if poster else ""
        label = f' aria-label="{esc(alt)}"' if alt else ""
        return (f'<video class="{cls} cm-loop" autoplay muted loop playsinline preload="metadata"{p}{label}>'
                f'<source src="{mp4}" type="video/mp4"></video>')
    src = thumb(site_path, width)
    size = image_size(src) or image_size(site_path)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    srcset = ""
    if width >= 900:
        small = thumb(site_path, width // 2)
        if small != src:
            srcset = f' srcset="{small} {width // 2}w, {src} {width}w" sizes="{sizes or "(max-width: 700px) 100vw, 50vw"}"'
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return f'<img class="{cls}" src="{src}"{srcset}{dims} alt="{esc(alt)}" {loading}>'


def lite_video(youtube=None, vimeo=None, title="", start=None):
    """Video placeholder: nothing is loaded from YouTube/Vimeo until the visitor clicks."""
    if youtube:
        embed = f"https://www.youtube-nocookie.com/embed/{youtube}?autoplay=1&rel=0" + (f"&start={start}" if start else "")
        thumb_url = f"https://i.ytimg.com/vi/{youtube}/hqdefault.jpg"
        link = f"https://www.youtube.com/watch?v={youtube}" + (f"&t={start}s" if start else "")
    else:
        embed = f"https://player.vimeo.com/video/{vimeo}?autoplay=1&dnt=1"
        thumb_url = f"https://vumbnail.com/{vimeo}.jpg"
        link = f"https://vimeo.com/{vimeo}"
    return (f'<div class="cm-video" data-embed="{esc(embed)}" style="--thumb: url(\'{thumb_url}\')">'
            f'<a class="cm-video__play" href="{esc(link)}" aria-label="Play video: {esc(title)}">'
            f'<span class="cm-video__icon" aria-hidden="true"></span></a></div>')


# --------------------------------------------------------------------------- ledger data

class Ledger:
    def __init__(self):
        td = DATA / "things_done"
        self.pubs = load(td / "publications.yaml").get("records") or []
        self.software = load(td / "software.yaml").get("records") or []
        self.datasets = load(td / "datasets.yaml").get("records") or []
        self.by_doi = {p["doi"].lower(): p for p in self.pubs}
        lag = td / "preprint_lag.yaml"
        self.lag = (load(lag).get("pairs") or []) if lag.exists() else []
        co = td / "coauthors.yaml"
        self.coauthors = (load(co).get("coauthors") or []) if co.exists() else []
        mt = td / "metrics.yaml"
        self.metrics = load(mt) if mt.exists() else {}
        # journal publication dates (from the ledger's lag report) to order papers within a year
        self.dates = {}
        for p in self.lag:
            if p.get("published_date_precision") == "day":
                self.dates[str(p["published_doi"]).lower()] = p["published_date"]

    def get(self, doi):
        return self.by_doi.get(str(doi).lower())

    def published_version(self, rec):
        """For a preprint, the journal version (when the ledger links them)."""
        if rec.get("status") == "published":
            return rec
        for d in rec.get("related_dois") or []:
            other = self.get(d)
            if other and other.get("status") in ("published", "in_press"):
                return other
        return rec

    def preprint_of(self, rec):
        for d in rec.get("related_dois") or []:
            other = self.get(d)
            if other and other.get("status") == "preprint":
                return other
        return None

    def grouped(self):
        """Publications with each preprint folded into its journal version."""
        hidden, out = set(), []
        for rec in self.pubs:
            if rec.get("status") == "preprint" and self.published_version(rec) is not rec:
                hidden.add(rec["doi"].lower())
        for rec in self.pubs:
            if rec["doi"].lower() not in hidden:
                out.append(rec)
        return out


def lab_names():
    names = set()
    for f in (DATA / "members").glob("*.y*ml"):
        m = load(f)
        for n in [m.get("name")] + list(m.get("also_known_as") or []):
            if n:
                names.add(normalize_name(n))
    return names


def normalize_name(name):
    return slugify(name).replace("-", "")


def author_list(authors, lab, limit=12):
    out = []
    for a in authors:
        name = esc(a)
        if normalize_name(a) in lab:
            name = f'<span class="cm-author--lab">{name}</span>'
        out.append(name)
    if len(out) > limit:
        hidden = len(out) - limit + 1
        return ", ".join(out[: limit - 1]) + f', <span class="cm-more">… +{hidden} more</span>, ' + out[-1]
    return ", ".join(out)


def badges(rec):
    out = []
    status = rec.get("status")
    if status == "preprint":
        out.append('<span class="cm-badge cm-badge--preprint">Preprint</span>')
    elif status == "in_press":
        out.append('<span class="cm-badge">In press</span>')
    oa = rec.get("open_access_status")
    if oa and oa != "closed":
        out.append('<span class="cm-badge cm-badge--oa" title="Open access">Open access</span>')
    return "".join(out)


def citation(rec, lab, ledger, featured_url=None, abstract=False, heading="h3"):
    doi = rec["doi"]
    pre = ledger.preprint_of(rec)
    extra = []
    if pre:
        extra.append(f'<a href="https://doi.org/{esc(pre["doi"])}">Preprint</a>')
    if featured_url:
        extra.append(f'<a href="{featured_url}">Read more</a>')
    parts = [
        f'<{heading} class="cm-pub__title"><a href="https://doi.org/{esc(doi)}">{esc(rec["title"])}</a></{heading}>',
        f'<p class="cm-pub__authors">{author_list(rec.get("authors") or [], lab)}</p>',
        f'<p class="cm-pub__venue"><em>{esc(rec.get("venue") or "")}</em>'
        f'{" · " + str(rec["year"]) if rec.get("year") else ""}'
        f' · <a class="cm-doi" href="https://doi.org/{esc(doi)}">doi:{esc(doi)}</a> {badges(rec)}</p>',
    ]
    if extra:
        parts.append(f'<p class="cm-pub__links">{" · ".join(extra)}</p>')
    if abstract and rec.get("abstract"):
        parts.append(f'<details class="cm-pub__abstract"><summary>Abstract</summary><p>{esc(rec["abstract"])}</p></details>')
    return "\n".join(parts)


# --------------------------------------------------------------------------- content

def load_members():
    members = []
    for f in sorted((DATA / "members").glob("*.y*ml")):
        m = load(f)
        m["_file"] = f"data/members/{f.name}"
        m["slug"] = m.get("slug") or f.stem
        if not m.get("photo"):
            for ext in ("jpg", "jpeg", "png", "webp"):
                p = DATA / "photos" / f"{m['slug']}.{ext}"
                if p.is_file():
                    dest = DOCS / "assets" / "images" / "members" / p.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists() or dest.stat().st_mtime < p.stat().st_mtime:
                        shutil.copy2(p, dest)
                    m["photo"] = f"assets/images/members/{p.name}"
                    break
        members.append(m)
    return members


def load_featured(ledger):
    """Featured research = every paper on which Guillaume is (co-)corresponding
    author (ledger `me.corresponding_author`, on the paper or its preprint).
    data/featured.yaml only adds pictures and page addresses; `show: true` adds a
    paper that is not corresponding-author, `hide: true` removes one.

    Returns (featured, extra): `extra` are papers listed in data/featured.yaml that
    are not featured; they keep their page so old addresses keep working."""
    entries = load(DATA / "featured.yaml") or []
    by_family = {}
    for e in entries:
        rec = ledger.get(e["doi"])
        if not rec:
            raise SystemExit(f"data/featured.yaml: DOI {e['doi']} is not in the things_done ledger")
        by_family[ledger.published_version(rec)["doi"].lower()] = e

    def family(rec):
        return [rec] + [ledger.get(d) for d in rec.get("related_dois") or [] if ledger.get(d)]

    def make(main, entry, pos):
        entry = entry or {}
        pubs = [main] + [ledger.published_version(ledger.get(d)) for d in entry.get("also") or [] if ledger.get(d)]
        return {
            "papers": [main["doi"]] + list(entry.get("also") or []),
            "_pubs": pubs,
            "image": entry.get("image"),
            "title": main["title"],
            "slug": entry.get("slug") or slugify(main["title"])[:90],
            "year": int(main.get("year") or 0),
            "date": ledger.dates.get(main["doi"].lower())
                    or next((ledger.dates[r["doi"].lower()] for r in family(main) if r["doi"].lower() in ledger.dates), None)
                    or f"{main.get('year') or 0}-06-30",
            "summary": "\n\n".join(p["abstract"] for p in pubs if p.get("abstract")),
            "_pos": pos,
        }

    featured, extra, used = [], [], set()
    for pos, main in enumerate(ledger.grouped()):
        key = main["doi"].lower()
        entry = by_family.get(key)
        corresponding = any(r.get("corresponding") for r in family(main))
        if entry and entry.get("hide"):
            corresponding = False
        if corresponding or (entry and entry.get("show")):
            featured.append(make(main, entry, pos))
            used.add(key)
    for pos, (key, entry) in enumerate(by_family.items()):
        if key not in used:
            extra.append(make(ledger.get(key), entry, 1000 + pos))
    featured.sort(key=lambda i: (i["date"], -i["_pos"]), reverse=True)
    return featured, extra


def featured_by_doi(featured, ledger):
    """DOI (journal and preprint) -> featured page, to link publications to their story."""
    out = {}
    for item in featured:
        for d in item.get("papers") or []:
            rec = ledger.get(d)
            out[d.lower()] = item
            for r in [ledger.published_version(rec)] + [ledger.get(x) for x in rec.get("related_dois") or []]:
                if r:
                    out.setdefault(r["doi"].lower(), item)
    return out


def section_title(text, level=2, id_=None):
    i = f' id="{id_}"' if id_ else ""
    return f'<h{level} class="cm-section-title"{i}><span>{esc(text)}</span></h{level}>'


# --------------------------------------------------------------------------- pages

def page_home(site, featured, ledger, lab):
    p = Page("index.md", template="home.html", title="Home",
             description=site["intro"], image=site["hero"]["image"])
    hero = site["hero"]
    p.add(
        '<section class="cm-hero">',
        '<div class="cm-hero__text">',
        f'<h1 class="cm-hero__title">{esc(site["tagline"])}</h1>',
        f'<p class="cm-hero__welcome">{esc(site["welcome"])}</p>',
        "</div>",
        f'<figure class="cm-hero__image">{media(hero["image"], hero.get("caption", ""), 2400, eager=True, sizes="100vw")}</figure>',
        "</section>",
        f'<p class="cm-intro">{esc(site["intro"])}</p>',
    )
    p.add(section_title("Featured research", id_="featured"), '<div class="cm-cards cm-cards--home">')
    for item in featured[:HOME_FEATURED]:
        p.add(feature_card(item))
    p.add("</div>", f'<p class="cm-more-link"><a href="featured-research/">All featured research ({len(featured)})</a></p>')

    bands = site.get("bands") or []

    def band(i):
        if i < len(bands):
            b = bands[i]
            cap = f'<figcaption>{esc(b["caption"])}</figcaption>' if b.get("caption") else ""
            p.add(f'<figure class="cm-band">{media(b["image"], b.get("caption", ""), 2400, sizes="100vw")}{cap}</figure>')

    band(0)
    latest = ledger.grouped()[:5]
    fmap = featured_by_doi(featured, ledger)
    p.add(section_title("Latest papers"), '<ol class="cm-pubs cm-pubs--compact">')
    for rec in latest:
        item = fmap.get(rec["doi"].lower())
        link = f"portfolio/{item['slug']}/" if item else None
        p.add(f'<li class="cm-pub">{citation(rec, lab, ledger, link, heading="h3")}</li>')
    p.add("</ol>", '<p class="cm-more-link"><a href="publications/">All publications</a></p>')

    band(1)
    p.add(section_title("Funding"), logo_row(site["funding"]))
    p.write()


HOME_FEATURED = 8


def feature_card(item, summary=False):
    pub = item["_pubs"][0]
    pic = (media(item["image"], "", 700) if item.get("image")
           else f'<span class="cm-card__placeholder">{esc(pub.get("venue") or "")}</span>')
    text = ""
    if summary:
        t = re.sub(r"\s+", " ", item.get("summary") or "").strip()
        text = f'<p class="cm-card__text">{esc(t[:200].rsplit(" ", 1)[0] + "…" if len(t) > 200 else t)}</p>'
    return (f'<a class="cm-card" href="portfolio/{item["slug"]}/">'
            f'<div class="cm-card__media">{pic}</div>'
            f'<p class="cm-card__title">{esc(item["title"])}</p>'
            f'<p class="cm-card__meta">{esc(pub.get("venue") or "")} · {pub.get("year")} {badges(pub)}</p>{text}</a>')


def logo_row(items):
    out = ['<ul class="cm-logos">']
    for it in items:
        src = thumb(it["logo"], 400)
        out.append(f'<li><a href="{esc(it["url"])}" title="{esc(it["name"])}">'
                   f'<img src="{src}" alt="{esc(it["name"])}" loading="lazy"></a></li>')
    out.append("</ul>")
    return "\n".join(out)


def tile(color, media_html, body_html, media_right=False, extra_cls=""):
    color = color if color in COLORS else "light"
    side = " cm-tile--right" if media_right else ""
    media_part = f'<div class="cm-tile__media">{media_html}</div>' if media_html else ""
    nomedia = "" if media_html else " cm-tile--text"
    return (f'<section class="cm-tile cm-tile--{color}{side}{nomedia} {extra_cls}">'
            f'{media_part}<div class="cm-tile__body">{body_html}</div></section>')


def page_research(research, ledger, lab):
    p = Page("research.md", title="Research", edit_url=edit_url("data/research.yaml"),
             description="Our research interests: cancer metastasis, cell migration, the vasculature, filopodia and image analysis.",
             image=research["themes"][0]["image"])
    p.add("# Research", '<p class="cm-lead">Our research interests</p>')
    p.add('<div class="cm-videos">')
    for v in research.get("videos") or []:
        p.add(f'<figure>{lite_video(v.get("youtube"), v.get("vimeo"), v["title"], v.get("start"))}'
              f'<figcaption>{esc(v["title"])}</figcaption></figure>')
    p.add("</div>", '<div class="cm-wide">')
    for i, t in enumerate(research["themes"]):
        body = [f'<h2 id="{slugify(t["title"])}">{esc(t["title"])}</h2>']
        if t.get("lead"):
            body.append(f'<p class="cm-tile__lead">{md(t["lead"], inline=True)}</p>')
        body += [md(x) for x in t.get("text") or []]
        pubs = [ledger.get(d) for d in t.get("papers") or []]
        missing = [d for d, r in zip(t.get("papers") or [], pubs) if not r]
        if missing:
            raise SystemExit(f"data/research.yaml: DOIs not in the ledger: {missing}")
        if pubs:
            body.append('<p class="cm-tile__label">Selected papers</p><ul class="cm-tile__papers">')
            for r in pubs:
                r = ledger.published_version(r)
                body.append(f'<li><a href="https://doi.org/{esc(r["doi"])}">{esc(r["title"])}</a>'
                            f' <span>{esc(r.get("venue") or "")}, {r.get("year")}</span></li>')
            body.append("</ul>")
        if t.get("credit"):
            body.append(f'<p class="cm-tile__credit">{esc(t["credit"])}</p>')
        p.add(tile(t.get("color"), media(t.get("image"), t.get("credit", ""), 1000), "\n".join(body), media_right=i % 2 == 1))
    p.add("</div>", '<p class="cm-cta"><a class="cm-button" href="publications/">Browse all our publications</a></p>')
    p.write()


def page_members(members):
    current = [m for m in members if m.get("status", "current") == "current"]
    alumni = [m for m in members if m.get("status") == "alumni"]
    order = {g: i for i, (g, _) in enumerate(GROUPS)}
    current.sort(key=lambda m: (order.get(m.get("group", "other"), 99), m.get("order", 999), m["name"]))
    alumni.sort(key=lambda m: (m.get("order", 999), m["name"]))

    p = Page("lab-members.md", title="Lab members", edit_url=f"{REPO}/tree/main/data/members",
             description="Meet the people of the Cell Migration Lab in Turku, Finland.")
    # Everyone together in one grid (group leader first, then by position)
    p.add("# Lab members", '<ul class="cm-people">')
    for m in current:
        p.add(person_card(m))
    p.add("</ul>")

    team = load(DATA / "team.yaml") if (DATA / "team.yaml").is_file() else {}
    if team:
        p.add(section_title("Meet our team"), '<div class="cm-team">')
        for ph in team.get("photos") or []:
            cap = f'<figcaption>{esc(ph["caption"])}</figcaption>' if ph.get("caption") else ""
            p.add(f'<figure>{media(ph["image"], ph.get("caption") or "The Cell Migration Lab team", 1400)}{cap}</figure>')
        for v in team.get("videos") or []:
            p.add(f'<figure>{lite_video(v.get("youtube"), v.get("vimeo"), v["title"])}<figcaption>{esc(v["title"])}</figcaption></figure>')
        p.add("</div>")

    if alumni:
        p.add(section_title("Alumni"), '<ul class="cm-alumni">')
        for m in alumni:
            years = f' <span class="cm-alumni__years">{esc(m["years"])}</span>' if m.get("years") else ""
            now = f' <span class="cm-alumni__now">now {md(m["now"], inline=True)}</span>' if m.get("now") else ""
            p.add(f'<li><strong>{esc(m["name"])}</strong> <span>{esc(m.get("role", ""))}</span>{years}{now}</li>')
        p.add("</ul>")

    form = f"{REPO}/issues/new?template=lab-member.yml"
    p.add('<aside class="cm-join">',
          '<h2>Join us</h2>',
          '<p>Motivated students and researchers are always welcome to '
          '<a href="mailto:guillaume.jacquemet@abo.fi">contact us</a>!</p>',
          f'<p class="cm-small">Lab member? <a href="{form}">Add yourself or update your profile</a>.</p>',
          "</aside>")
    p.write()


def person_card(m):
    photo = m.get("photo")
    if photo:
        img = square_thumb(photo, 480, m.get("photo_position", "top"))
        pic = f'<img src="{img}" alt="" width="480" height="480" loading="lazy">'
    else:
        initials = "".join(w[0] for w in m["name"].split()[:2]).upper()
        pic = f'<span class="cm-person__initials" aria-hidden="true">{esc(initials)}</span>'
    links = []
    for key, label in (("email", "mail"), ("orcid", "orcid"), ("scholar", "scholar"),
                       ("github", "github"), ("bluesky", "bluesky"), ("website", "web")):
        v = m.get(key)
        if not v:
            continue
        url = f"mailto:{v}" if key == "email" else (f"https://orcid.org/{v}" if key == "orcid" and not v.startswith("http") else v)
        links.append(f'<a href="{esc(url)}" aria-label="{esc(m["name"])} – {key}">{ICONS[label]}</a>')
    link_html = f'<span class="cm-person__links">{"".join(links)}</span>' if links else ""
    bio = f'<span class="cm-person__bio">{md(m["bio"], inline=True)}</span>' if m.get("bio") else ""
    return (f'<li class="cm-person" id="{esc(m["slug"])}"><figure>{pic}'
            f'<figcaption><span class="cm-person__name">{esc(m["name"])}</span>'
            f'<span class="cm-person__role">{esc(m.get("role", ""))}</span>{bio}{link_html}</figcaption></figure></li>')


def software_list(ledger):
    """Ledger projects (source of truth) merged with the website presentation."""
    pres = load(DATA / "software.yaml") or []
    for i, s in enumerate(pres):
        s["_pos"] = i
    by_id = {s["id"]: s for s in pres if s.get("id")}
    out = []
    for rec in ledger.software:
        s = dict(by_id.pop(rec["id"], {}))
        s.setdefault("title", rec["title"])
        s["year"] = s.get("year") or year_of(rec.get("start_date"))
        s.setdefault("github", rec.get("github_repo_url") or rec.get("repository_url"))
        s.setdefault("text", rec.get("description"))
        dois = rec.get("related_publication_dois") or []
        s.setdefault("dois", dois)
        s.setdefault("id", rec["id"])
        out.append(s)
    for s in pres:  # website-only projects
        if not s.get("id") or s["id"] in by_id:
            s = dict(s)
            s.setdefault("dois", [])
            out.append(s)
    # Newest first; within a year, the order of data/software.yaml
    out.sort(key=lambda s: (-(s.get("year") or 0), s.get("_pos", 999), s["title"].casefold()))
    return out


def page_software(ledger):
    p = Page("software.md", title="Software", edit_url=edit_url("data/software.yaml"),
             description="Open-source software for microscopy and image analysis developed or co-developed by the Cell Migration Lab.")
    p.add("# Software", '<p class="cm-lead">Here are the software we have developed or contributed to</p>', '<div class="cm-wide">')
    for i, s in enumerate(software_list(ledger)):
        title = f'{s["title"]} ({s["year"]})' if s.get("year") else s["title"]
        text = md(s.get("text") or "")
        text = text.replace("<p>", '<p class="cm-dropcap">', 1)
        links = []
        paper = s.get("paper") or (f'https://doi.org/{s["dois"][0]}' if s.get("dois") else None)
        if paper:
            links.append(f'<a href="{esc(paper)}">Read our paper</a>')
        if s.get("github"):
            host = "GitHub" if "github.com" in s["github"] else "Code"
            links.append(f'<a href="{esc(s["github"])}">Find {esc(s["title"])} on {host}</a>')
        for l in s.get("links") or []:
            links.append(f'<a href="{esc(l["url"])}">{esc(l["label"])}</a>')
        body = (f'<h2 id="{slugify(s["title"])}">{esc(title)}</h2>{text}'
                f'<p class="cm-tile__links">{" · ".join(links)}</p>')
        m = media(s.get("video") or s.get("image"), f'{s["title"]} logo' if s.get("image") else "", 900)
        p.add(tile(s.get("color", "light"), m, body, media_right=i % 2 == 0))
    p.add("</div>", '<p class="cm-cta"><a class="cm-button" href="publications/">Browse all our publications</a> '
          '<a class="cm-button cm-button--ghost" href="https://github.com/CellMigrationLab">CellMigrationLab on GitHub</a></p>')
    p.write()


def page_featured(featured, extra, ledger, lab):
    p = Page("featured-research.md", title="Featured Research", edit_url=edit_url("data/featured.yaml"),
             description="Our main papers: every paper led by the Cell Migration Lab, with its abstract.")
    p.add("# Featured Research",
          '<p class="cm-lead">Papers led by our lab, newest first. See <a href="publications/">all our publications</a>.</p>',
          '<div class="cm-cards cm-cards--grid">')
    for item in featured:
        p.add(feature_card(item))
    p.add("</div>")
    p.write()
    software = software_list(ledger)
    for i, item in enumerate(featured):
        page_story(item, featured, i, ledger, lab, software)
    for item in extra:  # old addresses, not listed
        page_story(item, [item], 0, ledger, lab, software)


def page_story(item, featured, i, ledger, lab, software):
    p = Page(f"portfolio/{item['slug']}.md", title=item["title"], edit_url=edit_url("data/featured.yaml"),
             description=re.sub(r"\s+", " ", str(item.get("summary") or ""))[:300],
             image=item.get("image") if item.get("image") and not item["image"].endswith(".gif") else None)
    p.add(f'# {esc(item["title"])}')
    if item.get("image"):
        p.add(f'<figure class="cm-story__media">{media(item["image"], item["title"], 1600, eager=True, sizes="(max-width: 900px) 100vw, 900px")}</figure>')
    for rec in item["_pubs"]:
        p.add(f'<div class="cm-story__cite cm-pub">{citation(rec, lab, ledger, heading="p")}</div>')
    for para in re.split(r"\n\s*\n|\n", str(item.get("summary") or "").strip()):
        if para.strip():
            p.add(f"<p>{esc(para.strip())}</p>")

    all_dois = set()
    for d in item.get("papers") or []:
        rec = ledger.get(d)
        all_dois.add(d.lower())
        all_dois.update(x.lower() for x in rec.get("related_dois") or [])
        all_dois.add(ledger.published_version(rec)["doi"].lower())
    main = item["_pubs"][0]
    links = [{"label": "Read the paper", "url": f"https://doi.org/{main['doi']}"}]
    pre = ledger.preprint_of(main)
    if pre:
        links.append({"label": "Preprint", "url": f"https://doi.org/{pre['doi']}"})
    if links:
        p.add('<p class="cm-story__links">' + " ".join(
            f'<a class="cm-button{" cm-button--ghost" if j else ""}" href="{esc(l["url"])}">{esc(l["label"])}</a>'
            for j, l in enumerate(links)) + "</p>")

    related_sw = [s for s in software if {d.lower() for d in s.get("dois") or []} & all_dois]
    related_ds = [d for d in ledger.datasets if {x.lower() for x in d.get("related_publication_dois") or []} & all_dois]
    if related_sw or related_ds:
        p.add('<aside class="cm-related">')
        if related_sw:
            p.add("<h2>Software</h2><ul>")
            for s in related_sw:
                p.add(f'<li><a href="software/#{slugify(s["title"])}">{esc(s["title"])}</a>'
                      + (f' · <a href="{esc(s["github"])}">code</a>' if s.get("github") else "") + "</li>")
            p.add("</ul>")
        if related_ds:
            p.add("<h2>Data</h2><ul>")
            for d in related_ds:
                p.add(f'<li><a href="{esc(d["repository_url"])}">{esc(d["title"])}</a></li>')
            p.add("</ul>")
        p.add("</aside>")

    nav = []
    if i > 0:
        nav.append(f'<a class="cm-pager__prev" href="portfolio/{featured[i - 1]["slug"]}/"><span>Newer</span>{esc(featured[i - 1]["title"])}</a>')
    if i + 1 < len(featured):
        nav.append(f'<a class="cm-pager__next" href="portfolio/{featured[i + 1]["slug"]}/"><span>Older</span>{esc(featured[i + 1]["title"])}</a>')
    p.add(f'<nav class="cm-pager" aria-label="More featured research">{"".join(nav)}</nav>')
    p.write()


def page_publications(ledger, featured, lab):
    records = ledger.grouped()
    fmap = featured_by_doi(featured, ledger)
    years = sorted({r.get("year") for r in records if r.get("year")}, reverse=True)
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
        for rec in [r for r in records if r.get("year") == y]:
            item = fmap.get(rec["doi"].lower())
            link = f"portfolio/{item['slug']}/" if item else None
            kind = "preprint" if rec.get("status") == "preprint" else "published"
            text = " ".join([rec["title"], " ".join(rec.get("authors") or []), rec.get("venue") or "", rec["doi"]]).lower()
            p.add(f'<li class="cm-pub" data-kind="{kind}" data-search="{esc(text)}">'
                  f'{citation(rec, lab, ledger, link, abstract=True)}</li>')
        p.add("</ol></section>")
    p.add('<p class="cm-small cm-source">This list is generated from our '
          '<em>things_done</em> activity ledger and updates automatically when a paper is added. '
          'Also on <a href="https://scholar.google.com/citations?user=dnBWtfsAAAAJ&hl=en">Google Scholar</a> and '
          '<a href="https://orcid.org/0000-0002-9286-920X">ORCID</a>.</p>')
    p.write()


# --------------------------------------------------------------------------- lab in numbers

def is_lab_member(name, lab):
    """Lab member, also for "Joanna W. Pylvänäinen" vs "Joanna Pylvänäinen"."""
    parts = name.split()
    return normalize_name(name) in lab or (len(parts) > 2 and normalize_name(parts[0] + parts[-1]) in lab)


def flag(code):
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper()) if code and len(code) == 2 else ""


def fmt(n):
    return f"{n:,}".replace(",", " ")  # thin space as thousands separator


def world_map(counts):
    """Choropleth of co-authors per country, rendered at build time as SVG
    (Equal Earth projection; world-atlas / Natural Earth outlines)."""
    import json
    import math
    world = json.loads((DATA / "world" / "countries-110m.json").read_text(encoding="utf-8"))
    iso = json.loads((DATA / "world" / "iso-alpha2-to-numeric.json").read_text(encoding="utf-8"))
    num_to_a2 = {v: k for k, v in iso.items()}
    sx, sy = world["transform"]["scale"]
    tx, ty = world["transform"]["translate"]
    arcs = []
    for arc in world["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    A1, A2, A3, A4, M = 1.340264, -0.081106, 0.000893, 0.003796, math.sqrt(3) / 2

    def project(lon, lat):
        lam, phi = math.radians(lon), math.radians(lat)
        th = math.asin(M * math.sin(phi))
        t2 = th * th
        t6 = t2 * t2 * t2
        x = lam * math.cos(th) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
        y = th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
        return x, y

    W, H = 960, 440
    k, cx, cy = W / (2 * 2.7064), W / 2, 250  # Antarctica left out, so shift up

    def ring(indexes):
        pts = []
        for i in indexes:
            arc = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(arc if not pts else arc[1:])
        out, prev = [], None
        for lon, lat in pts:
            x, y = project(lon, lat)
            px, py = cx + k * x, cy - k * y
            # a jump across the map = the ring crosses the antimeridian: start a new subpath
            cmd = "M" if prev is None or abs(px - prev) > W / 3 else "L"
            out.append(f"{cmd}{px:.1f},{py:.1f}")
            prev = px
        return "".join(out) + "Z"

    top = max(counts.values()) if counts else 1
    steps = [(1, 1), (2, 4), (5, 9), (10, 24), (25, 99), (100, 10 ** 9)]
    # One hue, light -> dark (sequential)
    ramp = ["#e9ddf7", "#d2b8ef", "#b48ae3", "#9560d3", "#733cb3", "#4f2182"]

    def color(n):
        for (lo, hi), c in zip(steps, ramp):
            if lo <= n <= hi:
                return c
        return ramp[-1]

    paths = []
    for g in world["objects"]["countries"]["geometries"]:
        if g.get("id") == "010" or g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = "".join(ring(r) for poly in polys for r in poly)
        a2 = num_to_a2.get(g.get("id"), "")
        name = (g.get("properties") or {}).get("name", "")
        n = counts.get(a2, 0)
        if n:
            tip = f"{name}: {n} co-author{'s' if n != 1 else ''}"
            paths.append(f'<path class="cm-map__on" d="{d}" style="fill:{color(n)}" data-tip="{esc(tip)}" tabindex="0">'
                         f'<title>{esc(tip)}</title></path>')
        else:
            paths.append(f'<path d="{d}"/>')
    legend = "".join(
        f'<li><span style="background:{c}"></span>{lo if lo == hi else (f"{lo}+" if hi > 10 ** 6 else f"{lo}–{hi}")}</li>'
        for (lo, hi), c in zip(steps, ramp) if lo <= top)
    return (f'<div class="cm-map"><svg class="cm-map__svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="World map of co-authors by country">{"".join(paths)}</svg>'
            f'<div class="cm-chart-tip" hidden></div></div>'
            f'<ul class="cm-map__legend" aria-label="Co-authors per country">{legend}</ul>')


def lag_section(ledger):
    """Preprint-to-publication lag from things_done's report (nothing computed
    here but the summary). Hollow dots: a date known only to the month/year."""
    rows = [p for p in ledger.lag if isinstance(p.get("gap_days"), int) and p["gap_days"] >= 0]
    if len(rows) < 3:
        return ""
    gaps = sorted(r["gap_days"] for r in rows)
    n = len(gaps)
    median = gaps[n // 2] if n % 2 else (gaps[n // 2 - 1] + gaps[n // 2]) / 2
    to_m = lambda d: d / 30.44  # noqa: E731
    top = max(12, int((to_m(gaps[-1]) + 5.99) // 6 * 6))
    W, left, right, r, gap = 640, 16, 16, 5, 12
    x = lambda m: left + (W - left - right) * m / top  # noqa: E731
    bins = {}
    for row in sorted(rows, key=lambda r: r["gap_days"]):
        bins.setdefault(int(to_m(row["gap_days"])), []).append(row)
    tallest = max(len(v) for v in bins.values())
    base = 24 + tallest * gap
    H = base + 34
    parts = [f'<svg class="cm-lag__chart" viewBox="0 0 {W} {H}" role="img" '
             f'aria-label="Months from preprint to journal publication for {n} papers; median {to_m(median):.1f} months">']
    for t in range(0, top, 6):
        parts.append(f'<line class="cm-lag__grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="12" y2="{base}"/>'
                     f'<text class="cm-lag__tick" x="{x(t):.1f}" y="{base + 18}">{t}</text>')
    parts.append(f'<line class="cm-lag__axis" x1="{left}" x2="{W - right}" y1="{base}" y2="{base}"/>')
    mx = x(to_m(median))
    parts.append(f'<line class="cm-lag__median" x1="{mx:.1f}" x2="{mx:.1f}" y1="4" y2="{base}"/>'
                 f'<text class="cm-lag__label" x="{mx + 6:.1f}" y="14">median {to_m(median):.1f} months</text>')
    for b, items in bins.items():
        for i, row in enumerate(items):
            exact = row.get("preprint_date_precision") == "day" and row.get("published_date_precision") == "day"
            tip = (f'{row.get("published_title", "")}: {to_m(row["gap_days"]):.1f} months '
                   f'({row.get("preprint_date")} → {row.get("published_date")}{"" if exact else ", approximate date"})')
            parts.append(f'<a href="https://doi.org/{esc(row["published_doi"])}"><circle class="cm-lag__dot{"" if exact else " is-approx"}" '
                         f'cx="{x(b + 0.5):.1f}" cy="{base - 10 - i * gap:.1f}" r="{r}" data-tip="{esc(tip)}"><title>{esc(tip)}</title></circle></a>')
    parts.append("</svg>")
    table = "".join(
        f'<tr><td>{esc(r.get("published_title", ""))}</td><td>{r.get("preprint_date")}</td>'
        f'<td>{r.get("published_date")}</td><td>{to_m(r["gap_days"]):.1f}</td></tr>'
        for r in sorted(rows, key=lambda r: r.get("published_date", ""), reverse=True))
    approx = sum(1 for r in rows if not (r.get("preprint_date_precision") == "day" and r.get("published_date_precision") == "day"))
    note = f" Hollow dots ({approx}): one of the two dates is only known to the month." if approx else ""
    return (f'<div class="cm-lag">'
            f'<div class="cm-lag__head"><p class="cm-lag__hero"><strong>{to_m(median):.1f}</strong> months</p>'
            f'<p><span class="cm-lag__title">Median time from preprint to journal</span>'
            f'Months between posting and journal publication, for {n} papers. Each dot is a paper; hover or tap for details.{note}</p></div>'
            f'<div class="cm-lag__plot">{"".join(parts)}<div class="cm-chart-tip" hidden></div></div>'
            f'<details class="cm-lag__table"><summary>Show as table</summary><table><thead><tr><th>Paper</th>'
            f'<th>Preprint</th><th>Journal</th><th>Months</th></tr></thead><tbody>{table}</tbody></table></details></div>')


def papers_per_year(records):
    counts = {}
    for r in records:
        if r.get("year"):
            counts[int(r["year"])] = counts.get(int(r["year"]), 0) + 1
    years = list(range(min(counts), max(counts) + 1))
    top = max(counts.values())
    W, H, pad, base = 640, 170, 24, 140
    bw = (W - 2 * pad) / len(years)
    bars = []
    for i, y in enumerate(years):
        n = counts.get(y, 0)
        h = (base - 16) * n / top
        bx = pad + i * bw + 2
        tip = f"{y}: {n} paper{'s' if n != 1 else ''}"
        if n:
            bars.append(f'<rect class="cm-bars__bar" x="{bx:.1f}" y="{base - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" rx="3" '
                        f'data-tip="{esc(tip)}" tabindex="0"><title>{esc(tip)}</title></rect>')
        if y % 2 == years[-1] % 2:
            bars.append(f'<text class="cm-lag__tick" x="{bx + (bw - 4) / 2:.1f}" y="{base + 18}">{y}</text>')
    bars.append(f'<line class="cm-lag__axis" x1="{pad}" x2="{W - pad}" y1="{base}" y2="{base}"/>')
    return (f'<div class="cm-bars"><svg class="cm-lag__chart" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Papers per year">{"".join(bars)}</svg><div class="cm-chart-tip" hidden></div></div>')


def page_numbers(ledger, lab, members):
    records = ledger.grouped()
    papers = [r for r in records if r.get("status") != "preprint"]
    preprints = [r for r in records if r.get("status") == "preprint"]
    current = [m for m in members if m.get("status", "current") == "current"]
    alumni = [m for m in members if m.get("status") == "alumni"]
    co = ledger.coauthors
    countries = {}
    for c in co:
        if c.get("country"):
            countries[c["country"]] = countries.get(c["country"], 0) + 1
    mt = ledger.metrics

    p = Page("lab-in-numbers.md", title="Lab in numbers",
             description="The Cell Migration Lab in numbers: papers, citations, people, collaborators and how long it takes a preprint to become a paper.")
    p.add("# Lab in numbers", '<p class="cm-lead">Generated automatically from our activity ledger.</p>')
    tiles = [
        (fmt(len(papers)), "papers", "publications/"),
        (fmt(len(preprints)), "preprints", "publications/"),
    ]
    if mt.get("citation_count"):
        tiles.append((fmt(mt["citation_count"]), "citations", mt.get("scholar_url")))
    if mt.get("h_index"):
        tiles.append((str(mt["h_index"]), "h-index", mt.get("scholar_url")))
    tiles += [
        (str(len(current) + len(alumni)), f"lab members ({len(current)} now)", "lab-members/"),
        (fmt(len(co)), "co-authors", "#collaborators"),
        (str(len(countries)), "countries", "#map"),
        (str(len(software_list(ledger))), "software tools", "software/"),
        (str(len(ledger.datasets)), "datasets", "datasets/"),
    ]
    p.add('<ul class="cm-tiles">' + "".join(
        f'<li><a href="{esc(link)}"><strong>{value}</strong><span>{esc(label)}</span></a></li>' for value, label, link in tiles) + "</ul>")
    if mt.get("fetched_at"):
        p.add(f'<p class="cm-small">Citations and h-index from Google Scholar, {str(mt["fetched_at"])[:10]}.</p>')

    p.add(section_title("Papers per year"), papers_per_year(records))
    lag = lag_section(ledger)
    if lag:
        p.add(section_title("From preprint to paper"), lag)

    external = [c for c in co if not is_lab_member(c["name"], lab)]
    top = external[:12]
    if top:
        most = top[0]["papers"]
        p.add(section_title("Top collaborators", id_="collaborators"), '<ol class="cm-toplist">')
        for c in top:
            years = f'{c["first_year"]}–{c["last_year"]}' if c.get("first_year") != c.get("last_year") else str(c.get("last_year"))
            p.add(f'<li><span class="cm-toplist__name">{esc(c["name"])} <span aria-hidden="true">{flag(c.get("country"))}</span></span>'
                  f'<span class="cm-toplist__bar"><span style="width:{100 * c["papers"] / most:.0f}%"></span></span>'
                  f'<a class="cm-toplist__n" href="publications/?q={esc(c["name"].split()[-1])}">{c["papers"]} papers</a>'
                  f'<span class="cm-toplist__years">{years}</span></li>')
        p.add("</ol>")

    if countries:
        p.add(section_title("Where our co-authors are", id_="map"), world_map(countries))

    cloud = co[:70]
    if cloud:
        most = cloud[0]["papers"]
        words = sorted(cloud, key=lambda c: c["name"].split()[-1])
        p.add(section_title("Co-authors"), '<p class="cm-cloud" aria-label="Co-authors; larger names share more papers">')
        for c in words:
            size = 0.7 + 1.8 * (c["papers"] / most) ** 0.5
            cls = "cm-cloud__lab" if is_lab_member(c["name"], lab) else ""
            p.add(f'<span class="{cls}" style="font-size:{size:.2f}rem" title="{esc(c["name"])}: {c["papers"]} joint papers">{esc(c["name"])}</span>')
        p.add("</p>", '<p class="cm-small cm-cloud__legend">Size: number of joint papers. '
              '<span class="cm-cloud__lab">Purple</span>: lab members.</p>')
    p.add('<p class="cm-small cm-source">All numbers come from our <em>things_done</em> activity ledger and its reports '
          '(co-author countries from OpenAlex) and update automatically.</p>')
    p.write()


def page_datasets(ledger, site):
    p = Page("datasets.md", title="Datasets",
             description="Open datasets, deep learning models and materials shared by the Cell Migration Lab.")
    p.add("# Datasets",
          '<p class="cm-lead">We share our data. Here are the datasets, models and materials that accompany our papers.</p>')
    res = site.get("resources") or []
    if res:
        p.add('<ul class="cm-resources">')
        for r in res:
            p.add(f'<li><a href="{esc(r["url"])}"><strong>{esc(r["title"])}</strong><span>{esc(r.get("text", ""))}</span></a></li>')
        p.add("</ul>")
    labels = dict(DATASET_TYPES)
    groups = {}
    for d in ledger.datasets:
        key = labels.get(str(d.get("dataset_type") or "").lower(), "Other data")
        groups.setdefault(key, []).append(d)
    order = list(dict.fromkeys(labels.values())) + ["Other data"]
    p.add('<nav class="cm-toc-inline">' + " · ".join(
        f'<a href="#{slugify(g)}">{esc(g)} ({len(groups[g])})</a>' for g in order if g in groups) + "</nav>")
    for g in order:
        if g not in groups:
            continue
        p.add(f'<h2 id="{slugify(g)}">{esc(g)}</h2>', '<ul class="cm-datasets">')
        for d in groups[g]:
            refs = []
            for doi in d.get("related_publication_dois") or []:
                rec = ledger.get(doi)
                label = f'{rec.get("venue")}, {rec.get("year")}' if rec else "paper"
                refs.append(f'<a href="https://doi.org/{esc(doi)}">{esc(label)}</a>')
            tags = "".join(f'<span class="cm-badge">{esc(t)}</span>' for t in d.get("dataset_tags") or [] if t in ("model-zoo", "dl-ready"))
            archive = f' · <a href="https://doi.org/{esc(d["archive_doi"])}">doi:{esc(d["archive_doi"])}</a>' if d.get("archive_doi") and d["archive_doi"] not in d.get("repository_url", "") else ""
            p.add(f'<li><a class="cm-datasets__title" href="{esc(d["repository_url"])}">{esc(d["title"])}</a>{tags}'
                  f'<p>{esc(d.get("description") or "")}</p>'
                  f'<p class="cm-small">{year_of(d.get("start_date")) or ""}{archive}'
                  f'{" · Paper: " + ", ".join(refs) if refs else ""}</p></li>')
        p.add("</ul>")
    p.add('<p class="cm-small cm-source">Generated from our <em>things_done</em> activity ledger; updates automatically.</p>')
    p.write()


def page_gallery(gallery):
    p = Page("gallery.md", title="Gallery", edit_url=edit_url("data/gallery.yaml"),
             description="Microscopy images and journal covers from the Cell Migration Lab.",
             image=gallery["images"][0]["image"])
    p.add("# Gallery", section_title("Journal covers"), '<ul class="cm-covers">')
    for c in gallery.get("covers") or []:
        full = thumb(c["image"], 1600)
        p.add(f'<li><a href="{full}" data-cm-lightbox data-caption="{esc(c.get("caption", ""))}">'
              f'{media(c["image"], c.get("caption", ""), 500)}</a><span>{esc(c.get("caption", ""))}</span></li>')
    p.add("</ul>", section_title("Images"), '<ul class="cm-gallery">')
    for g in gallery.get("images") or []:
        full = thumb(g["image"], 2000)
        p.add(f'<li><a href="{full}" data-cm-lightbox data-caption="{esc(g.get("caption", ""))}">'
              f'{media(g["image"], g.get("caption", ""), 600)}</a></li>')
    p.add("</ul>")
    p.write()


def page_talks(talks):
    p = Page("online-lectures.md", title="Online talks", edit_url=edit_url("data/talks.yaml"),
             description="Recorded talks, webinars and interviews from the Cell Migration Lab.")
    p.add("# Online talks", '<div class="cm-talks">')
    for t in talks:
        meta = " · ".join(str(x) for x in (t.get("event"), t.get("year")) if x)
        p.add(f'<figure class="cm-talk">{lite_video(t.get("youtube"), t.get("vimeo"), t["title"], t.get("start"))}'
              f'<figcaption><strong>{esc(t["title"])}</strong><span>{esc(meta)}</span></figcaption></figure>')
    p.add("</div>")
    p.write()


def write_footer(site):
    """Footer partial for overrides/main.html (links are made relative with the url filter)."""
    def u(path):
        return path if is_external(path) else "{{ '" + path + "' | url }}"
    logos = "".join(
        f'<li><a href="{esc(a["url"])}" title="{esc(a["name"])}"><img src="{u(thumb(a.get("logo_dark") or a["logo"], 300))}" '
        f'alt="{esc(a["name"])}" loading="lazy"></a></li>' for a in site["affiliations"])
    social = "".join(
        f'<li><a href="{esc(s["url"])}">{ICONS.get(s.get("icon"), "")}<span>{esc(s["label"])}</span></a></li>'
        for s in site.get("social") or [])
    address = "<br>".join(esc(x) for x in site["contact"]["address"])
    out = f"""{{#- Generated by scripts/build_pages.py from data/site.yaml - edit that file instead. -#}}
<footer class="cm-footer">
  <div class="cm-footer__inner">
    <div class="cm-footer__col">
      <p class="cm-footer__title">{esc(site["name"])}</p>
      <p>{esc(site["motto"])}</p>
      <img class="cm-footer__logo" src="{u(thumb(site["footer_logo"], 500))}" alt="Cell Migration – Jacquemet Lab logo" loading="lazy">
    </div>
    <div class="cm-footer__col">
      <p class="cm-footer__title">Affiliations</p>
      <ul class="cm-footer__logos">{logos}</ul>
    </div>
    <div class="cm-footer__col">
      <p class="cm-footer__title">Get in touch</p>
      <ul class="cm-footer__social">{social}</ul>
      <p class="cm-footer__address">{address}</p>
    </div>
  </div>
  <div class="cm-footer__bottom">
    <span>{{{{ config.copyright }}}}</span>
    <span><a href="{u('feed.xml')}">RSS</a> · <a href="{{{{ config.repo_url }}}}">Website source on GitHub</a></span>
  </div>
</footer>
"""
    path = ROOT / "overrides" / "partials" / "cm-footer.html"
    path.write_text(out, encoding="utf-8")


def write_feed(site, featured):
    entries = []
    for f in featured:
        entries.append((f["date"], f["title"], f'portfolio/{f["slug"]}/', md(f.get("summary") or "")))
    entries.sort(key=lambda e: e[0], reverse=True)
    items = []
    for d, title, path, body in entries[:30]:
        when = format_datetime(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc))
        url = SITE_URL + path
        items.append(f"<item><title>{esc(title)}</title><link>{url}</link><guid>{url}</guid>"
                     f"<pubDate>{when}</pubDate><description>{esc(body)}</description></item>")
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
           f'<title>{esc(site["name"])}</title><link>{SITE_URL}</link>'
           f'<atom:link href="{SITE_URL}feed.xml" rel="self" type="application/rss+xml"/>'
           f'<description>{esc(site["motto"])}</description><language>en</language>'
           + "".join(items) + "</channel></rss>\n")
    (DOCS / "feed.xml").write_text(rss, encoding="utf-8")
    (DOCS / "feed").mkdir(exist_ok=True)
    (DOCS / "feed" / "index.html").write_text(rss, encoding="utf-8")  # old WordPress feed address


# --------------------------------------------------------------------------- main

def clean():
    for name in GENERATED:
        path = DOCS / name
        if name == THUMBS:
            continue  # thumbnails are kept between builds (only regenerated when the source changes)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def main():
    clean()
    site = load(DATA / "site.yaml")
    ledger = Ledger()
    lab = lab_names()
    members = load_members()
    featured, extra = load_featured(ledger)

    page_home(site, featured, ledger, lab)
    page_research(load(DATA / "research.yaml"), ledger, lab)
    page_members(members)
    page_software(ledger)
    page_featured(featured, extra, ledger, lab)
    page_numbers(ledger, lab, members)
    page_publications(ledger, featured, lab)
    page_datasets(ledger, site)
    page_gallery(load(DATA / "gallery.yaml"))
    page_talks(load(DATA / "talks.yaml") or [])
    write_feed(site, featured)
    write_footer(site)
    print(f"Generated pages: {len(featured)} stories, {len(ledger.grouped())} publications, "
          f"{len(ledger.datasets)} datasets, {len(members)} people.")


if __name__ == "__main__":
    main()
