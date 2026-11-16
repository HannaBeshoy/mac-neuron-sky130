"""Measure all cells at all corners and write results/cells.md and plots."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cellsim

OUT = os.path.join(cellsim.ROOT, "results")
LOADS = (1e-15, 2e-15, 5e-15, 10e-15, 20e-15)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {}
    for cell in cellsim.CELLS:
        for corner in cellsim.CORNERS:
            data[f"{cell}/{corner}"] = {
                "dc": cellsim.dc_figures(cell, corner),
                "fit": cellsim.delay_fit(cell, corner, LOADS),
            }
    with open(os.path.join(OUT, "cells.json"), "w") as f:
        json.dump(data, f, indent=1)

    # transfer curves, typical corner
    fig, ax = plt.subplots(figsize=(5, 4))
    for cell in cellsim.CELLS:
        vin, vout, vdd = cellsim.transfer_curve(cell, "tt")
        ax.plot(vin, vout, label=cell)
    ax.plot([0, vdd], [0, vdd], "k:", linewidth=0.8, label="output = input")
    ax.set_xlabel("input a (V)")
    ax.set_ylabel("output (V)")
    ax.set_title("Transfer curves, typical corner, 1.8 V, 25 °C")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "transfer_curves.png"), dpi=150)

    # inverter transfer curve at the three corners
    fig, ax = plt.subplots(figsize=(5, 4))
    for corner in cellsim.CORNERS:
        vin, vout, vdd = cellsim.transfer_curve("inv", corner)
        ax.plot(vin, vout, label=f"{corner}, {vdd:.2f} V")
    ax.set_xlabel("input (V)")
    ax.set_ylabel("output (V)")
    ax.set_title("Inverter transfer curve at the three corners")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "inverter_corners.png"), dpi=150)

    # delay against load, typical corner
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    for ax, key, title in zip(axes, ("tphl", "tplh"),
                              ("output falling", "output rising")):
        for cell in cellsim.CELLS:
            pts = data[f"{cell}/tt"]["fit"]["points"]
            ax.plot([c * 1e15 for c in LOADS],
                    [p[key] * 1e12 for p in pts], "o-", label=cell)
        ax.set_xlabel("load (fF)")
        ax.set_title(f"Delay, {title}")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("delay (ps)")
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "delay_vs_load.png"), dpi=150)

    lines = ["# Stage 1 results: three cells at transistor level", "",
             "Written by `tools/report.py`. Input edge 50 ps, input a "
             "switching, the other input held at the level that lets a "
             "control the output.", "",
             "## Transfer curve", "",
             "| Cell | Corner | Supply (V) | Threshold (V) | V_IL (V) | "
             "V_IH (V) | NM_L (V) | NM_H (V) | Peak gain |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, d in data.items():
        cell, corner = name.split("/")
        f = d["dc"]
        lines.append(f"| {cell} | {corner} | {f['vdd']:.2f} | {f['vm']:.3f} "
                     f"| {f['vil']:.3f} | {f['vih']:.3f} | {f['nml']:.3f} "
                     f"| {f['nmh']:.3f} | {f['gain']:.1f} |")
    lines += ["", "![transfer curves](transfer_curves.png)", "",
              "![inverter at three corners](inverter_corners.png)", "",
              "## Delay and energy with a 5 fF load", "",
              "| Cell | Corner | Fall delay (ps) | Rise delay (ps) | "
              "Fall time (ps) | Rise time (ps) | Energy per cycle (fJ) | "
              "Load part C·Vdd² (fJ) |",
              "|---|---|---|---|---|---|---|---|"]
    for name, d in data.items():
        cell, corner = name.split("/")
        p = d["fit"]["points"][2]
        lines.append(f"| {cell} | {corner} | {p['tphl']*1e12:.1f} "
                     f"| {p['tplh']*1e12:.1f} | {p['tfall']*1e12:.1f} "
                     f"| {p['trise']*1e12:.1f} | {p['e_cycle']*1e15:.1f} "
                     f"| {5e-15*p['vdd']**2*1e15:.1f} |")
    lines += ["", "## Delay against load", "",
              "Straight-line fit `delay = t0 + 0.69 · R · C` over loads of "
              "1, 2, 5, 10 and 20 fF.", "",
              "| Cell | Corner | Fall t0 (ps) | Fall R (kΩ) | Rise t0 (ps) "
              "| Rise R (kΩ) |",
              "|---|---|---|---|---|---|"]
    for name, d in data.items():
        cell, corner = name.split("/")
        f = d["fit"]
        lines.append(f"| {cell} | {corner} | {f['tphl']['t0']*1e12:.1f} "
                     f"| {f['tphl']['r']/1e3:.2f} "
                     f"| {f['tplh']['t0']*1e12:.1f} "
                     f"| {f['tplh']['r']/1e3:.2f} |")
    lines += ["", "![delay against load](delay_vs_load.png)", ""]
    with open(os.path.join(OUT, "cells.md"), "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
