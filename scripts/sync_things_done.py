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
  report/generated/publications/
    preprint_publication_crosswalk.json  (pairs)         related_dois in publications.yaml
    preprint_lag.json                                    preprint_lag.yaml
    coauthor_network.json (nodes) + coauthor_countries   coauthors.yaml
  .cache/scholar_metrics.json                            metrics.yaml

Only fields that are already public are copied (title, authors, venue, DOI,
abstract, links, whether Guillaume is corresponding author, descriptions,
co-author countries). Supervision, roles, notes and conflict-of-interest
data are never read.
"""

import argparse
import html
import json
import re
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


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def load_json(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def clean_text(value):
    """Crossref abstracts come with JATS tags (<jats:p>...); keep plain text."""
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    value = html.unescape(value)
    value = re.sub(r"^\s*(Abstract|Summary)\b[:.]?\s*", "", value, flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def pick(record, fields):
    return {k: record[k] for k in fields if record.get(k) not in (None, "", [])}


def dump(name, data, source):
    OUT.mkdir(parents=True, exist_ok=True)
    header = (f"# Copied by scripts/sync_things_done.py from things_done/{source}.\n"
              "# Do not edit by hand: change things_done instead, the website updates itself.\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    (OUT / f"{name}.yaml").write_text(header + body, encoding="utf-8")


def publications(ledger):
    records = []
    for path in sorted((ledger / "ledger" / "publications").glob("[0-9]*.yaml")):
        for rec in load(path).get("records") or []:
            if not rec.get("doi") or not rec.get("title"):
                continue
            item = pick(rec, PUBLICATION_FIELDS)
            item["title"] = clean_text(item["title"])
            if "abstract" in item:
                item["abstract"] = clean_text(item["abstract"])
            if (rec.get("me") or {}).get("corresponding_author"):
                item["corresponding"] = True   # Guillaume is (co-)corresponding author
            records.append(item)

    # Preprint <-> journal pairs, as matched by the ledger's crosswalk report
    crosswalk = load_json(ledger / REPORTS / "preprint_publication_crosswalk.json") or {}
    by_doi = {r["doi"].lower(): r for r in records}
    pairs = 0
    for match in crosswalk.get("matched_pairs") or []:
        ev = match.get("evidence") or {}
        a = by_doi.get(str(ev.get("preprint_doi")).lower())
        b = by_doi.get(str(ev.get("published_doi")).lower())
        if not (a and b):
            continue
        pairs += 1
        for x, y in ((a, b), (b, a)):
            links = x.setdefault("related_dois", [])
            if y["doi"].lower() not in {str(d).lower() for d in links}:
                links.append(y["doi"])
    records.sort(key=lambda r: (-int(r.get("year") or 0), r["title"].casefold()))
    dump("publications", {"records": records}, "ledger/publications")
    print(f"publications: {len(records)} records, {pairs} preprint/journal pairs")


def registry(ledger, name, fields):
    data = load(ledger / "ledger" / "registries" / f"{name}.yaml")
    out = [pick(r, fields) for r in data.get("records") or [] if r.get("title")]
    out.sort(key=lambda r: (-int(str(r.get("start_date") or "0")[:4] or 0), r["title"].casefold()))
    dump(name, {"records": out}, f"ledger/registries/{name}.yaml")
    print(f"{name}: {len(out)} records")


def lab_members(ledger):
    """The public roster: name, website role, group, start/end dates."""
    path = ledger / "ledger" / "profile" / "lab_members.yaml"
    if not path.exists():
        return
    fields = ("name", "role", "group", "start_date", "end_date", "also_known_as")
    records = [pick(r, fields) for r in load(path).get("records") or [] if r.get("name")]
    dump("lab_members", {"records": records}, "ledger/profile/lab_members.yaml")
    print(f"lab members: {sum(1 for r in records if not r.get('end_date'))} current, "
          f"{sum(1 for r in records if r.get('end_date'))} alumni")


def preprint_lag(ledger):
    data = load_json(ledger / REPORTS / "preprint_lag.json")
    if not data:
        print("preprint lag: not in things_done yet (run 'Analyze Preprint-to-Publication Lag' there)")
        return
    pairs = [pick(p, LAG_FIELDS) for p in data.get("pairs") or [] if "gap_days" in p]
    dump("preprint_lag", {"generated_at": data.get("generated_at"), "pairs": pairs},
         f"{REPORTS}/preprint_lag.json")
    print(f"preprint lag: {len(pairs)} pairs")


def coauthors(ledger):
    network = load_json(ledger / REPORTS / "coauthor_network.json")
    if not network:
        return
    countries = load_json(ledger / REPORTS / "coauthor_countries.json") or {}
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


def metrics(ledger):
    data = load_json(ledger / ".cache" / "scholar_metrics.json")
    if not data:
        return
    keep = {k: data[k] for k in ("citation_count", "h_index", "i10_index", "fetched_at", "scholar_url") if k in data}
    dump("metrics", keep, ".cache/scholar_metrics.json")
    print(f"metrics: {keep.get('citation_count')} citations, h-index {keep.get('h_index')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", required=True, type=Path, help="path to a things_done checkout")
    ledger = parser.parse_args().ledger.resolve()
    if not (ledger / "ledger").is_dir():
        raise SystemExit(f"{ledger} does not look like a things_done checkout (no ledger/ folder)")
    for old in ("dates.yaml", "authors.yaml"):  # computed by an earlier version of this script
        (OUT / old).unlink(missing_ok=True)
    publications(ledger)
    registry(ledger, "software", SOFTWARE_FIELDS)
    registry(ledger, "datasets", DATASET_FIELDS)
    lab_members(ledger)
    preprint_lag(ledger)
    coauthors(ledger)
    metrics(ledger)


if __name__ == "__main__":
    main()
