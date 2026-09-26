"""Small string helpers used everywhere."""

import html
import re
import unicodedata

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


def is_external(url: str) -> bool:
    """True for absolute URLs, mailto:, fragments and protocol-relative links."""
    return bool(re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", str(url), flags=re.I))


def fmt(n: int) -> str:
    """1234 -> "1\u202f234" (narrow no-break space as thousands separator)."""
    return f"{n:,}".replace(",", "\u202f")


def flag(code: str | None) -> str:
    """Flag emoji for a two-letter country code ("FI" -> 🇫🇮)."""
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper()) if code and len(code) == 2 else ""


def plural(n: int, word: str) -> str:
    """plural(1, "paper") -> "1 paper"; plural(2, "paper") -> "2 papers"."""
    return f"{n} {word}{'' if n == 1 else 's'}"
