"""Paths, site-wide constants, and loading data files."""

from pathlib import Path
from typing import Any, NoReturn

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
LEDGER_DATA = DATA / "things_done"   # copied from things_done; never edited here
DOCS = ROOT / "docs"
THUMBS = "assets/thumbs"             # resized images, relative to docs/
REPO = "https://github.com/CellMigrationLab/website"
SITE_URL = "https://cellmig.org/"
HOME_FEATURED = 8                    # featured papers shown on the home page

# Everything build_pages.py writes into docs/ (deleted and rebuilt on every
# run, except the thumbnail cache). All git-ignored.
GENERATED = [
    "index.md", "research.md", "lab-members.md", "software.md", "lab-in-numbers.md",
    "featured-research.md", "publications.md", "datasets.md", "gallery.md",
    "online-lectures.md", "portfolio", "feed.xml", "feed",
]

# Background colours a tile may use (cm-tile--<colour> in cellmig.css).
COLORS = {"purple", "orange", "blue", "black", "white", "sky", "grey", "mint", "red",
          "green", "amber", "pink", "light"}

# Roster groups, in the order people are listed on the members page.
GROUPS = ["pi", "staff", "postdoc", "phd", "student", "other"]

# Dataset type (things_done `dataset_type`) -> heading on the datasets page.
# Headings are listed in this order; any other type goes under "Other data".
DATASET_TYPES = {
    "image": "Image data",
    "video": "Image data",
    "proteomic": "Proteomic data",
    "rna_seq": "Sequencing data",
    "sequencing": "Sequencing data",
    "model": "Deep learning models",
}
OTHER_DATA = "Other data"


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
