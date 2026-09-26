"""One generated Markdown page, with links made relative to where it lives."""

import re

import yaml

from .config import DOCS
from .images import gif_video, share_jpeg
from .text import is_external


def share_image(site_path: str | None) -> str | None:
    """A link-preview image: a 1200 px JPEG still (a GIF's poster frame); None
    when there is no still, so the template's default image is used."""
    if not site_path:
        return None
    if site_path.lower().endswith(".gif"):
        twin = gif_video(site_path)
        return share_jpeg(twin[1]) if twin and twin[1] else None
    if site_path.lower().endswith(".svg"):
        return None
    return share_jpeg(site_path)


class Page:
    """Collects HTML/Markdown chunks and writes docs/<path> with front matter.

    Chunks write links as site paths ("software/", "assets/x.png"); write()
    turns them into paths relative to this page, so the site also works
    under a sub-path (e.g. a GitHub Pages preview).
    """

    def __init__(self, path: str, **meta: object) -> None:
        self.path = path                      # e.g. "portfolio/cdm.md"
        meta["image"] = share_image(meta.get("image"))
        self.meta = {k: v for k, v in meta.items() if v not in (None, "", [])}
        self.parts: list[str] = []
        # Zensical rewrites href/src in raw HTML as paths relative to the
        # Markdown file; other attributes (srcset, poster, data-full) are used
        # as they are, so they must be relative to the page's final URL,
        # which is one level deeper for every page except index.md.
        self.depth_file = path.count("/")
        stem = path[:-3]
        self.depth_url = self.depth_file + (0 if stem == "index" or stem.endswith("/index") else 1)

    def u(self, target: str, final_url: bool = False) -> str:
        """Site path -> path relative to this page (external URLs unchanged)."""
        target = str(target or "")
        if not target or is_external(target):
            return target
        depth = self.depth_url if final_url else self.depth_file
        return "../" * depth + target.lstrip("/") if depth else (target.lstrip("/") or "./")

    def add(self, *chunks: str) -> None:
        """Append chunks of HTML/Markdown (joined with newlines on write)."""
        self.parts.extend(chunks)

    def fix_links(self, text: str) -> str:
        """Make href/src/poster/data-full/srcset site paths relative to this page."""
        def repl(m: re.Match) -> str:
            attr, url = m.group(1), m.group(2)
            if is_external(url) or url.startswith(("../", "./")):
                return m.group(0)
            return f'{attr}="{self.u(url, final_url=attr in ("poster", "data-full"))}"'

        def repl_srcset(m: re.Match) -> str:
            items = []
            for part in m.group(1).split(","):
                url, _, size = part.strip().partition(" ")
                items.append(f"{url if is_external(url) else self.u(url, final_url=True)} {size}".strip())
            return f'srcset="{", ".join(items)}"'

        text = re.sub(r'\bsrcset="([^"]*)"', repl_srcset, text)
        return re.sub(r'\b(href|src|poster|data-full)="([^"]*)"', repl, text)

    def write(self) -> None:
        """Write docs/<path> (front matter + body)."""
        out = DOCS / self.path
        out.parent.mkdir(parents=True, exist_ok=True)
        front = yaml.safe_dump(self.meta, allow_unicode=True, sort_keys=False, width=1000).strip()
        body = self.fix_links("\n".join(self.parts))
        out.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")
