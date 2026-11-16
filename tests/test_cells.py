"""Checks on the three cells. Run with:  python3 -m pytest tests"""
import itertools
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import cellsim  # noqa: E402

TRUTH = {
    "inv": lambda a: not a,
    "nand2": lambda a, b: not (a and b),
    "nor2": lambda a, b: not (a or b),
}
CELLS = list(cellsim.CELLS)
CORNERS = list(cellsim.CORNERS)
LOADS = (1e-15, 2e-15, 5e-15, 10e-15, 20e-15)


@pytest.fixture(scope="module")
def fits():
    """Delay against load for every cell and corner, simulated once."""
    return {(c, k): cellsim.delay_fit(c, k, LOADS)
            for c in CELLS for k in CORNERS}


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("corner", CORNERS)
def test_truth_table(cell, corner):
    """Every input combination gives a clean 0 or 1 at the output."""
    n = cellsim.CELLS[cell]
    for bits in itertools.product((0, 1), repeat=n):
        level = cellsim.logic_level(cell, bits, corner)
        if TRUTH[cell](*bits):
            assert level > 0.99, (bits, level)
        else:
            assert level < 0.01, (bits, level)


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("corner", CORNERS)
def test_transfer_curve(cell, corner):
    """Threshold near the middle, steep curve, usable noise margins."""
    f = cellsim.dc_figures(cell, corner)
    assert 0.35 * f["vdd"] < f["vm"] < 0.65 * f["vdd"]
    assert f["vil"] < f["vm"] < f["vih"]
    assert f["gain"] > 5
    assert f["nml"] > 0.3 * f["vdd"]
    assert f["nmh"] > 0.3 * f["vdd"]


@pytest.mark.parametrize("cell", CELLS)
@pytest.mark.parametrize("corner", CORNERS)
def test_delay_grows_with_load(cell, corner, fits):
    """More load, more delay, and close to a straight line."""
    fit = fits[(cell, corner)]
    for key in ("tphl", "tplh"):
        d = [p[key] for p in fit["points"]]
        assert all(b > a for a, b in zip(d, d[1:]))
        t0, r = fit[key]["t0"], fit[key]["r"]
        assert t0 > 0 and r > 0
        for c, measured in zip(LOADS, d):
            line = t0 + 0.69 * r * c
            assert abs(measured - line) < 0.1 * measured + 2e-12


@pytest.mark.parametrize("cell", CELLS)
def test_corner_order(cell, fits):
    """The slow corner is slower than typical, the fast corner faster."""
    for key in ("tphl", "tplh"):
        d = {k: fits[(cell, k)]["points"][2][key] for k in CORNERS}
        assert d["ff"] < d["tt"] < d["ss"]


def test_series_transistors_cost_drive(fits):
    """Two transistors in series give a higher output resistance."""
    inv = fits[("inv", "tt")]
    assert fits[("nand2", "tt")]["tphl"]["r"] > 1.3 * inv["tphl"]["r"]
    assert fits[("nor2", "tt")]["tplh"]["r"] > 1.3 * inv["tplh"]["r"]
    # the side without series transistors stays close to the inverter
    assert fits[("nand2", "tt")]["tplh"]["r"] < 1.2 * inv["tplh"]["r"]
    assert fits[("nor2", "tt")]["tphl"]["r"] < 1.2 * inv["tphl"]["r"]


@pytest.mark.parametrize("cell", CELLS)
def test_energy_follows_c_v_squared(cell, fits):
    """Each extra farad of load costs Vdd squared joules per cycle."""
    pts = fits[(cell, "tt")]["points"]
    vdd = pts[0]["vdd"]
    for c, p in zip(LOADS, pts):
        assert p["e_cycle"] > c * vdd ** 2
    extra = pts[-1]["e_cycle"] - pts[0]["e_cycle"]
    expected = (LOADS[-1] - LOADS[0]) * vdd ** 2
    assert abs(extra - expected) < 0.1 * expected
