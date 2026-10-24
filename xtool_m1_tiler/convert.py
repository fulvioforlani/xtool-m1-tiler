"""Pipeline: SVG -> .xcs con incisione divisa in gruppi compatti."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from shapely import affinity

from .estimate import EFFICIENCY, cut_minutes, engrave_minutes, ring_length
from .svgio import load_svg
from .tiling import BUMPS, make_tiles, normalize, tight_area
from .xcs import Layer, rings_to_d, write_xcs

PALETTE = ["#000000", "#0000ff", "#00a000", "#ff00ff", "#ff8000", "#00b4b4", "#800080", "#808000",
           "#a00000", "#006080", "#604020", "#2060a0", "#a060c0", "#40a040", "#c08000", "#606060"]
CUT_COLOR = "#fe0002"


@dataclass
class Options:
    size_mm: float = 0.0            # lato lungo desiderato (0 = misura originale)
    thickness_mm: float = 2.0
    power: int = 55                 # incisione %
    speed: float = 150              # incisione mm/s
    density: int = 83               # righe/cm (100 = 0,1 mm; 83 = 0,12 mm; 67 = 0,15 mm)
    cut_power: int = 73
    cut_speed: float = 10
    cut_passes: int = 2
    max_groups: int = 8
    overhead_min: float = 0.4       # costo (minuti) di un gruppo in piu'
    overlap_mm: float = 0.0
    seam_free: bool = True          # taglia i gruppi solo nei vuoti (nessuna giunzione visibile)
    cut_color: str = "#ff0000"      # colore del tratto che indica il taglio nell'SVG
    margin_mm: float = 6.0


@dataclass
class Result:
    out_path: str
    groups: int
    minutes_single: float
    minutes_split: float
    cut_minutes: float
    size_mm: tuple
    boxes: list = field(default_factory=list)
    tiles: list = field(default_factory=list)
    cut_rings: list = field(default_factory=list)


def convert(svg_path: str, out_xcs: str, opt: Options | None = None, preview_png: str | None = None) -> Result:
    opt = opt or Options()
    d = load_svg(svg_path, opt.cut_color)
    G, rings = d.engrave, d.cut_rings
    if opt.size_mm and max(d.width_mm, d.height_mm) > 0:
        k = opt.size_mm / max(d.width_mm, d.height_mm)
        G = affinity.scale(G, k, k, origin=(0, 0))
        rings = [[(x * k, y * k) for x, y in r] for r in rings]
    G, rings = normalize(G, rings, opt.margin_mm)

    pitch = 10.0 / opt.density
    # costo di un gruppo in piu' espresso come area di riquadro equivalente
    area_per_min = pitch * opt.speed * 60.0 * EFFICIENCY      # mm2 di riquadro scansionati al minuto
    overhead_mm2 = opt.overhead_min * area_per_min
    tiles = make_tiles(G, opt.max_groups, overhead_mm2, opt.overlap_mm, opt.seam_free)
    if len(tiles) > len(BUMPS):
        tiles = tiles[:len(BUMPS)]

    boxes = [tight_area(t)[1] for t in tiles]
    single = engrave_minutes([G.bounds], opt.speed, opt.density, 0.0)
    split = engrave_minutes(boxes, opt.speed, opt.density, opt.overhead_min)
    clen = ring_length(rings)
    cut_min = cut_minutes(clen, opt.cut_speed, opt.cut_passes) if rings else 0.0

    layers = []
    for i, t in enumerate(tiles):
        dp, ds = BUMPS[i]
        layers.append(Layer(name=f"T{i + 1}", color=PALETTE[i % len(PALETTE)], d=rings_to_d([t]),
                            bbox=boxes[i], kind="FILL_VECTOR_ENGRAVING",
                            power=opt.power + dp, speed=opt.speed + ds, density=opt.density))
    if rings:
        xs = [x for r in rings for x, _ in r]; ys = [y for r in rings for _, y in r]
        layers.append(Layer(name="CUT", color=CUT_COLOR, d=rings_to_d(rings),
                            bbox=(min(xs), min(ys), max(xs), max(ys)), kind="VECTOR_CUTTING",
                            power=opt.cut_power, speed=opt.cut_speed, repeat=opt.cut_passes))
    write_xcs(out_xcs, layers, opt.thickness_mm)
    res = Result(out_xcs, len(tiles), single, split, cut_min,
                 (G.bounds[2] - G.bounds[0], G.bounds[3] - G.bounds[1]), boxes, tiles, rings)
    if preview_png:
        save_preview(res, preview_png)
    return res


def save_preview(res: Result, path: str, scale: float = 6.0) -> None:
    from PIL import Image, ImageDraw
    allx = [b[2] for b in res.boxes] + [x for r in res.cut_rings for x, _ in r]
    ally = [b[3] for b in res.boxes] + [y for r in res.cut_rings for _, y in r]
    W, H = int((max(allx) + 6) * scale), int((max(ally) + 6) * scale)
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    for i, t in enumerate(res.tiles):
        col = PALETTE[i % len(PALETTE)]
        rgb = tuple(int(col[j:j + 2], 16) for j in (1, 3, 5))
        polys = [t] if t.geom_type == "Polygon" else [p for p in t.geoms if p.geom_type == "Polygon"]
        for p in polys:
            dr.polygon([(x * scale, y * scale) for x, y in p.exterior.coords], fill=rgb)
            for h in p.interiors:
                dr.polygon([(x * scale, y * scale) for x, y in h.coords], fill="white")
        b = res.boxes[i]
        dr.rectangle([b[0] * scale, b[1] * scale, b[2] * scale, b[3] * scale], outline=rgb, width=1)
    for r in res.cut_rings:
        pts = [(x * scale, y * scale) for x, y in r]
        dr.line(pts + [pts[0]], fill=(255, 0, 0), width=1)
    im.save(path)
