"""Guillaume's short profile (About us), its teaser (Lab members) and his recent
talks (llms-full.txt), from things_done data."""

import re
from datetime import date, timedelta

from .components import PROFILE_LINKS, section_title
from .icons import ICONS
from .images import square_thumb
from .ledger import Ledger, Record
from .people import Person
from .text import esc, md

RECENT_TALK_DAYS = 730   # "recent talks": the last two years
TALK_KINDS = {           # ledger talk_kinds that are listed; other kinds are not
    "keynote", "plenary", "invited_talk", "seminar", "contributed_talk", "webinar", "chair_and_speaker",
}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month_year(value: str) -> str:
    """"2026-08" or "2026-08-19" -> "Aug 2026"; "2026" -> "2026"."""
    parts = str(value).split("-")
    return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}" if len(parts) > 1 else parts[0]


def pi_profile(profile: Record, leader: Person) -> str:
    """About-us section on the group leader: photo, name, title, profile links
    and the public short bio from Things Done."""
    photo = ""
    if leader.get("photo"):
        img = square_thumb(leader["photo"], 480, leader.get("photo_position", "top"))
        photo = f'<img class="cm-profile__photo" src="{img}" alt="{esc(profile["name"])}" width="240" height="240" loading="lazy">'
    links = "".join(f'<a href="{esc(url(leader[key]))}" aria-label="{esc(profile["name"])} – {key}">{ICONS[icon]}</a>'
                    for key, icon, url in PROFILE_LINKS if leader.get(key))
    return (f'{section_title("Group leader", id_="group-leader")}<section class="cm-profile">'
            f'<div class="cm-profile__head">{photo}<div><h2 class="cm-profile__name">{esc(profile["name"])}</h2>'
            f'<p class="cm-profile__title">{esc(profile["title"])}</p>'
            f'<p class="cm-profile__links">{links}</p></div></div>'
            f'<div class="cm-profile__bio">{md(profile["short_bio"])}</div></section>')


def pi_teaser(profile: Record) -> str:
    """The first sentence of the group leader's bio, with a link to the whole
    profile on About us (Lab members page)."""
    # a sentence ends with a word or a link, then ". " (so "K. Albin" does not end one)
    first = re.split(r"(?<=[a-z)\]])\.\s+", profile["short_bio"].strip(), maxsplit=1)[0].rstrip(".")
    return (f'<p class="cm-lead">{md(first, inline=True)}. '
            f'<a href="about-us/#group-leader">More about {esc(profile["name"].split()[0])}</a></p>')


def recent_talks(ledger: Ledger, today: date) -> list[Record]:
    """Talks of the listed kinds from the last RECENT_TALK_DAYS days, newest first."""
    since = (today - timedelta(days=RECENT_TALK_DAYS)).isoformat()
    return [t for t in ledger.talks if t["talk_kind"] in TALK_KINDS and str(t["date"]) >= since]
