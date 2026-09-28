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
  ledger/profile/person.yaml, education.yaml,            profile.yaml
    ledger/roles/*.yaml  (current roles)
  ledger/activities/*/talks.yaml                         talks.yaml
  ledger/registries/grants.yaml  (no amounts; `current`)  grants.yaml
  report/generated/publications/
    preprint_publication_crosswalk.json  (pairs)         related_dois in publications.yaml
    preprint_lag.json                                    preprint_lag.yaml
    coauthor_network.json (nodes) + coauthor_countries   coauthors.yaml
  .cache/scholar_metrics.json                            metrics.yaml

Only fields that are already public are copied (title, authors, venue, DOI,
abstract, links, whether Guillaume is corresponding author, descriptions,
co-author countries, the public lab roster: names, roles in the lab and
current/alumni, Guillaume's current affiliations, roles and education, talks,
and grant titles, funder names, programmes and dates
without amounts). Records marked `confidentiality: internal` or
`confidential` are never copied. Supervision records, teaching, notes and
conflict-of-interest data are never read. Every input is required: a
missing file or field stops the sync rather than leaving part of the website
stale without anyone noticing. "Current" (affiliations, roles, grants) is
decided here, on the day of the sync, so the website build does not depend on
its own date. Files in data/things_done/ that the sync no longer writes are
removed.
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
    "doi", "year", "publication_date", "status", "title", "authors", "venue",
    "abstract", "peer_reviewed", "open_access_status", "related_dois",
)
SOFTWARE_FIELDS = (
    "id", "title", "start_date", "github_repo_url", "description", "summary", "related_publication_dois",
)
DATASET_FIELDS = (
    "title", "dataset_type", "start_date", "repository_url",
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


NO_ABSTRACT = "Abstract unavailable from Crossref"   # things_done placeholder for "none found yet"
INLINE_TAGS = r"</?(?:jats:)?(?:i|b|em|strong|italic|bold|sup|sub|sc|u)\b[^>]*>"


def clean_text(value: str, abstract: bool = False) -> str:
    """Crossref titles and abstracts come with JATS tags (<jats:p>, <jats:italic>
    ...); keep plain text. Inline tags go without a space ("<i>in vitro</i>,"
    -> "in vitro,"), block tags become a space. Abstracts also lose a leading
    "Abstract"/"Summary" heading."""
    value = re.sub(INLINE_TAGS, "", value, flags=re.I)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    if abstract:
        value = re.sub(r"^\s*(Abstract|Summary)\b[:.]?\s*", "", value, flags=re.I)
    value = re.sub(r"\s+([,.;:)])", r"\1", value)   # no space before punctuation left by a removed tag
    return re.sub(r"\s+", " ", value).strip()


PUBLIC = (None, "public")   # ledger `confidentiality`: absent or public may be copied


def public_records(path: Path) -> list[dict]:
    """The records of a ledger file that may be published: those marked
    `confidentiality: internal` or `confidential` are never copied."""
    return [r for r in load(path)["records"] if r.get("confidentiality") in PUBLIC]


def pick(record: dict, fields: tuple[str, ...]) -> dict:
    """The listed fields of a record, leaving out empty ones."""
    return {k: record[k] for k in fields if record.get(k) not in (None, "", [])}


WRITTEN: set[str] = set()


def dump(name: str, data: dict, source: str) -> None:
    """Write data/things_done/<name>.yaml with a do-not-edit header."""
    OUT.mkdir(parents=True, exist_ok=True)
    WRITTEN.add(f"{name}.yaml")
    header = (f"# Copied by scripts/sync_things_done.py from things_done/{source}.\n"
              "# Do not edit by hand: change things_done instead, the website updates itself.\n")
    body = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)
    (OUT / f"{name}.yaml").write_text(header + body, encoding="utf-8")


def publications(ledger: Path) -> None:
    """Publications, with preprint <-> journal links from the crosswalk report."""
    pub_dir = ledger / "ledger" / "publications"
    overrides = load(pub_dir / "display_overrides.yaml").get("overrides") or {}
    records = []
    for path in sorted(pub_dir.glob("[0-9]*.yaml")):
        for rec in public_records(path):   # doi and title are required by the ledger schema
            item = pick(rec, PUBLICATION_FIELDS)
            if (overrides.get(rec["doi"]) or {}).get("force_preprint_bucket"):
                item["standalone"] = True   # listed on its own even when a journal version exists
            item["title"] = clean_text(item["title"])
            if item["abstract"].strip() == NO_ABSTRACT:
                del item["abstract"]   # things_done's placeholder (tools/fetch_missing_abstracts.py fills it later)
            else:
                item["abstract"] = clean_text(item["abstract"], abstract=True)
            if (rec.get("me") or {}).get("corresponding_author"):
                item["corresponding"] = True   # Guillaume is (co-)corresponding author
            records.append(item)

    # Preprint <-> journal pairs, as matched by the ledger's crosswalk report
    crosswalk = load_json(ledger / REPORTS / "preprint_publication_crosswalk.json")
    by_doi = {r["doi"].lower(): r for r in records}
    pairs = 0
    for match in crosswalk["matched_pairs"]:
        ev = match["evidence"]
        a = by_doi.get(str(ev["preprint_doi"]).lower())
        b = by_doi.get(str(ev["published_doi"]).lower())
        if not (a and b):
            raise SystemExit(f"sync_things_done: crosswalk pair {ev['preprint_doi']} -> {ev['published_doi']} is not "
                             "in ledger/publications; re-run 'Ledger Cleanup and Preprint Links' in things_done")
        pairs += 1
        for x, y in ((a, b), (b, a)):
            links = x.setdefault("related_dois", [])
            if y["doi"].lower() not in {str(d).lower() for d in links}:
                links.append(y["doi"])
    records.sort(key=lambda r: (-int(r.get("year") or 0), r["title"].casefold()))
    dump("publications", {"records": records}, "ledger/publications")
    print(f"publications: {len(records)} records, {pairs} preprint/journal pairs")


def registry(ledger: Path, name: str, fields: tuple[str, ...]) -> None:
    """A registry (software or datasets), newest first."""
    out = [pick(r, fields) for r in public_records(ledger / "ledger" / "registries" / f"{name}.yaml")]
    out.sort(key=lambda r: (-int(str(r.get("start_date") or "0")[:4] or 0), r["title"].casefold()))
    dump(name, {"records": out}, f"ledger/registries/{name}.yaml")
    print(f"{name}: {len(out)} records")


def lab_members(ledger: Path) -> None:
    """The public roster: stable id (the website's join key), name, current/last
    role, earlier roles, group, status."""
    path = ledger / "ledger" / "profile" / "lab_members.yaml"
    fields = ("id", "name", "role", "previous_roles", "group", "status", "also_known_as")
    records = [pick(r, fields) for r in public_records(path)]
    dump("lab_members", {"records": records}, "ledger/profile/lab_members.yaml")
    print(f"lab members: {sum(1 for r in records if r.get('status') != 'alumni')} current, "
          f"{sum(1 for r in records if r.get('status') == 'alumni')} alumni")


def affiliations(ledger: Path, today: str) -> None:
    """Guillaume's current affiliations: no end date, or one not yet passed."""
    path = ledger / "ledger" / "profile" / "affiliations.yaml"
    records = [pick(r, ("id", "organization", "title")) for r in public_records(path) if not ended(r, today)]
    dump("affiliations", {"records": records}, "ledger/profile/affiliations.yaml (current)")
    print(f"affiliations: {len(records)} current")


def ended(record: dict, today: str) -> bool:
    """Whether a record's (optional) end date has passed."""
    return "end_date" in record and str(record["end_date"]) < today


def current(records: list[dict], today: str) -> list[dict]:
    """Roles that are current: ledger status `current` and not ended."""
    return [r for r in records if r["status"] == "current" and not ended(r, today)]


def profile(ledger: Path, today: str) -> None:
    """Guillaume's public profile: title, short bio (Markdown; paragraphs kept,
    lines within a paragraph joined), current appointments, editorial and
    service roles, and education."""
    person = load(ledger / "ledger" / "profile" / "person.yaml")
    roles = ledger / "ledger" / "roles"
    role_fields = ("title", "organization", "start_date")
    data = {
        "name": person["preferred_name"],
        "title": person["primary_title"],
        "short_bio": "\n\n".join(" ".join(para.split()) for para in person["short_bio"].split("\n\n")),
        "appointments": [pick(r, role_fields) for r in current(public_records(roles / "appointments.yaml"), today)],
        "editorial": [pick(r, role_fields) for r in current(public_records(roles / "editorial_roles.yaml"), today)],
        "service": [pick(r, role_fields) for r in current(public_records(roles / "service_and_leadership.yaml"), today)],
        "education": [pick(r, ("degree", "organization", "end_date"))
                      for r in public_records(ledger / "ledger" / "profile" / "education.yaml")],
    }
    dump("profile", data, "ledger/profile/person.yaml, education.yaml and ledger/roles/ (current)")
    print(f"profile: {len(data['appointments'])} appointments, {len(data['editorial'])} editorial, "
          f"{len(data['service'])} service roles, {len(data['education'])} education")


def activities(ledger: Path, kind: str, fields: tuple[str, ...]) -> None:
    """All records of ledger/activities/<year>/<kind>.yaml, newest first."""
    records = [pick(r, fields) for path in sorted((ledger / "ledger" / "activities").glob(f"*/{kind}.yaml"))
               for r in public_records(path)]
    records.sort(key=lambda r: str(r.get("date") or r.get("start_date") or ""), reverse=True)
    dump(kind, {"records": records}, f"ledger/activities/*/{kind}.yaml")
    print(f"{kind}: {len(records)} records")


CURRENT_GRANT = ("active", "awarded")


def grants(ledger: Path, today: str) -> None:
    """Public grant metadata: title, direct funder names, programme and
    programme co-funders (for website#27), status, dates, and `current`
    (active or awarded, not ended; decided here so the website does not
    depend on the build date). Amounts, award ids and descriptions (which
    hold internal order numbers) are never copied."""
    fields = ("title", "program", "program_cofunders", "status", "start_date", "end_date")
    records = []
    for r in public_records(ledger / "ledger" / "registries" / "grants.yaml"):
        item = pick(r, fields)
        item["funders"] = [f["name"] for f in r["funders"]]
        item["current"] = r["status"] in CURRENT_GRANT and not ended(r, today)
        records.append(item)
    dump("grants", {"records": records}, "ledger/registries/grants.yaml (no amounts)")
    print(f"grants: {len(records)} records")


def preprint_lag(ledger: Path) -> None:
    """Resolved preprint/journal pairs and things_done's summary (median etc.)."""
    data = load_json(ledger / REPORTS / "preprint_lag.json")
    if not data.get("summary"):
        raise SystemExit("sync_things_done: preprint_lag.json has no summary; "
                         "re-run 'Analyze Preprint-to-Publication Lag' in things_done")
    pairs = [pick(p, LAG_FIELDS) for p in data["pairs"] if "gap_days" in p]   # unresolved pairs have no gap
    summary = {k: data["summary"][k] for k in ("pairs", "median_months")}
    dump("preprint_lag", {"summary": summary, "pairs": pairs},
         f"{REPORTS}/preprint_lag.json")
    print(f"preprint lag: {len(pairs)} pairs, median {data['summary']['median_months']} months")


def coauthors(ledger: Path) -> None:
    """Co-authors (joint papers, first/last year) with their country."""
    network = load_json(ledger / REPORTS / "coauthor_network.json")
    countries = load_json(ledger / REPORTS / "coauthor_countries.json")
    country = {c["name"]: c["country"] for c in countries["coauthors"] if c.get("country")}
    if not country:
        raise SystemExit("sync_things_done: coauthor_countries.json has no countries; "
                         "re-run 'Co-author Countries' in things_done")
    nodes = []
    for n in network["nodes"]:
        if n.get("is_self"):
            continue
        item = {"name": n["id"], "papers": n["total"], "first_year": n["first_year"], "last_year": n["last_year"]}
        if country.get(n["id"]):
            item["country"] = country[n["id"]]
        nodes.append(item)
    nodes.sort(key=lambda n: (-n["papers"], n["name"]))
    dump("coauthors", {"coauthors": nodes},
         f"{REPORTS}/coauthor_network.json + coauthor_countries.json")
    print(f"coauthors: {len(nodes)} ({sum(1 for n in nodes if 'country' in n)} with a country)")


METRICS = ("citation_count", "h_index", "fetched_at", "scholar_url")


def metrics(ledger: Path) -> None:
    """Citation count and h-index (Google Scholar, fetched by things_done)."""
    data = load_json(ledger / ".cache" / "scholar_metrics.json")
    missing = [k for k in METRICS if k not in data]
    if missing:
        raise SystemExit(f"sync_things_done: .cache/scholar_metrics.json has no {missing}")
    keep = {k: data[k] for k in METRICS}
    dump("metrics", keep, ".cache/scholar_metrics.json")
    print(f"metrics: {keep['citation_count']} citations, h-index {keep['h_index']}")


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
    today = date.today().isoformat()
    affiliations(ledger, today)
    profile(ledger, today)
    activities(ledger, "talks", ("date", "title", "event_name", "location", "talk_kind"))
    grants(ledger, today)
    preprint_lag(ledger)
    coauthors(ledger)
    metrics(ledger)
    for old in sorted(p for p in OUT.glob("*.yaml") if p.name not in WRITTEN):   # outputs no longer made
        old.unlink()
        print(f"removed {old.name} (no longer copied)")


if __name__ == "__main__":
    main()
