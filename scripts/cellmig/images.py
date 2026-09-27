"""Images and videos: resized WebP thumbnails and the markup that shows them.

Thumbnails go to docs/assets/thumbs/ and are kept between builds; one is
only remade when its source image is newer.
"""

from functools import cache
from pathlib import Path

from PIL import Image, ImageOps

from .config import DOCS, THUMBS, fail
from .text import esc

VECTOR_OR_ANIMATED = (".svg", ".gif")   # served as they are, never resized
SMALL_FILE = 150_000                    # bytes; smaller images are not resized


def source(site_path: str) -> Path:
    """The file behind a site path; the build stops if it does not exist."""
    path = DOCS / site_path
    if not path.is_file():
        fail(f"missing image docs/{site_path}")
    return path


@cache
def image_size(site_path: str) -> tuple[int, int] | None:
    """(width, height) after EXIF rotation; None for SVG (no pixel size)."""
    if site_path.lower().endswith(".svg"):
        return None
    with Image.open(source(site_path)) as im:
        return ImageOps.exif_transpose(im).size


def _stale(out: Path, src: Path) -> bool:
    return not out.exists() or out.stat().st_mtime < src.stat().st_mtime


def thumb(site_path: str, width: int) -> str:
    """Site path of a WebP copy at most `width` px wide (the original when it
    is already small, or is an SVG/GIF)."""
    src = source(site_path)
    if src.suffix.lower() in VECTOR_OR_ANIMATED:
        return site_path
    size = image_size(site_path)
    if size[0] <= width and src.stat().st_size < SMALL_FILE:
        return site_path
    out_rel = f"{THUMBS}/{width}/{Path(site_path).with_suffix('.webp').as_posix()}"
    out = DOCS / out_rel
    if _stale(out, src):
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "transparency" in im.info or im.mode in ("LA", "P") else "RGB")
            im.thumbnail((width, width * 4), Image.LANCZOS)
            im.save(out, "WEBP", quality=82, method=4)
    return out_rel


def share_jpeg(site_path: str, width: int = 1200) -> str:
    """JPEG copy at most `width` px wide, for link previews (og:image): some
    sites that show previews do not read WebP."""
    src = source(site_path)
    out_rel = f"{THUMBS}/share/{Path(site_path).with_suffix('.jpg').as_posix()}"
    out = DOCS / out_rel
    if _stale(out, src):
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((width, width * 4), Image.LANCZOS)
            im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out_rel


def square_thumb(site_path: str, size: int = 480, position: str = "top") -> str:
    """Square WebP crop (member photos); `position` "top" keeps faces in frame,
    "center" crops evenly."""
    if position not in ("top", "center"):
        fail(f"photo_position must be 'top' or 'center', not {position!r} ({site_path})")
    src = source(site_path)
    out_rel = f"{THUMBS}/square/{Path(site_path).with_suffix('.webp').as_posix()}"
    out = DOCS / out_rel
    if _stale(out, src):
        out.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            centering = (0.5, 0.5) if position == "center" else (0.5, 0.25)
            im = ImageOps.fit(im, (size, size), Image.LANCZOS, centering=centering)
            im.save(out, "WEBP", quality=84, method=4)
    return out_rel


def gif_video(site_path: str) -> tuple[str, str | None] | None:
    """(mp4, poster) for a GIF that has an MP4 twin in docs/assets/media/gif/
    (much smaller than the GIF); None when there is no twin."""
    if not site_path.lower().endswith(".gif"):
        return None
    rel = site_path.split("wp-content/uploads/", 1)[-1]
    mp4 = f"assets/media/gif/{rel[:-4]}.mp4"
    if not (DOCS / mp4).is_file():
        return None
    poster = mp4[:-4] + ".jpg"
    return mp4, poster if (DOCS / poster).is_file() else None


def media(site_path: str | None, alt: str = "", width: int = 900, cls: str = "",
          eager: bool = False, sizes: str | None = None) -> str:
    """Markup for an image or video file.

    - .mp4: a <video> with controls (poster = same name .jpg, if present)
    - .gif with an MP4 twin: a silent looping <video>
    - anything else: a lazy <img> (with a half-size srcset from 900 px up)
    """
    if not site_path:
        return ""
    if site_path.lower().endswith(".mp4"):
        source(site_path)
        poster = site_path[:-4] + ".jpg"
        p = f' poster="{poster}"' if (DOCS / poster).is_file() else ""
        return (f'<video class="{cls}" controls preload="none" playsinline{p}>'
                f'<source src="{site_path}" type="video/mp4"></video>')
    twin = gif_video(site_path)
    if twin:
        mp4, poster = twin
        p = f' poster="{poster}"' if poster else ""
        label = f' aria-label="{esc(alt)}"' if alt else ""
        # No autoplay: cellmig.js plays loops only while they are on screen.
        return (f'<video class="{cls} cm-loop" muted loop playsinline preload="none"{p}{label}>'
                f'<source src="{mp4}" type="video/mp4"></video>')
    src = thumb(site_path, width)
    size = image_size(src)
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    srcset = ""
    if width >= 900:
        small = thumb(site_path, width // 2)
        if small != src:
            srcset = f' srcset="{small} {width // 2}w, {src} {width}w" sizes="{sizes or "(max-width: 700px) 100vw, 50vw"}"'
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return f'<img class="{cls}" src="{src}"{srcset}{dims} alt="{esc(alt)}" {loading}>'


def lite_video(youtube: str | None = None, vimeo: str | None = None, title: str = "",
               start: int | None = None) -> str:
    """Video placeholder: nothing loads from YouTube/Vimeo until the visitor
    clicks (cellmig.js swaps in the player). Exactly one of youtube/vimeo."""
    if bool(youtube) == bool(vimeo):
        fail(f"video {title!r} needs exactly one of 'youtube' or 'vimeo'")
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


def dims(site_path: str) -> str:
    """ width="…" height="…" for an image (empty for SVG), to reserve its space."""
    size = image_size(site_path)
    return f' width="{size[0]}" height="{size[1]}"' if size else ""
