"""Write site/sitemap.xml and site/robots.txt after `zensical build`.

    python scripts/write_sitemap.py

Zensical's own sitemap only lists the pages in the menu, which leaves out
every featured-paper page (/portfolio/<slug>/). This lists every page in
site/ instead, leaving out redirect pages (old addresses), the 404 page and
the RSS copy at feed/index.html (not a web page),
and points robots.txt at it. Addresses use `site_url` from mkdocs.yml, so
moving the domain only needs that one setting changed.
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
REDIRECT = re.compile(r'<meta[^>]+http-equiv="refresh"', re.I)


def site_url() -> str:
    """`site_url` from mkdocs.yml, ending in a slash; stops if it is missing."""
    m = re.search(r"^site_url:\s*(\S+)", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("write_sitemap: mkdocs.yml has no site_url")
    return m.group(1).rstrip("/") + "/"


def page_paths(site: Path) -> list[str]:
    """Site-relative directory addresses ("", "research/", ...) of every real
    page: each index.html that is an HTML page and not a redirect page."""
    paths = []
    for index in sorted(site.rglob("index.html")):
        head = index.read_text(encoding="utf-8", errors="ignore")[:2000]
        if head.lstrip().startswith("<?xml") or REDIRECT.search(head):
            continue
        rel = index.parent.relative_to(site).as_posix()
        paths.append("" if rel == "." else f"{rel}/")
    return paths


def sitemap(base: str, paths: list[str]) -> str:
    """sitemap.xml listing base + each path."""
    urls = "".join(f"<url><loc>{escape(base + p)}</loc></url>\n" for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')


def robots(base: str) -> str:
    """robots.txt: everything may be crawled; says where the sitemap is."""
    return f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n"


def main() -> None:
    """Replace Zensical's sitemap.xml and write robots.txt in site/."""
    if not (SITE / "index.html").is_file():
        raise SystemExit("write_sitemap: run `zensical build` first (no site/index.html)")
    base, paths = site_url(), page_paths(SITE)
    (SITE / "sitemap.xml").write_text(sitemap(base, paths), encoding="utf-8")
    (SITE / "robots.txt").write_text(robots(base), encoding="utf-8")
    print(f"sitemap.xml: {len(paths)} pages")


if __name__ == "__main__":
    main()
