"""Checks for basin_calc.py. Run:  python tests/test_basin.py"""
import os, sys, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import basin_calc as bc


def test_lecture_example():
    # CE 323 design procedure: Q = 5,000 m³/d, v0 = 37.9 m/d -> A = 132 m²; H = 4 m -> V = 528 m³, t = 2.53 h
    d = bc.design(5000, 37.9, t_h=1.0, n_basins=1, depth_m=4.0, lw=4.0)
    assert d["governs"] == "overflow rate"
    assert abs(d["A"] - 131.9) < 0.1
    assert abs(d["V"] - 527.7) < 0.5
    assert abs(d["detention"] - 2.53) < 0.01


def test_detention_can_govern():
    d = bc.design(5000, 37.9, t_h=4.0, n_basins=1, depth_m=3.0)
    assert d["governs"] == "detention time"
    assert abs(d["detention"] - 4.0) < 1e-9 and d["overflow"] < 37.9


def test_both_requirements_always_met_in_auto_mode():
    for t in (0.5, 1.5, 3, 6):
        for H in (2.5, 3.5, 5):
            d = bc.design(12000, 30, t, n_basins=3, depth_m=H, lw=4)
            c = {name: ok for name, _, _, ok in bc.checks(d)}
            assert c["Overflow rate ≤ design value"] and c["Detention time ≥ design value"]


def test_safety_factor_and_scale_up():
    base = bc.design(5000, 40, 2, n_basins=1, depth_m=4)
    sf = bc.design(5000, 40, 2, n_basins=1, depth_m=4, safety=1.15)
    assert abs(sf["A"] / base["A"] - 1.15) < 1e-9
    up = bc.design(5000, 40, 2, n_basins=1, depth_m=4, scale=True, f_overflow=0.75, f_detention=1.4)
    assert abs(up["v_design"] - 30) < 1e-9 and abs(up["t_design"] - 2.8) < 1e-9


def test_manual_dimensions():
    d = bc.design(5000, 37.9, 1.0, n_basins=1, depth_m=4, L_m=20, W_m=7)
    assert d["A"] == 140 and abs(d["lw"] - 20 / 7) < 1e-12
    assert abs(d["overflow"] - 5000 / 140) < 1e-9


def test_unit_conversions():
    assert abs(bc.FLOW_TO_M3D["MGD"] - 3785.41) < 0.01
    assert abs(bc.FLOW_TO_M3D["L/s"] - 86.4) < 1e-12
    assert abs(bc.LIMITS["horizontal_velocity_cm_s"] - 0.508) < 0.001
    assert abs(bc.LIMITS["weir_loading_m3_d_m"] - 248.4) < 0.1


def test_viscosity():
    assert abs(bc.nu_water(20) * 1e6 - 1.002) < 0.01   # matches the Fluids Report 3 table
    assert abs(bc.nu_water(10) * 1e6 - 1.307) < 0.02


def test_hydraulic_radius_and_weir():
    d = bc.design(10000, 40, 2, n_basins=1, depth_m=4, lw=4, weir_runs=3)
    assert abs(d["R_h"] - d["W"] * 4 / (d["W"] + 8)) < 1e-12
    assert abs(d["weir_length"] - 3 * d["W"]) < 1e-12


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); n += 1
    print(f"{n} checks passed")
