"""The lab members page (docs/lab-members.md)."""

from .components import JOIN_CARD, person_card, section_title
from .config import DATA, GROUPS, REPO, load
from .images import lite_video, media
from .page import Page
from .people import Person
from .previews import preview
from .structured import item_list, person_item, to_json
from .text import esc, md


def _team_media() -> str:
    """Team photos and videos from data/team.yaml."""
    team = load(DATA / "team.yaml")
    out = [section_title("Meet our team"), '<div class="cm-team">']
    for ph in team.get("photos") or []:
        cap = f'<figcaption>{esc(ph["caption"])}</figcaption>' if ph.get("caption") else ""
        out.append(f'<figure>{media(ph["image"], ph.get("caption") or "The Cell Migration Lab team", 1400)}{cap}</figure>')
    for v in team.get("videos") or []:
        out.append(f'<figure>{lite_video(v.get("youtube"), v.get("vimeo"), v["title"])}<figcaption>{esc(v["title"])}</figcaption></figure>')
    out.append("</div>")
    return "\n".join(out)


def _alumnus(m: Person) -> str:
    """One alumni line: name, every role held in the lab, and where they are now."""
    now = f' <span class="cm-alumni__now">now {md(m["now"], inline=True)}</span>' if m.get("now") else ""
    return f'<li><strong>{esc(m["name"])}</strong> <span>{esc(", ".join(m["roles"]))}</span>{now}</li>'


def page_members(members: list[Person], teaser: str) -> None:
    """The group leader's teaser (profile.pi_teaser), then current members in one grid (group leader first, then by group and roster
    order) showing only their current role; team pictures; alumni with all roles."""
    current = sorted((m for m in members if m["status"] == "current"),
                     key=lambda m: (GROUPS.index(m["group"]), m["order"]))
    alumni = [m for m in members if m["status"] == "alumni"]
    p = Page("lab-members.md", title="Lab members", edit_url=f"{REPO}/tree/main/data/members",
             **preview("lab-members"))
    p.meta["jsonld"] = to_json(item_list("Members of the Cell Migration Lab", [person_item(m) for m in current]))
    # the group leader's card opens the profile on About us
    cards = [person_card(m, "about-us/#group-leader" if m["group"] == "pi" else None) for m in current]
    p.add("# Lab members", teaser, '<ul class="cm-people">', *cards, JOIN_CARD, "</ul>")
    p.add(_team_media())
    if alumni:
        p.add(section_title("Alumni"), '<ul class="cm-alumni">', *(_alumnus(m) for m in alumni), "</ul>")
    p.write()
