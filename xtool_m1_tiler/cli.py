"""Interfaccia a riga di comando."""
import argparse
import os
import sys

from .convert import Options, convert


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="xtool-m1-tiler",
        description="Converte un SVG in un file .xcs per xTool M1 dividendo l'incisione a riempimento in "
                    "gruppi compatti (colore + parametri diversi di 1 punto) per ridurre il tempo di lavoro.")
    ap.add_argument("svg", help="file SVG: incisione = forme con riempimento, taglio = tratto rosso senza riempimento")
    ap.add_argument("-o", "--output", help="file .xcs di uscita (default: accanto all'SVG)")
    ap.add_argument("--preview", help="PNG di anteprima con i gruppi colorati")
    ap.add_argument("--size", type=float, default=0.0, help="lato lungo in mm (0 = misura originale dell'SVG)")
    ap.add_argument("--thickness", type=float, default=2.0, help="spessore del materiale in mm (messa a fuoco)")
    ap.add_argument("--power", type=int, default=55, help="potenza incisione %%")
    ap.add_argument("--speed", type=float, default=150, help="velocita' incisione mm/s")
    ap.add_argument("--density", type=int, default=83, help="righe/cm: 100=0,1 mm, 83=0,12 mm, 67=0,15 mm")
    ap.add_argument("--cut-power", type=int, default=73)
    ap.add_argument("--cut-speed", type=float, default=10)
    ap.add_argument("--cut-passes", type=int, default=2)
    ap.add_argument("--max-groups", type=int, default=8, help="numero massimo di gruppi (oltre 4-6 il guadagno e' minimo)")
    ap.add_argument("--overhead", type=float, default=0.4, help="minuti persi per ogni gruppo in piu'")
    ap.add_argument("--cut-color", default="#ff0000", help="colore del tratto di taglio nell'SVG")
    a = ap.parse_args(argv)

    out = a.output or os.path.splitext(a.svg)[0] + ".xcs"
    prev = a.preview
    opt = Options(size_mm=a.size, thickness_mm=a.thickness, power=a.power, speed=a.speed, density=a.density,
                  cut_power=a.cut_power, cut_speed=a.cut_speed, cut_passes=a.cut_passes,
                  max_groups=a.max_groups, overhead_min=a.overhead, cut_color=a.cut_color)
    r = convert(a.svg, out, opt, prev)
    print(f"Scritto: {r.out_path}")
    print(f"Misura incisione: {r.size_mm[0]:.1f} x {r.size_mm[1]:.1f} mm, gruppi: {r.groups}")
    print(f"Incisione stimata: {r.minutes_single:.1f} min (un gruppo) -> {r.minutes_split:.1f} min (gruppi)")
    print(f"Taglio stimato: {r.cut_minutes:.1f} min")
    print("Stime da modello empirico: misura sempre il primo pezzo e prova su un ritaglio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
