"""Sound Systems Rebalanced artwork: banner (the Nexus header format, 1300x372) and square cover.

    python art.py [folder]     (default: the assets folder above this one)

A mission's music as a volume strip from the drop through landing to the fight, with no silent stretch, its loudest
bars just under a dashed yellow ceiling they never cross. The banner names both fixes beside the strip; the cover says
them in its side text. The strip is drawn from a fixed seed, so both PNGs re-render pixel for pixel."""
import sys
from pathlib import Path

import numpy as np

import style
from style import UI, UI_SEMI, Menu, Row, Spec, menu_panel, ui_size

SECTIONS = [('DROP', 0.0, 0.62), ('LANDING', 0.24, 0.52), ('FIGHT', 0.52, 0.86)]   # (label, start, loudness)


def levels(count: int) -> np.ndarray:
    """Bar heights in 0..1: each section's loudness with a beat and some variation, never silent, never above 1."""
    rng = np.random.default_rng(7)
    t = np.linspace(0, 1, count, endpoint=False)
    base = np.zeros(count)
    for _, start, loud in SECTIONS:
        base[t >= start] = loud
    kernel = np.hanning(9) / np.hanning(9).sum()
    base = np.convolve(np.pad(base, 4, mode='edge'), kernel, mode='valid')          # sections blend
    beat = 0.82 + 0.18 * (np.arange(count) % 4 == 0)
    wobble = 0.78 + 0.22 * rng.random(count)
    return np.clip(base * beat * wobble / 0.9, 0.12, 1.0)


def dashed(cv, x0, x1, y, width, dash, gap):
    x = x0
    while x < x1:
        cv.rect('yellow', x, y - width / 2, min(x + dash, x1), y + width / 2)
        x += dash + gap


def strip(cv, x0, x1, ceiling, floor, bar, gap, cap, line_w, label_dy, clear):
    """The volume strip filling x0..x1: cream bars grow up from `floor`, the loudest one up to `clear` below the
    dashed yellow ceiling at `ceiling`. Section labels sit label_dy capitals below the bars."""
    count = int((x1 - x0 + gap) // (bar + gap))
    pitch = (x1 - x0 + gap) / count                 # the last bar ends on x1
    heights = levels(count)
    span = floor - ceiling - line_w / 2 - clear
    for i, h in enumerate(heights):
        x = x0 + i * pitch
        cv.rrect('cream', x, floor - h / heights.max() * span, x + bar, floor, bar / 2)
    dashed(cv, x0, x1, ceiling, line_w, dash=line_w * 4, gap=line_w * 2.5)
    size = ui_size(cap)
    for name, start, _ in SECTIONS:
        cv.text('gray', x0 + round(start * count) * pitch, floor + cap * label_dy, name, UI, size, UI_SEMI,
                tracking=0.1)


def menu(cv, g: Menu) -> None:
    menu_panel(cv, g)
    cap = 11
    base = g.cap_top + 14                       # level with the title's first line, as the siblings' headers
    ceiling = base + 22
    strip(cv, g.x0, g.x1, ceiling, ceiling + 96, bar=5, gap=3, cap=cap, line_w=2, label_dy=1.9, clear=4)
    # Both claims on one left-aligned line, a yellow dot between them, so neither reads as one half's heading.
    size = ui_size(11)
    _, right = cv.text('gray', g.x0, base, 'SAME MUSIC VOLUME WHEN YOU JOIN', UI, size, UI_SEMI, tracking=0.09)
    cv.circle('yellow', right + 13, base - 11 / 2, 2.2)
    cv.text('gray', right + 26, base, 'MUSIC ON EVERY PLANET', UI, size, UI_SEMI, tracking=0.09)


def cover_row(cv, r: Row) -> None:
    """The panel above the title: it bleeds off the right edge and ends above the title's first line."""
    panel_x, corner = r.x0 - 24, 30
    top, bottom = r.top + 40, r.top + r.h
    cv.poly('panel', [(panel_x + corner, top), (cv.width, top), (cv.width, bottom), (panel_x, bottom),
                      (panel_x, top + corner)])
    cv.polyline('edge', [(cv.width, bottom), (panel_x, bottom), (panel_x, top + corner), (panel_x + corner, top),
                         (cv.width, top)], 2)
    cv.line('yellow', panel_x, top + corner, panel_x + corner, top, 3.5)
    cap = 20
    floor = bottom - 2.4 * cap - 30
    strip(cv, r.x0, r.x1, top + 56, floor, bar=14, gap=8, cap=cap, line_w=3.5, label_dy=2.4, clear=9)


SPEC = Spec(wide='SOUND SYSTEMS', bar='REBALANCED', square=['SOUND', 'SYSTEMS'], menu=menu, cover_row=cover_row,
            caption=['SAME MUSIC VOLUME', 'WHEN YOU JOIN', '', 'MUSIC ON', 'EVERY PLANET'], caption_line=0,
            cover_layout='bottom', menu_x0=770)

if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    style.nexus(SPEC, out / 'banner.png')
    style.cover(SPEC, out / 'thumbnail.png')
    print(out)
