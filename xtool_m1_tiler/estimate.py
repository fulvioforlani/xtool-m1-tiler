"""Stima del tempo di lavorazione (modello empirico misurato su xTool M1, compensato 2 mm).

Incisione FILL: la testa percorre ogni riga dell'intero riquadro del gruppo:
    tempo = (altezza / interlinea) * (larghezza / velocita') / efficienza + overhead_gruppo
con efficienza ~0,9 (accelerazioni) e overhead per gruppo ~0,25-0,4 min.
Taglio: lunghezza / velocita' * passate * 1,3.
E' una STIMA: misurare sempre il primo pezzo.
"""
from __future__ import annotations

EFFICIENCY = 0.9


def engrave_minutes(boxes_mm, speed_mm_s: float, density: int, overhead_per_group_min: float = 0.4) -> float:
    pitch = 10.0 / density          # mm tra due righe
    t = 0.0
    for (x0, y0, x1, y1) in boxes_mm:
        t += ((y1 - y0) / pitch) * ((x1 - x0) / speed_mm_s) / 60.0 / EFFICIENCY
    return t + overhead_per_group_min * len(boxes_mm)


def cut_minutes(length_mm: float, speed_mm_s: float, passes: int) -> float:
    return length_mm / speed_mm_s * passes / 60.0 * 1.3


def ring_length(rings) -> float:
    total = 0.0
    for r in rings:
        for (xa, ya), (xb, yb) in zip(r, r[1:] + r[:1]):
            total += ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    return total
