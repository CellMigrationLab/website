"""Paths, site-wide constants, and loading data files."""

import re
from pathlib import Path
from typing import Any, NoReturn

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
LEDGER_DATA = DATA / "things_done"   # copied from things_done; never edited here
DOCS = ROOT / "docs"
THUMBS = "assets/thumbs"             # resized images, relative to docs/
REPO = "https://github.com/CellMigrationLab/website"
CONTENT = ROOT / "content"            # hand-written pages, copied into docs/ by the build
HOME_FEATURED = 8                    # featured papers shown on the home page
LAB_FOUNDED = 2019                   # publications before this are Guillaume's PhD/postdoc work

def _site_url() -> str:
    """`site_url` from mkdocs.yml, ending in a slash: the one place the site's
    address is set (canonical links, sitemap, RSS, structured data, llms.txt)."""
    m = re.search(r"^site_url:\s*(\S+)", (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("build_pages: mkdocs.yml has no site_url")
    return m.group(1).rstrip("/") + "/"


SITE_URL = _site_url()

# Everything build_pages.py writes into docs/ (deleted and rebuilt on every
# run, except the thumbnail cache). All git-ignored.
GENERATED = [
    "index.md", "research.md", "lab-members.md", "software.md", "lab-in-numbers.md",
    "featured-research.md", "publications.md", "datasets.md", "gallery.md",
    "online-lectures.md", "about-us.md", "join-us.md", "licensing.md", "portfolio", "feed.xml", "feed",
    "llms.txt", "llms-full.txt", "assets/images/members",   # copied from data/photos/
]

# Alt text for a picture that has no caption in its data file (add a caption
# to describe it better).
UNCAPTIONED_ALT = "Microscopy image from the Cell Migration Lab"

# Background colours a tile may use (cm-tile--<colour> in cellmig.css).
# Tiles (Research, Software) alternate white and light; `color: dark` is the
# only override (#25: the microscopy and artwork carry the colour).
COLORS = {"dark"}
FITS = {"cover", "contain"}   # optional `fit` of a picture; cover (fill) unless contain

# Roster groups, in the order people are listed on the members page.
GROUPS = ["pi", "staff", "postdoc", "phd", "student", "other"]

# Dataset type (things_done `dataset_type`) -> heading on the datasets page.
# Headings are listed in this order; any other type goes under "Other data".
# things_done dataset_type (schema enum) -> section of the Datasets page, in page order
DATASET_TYPES = {
    "image": "Image data",
    "proteomic": "Proteomic data",
    "rna_seq": "Sequencing data",
    "model": "Deep learning models",
}
# things_done dataset_tags (schema enum) -> badge
DATASET_TAGS = {"deep-learning-ready": "DL-ready", "model-zoo": "Model zoo"}


def fail(message: str) -> NoReturn:
    """Stop the build with a message that says which file to fix."""
    raise SystemExit(f"build_pages: {message}")


def load(path: Path) -> Any:
    """Parse a YAML file that must exist; an empty file gives {}."""
    if not path.is_file():
        fail(f"missing file {path.relative_to(ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def edit_url(path: str) -> str:
    """GitHub "edit this file" link for a file in this repository."""
    return f"{REPO}/edit/main/{path}"
