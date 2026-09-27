"""Guillaume's profile (About us), recent talks and teaching (Online talks),
all from things_done data."""

from datetime import date, timedelta

from .components import PROFILE_LINKS, section_title
from .icons import ICONS
from .images import square_thumb
from .ledger import Ledger, Record
from .people import Person
from .text import esc

RECENT_TALK_DAYS = 730   # "recent talks": the last two years
TALK_KINDS = {           # ledger talk_kind -> label (None: no label); others are not listed
    "keynote": "Keynote", "plenary": "Plenary", "invited_talk": None, "seminar": "Seminar",
    "contributed_talk": None, "webinar": "Webinar", "chair_and_speaker": None,
}
TEACHING_ROLES = {"course_director": "Course director", "course_lecturer": "Lecturer",
                  "guest_lecturer": "Guest lecturer"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month_year(value: str) -> str:
    """"2026-08" or "2026-08-19" -> "Aug 2026"; "2026" -> "2026"."""
    parts = str(value).split("-")
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}" if len(parts) > 1 else parts[0]


def _role_list(title: str, roles: list[Record]) -> str:
    """A titled list of roles ("Title, Organization")."""
    if not roles:
        return ""
    items = "".join(f'<li>{esc(r["title"])}<span>{esc(r["organization"])}</span></li>' for r in roles)
    return f'<div><h3>{esc(title)}</h3><ul>{items}</ul></div>'


def pi_profile(profile: Record, leader: Person) -> str:
    """About-us section on the group leader: photo, title, links, current
    positions, editorial and service roles, education."""
    photo = ""
    if leader.get("photo"):
        img = square_thumb(leader["photo"], 480, leader.get("photo_position", "top"))
        photo = f'<img class="cm-profile__photo" src="{img}" alt="{esc(profile["name"])}" width="240" height="240" loading="lazy">'
    links = "".join(f'<a href="{esc(url(leader[key]))}" aria-label="{esc(profile["name"])} – {key}">{ICONS[icon]}</a>'
                    for key, icon, url in PROFILE_LINKS if leader.get(key))
    education = [{"title": e["degree"] + (f' ({str(e["end_date"])[:4]})' if e.get("end_date") else ""),
                  "organization": e["organization"]} for e in profile["education"]]
    return (f'{section_title("Group leader", id_="group-leader")}<section class="cm-profile">'
            f'<div class="cm-profile__head">{photo}<div><h2 class="cm-profile__name">{esc(profile["name"])}</h2>'
            f'<p class="cm-profile__title">{esc(profile["title"])}</p>'
            f'<p class="cm-profile__links">{links}</p></div></div>'
            f'<div class="cm-profile__cols">'
            f'{_role_list("Positions", profile["appointments"])}'
            f'{_role_list("Editorial roles", profile.get("editorial") or [])}'
            f'{_role_list("Service and leadership", profile.get("service") or [])}'
            f'{_role_list("Education", education)}</div></section>')


def recent_talks(ledger: Ledger, today: date) -> list[Record]:
    """Talks of the listed kinds from the last RECENT_TALK_DAYS days, newest first."""
    since = (today - timedelta(days=RECENT_TALK_DAYS)).isoformat()
    return [t for t in ledger.talks if t.get("talk_kind") in TALK_KINDS and str(t["date"]) >= since]


def talks_section(ledger: Ledger, today: date) -> str:
    """List of recent talks: date, title, event and place."""
    rows = []
    for t in recent_talks(ledger, today):
        label = TALK_KINDS[t["talk_kind"]]
        badge = f' <span class="cm-badge">{label}</span>' if label else ""
        where = " · ".join(esc(x) for x in (t.get("event_name"), t.get("location")) if x)
        rows.append(f'<li><span class="cm-talklist__date">{month_year(t["date"])}</span>'
                    f'<span><strong>{esc(t["title"])}</strong>{badge}<span class="cm-talklist__where">{where}</span></span></li>')
    return (f'{section_title("Recent talks", id_="recent-talks")}<ul class="cm-talklist">{"".join(rows)}</ul>'
            '<p class="cm-small cm-source">From our <em>things_done</em> activity ledger; updates automatically.</p>')


def teaching_section(ledger: Ledger, today: date) -> str:
    """Courses taught this year (teaching records that have not ended)."""
    now = today.isoformat()
    seen, rows = set(), []
    for t in ledger.teaching:
        if str(t.get("end_date") or "9999") < now or t["title"] in seen:
            continue
        seen.add(t["title"])
        role = TEACHING_ROLES.get(t.get("teaching_kind"), "")
        rows.append(f'<li><span class="cm-talklist__date">{esc(role)}</span>'
                    f'<span><strong>{esc(t["title"])}</strong><span class="cm-talklist__where">{esc(t["organization"])}</span></span></li>')
    return f'{section_title("Teaching", id_="teaching")}<ul class="cm-talklist">{"".join(rows)}</ul>' if rows else ""
