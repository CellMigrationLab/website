"""Lab members: the things_done roster plus photos and links from this website.

Who is in the lab, their role(s) and whether they are current or alumni come
from data/things_done/lab_members.yaml (things_done's ledger/profile/lab_members.yaml).
Photos and links live here: data/members/<slug>.yaml and data/photos/<slug>.<ext>,
where <slug> is the roster name slugified ("Iván Hidalgo Cenalmor" ->
ivan-hidalgo-cenalmor). A file here that matches nobody in the roster, or a key
that is not listed below, stops the build (it would otherwise be ignored).
"""

import shutil
from typing import Any

from .config import DATA, DOCS, GROUPS, LEDGER_DATA, fail, load
from .text import normalize_name, slugify

Person = dict[str, Any]

# Keys allowed in data/members/<slug>.yaml.
PROFILE_KEYS = {"photo", "photo_position", "email", "orcid", "scholar", "github",
                "bluesky", "website", "bio", "now"}
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
STATUSES = ("current", "alumni")


def _publish_photo(slug: str) -> str | None:
    """Copy data/photos/<slug>.<ext> into docs/ and return its site path."""
    for ext in PHOTO_EXTENSIONS:
        src = DATA / "photos" / f"{slug}{ext}"
        if src.is_file():
            dest = DOCS / "assets" / "images" / "members" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)   # the folder is emptied by build_pages.clean() on every build
            return f"assets/images/members/{src.name}"
    return None


def _check_no_orphans(slugs: set[str]) -> None:
    """Every data/members/*.yaml and data/photos/* file must belong to someone."""
    files = list((DATA / "members").glob("*.yaml")) + [
        p for p in (DATA / "photos").glob("*") if p.suffix.lower() in PHOTO_EXTENSIONS]
    orphans = sorted(str(p.relative_to(DATA.parent)) for p in files if p.stem not in slugs)
    if orphans:
        fail(f"{', '.join(orphans)}: no one with this name in the things_done roster "
             "(rename the file to match the roster name, or remove it)")


def load_members() -> list[Person]:
    """Everyone in the roster, in roster order, with website profile data merged in.

    Adds: slug, order (roster position), roles (previous roles + current role,
    oldest first) and photo (site path) when there is one."""
    people = []
    for i, rec in enumerate(load(LEDGER_DATA / "lab_members.yaml").get("records") or []):
        person = dict(rec, slug=slugify(rec["name"]), order=i)
        if person["status"] not in STATUSES:
            fail(f"lab_members.yaml: {rec['name']}: status must be one of {STATUSES}")
        if person["group"] not in GROUPS:
            fail(f"lab_members.yaml: {rec['name']}: group must be one of {GROUPS}")
        profile_file = DATA / "members" / f"{person['slug']}.yaml"
        if profile_file.is_file():
            profile = load(profile_file)
            unknown = set(profile) - PROFILE_KEYS
            if unknown:
                fail(f"{profile_file.relative_to(DATA.parent)}: unknown keys {sorted(unknown)} "
                     f"(allowed: {sorted(PROFILE_KEYS)}; name and role come from things_done)")
            person.update(profile)
        person["roles"] = list(person.get("previous_roles") or []) + [person["role"]]
        photo = _publish_photo(person["slug"])
        if photo and person.get("photo"):
            fail(f"{person['name']}: both data/photos/{person['slug']}.* and 'photo:' in "
                 f"data/members/{person['slug']}.yaml; keep one")
        person["photo"] = person.get("photo") or photo
        people.append(person)
    if not people:
        fail("data/things_done/lab_members.yaml has no records")
    _check_no_orphans({p["slug"] for p in people})
    return people


def leader(members: list[Person]) -> Person:
    """The current group leader (group `pi`), who must have an email in
    data/members/<slug>.yaml (it is the lab's contact address)."""
    pis = [m for m in members if m["group"] == "pi" and m["status"] == "current"]
    if len(pis) != 1:
        fail(f"things_done lab_members.yaml: expected one current group leader (group pi), found {len(pis)}")
    if not pis[0].get("email"):
        fail(f"data/members/{pis[0]['slug']}.yaml: the group leader needs an email (the lab's contact address)")
    return pis[0]


def lab_names(members: list[Person]) -> set[str]:
    """Normalized names (and other spellings) of everyone ever in the lab,
    current members and alumni alike (no dates: see components.author_list)."""
    return {normalize_name(n) for m in members for n in [m["name"], *(m.get("also_known_as") or [])]}


def is_lab_member(name: str, lab: set[str]) -> bool:
    """Whether an author is directly associated with the lab (now or before); ignores a middle initial
    ("Joanna W. Pylvänäinen" matches "Joanna Pylvänäinen")."""
    parts = name.split()
    return normalize_name(name) in lab or (len(parts) > 2 and normalize_name(parts[0] + parts[-1]) in lab)
