"""World map of co-authors per country, rendered at build time as SVG.

Country outlines: world-atlas countries-110m TopoJSON (Natural Earth, public
domain; data/world/). Projection: Equal Earth. Antarctica is left out.
"""

import json
import math

from .config import DATA, fail
from .text import esc, plural

W, H = 960, 440
# Colour steps (inclusive ranges of co-authors) and a light -> dark purple ramp.
STEPS = [(1, 1), (2, 4), (5, 9), (10, 24), (25, 99), (100, math.inf)]
RAMP = ["#e9ddf7", "#d2b8ef", "#b48ae3", "#9560d3", "#733cb3", "#4f2182"]
ANTARCTICA = "010"
# Co-author countries with no shape in countries-110m (ISO alpha-2 -> name), listed under the map
TOO_SMALL = {"SG": "Singapore"}


def equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """Equal Earth projection (Šavrič et al. 2018), unit sphere."""
    A1, A2, A3, A4, M = 1.340264, -0.081106, 0.000893, 0.003796, math.sqrt(3) / 2
    th = math.asin(M * math.sin(math.radians(lat)))
    t2 = th * th
    t6 = t2 * t2 * t2
    x = math.radians(lon) * math.cos(th) / (M * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


def decode_arcs(topo: dict) -> list[list[tuple[float, float]]]:
    """TopoJSON delta-encoded, quantized arcs -> lists of (lon, lat)."""
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring_path(indexes: list[int], arcs: list[list[tuple[float, float]]]) -> str:
    """SVG path data for one polygon ring. A jump across the map means the ring
    crosses the antimeridian, so a new subpath starts there."""
    pts: list[tuple[float, float]] = []
    for i in indexes:
        arc = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(arc if not pts else arc[1:])
    k, cx, cy = W / (2 * 2.7064), W / 2, 250   # scale, centre (shifted up: no Antarctica)
    out, prev = [], None
    for lon, lat in pts:
        x, y = equal_earth(lon, lat)
        px, py = cx + k * x, cy - k * y
        out.append(f"{'M' if prev is None or abs(px - prev) > W / 3 else 'L'}{px:.1f},{py:.1f}")
        prev = px
    return "".join(out) + "Z"


def color(n: int) -> str:
    """Fill colour for n >= 1 co-authors."""
    return next(c for (lo, hi), c in zip(STEPS, RAMP, strict=True) if lo <= n <= hi)


def world_map(counts: dict[str, int]) -> str:
    """Choropleth: {"FI": 12, ...} (ISO alpha-2 -> co-authors) -> map + legend."""
    topo = json.loads((DATA / "world" / "countries-110m.json").read_text(encoding="utf-8"))
    iso = json.loads((DATA / "world" / "iso-alpha2-to-numeric.json").read_text(encoding="utf-8"))
    alpha2 = {num: a2 for a2, num in iso.items()}
    arcs = decode_arcs(topo)
    paths, drawn = [], set()
    for g in topo["objects"]["countries"]["geometries"]:
        if g.get("id") == ANTARCTICA or g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = "".join(ring_path(r, arcs) for poly in polys for r in poly)
        n = counts.get(alpha2.get(g.get("id"), ""), 0)
        if n:
            drawn.add(alpha2[g["id"]])
            tip = f"{g['properties']['name']}: {plural(n, 'co-author')}"
            paths.append(f'<path class="cm-map__on" d="{d}" style="fill:{color(n)}" data-tip="{esc(tip)}" tabindex="0">'
                         f'<title>{esc(tip)}</title></path>')
        else:
            paths.append(f'<path d="{d}"/>')
    unknown = sorted(set(counts) - drawn - set(TOO_SMALL))
    if unknown:
        fail(f"co-author countries {unknown} have no shape on the map; add them to TOO_SMALL in scripts/cellmig/worldmap.py")
    small = [f"{TOO_SMALL[c]} ({counts[c]})" for c in sorted(set(counts) - drawn)]
    note = (f'<p class="cm-small">Too small to show at this scale: {esc(", ".join(small))}.</p>' if small else "")
    top = max(counts.values())
    legend = "".join(
        f'<li><span style="background:{c}"></span>{lo if lo == hi else (f"{lo}+" if hi == math.inf else f"{lo}–{hi}")}</li>'
        for (lo, hi), c in zip(STEPS, RAMP, strict=True) if lo <= top)
    return (f'<div class="cm-map"><svg class="cm-map__svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="World map of co-authors by country">{"".join(paths)}</svg>'
            f'<div class="cm-chart-tip" hidden></div></div>'
            f'<ul class="cm-map__legend" aria-label="Co-authors per country">{legend}</ul>{note}')
