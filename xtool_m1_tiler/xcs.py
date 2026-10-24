"""Scrittura di un file .xcs (xTool Creative Space) per xTool M1.

Il formato e' un JSON; la struttura qui usata e' stata ricavata da file .xcs reali creati con
xTool Creative Space (versione 1.x). Non e' un formato documentato ufficialmente: potrebbe cambiare.
"""
from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass


@dataclass
class Layer:
    name: str
    color: str            # "#rrggbb"
    d: str                # tracciato SVG assoluto (solo M, L, Z)
    bbox: tuple           # (x0, y0, x1, y1) in mm
    kind: str = "FILL_VECTOR_ENGRAVING"   # oppure "VECTOR_CUTTING"
    power: int = 55
    speed: float = 150
    repeat: int = 1
    density: int = 100    # righe per cm (100 = 0,1 mm, 83 = 0,12 mm, 67 = 0,15 mm)

    @property
    def is_fill(self) -> bool:
        return self.kind == "FILL_VECTOR_ENGRAVING"


def rings_to_d(polys_or_rings, ox: float = 0.0, oy: float = 0.0) -> str:
    """Converte poligoni shapely o liste di anelli [(x, y), ...] in un tracciato 'M x y L ... Z'."""
    rings = []
    for g in polys_or_rings:
        if hasattr(g, "geom_type"):
            polys = [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]
            for p in polys:
                if p.is_empty or p.area < 0.01:
                    continue
                rings.append(list(p.exterior.coords)[:-1])
                for i in p.interiors:
                    rings.append(list(i.coords)[:-1])
        else:
            rings.append(list(g))
    parts = ["M " + " L ".join(f"{x + ox:.3f} {y + oy:.3f}" for x, y in r) + " Z" for r in rings if len(r) >= 3]
    return " ".join(parts)


def _cust(**k):
    return {"materialType": "customize", "parameter": {"customize": k}}


def write_xcs(path: str, layers: list, thickness_mm: float, cover_png: str | None = None) -> None:
    displays, dmap, cols = [], [], {}
    for z, ly in enumerate(layers, 1):
        uid = str(uuid.uuid4())
        x0, y0, x1, y1 = ly.bbox
        cols[ly.color] = {"name": "{layer} %d" % z, "order": z, "visible": True}
        displays.append({
            "id": uid, "type": "PATH", "x": float(x0), "y": float(y0), "angle": 0,
            "scale": {"x": 1, "y": 1}, "skew": {"x": 0, "y": 0}, "pivot": {"x": 0, "y": 0},
            "localSkew": {"x": 0, "y": 0}, "offsetX": 0, "offsetY": 0, "lockRatio": True,
            "isClosePath": True, "zOrder": z, "sourceId": str(uuid.uuid4()), "groupTag": "",
            "layerTag": ly.color, "layerColor": ly.color, "visible": True, "originColor": ly.color,
            "width": float(x1 - x0), "height": float(y1 - y0), "isFill": ly.is_fill,
            "lineColor": 0, "fillColor": 0, "points": [], "dPath": ly.d, "fillRule": "evenodd",
            "graphicX": 0.0, "graphicY": 0.0})
        cut = ly.kind == "VECTOR_CUTTING"
        dmap.append([uid, {"isFill": ly.is_fill, "type": "PATH", "processingType": ly.kind, "data": {
            "VECTOR_CUTTING": _cust(power=ly.power if cut else 1, speed=ly.speed if cut else 16,
                                    repeat=ly.repeat if cut else 1, enableBreakPoint=False,
                                    breakPointSize=0.5, breakPointCount=2, breakPointPower=0),
            "VECTOR_ENGRAVING": _cust(power=1, speed=20, repeat=1),
            "FILL_VECTOR_ENGRAVING": _cust(power=1 if cut else ly.power, speed=80 if cut else ly.speed,
                                           repeat=1, density=ly.density, bitmapScanMode="zMode"),
            "KNIFE_CUTTING": _cust(cutPressure=45, speed=40, repeat=1)}, "processIgnore": False}])
    cid, now = str(uuid.uuid4()), int(time.time() * 1000)
    cover = ""
    if cover_png and os.path.exists(cover_png):
        with open(cover_png, "rb") as f:
            cover = "data:image/png;base64," + base64.b64encode(f.read()).decode()
    doc = {"canvasId": cid,
           "canvas": [{"id": cid, "title": "{panel}1", "layerData": cols, "displays": displays}],
           "extId": "M1",
           "device": {"id": "M1", "power": [10], "data": {"dataType": "Map", "value": [[cid, {
               "mode": "LASER_PLANE",
               "data": {"LASER_PLANE": {"material": 0, "cushion": 0, "thickness": thickness_mm,
                                        "perimeter": None, "diameter": None, "processPath": "auto"}},
               "displays": {"dataType": "Map", "value": dmap}}]]}, "materialList": [], "materialTypeList": []},
           "version": "1.7.8", "created": str(now), "modify": str(now),
           "ua": "xtool-m1-tiler", "meta": [{"version": "1.7.8", "date": now}], "cover": cover}
    with open(path, "w", encoding="utf8") as f:
        json.dump(doc, f, ensure_ascii=False)
