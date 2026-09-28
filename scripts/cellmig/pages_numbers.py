"""The "Lab in numbers" page (docs/lab-in-numbers.md). Every number comes from
things_done data; this page only counts and draws."""

from urllib.parse import quote

from .charts import lag_section, papers_per_year
from .components import section_title
from .ledger import Ledger, Record, software_list
from .page import Page
from .people import Person, is_lab_member
from .previews import preview
from .text import esc, flag, fmt, long_date, plural
from .worldmap import world_map

TOP_COLLABORATORS = 12
CLOUD_MIN, CLOUD_MAX = 0.62, 1.55   # font sizes (rem) of the least and most frequent co-author


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
        f'<p class="cm-small">Citations and h-index from Google Scholar, {long_date(mt["fetched_at"])}.</p>')


def _top_collaborators(coauthors: list[Record], lab: set[str]) -> str:
    """Bar list of the co-authors outside the lab with the most joint papers."""
    top = [c for c in coauthors if not is_lab_member(c["name"], lab)][:TOP_COLLABORATORS]
    most = top[0]["papers"]
    rows = []
    for c in top:
        years = str(c["last_year"]) if c["first_year"] == c["last_year"] else f'{c["first_year"]}–{c["last_year"]}'
        rows.append(f'<li><span class="cm-toplist__name">{esc(c["name"])} <span aria-hidden="true">{flag(c.get("country"))}</span></span>'
                    f'<span class="cm-toplist__bar"><span style="width:{100 * c["papers"] / most:.0f}%"></span></span>'
                    f'<a class="cm-toplist__n" href="publications/?q={esc(quote(c["name"]))}">{c["papers"]} papers</a>'
                    f'<span class="cm-toplist__years">{years}</span></li>')
    return '<ol class="cm-toplist">' + "".join(rows) + "</ol>"


def cloud_size(papers: int, most: int) -> float:
    """Font size (rem) of a name: grows with the square root of joint papers."""
    return CLOUD_MIN + (CLOUD_MAX - CLOUD_MIN) * (papers / most) ** 0.5


def _words(coauthors: list[Record], lab: set[str], most: int) -> str:
    """Names sorted by surname, sized by joint papers (cloud_size)."""
    words = []
    for c in sorted(coauthors, key=lambda c: c["name"].split()[-1]):
        size = cloud_size(c["papers"], most)
        cls = "cm-cloud__lab" if is_lab_member(c["name"], lab) else ""
        words.append(f'<span class="{cls}" style="font-size:{size:.2f}rem" '
                     f'title="{esc(c["name"])}: {plural(c["papers"], "joint paper")}">{esc(c["name"])}</span>')
    return "\n".join(words)


def _cloud(coauthors: list[Record], lab: set[str]) -> str:
    """Every co-author: those with several joint papers as a word cloud,
    those with one paper in a list that opens on request (the page stays
    short on phones)."""
    most = max(c["papers"] for c in coauthors)
    several = [c for c in coauthors if c["papers"] > 1]
    once = [c for c in coauthors if c["papers"] == 1]
    out = [f'<p class="cm-small cm-cloud__legend">{fmt(len(coauthors))} people have co-authored papers with us. '
           f'The {fmt(len(several))} who share more than one paper with us are shown below'
           + (f'; the {fmt(len(once))} with one joint paper are listed underneath.</p>' if once else '.</p>'),
           f'<p class="cm-cloud" aria-label="Co-authors of several papers; larger names share more papers">'
           f'{_words(several, lab, most)}</p>']
    if once:
        out.append(f'<details class="cm-cloud__more"><summary>Show the {plural(len(once), "co-author")} with one joint paper</summary>'
                   f'<p class="cm-cloud">{_words(once, lab, most)}</p></details>')
    out.append('<p class="cm-small cm-cloud__legend">Size: number of joint papers. '
               '<span class="cm-cloud__lab">Purple</span>: authors directly associated with the lab.</p>')
    return "".join(out)


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
          section_title("Our co-authors", id_="coauthors"), _cloud(ledger.coauthors, lab))
    p.write()
