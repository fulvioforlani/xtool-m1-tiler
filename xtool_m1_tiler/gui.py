"""Interfaccia grafica minimale (Tkinter): scegli l'SVG, imposta i parametri, converti."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .convert import Options, convert


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("xtool-m1-tiler - SVG -> .xcs per xTool M1")
        self.geometry("720x560")
        self.svg = tk.StringVar()
        self.vars = {}
        top = ttk.Frame(self, padding=10); top.pack(fill="x")
        ttk.Entry(top, textvariable=self.svg, width=60).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Scegli SVG...", command=self.pick).pack(side="left", padx=6)
        grid = ttk.LabelFrame(self, text="Parametri", padding=10); grid.pack(fill="x", padx=10)
        fields = [("Lato lungo (mm, 0 = originale)", "size", "0"), ("Spessore materiale (mm)", "thickness", "2"),
                  ("Incisione: potenza %", "power", "55"), ("Incisione: velocita' mm/s", "speed", "150"),
                  ("Incisione: righe/cm (100=0,1 mm)", "density", "83"), ("Taglio: potenza %", "cut_power", "73"),
                  ("Taglio: velocita' mm/s", "cut_speed", "10"), ("Taglio: passate", "cut_passes", "2"),
                  ("Gruppi massimi", "max_groups", "8"), ("Minuti persi per gruppo", "overhead", "0.4")]
        for i, (lab, key, dflt) in enumerate(fields):
            ttk.Label(grid, text=lab).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=4, pady=3)
            v = tk.StringVar(value=dflt); self.vars[key] = v
            ttk.Entry(grid, textvariable=v, width=8).grid(row=i // 2, column=(i % 2) * 2 + 1, padx=4)
        ttk.Button(self, text="Converti e salva .xcs", command=self.run).pack(pady=10)
        self.out = tk.Text(self, height=14); self.out.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log("Importa un SVG: incisione = forme con riempimento, taglio = tratto rosso senza riempimento.")

    def log(self, s):
        self.out.insert("end", s + "\n"); self.out.see("end")

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("SVG", "*.svg")])
        if p:
            self.svg.set(p)

    def run(self):
        try:
            v = {k: x.get().replace(",", ".") for k, x in self.vars.items()}
            opt = Options(size_mm=float(v["size"]), thickness_mm=float(v["thickness"]), power=int(float(v["power"])),
                          speed=float(v["speed"]), density=int(float(v["density"])), cut_power=int(float(v["cut_power"])),
                          cut_speed=float(v["cut_speed"]), cut_passes=int(float(v["cut_passes"])),
                          max_groups=int(float(v["max_groups"])), overhead_min=float(v["overhead"]))
            src = self.svg.get()
            out = os.path.splitext(src)[0] + ".xcs"
            prev = os.path.splitext(src)[0] + "_anteprima.png"
            r = convert(src, out, opt, prev)
            self.log(f"Scritto: {out}\nAnteprima: {prev}")
            self.log(f"Misura incisione {r.size_mm[0]:.1f} x {r.size_mm[1]:.1f} mm, gruppi: {r.groups}")
            self.log(f"Incisione: {r.minutes_single:.1f} min -> {r.minutes_split:.1f} min; taglio {r.cut_minutes:.1f} min (stime)")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Errore", str(e))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
