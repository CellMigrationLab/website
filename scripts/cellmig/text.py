"""Small string helpers used everywhere."""

import html
import re
import unicodedata
from urllib.parse import urlsplit

import markdown

_MD = markdown.Markdown(extensions=["smarty"])


def esc(value: object) -> str:
    """HTML-escape a value (None becomes an empty string)."""
    return html.escape(str(value if value is not None else ""), quote=True)


def md(text: str | None, inline: bool = False) -> str:
    """Markdown -> HTML. Site paths in links ("software/") are made relative
    to the page later, by Page.fix_links(). `inline` drops the <p> wrapper."""
    _MD.reset()
    out = _MD.convert(str(text or "").strip())
    if inline:
        out = re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)
    return out


def slugify(text: str) -> str:
    """ASCII, lowercase, dash-separated: "Iván Hidalgo" -> "ivan-hidalgo"."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize_name(name: str) -> str:
    """Accent-, case- and punctuation-insensitive key for matching author names."""
    return slugify(name).replace("-", "")


def year_of(value: object) -> int | None:
    """Year from "2021", "2021-05-03" or 2021; None when there is no year."""
    m = re.match(r"\d{4}", str(value or ""))
    return int(m.group(0)) if m else None


PRECISIONS = {"day": 10, "month": 7, "year": 4}   # length of an ISO date known to that precision


def known_date(date: object, precision: str) -> str:
    """An ISO date cut to what is known: "2021-09-14", "2021-09" or "2021".
    Partial dates sort as strings: newer first with reverse=True, and within
    a year or month the less precise date comes after the more precise ones."""
    return str(date)[:PRECISIONS[precision]]


def precision_of(date: str) -> str:
    """"day", "month" or "year" for a date made by known_date."""
    return {n: p for p, n in PRECISIONS.items()}[len(date)]


def full_date(date: str | None) -> str | None:
    """The date when it is known to the day (schema.org and Scholar dates), else None."""
    return date if date and precision_of(date) == "day" else None


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def long_date(iso: str) -> str:
    """"2026-09-21" (or a longer ISO timestamp) -> "21 September 2026", the way
    dates are written on the site."""
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def is_external(url: str) -> bool:
    """True for absolute URLs, mailto:, fragments and protocol-relative links."""
    return bool(re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", str(url), flags=re.I))


SAME_SITE_HOSTS = {"cellmig.org", "www.cellmig.org"}   # the lab's own domain


def opens_new_tab(url: str) -> bool:
    """Web links that leave the site open in a new tab (#16); site pages
    (also absolute ones), fragments, mailto: and other schemes do not.
    Compared by host name (and, for SITE_URL, its path), not by text prefix:
    https://cellmig.org.example.org is another site."""
    from .config import SITE_URL   # config imports text: import here
    link, site = urlsplit(str(url)), urlsplit(SITE_URL)
    if link.scheme.lower() not in ("http", "https"):
        return False
    if link.hostname in SAME_SITE_HOSTS:
        return False
    return not (link.hostname == site.hostname and f"{link.path.rstrip('/')}/".startswith(site.path))


NEW_TAB = 'target="_blank" rel="noopener"'


def fmt(n: int) -> str:
    """1234 -> "1\u202f234" (narrow no-break space as thousands separator)."""
    return f"{n:,}".replace(",", "\u202f")


def flag(code: str | None) -> str:
    """Flag emoji for a two-letter country code ("FI" -> 🇫🇮)."""
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper()) if code and len(code) == 2 else ""


def plural(n: int, word: str) -> str:
    """plural(1, "paper") -> "1 paper"; plural(2, "paper") -> "2 papers"."""
    return f"{n} {word}{'' if n == 1 else 's'}"
