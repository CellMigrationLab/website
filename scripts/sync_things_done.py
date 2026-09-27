"""Copy the public part of the things_done ledger into data/things_done/.

    python scripts/sync_things_done.py --ledger ../things_done

things_done is the single source of truth: this script only copies (and
leaves out private fields). It computes nothing and needs no network, so
there is one place to maintain. things_done runs it after every update
(.github/workflows/update_website.yml there).

Reads (in the things_done checkout)                    Writes (data/things_done/)
  ledger/publications/<year>.yaml                        publications.yaml
  ledger/registries/software.yaml                        software.yaml
  ledger/registries/datasets.yaml                        datasets.yaml
  ledger/profile/lab_members.yaml                        lab_members.yaml
  ledger/profile/affiliations.yaml  (current ones)       affiliations.yaml
  report/generated/publications/
    preprint_publication_crosswalk.json  (pairs)         related_dois in publications.yaml
    preprint_lag.json                                    preprint_lag.yaml
    coauthor_network.json (nodes) + coauthor_countries   coauthors.yaml
  .cache/scholar_metrics.json                            metrics.yaml

Only fields that are already public are copied (title, authors, venue, DOI,
abstract, links, whether Guillaume is corresponding author, descriptions,
co-author countries, the public lab roster: names, roles in the lab and
current/alumni, and Guillaume's current affiliations). Supervision records, notes and conflict-of-interest data are
never read. Every input is required: a missing file stops the sync rather
than leaving part of the website stale without anyone noticing.
"""

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "things_done"
REPORTS = Path("report") / "generated" / "publications"

PUBLICATION_FIELDS = (
    "doi", "year", "type", "status", "title", "authors", "venue",
    "abstract", "peer_reviewed", "open_access_status", "related_dois",
)
SOFTWARE_FIELDS = (
    "id", "title", "status", "start_date", "repository_url", "github_repo_url",
    "description", "related_publication_dois",
)
DATASET_FIELDS = (
    "id", "title", "status", "dataset_type", "start_date", "repository_url",
    "archive_doi", "description", "dataset_tags", "related_publication_dois",
)
LAG_FIELDS = (
    "preprint_doi", "published_doi", "published_title", "preprint_date",
    "preprint_date_precision", "published_date", "published_date_precision", "gap_days",
)


def require(path: Path) -> Path:
    """The path, or stop: every input of the sync is required."""
    if not path.is_file():
        raise SystemExit(f"sync_things_done: missing {path} (is the things_done checkout complete?)")
    return path


def load(path: Path) -> dict:
    """Parse a YAML file that must exist."""
    return yaml.safe_load(require(path).read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    """Parse a JSON file that must exist."""
    return json.loads(require(path).read_text(encoding="utf-8"))


def clean_text(value: object) -> str:
    """Crossref abstracts come with JATS tags (<jats:p>...); keep plain text."""
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    value = html.unescape(value)
    value = re.sub(r"^\s*(Abstract|Summary)\b[:.]?\s*", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def pick(record: dict, fields: tuple[str, ...]) -> dict:
    """The listed fields of a record, leaving out empty ones."""
    return {k: record[k] for k in fields if record.get(k) not in (None, "", [])}


def dump(name: str, data: dict, source: str) -> None:
    """Write data/things_done/<name>.yaml with a do-not-edit header."""
    OUT.mkdir(parents=True, exist_ok=True)
    header = (f"# Copied by scripts/sync_things_done.py from things_done/{source}.\n"
              "# Do not edit by hand: change things_done instead, the website updates itself.\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    (OUT / f"{name}.yaml").write_text(header + body, encoding="utf-8")


def publications(ledger: Path) -> None:
    """Publications, with preprint <-> journal links from the crosswalk report."""
    pub_dir = ledger / "ledger" / "publications"
    overrides = load(pub_dir / "display_overrides.yaml").get("overrides") or {}
    records, skipped = [], []
    for path in sorted(pub_dir.glob("[0-9]*.yaml")):
        for rec in load(path).get("records") or []:
            if not rec.get("doi") or not rec.get("title"):
                skipped.append(rec.get("title") or rec.get("doi") or "?")
                continue
            item = pick(rec, PUBLICATION_FIELDS)
            if (overrides.get(rec["doi"]) or {}).get("force_preprint_bucket"):
                item["standalone"] = True   # listed on its own even when a journal version exists
            item["title"] = clean_text(item["title"])
            if "abstract" in item:
                item["abstract"] = clean_text(item["abstract"])
            if (rec.get("me") or {}).get("corresponding_author"):
                item["corresponding"] = True   # Guillaume is (co-)corresponding author
            records.append(item)

    # Preprint <-> journal pairs, as matched by the ledger's crosswalk report
    crosswalk = load_json(ledger / REPORTS / "preprint_publication_crosswalk.json")
    by_doi = {r["doi"].lower(): r for r in records}
    pairs, unmatched = 0, []
    for match in crosswalk.get("matched_pairs") or []:
        ev = match.get("evidence") or {}
        a = by_doi.get(str(ev.get("preprint_doi")).lower())
        b = by_doi.get(str(ev.get("published_doi")).lower())
        if not (a and b):
            unmatched.append(f"{ev.get('preprint_doi')} -> {ev.get('published_doi')}")
            continue
        pairs += 1
        for x, y in ((a, b), (b, a)):
            links = x.setdefault("related_dois", [])
            if y["doi"].lower() not in {str(d).lower() for d in links}:
                links.append(y["doi"])
    records.sort(key=lambda r: (-int(r.get("year") or 0), r["title"].casefold()))
    dump("publications", {"records": records}, "ledger/publications")
    print(f"publications: {len(records)} records, {pairs} preprint/journal pairs")
    for title in skipped:
        print(f"  left out (no DOI or title): {title}")
    for pair in unmatched:
        print(f"  crosswalk pair not in the ledger, left out: {pair}")


def registry(ledger: Path, name: str, fields: tuple[str, ...]) -> None:
    """A registry (software or datasets), newest first."""
    data = load(ledger / "ledger" / "registries" / f"{name}.yaml")
    out = [pick(r, fields) for r in data.get("records") or []]
    out.sort(key=lambda r: (-int(str(r.get("start_date") or "0")[:4] or 0), r["title"].casefold()))
    dump(name, {"records": out}, f"ledger/registries/{name}.yaml")
    print(f"{name}: {len(out)} records")


def lab_members(ledger: Path) -> None:
    """The public roster: name, current/last role, earlier roles, group, status."""
    path = ledger / "ledger" / "profile" / "lab_members.yaml"
    fields = ("name", "role", "previous_roles", "group", "status", "also_known_as")
    records = [pick(r, fields) for r in load(path).get("records") or []]
    dump("lab_members", {"records": records}, "ledger/profile/lab_members.yaml")
    print(f"lab members: {sum(1 for r in records if r.get('status') != 'alumni')} current, "
          f"{sum(1 for r in records if r.get('status') == 'alumni')} alumni")


def affiliations(ledger: Path, today: str) -> None:
    """Guillaume's current affiliations: no end date, or one not yet passed."""
    path = ledger / "ledger" / "profile" / "affiliations.yaml"
    records = [pick(r, ("id", "organization", "title")) for r in load(path).get("records") or []
               if str(r.get("end_date") or "9999") >= today]
    dump("affiliations", {"records": records}, "ledger/profile/affiliations.yaml (current)")
    print(f"affiliations: {len(records)} current")


def preprint_lag(ledger: Path) -> None:
    """Resolved preprint/journal pairs and things_done's summary (median etc.)."""
    data = load_json(ledger / REPORTS / "preprint_lag.json")
    if not data.get("summary"):
        raise SystemExit("sync_things_done: preprint_lag.json has no summary; "
                         "re-run 'Analyze Preprint-to-Publication Lag' in things_done")
    pairs = [pick(p, LAG_FIELDS) for p in data.get("pairs") or [] if "gap_days" in p]
    dump("preprint_lag", {"generated_at": data["generated_at"], "summary": data["summary"], "pairs": pairs},
         f"{REPORTS}/preprint_lag.json")
    print(f"preprint lag: {len(pairs)} pairs, median {data['summary']['median_months']} months")


def coauthors(ledger: Path) -> None:
    """Co-authors (joint papers, first/last year) with their country."""
    network = load_json(ledger / REPORTS / "coauthor_network.json")
    countries = load_json(ledger / REPORTS / "coauthor_countries.json")
    country = {c["name"]: c["country"] for c in countries.get("coauthors") or []}
    nodes = []
    for n in network.get("nodes") or []:
        if n.get("is_self"):
            continue
        item = {"name": n["id"], "papers": n.get("total", 0),
                "first_year": n.get("first_year"), "last_year": n.get("last_year")}
        if country.get(n["id"]):
            item["country"] = country[n["id"]]
        nodes.append(item)
    nodes.sort(key=lambda n: (-n["papers"], n["name"]))
    dump("coauthors", {"generated_at": network.get("generated_at"), "coauthors": nodes},
         f"{REPORTS}/coauthor_network.json + coauthor_countries.json")
    print(f"coauthors: {len(nodes)} ({sum(1 for n in nodes if 'country' in n)} with a country)")


def metrics(ledger: Path) -> None:
    """Citation count and h-index (Google Scholar, fetched by things_done)."""
    data = load_json(ledger / ".cache" / "scholar_metrics.json")
    keep = {k: data[k] for k in ("citation_count", "h_index", "i10_index", "fetched_at", "scholar_url") if k in data}
    dump("metrics", keep, ".cache/scholar_metrics.json")
    print(f"metrics: {keep.get('citation_count')} citations, h-index {keep.get('h_index')}")


def main() -> None:
    """Copy everything; see the module docstring."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, type=Path, help="path to a things_done checkout")
    ledger = parser.parse_args().ledger.resolve()
    if not (ledger / "ledger").is_dir():
        raise SystemExit(f"{ledger} does not look like a things_done checkout (no ledger/ folder)")
    publications(ledger)
    registry(ledger, "software", SOFTWARE_FIELDS)
    registry(ledger, "datasets", DATASET_FIELDS)
    lab_members(ledger)
    affiliations(ledger, date.today().isoformat())
    preprint_lag(ledger)
    coauthors(ledger)
    metrics(ledger)


if __name__ == "__main__":
    main()
