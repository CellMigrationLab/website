"""things_done data, as copied to data/things_done/ by scripts/sync_things_done.py.

Every file there is required: a missing or empty one stops the build instead
of silently leaving a section out of the site.
"""

from typing import Any

from .config import DATA, LEDGER_DATA, fail, load
from .text import known_date, year_of

Record = dict[str, Any]


def _records(name: str, key: str = "records") -> list[Record]:
    """The list under `key` in data/things_done/<name>.yaml; must not be empty."""
    rows = load(LEDGER_DATA / f"{name}.yaml").get(key) or []
    if not rows:
        fail(f"data/things_done/{name}.yaml has no {key}; re-run scripts/sync_things_done.py")
    return rows


class Ledger:
    """Publications, software, datasets and reports from things_done."""

    def __init__(self) -> None:
        self.pubs: list[Record] = _records("publications")
        for p in self.pubs:   # optional in things_done, but every citation on the site shows it
            if not p.get("venue"):
                fail(f"things_done publication {p['doi']} has no venue (journal or preprint server); add it to the ledger")
        self.software: list[Record] = _records("software")
        self.datasets: list[Record] = _records("datasets")
        self.coauthors: list[Record] = _records("coauthors", "coauthors")
        self.affiliations: list[Record] = _records("affiliations")
        self.talks: list[Record] = _records("talks")
        self.grants: list[Record] = _records("grants")
        self.profile: Record = load(LEDGER_DATA / "profile.yaml")
        for key in ("name", "title", "short_bio", "appointments", "education"):
            if not self.profile.get(key):
                fail(f"data/things_done/profile.yaml has no {key}; re-run scripts/sync_things_done.py")
        for key in ("editorial", "service"):   # lists that may be empty, but must be there
            if not isinstance(self.profile.get(key), list):
                fail(f"data/things_done/profile.yaml has no {key} list; re-run scripts/sync_things_done.py")
        self.lag_pairs: list[Record] = _records("preprint_lag", "pairs")   # the sync keeps pairs with a gap only
        self.lag_summary: Record = load(LEDGER_DATA / "preprint_lag.yaml").get("summary") or fail(
            "data/things_done/preprint_lag.yaml has no summary; update things_done and re-sync")
        self.metrics: Record = load(LEDGER_DATA / "metrics.yaml")
        for key in ("citation_count", "h_index", "fetched_at", "scholar_url"):
            if key not in self.metrics:
                fail(f"data/things_done/metrics.yaml has no {key}")
        self.by_doi: dict[str, Record] = {p["doi"].lower(): p for p in self.pubs}
        # Journal publication dates from the lag report, cut to what is known
        # ("2021-09-14" or "2021-09"; text.known_date). A year alone adds
        # nothing to the publication's year, so those papers are undated.
        self.dates: dict[str, str] = {
            str(p["published_doi"]).lower(): known_date(p["published_date"], p["published_date_precision"])
            for p in self.lag_pairs if p["published_date_precision"] != "year"}

    def get(self, doi: str) -> Record | None:
        """Publication by DOI (case-insensitive), or None."""
        return self.by_doi.get(str(doi).lower())

    def require(self, doi: str, where: str) -> Record:
        """Publication by DOI; the build stops if it is not in the ledger."""
        rec = self.get(doi)
        if not rec:
            fail(f"{where}: DOI {doi} is not in the things_done ledger")
        return rec

    def related(self, rec: Record) -> list[Record]:
        """The other versions of a paper (preprint <-> journal) in the ledger."""
        return [r for r in (self.get(d) for d in rec.get("related_dois") or []) if r]

    def published_version(self, rec: Record) -> Record:
        """For a preprint, its journal version when the ledger links one; else rec."""
        if rec.get("status") == "published":
            return rec
        for other in self.related(rec):
            if other.get("status") in ("published", "in_press"):
                return other
        return rec

    def preprint_of(self, rec: Record) -> Record | None:
        """The preprint of a journal paper, when the ledger links one."""
        return next((r for r in self.related(rec) if r.get("status") == "preprint"), None)

    def family_dois(self, doi: str) -> set[str]:
        """Lower-case DOIs of a paper and all its versions."""
        rec = self.require(doi, "ledger")
        return {doi.lower(), self.published_version(rec)["doi"].lower()} | {
            r["doi"].lower() for r in self.related(rec)}

    def grouped(self) -> list[Record]:
        """Publications, each preprint folded into its journal version unless
        things_done marks it `standalone` (display override). Newest first:
        by year, then the journal date as far as it is known (a month comes
        after the days in it; undated papers come last in their year), then
        ledger order."""
        shown = [r for r in self.pubs
                 if not (r.get("status") == "preprint" and not r.get("standalone")
                         and self.published_version(r) is not r)]
        date = {id(r): self.dates.get(r["doi"].lower()) for r in shown}
        shown.sort(key=lambda r: date[id(r)] or "", reverse=True)         # stable: ties keep ledger order
        shown.sort(key=lambda r: (-int(r["year"]), date[id(r)] is None))
        return shown


def software_list(ledger: Ledger) -> list[Record]:
    """Software projects: things_done (title, year, code link, description,
    papers) merged with data/software.yaml (picture, colour, extra links, and
    optional overrides). An entry in data/software.yaml without an `id` is a
    website-only project; an entry whose `id` is not in the ledger is an error.
    Newest first; within a year, in the order of data/software.yaml."""
    presentation = load(DATA / "software.yaml") or []
    by_id = {s["id"]: (i, s) for i, s in enumerate(presentation) if s.get("id")}
    unknown = set(by_id) - {r["id"] for r in ledger.software}
    if unknown:
        fail(f"data/software.yaml: ids not in the things_done software registry: {sorted(unknown)}")
    out = []
    for rec in ledger.software:
        pos, extra = by_id.get(rec["id"], (999, {}))
        s = dict(extra)
        s.setdefault("title", rec["title"])
        s["year"] = s.get("year") or year_of(rec["start_date"])      # start_date, github_repo_url and
        s.setdefault("github", rec["github_repo_url"])                 # description are required in
        s.setdefault("text", rec["description"])                       # the things_done registry
        s.setdefault("dois", rec.get("related_publication_dois") or [])
        s["id"], s["_pos"] = rec["id"], pos
        out.append(s)
    for pos, s in enumerate(presentation):
        if not s.get("id"):
            out.append({"dois": [], **s, "_pos": pos})
    out.sort(key=lambda s: (-(s.get("year") or 0), s["_pos"], s["title"].casefold()))
    return out


def _presentation(section: str, entries: list[Record], key: str, current: set[str], source: str) -> list[Record]:
    """The data/site.yaml `section` entries (logo and link) for what things_done
    says is current, matched by `key`, in site.yaml order. A current item
    without an entry, or an entry without name, url and logo (null for
    text only), stops the build. An entry for something no longer current
    (a grant or affiliation that ended since the last edit) is left out with
    a warning, so the site does not break on the day something ends."""
    listed = [e.get(key) for e in entries]
    missing = sorted(current - set(listed))
    if missing:
        fail(f"data/site.yaml {section}: add an entry ({key}, name, url, logo) for {missing} (current in {source})")
    for e in entries:
        absent = [k for k in (key, "name", "url", "logo") if k not in e]
        if absent:
            fail(f"data/site.yaml {section}: entry {e.get(key)!r} has no {absent}")
    for e in entries:
        if e[key] not in current:
            print(f"warning: data/site.yaml {section}: {e[key]!r} is no longer current in {source}; "
                  "it is not shown, remove it")
    return [e for e in entries if e[key] in current]


def affiliation_list(presentation: list[Record], ledger: Ledger) -> list[Record]:
    """Guillaume's current affiliations (things_done, current as of the sync)
    with their logo and link from data/site.yaml `affiliations` (matched by
    ledger `id`), in the order of data/site.yaml; see _presentation()."""
    current = {a["id"]: a for a in ledger.affiliations}
    shown = _presentation("affiliations", presentation, "id", set(current),
                          "things_done ledger/profile/affiliations.yaml")
    bad = [a["id"] for a in shown if a.get("relation") not in AFFILIATION_RELATIONS]
    if bad:
        fail(f"data/site.yaml affiliations {bad}: relation must be one of {AFFILIATION_RELATIONS}")
    return [{**current[a["id"]], **a} for a in shown]


AFFILIATION_RELATIONS = ("parent", "member", "leader")


def support_list(funders: list[Record], programmes: list[Record], ledger: Ledger) -> list[Record]:
    """Current research support for the home page, grouped by meaning
    (website#27), from the grants things_done marks `current`:

    - a funder (logo and link from data/site.yaml `funding`), with, beneath
      it, the programmes it alone funds (e.g. the Research Council of
      Finland -> Centre of Excellence IMMENs);
    - a programme with several direct funders (e.g. EOSS Cycle 6: Wellcome
      and the Chan Zuckerberg Initiative) as one group with their logos and
      the programme's co-funders (ledger `program_cofunders`) named in text.
      A funder whose only current grants are such awards has no tile of its
      own, so an award is never shown twice.

    Programmes are matched by the ledger `program` (data/site.yaml
    `programmes`: program, name, url, logo). Strict like _presentation():
    a current funder or programme without an entry stops the build; an
    entry that is no longer current is left out with a warning."""
    current = [g for g in ledger.grants if g["current"]]
    by_funder = {f["funder"]: f for f in _presentation(
        "funding", funders, "funder", {n for g in current for n in g["funders"]},
        "things_done ledger/registries/grants.yaml")}
    by_programme = {p["program"]: p for p in _presentation(
        "programmes", programmes, "program", {g["program"] for g in current if g.get("program")},
        "things_done ledger/registries/grants.yaml (`program`)")}
    shared = [g for g in current if len(g["funders"]) > 1]
    groups: list[Record] = []
    for f in funders:                                  # data/site.yaml order
        if f["funder"] not in by_funder:
            continue
        own = [g for g in current if g["funders"] == [f["funder"]]]
        if not own:                                    # only in shared awards: shown with them
            continue
        subs = [by_programme[p] for p in dict.fromkeys(g["program"] for g in own if g.get("program"))]
        groups.append({"logos": [f], "programmes": subs, "title": None, "cofunders": []})
    for p in programmes:
        grants = [g for g in shared if g.get("program") == p["program"]]
        if p["program"] not in by_programme or not grants:
            continue
        logos = [by_funder[n] for n in dict.fromkeys(n for g in grants for n in g["funders"])]
        cofunders = list(dict.fromkeys(c for g in grants for c in g.get("program_cofunders") or []))
        groups.append({"logos": logos, "programmes": [], "title": p, "cofunders": cofunders})
    unplaced = [g["title"] for g in shared if not g.get("program")]
    if unplaced:
        fail(f"things_done grants {unplaced} have several funders but no `program`; "
             "the home page groups a joint award by its programme")
    return groups
