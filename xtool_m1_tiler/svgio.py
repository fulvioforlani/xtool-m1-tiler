"""Lettura di un SVG: separa l'incisione (forme con riempimento) dal taglio (tratto rosso).

Tutto viene convertito in millimetri e in geometrie shapely.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
from svgelements import SVG, Path, Shape, Color

PX_TO_MM = 25.4 / 96.0  # svgelements lavora a 96 dpi


@dataclass
class Design:
    engrave: object                     # geometria shapely (unione di tutte le forme da incidere), in mm
    cut_rings: list = field(default_factory=list)   # anelli (liste di (x, y)) del taglio, in mm
    width_mm: float = 0.0
    height_mm: float = 0.0


def _is_cut_color(color, cut_hex: str) -> bool:
    if color is None or color.value is None:
        return False
    try:
        c = Color(cut_hex)
        return (abs(color.red - c.red) < 40 and abs(color.green - c.green) < 40
                and abs(color.blue - c.blue) < 40)
    except Exception:
        return False


def _has_fill(el) -> bool:
    f = getattr(el, "fill", None)
    return f is not None and f.value is not None and getattr(f, "alpha", 255) > 0


def _sample_subpath(sub, max_step_mm: float):
    pts = []
    for seg in sub:
        if seg.__class__.__name__ in ("Move",):
            pts.append((seg.end.x, seg.end.y))
            continue
        if seg.__class__.__name__ in ("Line", "Close"):
            if not pts:
                pts.append((seg.start.x, seg.start.y))
            pts.append((seg.end.x, seg.end.y))
            continue
        length = seg.length(error=1e-3) * PX_TO_MM if hasattr(seg, "length") else 1.0
        n = max(6, int(math.ceil(length / max_step_mm)))
        if not pts:
            pts.append((seg.start.x, seg.start.y))
        ts = np.linspace(0, 1, n + 1)[1:]
        for t in ts:
            p = seg.point(float(t))
            pts.append((p.x, p.y))
    return [(x * PX_TO_MM, y * PX_TO_MM) for x, y in pts]


def _rings_of(el, max_step_mm: float):
    path = el if isinstance(el, Path) else Path(el)
    rings = []
    for sub in path.as_subpaths():
        sp = Path(sub)
        pts = _sample_subpath(sp, max_step_mm)
        if len(pts) >= 3:
            rings.append(pts)
    return rings


def _evenodd(rings):
    g = None
    for r in rings:
        p = Polygon(r).buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    return g


def load_svg(path: str, cut_color: str = "#ff0000", max_step_mm: float = 0.05) -> Design:
    """Carica l'SVG. Le forme con stroke ~ `cut_color` e senza riempimento sono il TAGLIO,
    le forme con riempimento sono l'INCISIONE."""
    svg = SVG.parse(path, reify=True)
    engr = []
    cut_rings = []
    for el in svg.elements():
        if not isinstance(el, Shape):
            continue
        stroke = getattr(el, "stroke", None)
        if _is_cut_color(stroke, cut_color) and not _has_fill(el):
            for r in _rings_of(el, max_step_mm):
                cut_rings.append(r)
        elif _has_fill(el):
            g = _evenodd(_rings_of(el, max_step_mm))
            if g is not None and not g.is_empty:
                engr.append(g)
    if not engr:
        raise ValueError("Nessuna forma con riempimento trovata: l'incisione deve essere riempita (fill).")
    G = unary_union(engr)
    allx = [x for r in cut_rings for x, _ in r] or [G.bounds[0], G.bounds[2]]
    ally = [y for r in cut_rings for _, y in r] or [G.bounds[1], G.bounds[3]]
    x0 = min(min(allx), G.bounds[0]); x1 = max(max(allx), G.bounds[2])
    y0 = min(min(ally), G.bounds[1]); y1 = max(max(ally), G.bounds[3])
    return Design(engrave=G, cut_rings=cut_rings, width_mm=x1 - x0, height_mm=y1 - y0)
