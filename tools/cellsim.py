"""Run ngspice on the cells and measure them.

Every function builds a small deck, runs ngspice in batch mode and returns
plain numbers (volts, seconds, joules), so the tests and the report use the
same code.
"""
import os
import subprocess
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "sim")

# corner name: (supply in volts, temperature in Celsius)
CORNERS = {"tt": (1.80, 25), "ss": (1.60, 100), "ff": (1.95, -40)}

# cell name: number of inputs
CELLS = {"inv": 1, "nand2": 2, "nor2": 2}


def _instance(cell, in_node, other):
    """Instance line with `in_node` on input a and `other` on input b."""
    if CELLS[cell] == 1:
        return f"X1 {in_node} y vdd 0 {cell}"
    return f"X1 {in_node} {other} y vdd 0 {cell}"


def _enable_level(cell):
    """Level on the other input that lets input a control the output."""
    return "vdd" if cell == "nand2" else "0"


def _run(deck, outfile):
    """Run a deck in the sim folder and return the columns of `outfile`."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, outfile)
        deck = deck.replace("OUTFILE", out)
        path = os.path.join(tmp, "deck.cir")
        with open(path, "w") as f:
            f.write(deck)
        res = subprocess.run(["ngspice", "-b", path], cwd=SIM,
                             capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError("ngspice failed:\n" + res.stdout[-2000:]
                               + res.stderr[-2000:])
        return np.loadtxt(out)


def _header(corner):
    vdd, temp = CORNERS[corner]
    return (f"* generated deck\n"
            f".include \"{SIM}/models_{corner}.lib\"\n"
            f".include \"{ROOT}/cells/cells.spice\"\n"
            f".temp {temp}\n"
            f"Vdd vdd 0 {vdd}\n"), vdd


def logic_level(cell, inputs, corner="tt"):
    """Output voltage divided by the supply for fixed 0/1 inputs."""
    head, vdd = _header(corner)
    nodes = []
    src = ""
    for k, bit in enumerate(inputs):
        src += f"Vi{k} i{k} 0 {vdd if bit else 0}\n"
        nodes.append(f"i{k}")
    deck = (head + src + f"X1 {' '.join(nodes)} y vdd 0 {cell}\n"
            ".control\nop\nwrdata OUTFILE v(y)\n.endc\n.end\n")
    data = np.atleast_1d(_run(deck, "op.txt"))
    return float(data[-1]) / vdd


def transfer_curve(cell, corner="tt", step=0.002):
    """Sweep input a from 0 to the supply. Returns (vin, vout, vdd)."""
    head, vdd = _header(corner)
    deck = (head + "Vin a 0 0\n" + _instance(cell, "a", _enable_level(cell))
            + f"\n.control\ndc Vin 0 {vdd} {step}\n"
            "wrdata OUTFILE v(y)\n.endc\n.end\n")
    data = _run(deck, "dc.txt")
    return data[:, 0], data[:, 1], vdd


def dc_figures(cell, corner="tt"):
    """Switching threshold and noise margins from the transfer curve.

    V_IL and V_IH are the two inputs where the slope of the curve is -1.
    NM_L = V_IL - V_OL and NM_H = V_OH - V_IH, with V_OH and V_OL taken
    as the outputs at input 0 and input = supply.
    """
    vin, vout, vdd = transfer_curve(cell, corner)
    slope = np.gradient(vout, vin)
    steep = np.where(slope <= -1.0)[0]
    vil, vih = vin[steep[0]], vin[steep[-1]]
    vm = vin[np.argmin(np.abs(vout - vin))]
    voh, vol = vout[0], vout[-1]
    return {"vdd": vdd, "vm": float(vm), "vil": float(vil), "vih": float(vih),
            "voh": float(voh), "vol": float(vol),
            "nml": float(vil - vol), "nmh": float(voh - vih),
            "gain": float(-slope.min())}


def _cross(t, v, level, rising, t_from=0.0):
    """First time after t_from where v crosses level in the given direction."""
    for k in range(1, len(t)):
        if t[k] < t_from:
            continue
        a, b = v[k - 1], v[k]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return t[k - 1] + (level - a) * (t[k] - t[k - 1]) / (b - a)
    raise ValueError("no crossing found")


def switching(cell, load=5e-15, corner="tt", slew=50e-12):
    """One rising and one falling input edge on input a with a load capacitor.

    Returns the two propagation delays (50 % to 50 %), the output edge
    times (20 % to 80 %) and the energy taken from the supply for one
    full cycle of the output (one fall and one rise).
    """
    head, vdd = _header(corner)
    t1, t2, tend = 1e-9, 4e-9, 7e-9
    deck = (head
            + f"Vin a 0 pwl(0 0 {t1} 0 {t1 + slew} {vdd} "
              f"{t2} {vdd} {t2 + slew} 0)\n"
            + _instance(cell, "a", _enable_level(cell)) + "\n"
            + f"CL y 0 {load}\n"
            + f".control\ntran 1p {tend}\n"
              "wrdata OUTFILE v(a) v(y) i(Vdd)\n.endc\n.end\n")
    d = _run(deck, "tran.txt")
    t, va, vy, idd = d[:, 0], d[:, 1], d[:, 3], d[:, 5]
    half = vdd / 2
    lo, hi = 0.2 * vdd, 0.8 * vdd
    # input rises at t1, output falls
    tphl = _cross(t, vy, half, False, t1) - _cross(t, va, half, True, t1)
    tfall = _cross(t, vy, lo, False, t1) - _cross(t, vy, hi, False, t1)
    # input falls at t2, output rises
    tplh = _cross(t, vy, half, True, t2) - _cross(t, va, half, False, t2)
    trise = _cross(t, vy, hi, True, t2) - _cross(t, vy, lo, True, t2)

    def energy(a, b):
        m = (t >= a) & (t <= b)
        # i(Vdd) is negative when the supply delivers current
        ti, ii = t[m], idd[m]
        area = np.sum((ii[1:] + ii[:-1]) * np.diff(ti)) / 2
        return float(-vdd * area)

    return {"tphl": tphl, "tplh": tplh, "tfall": tfall, "trise": trise,
            "e_cycle": energy(t1 - 0.2e-9, tend), "vdd": vdd}


def delay_fit(cell, corner="tt", loads=(1e-15, 2e-15, 5e-15, 10e-15, 20e-15)):
    """Straight-line fit of delay against load: delay = t0 + 0.69 R C.

    Returns the delay without load t0 and the equivalent output resistance
    R for the falling and the rising output, plus the raw points.
    """
    pts = [switching(cell, c, corner) for c in loads]
    out = {"loads": list(loads), "points": pts}
    for key in ("tphl", "tplh"):
        k, t0 = np.polyfit(loads, [p[key] for p in pts], 1)
        out[key] = {"t0": float(t0), "r": float(k / 0.69)}
    return out
