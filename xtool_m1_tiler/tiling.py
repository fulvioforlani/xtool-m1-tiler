"""Divisione dell'incisione in gruppi compatti (tasselli).

Sull'xTool M1 l'incisione a riempimento (FILL) scansiona, riga per riga, l'intero riquadro
di un gruppo, anche dove non c'e' niente da incidere. xTool Creative Space crea un gruppo per
ogni combinazione di COLORE + PARAMETRI: dividendo il disegno in piu' gruppi compatti (con parametri
che differiscono di 1 punto, invisibili sul legno) la testa non attraversa i vuoti.
"""
from __future__ import annotations

from shapely.affinity import translate
from shapely.geometry import LineString, box


def tight_area(g):
    if g is None or g.is_empty:
        return 0.0, None
    x0, y0, x1, y1 = g.bounds
    return (x1 - x0) * (y1 - y0), (x0, y0, x1, y1)


def _crossing(G, kind, v, b):
    """Lunghezza (mm) di inchiostro attraversata dalla linea di taglio."""
    x0, y0, x1, y1 = b.bounds
    line = LineString([(v, y0), (v, y1)]) if kind == "v" else LineString([(x0, v), (x1, v)])
    return G.intersection(line).length


def partition(G, max_groups: int = 8, overhead_mm2: float = 390.0, step: float = 1.5,
              seam_free: bool = True, tol: float = 0.05):
    """Taglio ricorsivo del riquadro (guillotine) che minimizza la somma dei riquadri stretti.
    overhead_mm2 = costo di un gruppo in piu' espresso come area equivalente.
    seam_free=True: si taglia SOLO dove la linea di taglio non attraversa inchiostro (nessuna giunzione
    visibile: due gruppi che si toccano su un tratto lasciano una riga piu' scura/chiara)."""
    leaves = [box(*G.bounds)]
    while len(leaves) < max_groups:
        best = None
        for li, b in enumerate(leaves):
            g = G.intersection(b)
            a0, _ = tight_area(g)
            x0, y0, x1, y1 = b.bounds
            cands = []
            x = x0 + step
            while x < x1 - step:
                cands.append(("v", x)); x += step
            y = y0 + step
            while y < y1 - step:
                cands.append(("h", y)); y += step
            for kind, v in cands:
                if seam_free and _crossing(G, kind, v, b) > tol:
                    continue
                if kind == "v":
                    b1, b2 = box(x0, y0, v, y1), box(v, y0, x1, y1)
                else:
                    b1, b2 = box(x0, y0, x1, v), box(x0, v, x1, y1)
                a1, _ = tight_area(G.intersection(b1))
                a2, _ = tight_area(G.intersection(b2))
                gain = a0 - (a1 + a2)
                if best is None or gain > best[0]:
                    best = (gain, li, b1, b2)
        if best is None or best[0] < overhead_mm2:
            break
        leaves = [b for k, b in enumerate(leaves) if k != best[1]] + [best[2], best[3]]
    return leaves


def make_tiles(G, max_groups: int = 8, overhead_mm2: float = 390.0, overlap: float = 0.0,
               seam_free: bool = True):
    """Ritorna la lista di geometrie (una per gruppo).
    Con seam_free=True (default) i gruppi si separano solo nei vuoti e overlap resta 0.
    Con seam_free=False e overlap>0 i gruppi possono tagliare i tratti: la sovrapposizione doppia
    (overlap = una riga) lascia pero' una riga piu' scura visibile sulle zone piene."""
    tiles = []
    for b in partition(G, max_groups, overhead_mm2, step=0.5 if seam_free else 1.5, seam_free=seam_free):
        x0, y0, x1, y1 = b.bounds
        g = G.intersection(box(x0 - overlap, y0 - overlap, x1 + overlap, y1 + overlap))
        if not g.is_empty and g.area > 0.05:
            tiles.append(g)
    return tiles


# Variazioni (potenza, velocita') in punti: differenza minima per ottenere gruppi distinti.
BUMPS = [(0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2), (2, 1), (1, 2), (3, 0), (0, 3),
         (2, 2), (3, 1), (1, 3), (3, 2), (2, 3), (4, 0)]


def normalize(G, cut_rings, margin=6.0):
    """Sposta tutto in modo che il riquadro complessivo parta a (margin, margin)."""
    allx = [x for r in cut_rings for x, _ in r] + [G.bounds[0], G.bounds[2]]
    ally = [y for r in cut_rings for _, y in r] + [G.bounds[1], G.bounds[3]]
    dx, dy = margin - min(allx), margin - min(ally)
    G2 = translate(G, dx, dy)
    cut2 = [[(x + dx, y + dy) for x, y in r] for r in cut_rings]
    return G2, cut2
