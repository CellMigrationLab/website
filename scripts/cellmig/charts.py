"""SVG charts, rendered at build time (hover/tap tips come from cellmig.js)."""

import math

from .ledger import Record
from .text import esc, plural

DAYS_PER_MONTH = 30.44   # same constant as things_done's analyze_preprint_lag.py


def papers_per_year(records: list[Record]) -> str:
    """Bar chart: number of publications per year."""
    counts: dict[int, int] = {}
    for r in records:
        counts[int(r["year"])] = counts.get(int(r["year"]), 0) + 1
    years = list(range(min(counts), max(counts) + 1))
    top = max(counts.values())
    W, H, pad, base = 640, 170, 24, 140
    bw = (W - 2 * pad) / len(years)
    parts = []
    for i, y in enumerate(years):
        n = counts.get(y, 0)
        h = (base - 16) * n / top
        bx = pad + i * bw + 2
        tip = f"{y}: {plural(n, 'paper')}"
        if n:
            parts.append(f'<rect class="cm-bars__bar" x="{bx:.1f}" y="{base - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" rx="3" '
                         f'data-tip="{esc(tip)}" tabindex="0"><title>{esc(tip)}</title></rect>')
        if y % 2 == years[-1] % 2:   # label every other year, always the latest
            parts.append(f'<text class="cm-lag__tick" x="{bx + (bw - 4) / 2:.1f}" y="{base + 18}">{y}</text>')
    parts.append(f'<line class="cm-lag__axis" x1="{pad}" x2="{W - pad}" y1="{base}" y2="{base}"/>')
    return (f'<div class="cm-bars"><svg class="cm-lag__chart" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Papers per year">{"".join(parts)}</svg><div class="cm-chart-tip" hidden></div></div>')


def _is_exact(row: Record) -> bool:
    """Both dates known to the day."""
    return row.get("preprint_date_precision") == "day" and row.get("published_date_precision") == "day"


def _lag_dots(rows: list[Record], median_months: float) -> str:
    """Dot plot of the lag: one dot per paper, stacked per month."""
    months = [r["gap_days"] / DAYS_PER_MONTH for r in rows]
    lo = min(0, math.floor(min(months) / 6) * 6)      # a negative gap extends the axis left
    hi = max(12, math.ceil((max(months) + 0.01) / 6) * 6)
    W, left, right, radius, step = 640, 16, 16, 5, 12

    def x(m: float) -> float:
        return left + (W - left - right) * (m - lo) / (hi - lo)

    bins: dict[int, list[Record]] = {}
    for row in sorted(rows, key=lambda r: r["gap_days"]):
        bins.setdefault(math.floor(row["gap_days"] / DAYS_PER_MONTH), []).append(row)
    base = 24 + max(len(v) for v in bins.values()) * step
    H = base + 34
    parts = [f'<svg class="cm-lag__chart" viewBox="0 0 {W} {H}" role="img" aria-label="Months from preprint to '
             f'journal publication for {len(rows)} papers; median {median_months:.1f} months">']
    for t in range(lo, hi, 6):
        parts.append(f'<line class="cm-lag__grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="12" y2="{base}"/>'
                     f'<text class="cm-lag__tick" x="{x(t):.1f}" y="{base + 18}">{t}</text>')
    parts.append(f'<line class="cm-lag__axis" x1="{left}" x2="{W - right}" y1="{base}" y2="{base}"/>')
    mx = x(median_months)
    parts.append(f'<line class="cm-lag__median" x1="{mx:.1f}" x2="{mx:.1f}" y1="4" y2="{base}"/>'
                 f'<text class="cm-lag__label" x="{mx + 6:.1f}" y="14">median {median_months:.1f} months</text>')
    for month, items in bins.items():
        for i, row in enumerate(items):
            exact = _is_exact(row)
            tip = (f'{row["published_title"]}: {row["gap_days"] / DAYS_PER_MONTH:.1f} months '
                   f'({row["preprint_date"]} → {row["published_date"]}{"" if exact else ", approximate date"})')
            parts.append(f'<a href="https://doi.org/{esc(row["published_doi"])}"><circle class="cm-lag__dot{"" if exact else " is-approx"}" '
                         f'cx="{x(month + 0.5):.1f}" cy="{base - 10 - i * step:.1f}" r="{radius}" data-tip="{esc(tip)}">'
                         f'<title>{esc(tip)}</title></circle></a>')
    parts.append("</svg>")
    return "".join(parts)


def lag_section(pairs: list[Record], summary: Record) -> str:
    """Preprint-to-publication lag: headline median, dot plot and a table.
    The median comes from things_done's summary; nothing is recomputed here."""
    median = summary["median_months"]
    rows = sorted(pairs, key=lambda r: r["published_date"], reverse=True)
    table = "".join(
        f'<tr><td>{esc(r["published_title"])}</td><td>{r["preprint_date"]}</td>'
        f'<td>{r["published_date"]}</td><td>{r["gap_days"] / DAYS_PER_MONTH:.1f}</td></tr>' for r in rows)
    approx = sum(1 for r in rows if not _is_exact(r))
    note = f" Hollow dots ({approx}): one of the two dates is only known to the month." if approx else ""
    return (f'<div class="cm-lag">'
            f'<div class="cm-lag__head"><p class="cm-lag__hero"><strong>{median:.1f}</strong> months</p>'
            f'<p><span class="cm-lag__title">Median time from preprint to journal</span>'
            f'Months between posting and journal publication, for {summary["pairs"]} papers. '
            f'Each dot is a paper; hover or tap for details.{note}</p></div>'
            f'<div class="cm-lag__plot">{_lag_dots(rows, median)}<div class="cm-chart-tip" hidden></div></div>'
            f'<details class="cm-lag__table"><summary>Show as table</summary><table><thead><tr><th>Paper</th>'
            f'<th>Preprint</th><th>Journal</th><th>Months</th></tr></thead><tbody>{table}</tbody></table></details></div>')
