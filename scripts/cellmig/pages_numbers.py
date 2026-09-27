"""The "Lab in numbers" page (docs/lab-in-numbers.md). Every number comes from
things_done data; this page only counts and draws."""

from .charts import lag_section, papers_per_year
from .components import section_title
from .ledger import Ledger, Record, software_list
from .page import Page
from .people import Person, is_lab_member
from .previews import preview
from .text import esc, flag, fmt
from .worldmap import world_map

TOP_COLLABORATORS = 12
CLOUD_SIZE = 70


def _tiles(ledger: Ledger, members: list[Person], countries: dict[str, int]) -> str:
    """Headline numbers, each linking to where it comes from."""
    records = ledger.grouped()
    n_pre = sum(1 for r in records if r.get("status") == "preprint")
    n_now = sum(1 for m in members if m["status"] == "current")
    mt = ledger.metrics
    tiles = [
        (fmt(len(records) - n_pre), "papers", "publications/"),
        (fmt(n_pre), "preprints", "publications/"),
        (fmt(mt["citation_count"]), "citations", mt["scholar_url"]),
        (str(mt["h_index"]), "h-index", mt["scholar_url"]),
        (str(len(members)), f"members · {n_now} current", "lab-members/"),
        (fmt(len(ledger.coauthors)), "co-authors", "#collaborators"),
        (str(len(countries)), "co-author countries", "#map"),
        (str(len(software_list(ledger))), "software tools", "software/"),
        (str(len(ledger.datasets)), "datasets", "datasets/"),
    ]
    return ('<ul class="cm-tiles">' + "".join(
        f'<li><a href="{esc(link)}"><strong>{value}</strong><span>{esc(label)}</span></a></li>'
        for value, label, link in tiles) + "</ul>"
        f'<p class="cm-small">Citations and h-index from Google Scholar, {str(mt["fetched_at"])[:10]}.</p>')


def _top_collaborators(coauthors: list[Record], lab: set[str]) -> str:
    """Bar list of the co-authors outside the lab with the most joint papers."""
    top = [c for c in coauthors if not is_lab_member(c["name"], lab)][:TOP_COLLABORATORS]
    most = top[0]["papers"]
    rows = []
    for c in top:
        years = str(c["last_year"]) if c["first_year"] == c["last_year"] else f'{c["first_year"]}–{c["last_year"]}'
        rows.append(f'<li><span class="cm-toplist__name">{esc(c["name"])} <span aria-hidden="true">{flag(c.get("country"))}</span></span>'
                    f'<span class="cm-toplist__bar"><span style="width:{100 * c["papers"] / most:.0f}%"></span></span>'
                    f'<a class="cm-toplist__n" href="publications/?q={esc(c["name"].split()[-1])}">{c["papers"]} papers</a>'
                    f'<span class="cm-toplist__years">{years}</span></li>')
    return '<ol class="cm-toplist">' + "".join(rows) + "</ol>"


def _cloud(coauthors: list[Record], lab: set[str]) -> str:
    """Word cloud of the most frequent co-authors, sorted by surname."""
    cloud = coauthors[:CLOUD_SIZE]
    most = cloud[0]["papers"]
    words = []
    for c in sorted(cloud, key=lambda c: c["name"].split()[-1]):
        size = 0.7 + 1.8 * (c["papers"] / most) ** 0.5
        cls = "cm-cloud__lab" if is_lab_member(c["name"], lab) else ""
        words.append(f'<span class="{cls}" style="font-size:{size:.2f}rem" '
                     f'title="{esc(c["name"])}: {c["papers"]} joint papers">{esc(c["name"])}</span>')
    return ('<p class="cm-cloud" aria-label="Co-authors; larger names share more papers">' + "\n".join(words) + "</p>"
            '<p class="cm-small cm-cloud__legend">Size: number of joint papers. '
            '<span class="cm-cloud__lab">Purple</span>: authors directly associated with the lab.</p>')


def page_numbers(ledger: Ledger, lab: set[str], members: list[Person]) -> None:
    """Tiles, papers per year, preprint lag, top collaborators, map, co-author cloud."""
    countries: dict[str, int] = {}
    for c in ledger.coauthors:
        if c.get("country"):
            countries[c["country"]] = countries.get(c["country"], 0) + 1
    p = Page("lab-in-numbers.md", title="Lab in numbers", **preview("lab-in-numbers"))
    p.add("# Lab in numbers",
          _tiles(ledger, members, countries),
          section_title("Papers per year"), papers_per_year(ledger.grouped()),
          section_title("From preprint to paper"), lag_section(ledger.lag_pairs, ledger.lag_summary),
          section_title("Top collaborators", id_="collaborators"), _top_collaborators(ledger.coauthors, lab),
          section_title("Where our co-authors are", id_="map"), world_map(countries),
          section_title("Co-authors"), _cloud(ledger.coauthors, lab))
    p.write()
