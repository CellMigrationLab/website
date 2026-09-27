"""things_done data, as copied to data/things_done/ by scripts/sync_things_done.py.

Every file there is required: a missing or empty one stops the build instead
of silently leaving a section out of the site.
"""

from typing import Any

from .config import DATA, LEDGER_DATA, fail, load
from .text import year_of

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
        self.software: list[Record] = _records("software")
        self.datasets: list[Record] = _records("datasets")
        self.coauthors: list[Record] = _records("coauthors", "coauthors")
        self.affiliations: list[Record] = _records("affiliations")
        self.talks: list[Record] = _records("talks")
        self.teaching: list[Record] = _records("teaching")
        self.grants: list[Record] = _records("grants")
        self.events: list[Record] = _records("conference_organization")
        self.profile: Record = load(LEDGER_DATA / "profile.yaml")
        for key in ("name", "title", "short_bio", "appointments", "education"):
            if not self.profile.get(key):
                fail(f"data/things_done/profile.yaml has no {key}; re-run scripts/sync_things_done.py")
        lag = load(LEDGER_DATA / "preprint_lag.yaml")
        self.lag_pairs: list[Record] = [p for p in lag.get("pairs") or [] if "gap_days" in p]
        self.lag_summary: Record = lag.get("summary") or fail(
            "data/things_done/preprint_lag.yaml has no summary; update things_done and re-sync")
        self.metrics: Record = load(LEDGER_DATA / "metrics.yaml")
        for key in ("citation_count", "h_index", "fetched_at", "scholar_url"):
            if key not in self.metrics:
                fail(f"data/things_done/metrics.yaml has no {key}")
        self.by_doi: dict[str, Record] = {p["doi"].lower(): p for p in self.pubs}
        # Journal publication dates known to the day (from the lag report).
        self.dates: dict[str, str] = {
            str(p["published_doi"]).lower(): p["published_date"]
            for p in self.lag_pairs if p.get("published_date_precision") == "day"}

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
        """Publications (newest first), each preprint folded into its journal
        version, unless things_done marks it `standalone` (display override)."""
        return [r for r in self.pubs
                if not (r.get("status") == "preprint" and not r.get("standalone")
                        and self.published_version(r) is not r)]


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
        s["year"] = s.get("year") or year_of(rec.get("start_date"))
        s.setdefault("github", rec.get("github_repo_url") or rec.get("repository_url"))
        s.setdefault("text", rec.get("description"))
        s.setdefault("dois", rec.get("related_publication_dois") or [])
        s["id"], s["_pos"] = rec["id"], pos
        out.append(s)
    for pos, s in enumerate(presentation):
        if not s.get("id"):
            out.append({"dois": [], **s, "_pos": pos})
    out.sort(key=lambda s: (-(s.get("year") or 0), s["_pos"], s["title"].casefold()))
    return out


def affiliation_list(presentation: list[Record], ledger: Ledger) -> list[Record]:
    """Guillaume's current affiliations (things_done) with their logo and link
    from data/site.yaml `affiliations` (matched by ledger `id`), in the order
    of data/site.yaml. Strict both ways: a current affiliation without a logo
    entry, or an entry for an affiliation that is not current, stops the build."""
    current = {a["id"]: a for a in ledger.affiliations}
    listed = [a.get("id") for a in presentation]
    missing = sorted(set(current) - set(listed))
    stale = sorted({str(i) for i in listed} - set(current))
    if missing:
        fail(f"data/site.yaml affiliations: add an entry (id, name, url, logo) for {missing} "
             "(current in things_done ledger/profile/affiliations.yaml)")
    if stale:
        fail(f"data/site.yaml affiliations: {stale} are not current affiliations in things_done; "
             "remove them or fix the id")
    return [{**current[a["id"]], **a} for a in presentation]


CURRENT_GRANT = ("active", "awarded")


def funding_list(presentation: list[Record], ledger: Ledger, today: str) -> list[Record]:
    """Funders of the current grants in things_done (status active or awarded,
    not ended), with their logo and link from data/site.yaml `funding` (matched
    by the ledger `funder` name), in the order of data/site.yaml. Strict both
    ways, like affiliation_list()."""
    current = {g["funder"] for g in ledger.grants
               if g.get("status") in CURRENT_GRANT and str(g.get("end_date") or "9999") >= today}
    listed = [f.get("funder") for f in presentation]
    missing = sorted(current - set(listed))
    stale = sorted({str(f) for f in listed} - current)
    if missing:
        fail(f"data/site.yaml funding: add an entry (funder, name, url, logo) for {missing} "
             "(funders of current grants in things_done ledger/registries/grants.yaml)")
    if stale:
        fail(f"data/site.yaml funding: {stale} fund no current grant in things_done; remove them or fix the name")
    return presentation
