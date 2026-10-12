"""Pages for the sedimentation basin design app."""
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import basin_calc as bc
import ui_theme as ui

ISOREMOVAL_URL = "https://isoremoval.streamlit.app"
WALKTHROUGH_URL = ""   # paste the walkthrough video link here once it's posted


def _qp(name, default):
    try:
        return float(st.query_params.get(name, default))
    except (TypeError, ValueError):
        return default


def _png(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    return buf.getvalue()


def _sidebar():
    with st.sidebar:
        st.markdown('<a class="skip-link" href="#step-1">Skip to the tool</a>', unsafe_allow_html=True)
        st.markdown("### On this page")
        st.markdown(
            "1. [Settling-column results](#step-1)\n"
            "2. [Design flow](#step-2)\n"
            "3. [Basin shape](#step-3)\n"
            "4. [Check the design](#step-4)\n"
            "5. [Drawings and summary](#step-5)"
        )
        st.markdown("### Before this")
        st.markdown(f"Get your overflow rate and detention time from the [Isoremoval curves tool]({ISOREMOVAL_URL}).")
        if WALKTHROUGH_URL:
            st.markdown(f"[Watch the walkthrough video]({WALKTHROUGH_URL})")
        st.markdown("### Display")
        st.caption("Light or dark follows your device. To change it, open the menu at the top right, then Settings.")
        st.caption("Built for CE 323 Environmental and Fluids Laboratory, Boise State University. "
                   "For learning; not certified for engineering design.")


# ---------------------------------------------------------------------------
# Drawings
# ---------------------------------------------------------------------------
def plan_figure(d, u, k):
    L, W = d["L"] * k, d["W"] * k
    with ui.figure_style() as c:
        fig, ax = plt.subplots(figsize=(10, 4.6))
        ax.add_patch(Rectangle((0, 0), L, W, facecolor=c["fill"], edgecolor=c["ink"], lw=2))
        ax.add_patch(Rectangle((0, 0), 0.1 * L, W, facecolor="none", edgecolor=c["blue"], lw=2, hatch="//"))
        ax.add_patch(Rectangle((0.9 * L, 0), 0.1 * L, W, facecolor="none", edgecolor=c["orange"], lw=2, hatch=".."))
        ax.text(0.05 * L, W / 2, "INLET", rotation=90, ha="center", va="center", fontweight="bold",
                bbox=dict(fc=c["paper"], ec="none", pad=2))
        ax.text(0.95 * L, W / 2, "OUTLET\nWEIRS", rotation=90, ha="center", va="center", fontweight="bold",
                bbox=dict(fc=c["paper"], ec="none", pad=2))
        ax.text(0.5 * L, 0.55 * W, "SETTLING ZONE", ha="center", va="center", fontsize=15, fontweight="bold")
        ax.add_patch(FancyArrowPatch((0.25 * L, 0.3 * W), (0.72 * L, 0.3 * W), arrowstyle="-|>", mutation_scale=22,
                                     color=c["ink"], lw=2))
        ax.text(0.485 * L, 0.36 * W, "flow", ha="center", fontsize=13, color=c["ink"])
        for y, txt, va in [(-0.1 * W, f"L = {L:.1f} {u}", "top")]:
            ax.annotate("", (0, y), (L, y), arrowprops=dict(arrowstyle="<->", color=c["ink"], lw=1.5))
            ax.text(L / 2, y - 0.03 * W, txt, ha="center", va=va, fontweight="bold")
        ax.annotate("", (-0.03 * L, 0), (-0.03 * L, W), arrowprops=dict(arrowstyle="<->", color=c["ink"], lw=1.5))
        ax.text(-0.045 * L, W / 2, f"W = {W:.1f} {u}", rotation=90, ha="right", va="center", fontweight="bold")
        ax.set_xlim(-0.12 * L, 1.03 * L)
        ax.set_ylim(-0.3 * W, 1.08 * W)
        ax.set_aspect("equal")
        ax.axis("off")
        fig.tight_layout()
    return fig


def profile_figure(d, u, k, freeboard_m):
    L, H, fb = d["L"] * k, d["H"] * k, freeboard_m * k
    with ui.figure_style() as c:
        fig, ax = plt.subplots(figsize=(10, 4.2))
        ax.add_patch(Rectangle((0, 0), L, H, facecolor=c["fill"], edgecolor="none"))
        ax.add_patch(Rectangle((0, 0), L, H + fb, facecolor="none", edgecolor=c["ink"], lw=2))
        ax.plot([0, L], [H, H], color=c["blue"], lw=2)
        ax.text(L * 0.99, H + fb * 0.5, "freeboard", ha="right", va="center", fontsize=11, color=c["ink2"])
        ax.text(L * 0.99, H * 0.985, "water surface", ha="right", va="top", fontsize=11, color=c["ink"])
        sl = 0.08 * H
        ax.add_patch(Rectangle((0, 0), L, sl, facecolor=c["maroon"], edgecolor="none", alpha=0.9, hatch="xx"))
        ax.text(L / 2, sl / 2, "sludge", ha="center", va="center", fontsize=11, fontweight="bold",
                color=c["paper"])
        ax.plot([0, L], [H, sl], color=c["ink"], lw=2, ls="--")
        ax.text(L * 0.42, H * 0.6, "path of a particle that settles at the overflow rate:\n"
                "it enters at the surface and just reaches the bottom at the outlet",
                ha="center", va="center", fontsize=11, bbox=dict(fc=c["paper"], ec="none", alpha=0.85))
        ax.annotate("", (L * 1.02, 0), (L * 1.02, H), arrowprops=dict(arrowstyle="<->", color=c["ink"], lw=1.5))
        ax.text(L * 1.03, H / 2, f"H = {H:.2f} {u}", rotation=90, va="center", ha="left", fontweight="bold")
        ax.annotate("", (0, -0.12 * H), (L, -0.12 * H), arrowprops=dict(arrowstyle="<->", color=c["ink"], lw=1.5))
        ax.text(L / 2, -0.16 * H, f"L = {L:.1f} {u}", ha="center", va="top", fontweight="bold")
        ax.set_xlim(-0.02 * L, 1.1 * L)
        ax.set_ylim(-0.35 * H, (H + fb) * 1.08)
        ax.axis("off")
        fig.tight_layout()
    return fig


def view_3d(d, u, k):
    c = ui.colors()
    L, W, H = d["L"] * k, d["W"] * k, d["H"] * k
    x = [0, L, L, 0, 0, L, L, 0]
    y = [0, 0, W, W, 0, 0, W, W]
    z = [0, 0, 0, 0, H, H, H, H]
    fig = go.Figure()
    for a, b in [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]]:
        fig.add_trace(go.Scatter3d(x=[x[a], x[b]], y=[y[a], y[b]], z=[z[a], z[b]], mode="lines",
                                   line=dict(color=c["ink"], width=4), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[H] * 4, color=c["blue"], opacity=0.35,
                            name="Water surface", showlegend=True, hoverinfo="skip"))
    fig.update_layout(
        scene=dict(xaxis_title=f"Length ({u})", yaxis_title=f"Width ({u})", zaxis_title=f"Depth ({u})",
                   aspectmode="data", bgcolor=c["paper"],
                   xaxis=dict(color=c["ink"]), yaxis=dict(color=c["ink"]), zaxis=dict(color=c["ink"])),
        paper_bgcolor=c["paper"], font=dict(family="Atkinson Hyperlegible Next, sans-serif", color=c["ink"], size=14),
        height=520, margin=dict(l=0, r=0, t=10, b=0), legend=dict(x=0, y=1),
    )
    return fig


# ---------------------------------------------------------------------------
# The tool
# ---------------------------------------------------------------------------
def tool_page():
    ui.inject_css()
    _sidebar()
    st.title("Sedimentation basin design")
    st.markdown(
        "Size a rectangular sedimentation basin from your settling-column results: the **overflow rate** and "
        "**detention time** that give your target removal, read from the "
        f"[Isoremoval curves tool]({ISOREMOVAL_URL})."
    )
    st.markdown("**How it works:** 1 enter your column results → 2 set the flow → 3 choose a depth and shape → "
                "4 check the design → 5 see the drawings and download a summary.")

    # ---------------- Step 1 ----------------
    ui.step_header(1, "Settling-column results", "step-1")
    from_link = any(k in st.query_params for k in ("vo", "t", "R"))
    if from_link:
        st.success("Values filled in from the Isoremoval curves tool. Check they match your Step 4 readout.",
                   icon=":material/check_circle:")
    a, b, c_ = st.columns(3, gap="medium")
    v0 = a.number_input("Overflow rate, v₀ (m/d)", min_value=0.1, max_value=5000.0, value=_qp("vo", 43.8), step=0.5,
                        help="From the overall removal vs. overflow rate plot, at your target removal.")
    t_h = b.number_input("Detention time, t (h)", min_value=0.05, max_value=48.0, value=_qp("t", 1.42), step=0.05,
                         format="%.2f", help="From the overall removal vs. detention time plot, at the same target.")
    target = c_.number_input("Target overall removal (%)", min_value=0.0, max_value=100.0, value=_qp("R", 70.0),
                             step=1.0, help="The removal these two values give. Recorded in your summary.")
    st.caption("The column depth is already built into these two numbers, so you don't enter it here. "
               "The basin depth you choose in Step 3 can be different.")

    with st.expander("Scale up for a full-size basin (optional)"):
        st.markdown(
            "A real basin settles less well than a quiet lab column (inlet and outlet disturbances, wind, "
            "short-circuiting). A common allowance is to multiply the column's overflow rate by **0.65–0.85** and "
            "its detention time by **1.25–1.50** before sizing (NPTEL, *Wastewater Treatment*, IIT Kharagpur, "
            "Module 16, Lecture 21). Use it if your instructor asks you to."
        )
        scale = st.toggle("Apply scale-up factors", value=False)
        s1, s2 = st.columns(2)
        f_o = s1.slider("Overflow-rate factor", 0.65, 0.85, 0.75, 0.05, disabled=not scale)
        f_t = s2.slider("Detention-time factor", 1.25, 1.50, 1.40, 0.05, disabled=not scale)

    # ---------------- Step 2 ----------------
    ui.step_header(2, "Design flow", "step-2")
    a, b, c_, d_ = st.columns([1.2, 1, 1, 1], gap="medium")
    unit_q = b.selectbox("Flow units", list(bc.FLOW_TO_M3D), index=0)
    Q_in = a.number_input(f"Plant flow, Q ({unit_q})", min_value=0.001, value=10000.0 if unit_q == "m³/d" else 1.0,
                          step=100.0 if unit_q == "m³/d" else 0.1, key=f"Q-{unit_q}")
    Q = Q_in * bc.FLOW_TO_M3D[unit_q]
    n = c_.number_input("Basins in parallel", min_value=1, max_value=20, value=2, step=1,
                        help="Two or more let one basin be drained for cleaning while the others run.")
    temp = d_.number_input("Water temperature (°C)", min_value=0.0, max_value=40.0, value=20.0, step=1.0,
                           help="Used only for the Reynolds number (water viscosity).")
    if unit_q != "m³/d":
        st.caption(f"{Q_in:,.3g} {unit_q} = {Q:,.0f} m³/d, so each basin takes {Q / n:,.0f} m³/d.")
    else:
        st.caption(f"Each basin takes {Q / n:,.0f} m³/d.")

    # ---------------- Step 3 ----------------
    ui.step_header(3, "Basin shape", "step-3")
    a, b = st.columns(2, gap="large")
    unit_l = a.radio("Show lengths in", ["m", "ft"], horizontal=True,
                     format_func=lambda x: "meters" if x == "m" else "feet")
    k = 1 / bc.LEN_TO_M[unit_l]
    mode = b.radio("Dimensions", ["auto", "manual"], horizontal=True,
                   format_func=lambda x: "Let the tool size it" if x == "auto" else "Enter my own")
    a, b, c_ = st.columns(3, gap="medium")
    H_disp = a.number_input(f"Side-water depth, H ({unit_l})", min_value=0.5 * k, max_value=10.0 * k,
                            value=round(3.5 * k, 1), step=0.1 * k, key=f"H-{unit_l}",
                            help="Water depth in the basin, typically 3–5 m (10–16 ft). Not the column depth.")
    H = H_disp / k
    fb_disp = b.number_input(f"Freeboard ({unit_l})", min_value=0.0, max_value=3.0 * k, value=round(0.5 * k, 1),
                             step=0.1 * k, key=f"fb-{unit_l}", help="Wall height above the water. Drawings only.")
    runs = c_.number_input("Outlet weir runs", min_value=1, max_value=20, value=2, step=1,
                           help="Each run is one basin width of weir. A launder across the basin has two sides, "
                                "so it adds two runs.")
    if mode == "auto":
        a, b = st.columns(2, gap="medium")
        lw = a.slider("Length : width", 2.0, 6.0, 4.0, 0.5, help="Typically 3:1 to 5:1 for even, plug-like flow.")
        sf = b.slider("Area safety factor", 1.0, 1.3, 1.0, 0.05,
                      help="The lecture suggests 1.1–1.2 if a margin is required.")
        d = bc.design(Q, v0, t_h, n, H, lw, sf, scale, f_o, f_t, runs, temp)
    else:
        guide = bc.design(Q, v0, t_h, n, H, 4.0, 1.0, scale, f_o, f_t, runs, temp)
        st.caption(f"Each basin needs at least {guide['A_required']:,.1f} m² of surface "
                   f"({guide['A_required'] * k * k:,.0f} {unit_l}²) at this depth.")
        a, b = st.columns(2, gap="medium")
        L_disp = a.number_input(f"Length, L ({unit_l})", min_value=1.0, value=round(guide["L"] * k, 1), step=0.5,
                                key=f"L-{unit_l}")
        W_disp = b.number_input(f"Width, W ({unit_l})", min_value=0.5, value=round(guide["W"] * k, 1), step=0.5,
                                key=f"W-{unit_l}")
        d = bc.design(Q, v0, t_h, n, H, 4.0, 1.0, scale, f_o, f_t, runs, temp, L_disp / k, W_disp / k)

    # ---------------- Step 4 ----------------
    ui.step_header(4, "Check the design", "step-4")
    m = st.columns(5)
    m[0].metric("Length", f"{d['L'] * k:,.1f} {unit_l}")
    m[1].metric("Width", f"{d['W'] * k:,.1f} {unit_l}")
    m[2].metric("Depth", f"{d['H'] * k:,.2f} {unit_l}")
    m[3].metric("Surface area", f"{d['A'] * k * k:,.0f} {unit_l}²")
    m[4].metric("Volume", f"{d['V']:,.0f} m³")
    st.markdown(f"Per basin, for {n} basin(s). The **{d['governs']}** sets the size at this depth: the overflow "
                f"rate needs {d['A_overflow']:,.1f} m² and the detention time needs {d['A_volume']:,.1f} m².")

    rows = bc.checks(d)
    fix = {
        "Overflow rate ≤ design value": "Make the basin bigger in plan (longer or wider), or add a basin.",
        "Detention time ≥ design value": "Make the basin deeper or bigger in plan, or add a basin.",
        "Side-water depth (typical)": "Choose a depth between 3 and 5 m.",
        "Length : width (typical)": "Choose a ratio between 3:1 and 5:1.",
        "Horizontal velocity": "Make the basin wider or deeper, or add a basin.",
        "Weir loading": "Add weir runs (launders), or add a basin.",
    }
    table = pd.DataFrame([{"Result": "✓ Pass" if ok else "✗ Review", "Check": name, "Target": tgt,
                           "Your design": act} for name, tgt, act, ok in rows])
    st.dataframe(table, hide_index=True, use_container_width=True)
    n_fail = sum(not ok for *_, ok in rows)
    if n_fail == 0:
        st.success("Every check passes.", icon=":material/check_circle:")
    else:
        st.warning(f"{n_fail} check(s) need review:\n\n" + "\n".join(
            f"- **{name}:** {fix[name]}" for name, _, _, ok in rows if not ok), icon=":material/warning:")
    st.caption("Overflow rate and detention time are your design requirements. Depth and length : width are the "
               "lecture's typical ranges. Horizontal velocity (≤ 1 ft/min) and weir loading (≤ 20,000 gpd/ft) are the "
               "limits in Virginia's waterworks regulations (12 VAC 5-590-872), which follow the Ten States Standards; "
               "your local code may differ.")
    st.markdown(f"Reynolds number Re = v·R/ν = **{d['Re']:,.0f}** (hydraulic radius R = {d['R_h']:.2f} m) and "
                f"Froude number Fr = v²/(g·R) = **{d['Fr']:.1e}**. These are for information: a full-size basin is "
                "turbulent, so what matters is keeping the horizontal velocity low.")

    with st.expander("The calculation, step by step"):
        sc = f" (column value × {f_o:g})" if scale else ""
        sc2 = f" (column value × {f_t:g})" if scale else ""
        st.markdown(
            f"1. Flow per basin: q = {Q:,.0f} ÷ {n} = **{d['q_per_basin']:,.0f} m³/d**\n"
            f"2. Design overflow rate v₀ = {d['v_design']:.2f} m/d{sc}; design detention time t = "
            f"{d['t_design']:.3f} h{sc2}\n"
            f"3. Area for the overflow rate: A = q ÷ v₀ = {d['q_per_basin']:,.0f} ÷ {d['v_design']:.2f} = "
            f"**{d['A_overflow']:,.1f} m²**\n"
            f"4. Area for the detention time at H = {H:.2f} m: A = q × t ÷ H = {d['q_per_basin']:,.0f} × "
            f"{d['t_design']:.3f} ÷ 24 ÷ {H:.2f} = **{d['A_volume']:,.1f} m²**\n"
            + (f"5. Use the larger, times the safety factor: A = {d['A_required']:,.1f} × {sf:g} = "
               f"**{d['A']:,.1f} m²**; W = √(A ÷ {lw:g}) = {d['W']:.2f} m, L = {lw:g} × W = {d['L']:.2f} m\n"
               if mode == "auto" else
               f"5. Your dimensions: A = {d['L']:.2f} × {d['W']:.2f} = **{d['A']:,.1f} m²**\n")
            + f"6. Volume V = A × H = {d['A']:,.1f} × {H:.2f} = **{d['V']:,.0f} m³**\n"
            f"7. Check: overflow rate = q ÷ A = **{d['overflow']:.2f} m/d**; detention time = V ÷ q × 24 = "
            f"**{d['detention']:.2f} h**\n"
            f"8. Horizontal velocity = q ÷ (W × H) = {d['vh_cm_s']:.3f} cm/s; weir loading = q ÷ "
            f"({runs} × W) = {d['weir_loading']:,.0f} m³/d per m"
        )

    # ---------------- Step 5 ----------------
    ui.step_header(5, "Drawings and summary", "step-5")
    t1, t2, t3 = st.tabs(["Plan (from above)", "Profile (from the side)", "3D"])
    with t1:
        ui.figure_description(f"One basin seen from above: {d['L'] * k:.1f} {unit_l} long and {d['W'] * k:.1f} "
                              f"{unit_l} wide, with the inlet zone on the left, the settling zone in the middle and "
                              "the outlet weirs on the right. Water flows left to right.")
        f_plan = plan_figure(d, unit_l, k)
        st.pyplot(f_plan, use_container_width=True)
    with t2:
        ui.figure_description(f"The same basin from the side: {d['H'] * k:.2f} {unit_l} of water above a sludge "
                              f"layer, with {fb_disp:g} {unit_l} of freeboard. The dashed line is the path of a "
                              "particle that settles exactly at the overflow rate.")
        f_prof = profile_figure(d, unit_l, k, fb_disp / k)
        st.pyplot(f_prof, use_container_width=True)
    with t3:
        ui.figure_description("A 3D outline of one basin. Drag to turn it; the plan and profile tabs show the same "
                              "dimensions.")
        st.plotly_chart(view_3d(d, unit_l, k), use_container_width=True)

    summary = pd.DataFrame({
        "Parameter": ["Target overall removal", "Column overflow rate", "Column detention time", "Scale-up applied",
                      "Design overflow rate", "Design detention time", "Plant flow", "Basins", "Flow per basin",
                      "Length", "Width", "Side-water depth", "Freeboard", "Surface area (each)", "Volume (each)",
                      "Length : width", "Actual overflow rate", "Actual detention time", "Horizontal velocity",
                      "Weir length (each)", "Weir loading", "Reynolds number", "Froude number", "Checks passed"],
        "Value": [f"{target:g} %", f"{v0:g} m/d", f"{t_h:g} h", f"yes (×{f_o:g}, ×{f_t:g})" if scale else "no",
                  f"{d['v_design']:.2f} m/d", f"{d['t_design']:.3f} h", f"{Q:,.0f} m³/d", f"{n}",
                  f"{d['q_per_basin']:,.0f} m³/d", f"{d['L'] * k:.2f} {unit_l}", f"{d['W'] * k:.2f} {unit_l}",
                  f"{d['H'] * k:.2f} {unit_l}", f"{fb_disp:g} {unit_l}", f"{d['A']:,.1f} m²", f"{d['V']:,.0f} m³",
                  f"{d['lw']:.2f}:1", f"{d['overflow']:.2f} m/d", f"{d['detention']:.2f} h",
                  f"{d['vh_cm_s']:.3f} cm/s", f"{d['weir_length']:.1f} m", f"{d['weir_loading']:,.0f} m³/d per m",
                  f"{d['Re']:,.0f}", f"{d['Fr']:.1e}", f"{len(rows) - n_fail} of {len(rows)}"],
    })
    st.subheader("Design summary")
    st.dataframe(summary, hide_index=True, use_container_width=True)
    with st.expander("Rough material quantities"):
        wall = st.number_input("Wall and floor thickness (m)", 0.1, 1.0, 0.3, 0.05)
        Hw = d["H"] + fb_disp / k
        concrete = n * (d["L"] * d["W"] * wall + 2 * (d["L"] + d["W"]) * Hw * wall)
        excav = n * d["L"] * d["W"] * (Hw + wall)
        st.markdown(f"- Concrete for {n} basin(s): about **{concrete:,.0f} m³**\n"
                    f"- Excavation: about **{excav:,.0f} m³**\n- Footprint: **{n * d['A']:,.0f} m²**")
        st.caption("Simple box estimate for comparing options; it leaves out inlet and outlet structures, sludge "
                   "hoppers and site work.")
    x = BytesIO()
    with pd.ExcelWriter(x, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        table.to_excel(xw, sheet_name="Checks", index=False)
    c1, c2 = st.columns(2)
    c1.download_button("Summary and checks (.xlsx)", x.getvalue(), "basin_design.xlsx", icon=":material/download:",
                       use_container_width=True)
    c2.download_button("Summary (.csv)", summary.to_csv(index=False).encode(), "basin_design.csv",
                       icon=":material/download:", use_container_width=True)
    c3, c4 = st.columns(2)
    c3.download_button("Plan drawing (.png)", _png(f_plan), "basin_plan.png", icon=":material/download:",
                       use_container_width=True)
    c4.download_button("Profile drawing (.png)", _png(f_prof), "basin_profile.png", icon=":material/download:",
                       use_container_width=True)
    plt.close("all")


def accessibility_page():
    ui.inject_css()
    _sidebar()
    st.title("Accessibility")
    st.markdown("These are the choices behind this tool and where it still falls short. "
                "The target is WCAG 2.1 level AA.")
    st.markdown(
        "- Text is set in **Atkinson Hyperlegible Next** (Braille Institute) at 18 px, with lines of about "
        "70 characters and two weights.\n"
        "- Light mode is near-black on warm paper and dark mode is white on black, both above 4.5:1 contrast; the "
        "theme follows your device (menu at the top right, then Settings).\n"
        "- **Colour is never the only cue.** Checks say Pass or Review in words with a ✓ or ✗; the drawings label "
        "every zone in text and use hatching as well as colour. Colours follow Jack Baker's figure palette and "
        "were checked under simulated colour blindness (Machado, Oliveira and Fernandes, 2009).\n"
        "- Every drawing has a sentence above it saying what it shows, and every number is in the summary table "
        "and the downloads.\n"
        "- Everything works with a keyboard and shows a thick focus outline; buttons and fields are at least "
        "48 px tall; animations stop if your device asks for reduced motion."
    )
    st.subheader("What still falls short")
    st.markdown(
        "- Drawings are images; screen readers get the description and the tables, not the picture.\n"
        "- The 3D view is Plotly's and is hard to use without a mouse. The plan and profile show the same "
        "dimensions.\n"
        "- If something doesn't work for you, tell your instructor or open an issue on "
        "[GitHub](https://github.com/gregor-posadas/Sedimentation-Basin-Generator/issues).")
