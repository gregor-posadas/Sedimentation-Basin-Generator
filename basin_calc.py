"""Rectangular sedimentation basin sizing from settling-column results.

Inputs come from the isoremoval tool: the overflow rate v0 (m/d) and detention
time t (h) that give the target overall removal in the settling column.

Sizing (the CE 323 lecture's design procedure):
  area  A = Q / v0              (overflow rate sets the surface area)
  volume V = Q x t              (detention time sets the volume)
  For a chosen side-water depth H, the area must satisfy both, so
  A = max(Q / v0, Q x t / H) x safety factor, then L and W from the L:W ratio.
  Checks: actual overflow rate = Q / A,  actual detention time = A x H / Q.

Optional scale-up: column results are optimistic for a full-scale basin, so the
column overflow rate is often multiplied by 0.65-0.85 and the detention time by
1.25-1.50 (NPTEL, Wastewater Treatment, IIT Kharagpur, Module 16 Lecture 21).

Changes from the October 2025 version, and why:
- Checks now test the direction that matters: detention time must be at least
  the design value and overflow rate at most the design value. The old checks
  asked for a match within 10 %, so a safely oversized basin "failed".
- Horizontal velocity and weir loading have upper limits only (slower and
  lighter are never a problem for settling). Limits follow Virginia's
  waterworks regulations, which track the Ten States Standards:
  velocity <= 1.0 ft/min (0.508 cm/s), weir loading <= 20,000 gpd/ft (248 m3/d per m).
- Weir length is no longer assumed to be two basin widths ("weirs at both
  ends"); outlet weirs sit at the outlet end, and each launder adds length.
- The Reynolds number uses the hydraulic radius R = W H / (W + 2H) and is shown
  for information. Full-scale basins are turbulent, so the old "Re < 2000"
  pass/fail check failed every realistic design.
"""
import math

FLOW_TO_M3D = {
    "m³/d": 1.0,
    "m³/h": 24.0,
    "L/s": 86.4,
    "MGD": 3785.411784,
    "gpm": 5.450992,   # 1 US gal/min = 3.785411784 L/min
}
LEN_TO_M = {"m": 1.0, "ft": 0.3048}

# Lecture's typical ranges (CE 323 design procedure) and regulatory limits
TYPICAL = {
    "depth_m": (3.0, 5.0),
    "lw": (3.0, 5.0),
    "overflow_m_d": (None, 60.0),       # "typically <= 40-60 m/d"
    "detention_h": (2.0, None),         # "typically >= 2-4 h"
}
LIMITS = {
    "horizontal_velocity_cm_s": 0.3048 / 60 * 100,   # 1.0 ft/min
    "weir_loading_m3_d_m": 20000 * 0.003785411784 / 0.3048,  # 20,000 gpd/ft
}
SCALE_UP = {"overflow": (0.65, 0.85), "detention": (1.25, 1.50)}


def nu_water(temp_c):
    """Kinematic viscosity of water (m²/s), Vogel equation, 0-40 °C (within ~1 %)."""
    mu = 2.414e-5 * 10 ** (247.8 / (temp_c + 273.15 - 140.0))  # Pa·s
    rho = 1000.0 * (1 - (temp_c + 288.9414) / (508929.2 * (temp_c + 68.12963)) * (temp_c - 3.9863) ** 2)
    return mu / rho


def design(Q_m3d, v0_m_d, t_h, n_basins=2, depth_m=3.5, lw=4.0, safety=1.0,
           scale=False, f_overflow=0.75, f_detention=1.40, weir_runs=1, temp_c=20.0,
           L_m=None, W_m=None):
    """Size one of n identical basins. Give L_m and W_m to check a basin you sized yourself."""
    q = Q_m3d / n_basins
    v_design = v0_m_d * (f_overflow if scale else 1.0)
    t_design = t_h * (f_detention if scale else 1.0)
    A_overflow = q / v_design
    A_volume = q * t_design / 24.0 / depth_m
    A_req = max(A_overflow, A_volume)
    governs = "overflow rate" if A_overflow >= A_volume else "detention time"
    if L_m is None or W_m is None:
        A = A_req * safety
        W = math.sqrt(A / lw)
        L = W * lw
    else:
        L, W = float(L_m), float(W_m)
        A = L * W
    V = A * depth_m
    overflow = q / A
    detention = V / q * 24.0
    vh = q / 86400.0 / (W * depth_m)                    # m/s
    weir_len = W * max(weir_runs, 1)
    weir = q / weir_len
    R_h = W * depth_m / (W + 2 * depth_m)
    nu = nu_water(temp_c)
    Re = vh * R_h / nu
    Fr = vh ** 2 / (9.81 * R_h)
    return {
        "q_per_basin": q, "v_design": v_design, "t_design": t_design,
        "A_overflow": A_overflow, "A_volume": A_volume, "A_required": A_req, "governs": governs,
        "L": L, "W": W, "H": depth_m, "A": A, "V": V, "lw": L / W,
        "overflow": overflow, "detention": detention,
        "vh_cm_s": vh * 100, "weir_length": weir_len, "weir_loading": weir,
        "R_h": R_h, "Re": Re, "Fr": Fr, "nu": nu,
    }


def checks(d):
    """(criterion, target text, actual value, passes) for each design check."""
    out = []
    out.append(("Overflow rate ≤ design value", f"≤ {d['v_design']:.1f} m/d", f"{d['overflow']:.1f} m/d",
                d["overflow"] <= d["v_design"] * 1.0001))
    out.append(("Detention time ≥ design value", f"≥ {d['t_design']:.2f} h", f"{d['detention']:.2f} h",
                d["detention"] >= d["t_design"] * 0.9999))
    lo, hi = TYPICAL["depth_m"]
    out.append(("Side-water depth (typical)", f"{lo:g}–{hi:g} m", f"{d['H']:.2f} m", lo <= d["H"] <= hi))
    lo, hi = TYPICAL["lw"]
    out.append(("Length : width (typical)", f"{lo:g}:1 – {hi:g}:1", f"{d['lw']:.1f}:1",
                lo - 1e-9 <= d["lw"] <= hi + 1e-9))
    lim = LIMITS["horizontal_velocity_cm_s"]
    out.append(("Horizontal velocity", f"≤ {lim:.2f} cm/s (1 ft/min)", f"{d['vh_cm_s']:.3f} cm/s",
                d["vh_cm_s"] <= lim))
    lim = LIMITS["weir_loading_m3_d_m"]
    out.append(("Weir loading", f"≤ {lim:.0f} m³/d per m", f"{d['weir_loading']:.0f} m³/d per m",
                d["weir_loading"] <= lim))
    return out
