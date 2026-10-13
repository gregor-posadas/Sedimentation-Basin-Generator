"""Pages for the sedimentation basin design app: the tool (with its teaching text) and accessibility notes."""
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import basin_calc as bc
import ui_theme as ui
from explainers import LINKS, PICS
import basin_anim
import streamlit.components.v1 as components
from ui_theme import term, md

ISOREMOVAL_URL = "https://isoremoval.streamlit.app/"
WALKTHROUGH_URL = ""   # paste the walkthrough video link here once it's posted

D = {
    "overflow": "The flow divided by the basin's surface area (Q ÷ A), in m/d. It equals the settling speed a particle "
                "needs to fall the full depth before the water carrying it reaches the outlet. Also called the surface "
                "loading rate.",
    "detention": "How long water stays in the basin on average: volume ÷ flow (V ÷ Q).",
    "swd": "Side-water depth: the depth of water in the basin, from the floor to the water surface. Not the same as "
           "the settling column's depth.",
    "freeboard": "Extra wall height above the water surface, so waves and surges don't spill over.",
    "lw": "Length ÷ width. Long, narrow basins keep the flow even from inlet to outlet (close to plug flow), so "
          "less water short-circuits straight to the outlet.",
    "weir": "The outlet edge the clarified water spills over into a channel (a launder). Spreading the outflow over a "
            "longer weir keeps the water near the outlet slow, so it doesn't pull settled flocs back up.",
    "launder": "A trough that collects water from the outlet weirs. A launder running across the basin has a weir on "
               "both sides, so each one adds two basin-widths of weir.",
    "vh": "How fast water moves along the basin: flow ÷ the cross-section it flows through (width × depth). Too fast "
          "and it can sweep settled sludge back up (scour).",
    "weirload": "Flow divided by total weir length, in m³/d per metre of weir. Lower is gentler at the outlet.",
    "re": "Reynolds number: compares how strongly the water keeps moving to how strongly viscosity damps it. Real "
          "basins are turbulent (large Re); what matters for design is keeping velocity low.",
    "fr": "Froude number: compares the flow's speed with gravity's pull. Very small values mean the flow is easily "
          "disturbed by wind or temperature differences.",
    "scale": "Lab columns are perfectly still; real basins have inlet jets, wind, temperature currents and dead "
             "zones. Scale-up factors make the design conservative to allow for that.",
    "sf": "A multiplier on the required surface area to leave a margin, for example 1.1 for 10 % extra.",
    "hazen": "In an ideal basin, a particle is caught if it can sink the full depth H in the time the water takes to "
             "cross the basin. That time is V ÷ Q = A·H ÷ Q, so the particle needs a speed of at least Q ÷ A: the "
             "overflow rate. Depth cancels out.",
}


def T(text, key):
    return term(text, D[key], more=LINKS.get(key), pic=PICS.get(key))


def _qp(name, default):
    try:
        return float(st.query_params.get(name, default))
    except (TypeError, ValueError):
        return default


def _sidebar():
    with st.sidebar:
        st.markdown('<a class="skip-link" href="#step-1">Skip to the tool</a>', unsafe_allow_html=True)
        st.markdown("### On this page")
        st.markdown(
            "0. [New here? The idea](#the-idea)\n"
            "1. [Your column results](#step-1)\n"
            "2. [Design flow](#step-2)\n"
            "3. [Basin shape](#step-3)\n"
            "4. [Check the design](#step-4)\n"
            "5. [See it work](#step-5)\n"
            "6. [Summary](#step-6)"
        )
        st.markdown("### Before this")
        st.markdown(f"Get your overflow rate and detention time from the [Isoremoval curves tool]({ISOREMOVAL_URL}).")
        if WALKTHROUGH_URL:
            st.markdown(f"[Watch the walkthrough video]({WALKTHROUGH_URL})")
        st.markdown("### Display")
        st.caption("Opens in light mode. To switch to dark, open the menu at the top right, then Settings. "
                   "Dotted-underlined words explain themselves: hover, tap, or press Enter on them.")
        st.caption("Built for CE 323 Environmental and Fluids Laboratory, Boise State University. "
                   "For learning; not certified for engineering design.")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def particle_figure(d, u, k, vs_list, fb_m):
    """Side view of one basin with particle paths for chosen settling speeds (m/d)."""
    L, H, fb = d["L"] * k, d["H"] * k, fb_m * k
    v0 = d["overflow"]          # actual overflow rate of this basin, m/d
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, x1=L, y0=0, y1=H, fillcolor="#dbe6f3", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=0, x1=L, y0=0, y1=0.06 * H, fillcolor="#8c6b5a", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=0, x1=L, y0=0, y1=H + fb, line=dict(color=ui.INK, width=2), fillcolor="rgba(0,0,0,0)")
    fig.add_shape(type="line", x0=0, x1=L, y0=H, y1=H, line=dict(color=ui.BLUE, width=2))
    fig.add_annotation(x=0.5 * L, y=0.03 * H, text="sludge", showarrow=False, font=dict(color="#ffffff", size=13))
    fig.add_annotation(x=0.02 * L, y=H, yanchor="bottom", xanchor="left", text="water surface", showarrow=False,
                       font=dict(size=13, color=ui.INK2))
    # flow arrow above the drawing, where no particle path can cross it
    fig.add_annotation(x=0.62, y=1.0, xref="paper", yref="paper", ax=-150, ay=0, axref="pixel", ayref="pixel",
                       text="", showarrow=True, arrowhead=3, arrowsize=1.3, arrowwidth=2.2, arrowcolor=ui.INK, yshift=14)
    fig.add_annotation(x=0.5, y=1.0, xref="paper", yref="paper", text="water flows this way", showarrow=False,
                       yanchor="bottom", yshift=20, font=dict(size=13, color=ui.INK))
    styles = [("solid", ui.BLUE), ("dash", ui.ORANGE), ("dot", ui.MAROON), ("dashdot", "#2f6b4f")]
    for (vs, start), (dash, col) in zip(vs_list, styles):
        # horizontal travel: L over detention time; vertical: vs. Fraction of L travelled when it hits bottom:
        z0 = start * H                       # starting height above the floor
        x_hit = L * (z0 / H) * (v0 / vs) if vs > 0 else np.inf
        caught = x_hit <= L + 1e-9
        x_end = min(x_hit, L)
        z_end = 0.06 * H if caught else z0 - (z0 / x_hit) * L if np.isfinite(x_hit) else z0
        z_end = max(z_end, 0.06 * H)
        label = (f"{vs:g} m/d from {'the surface' if start >= 0.999 else f'{start * 100:.0f} % of the depth'}: "
                 + ("caught" if caught else "escapes"))
        fig.add_trace(go.Scatter(
            x=[0, x_end], y=[z0, z_end], mode="lines+markers", name=label, cliponaxis=False,
            line=dict(color=col, width=3, dash=dash),
            marker=dict(symbol=["circle", "circle" if caught else "x"], size=[10, 14], color=col,
                        line=dict(color="#ffffff", width=1)),
            hovertemplate=(f"<b>Particle settling at {vs:g} m/d</b><br>"
                           + ("Reaches the floor " + f"{x_end / L * 100:.0f} % of the way along" if caught
                              else "Still in suspension at the outlet") + "<extra></extra>")))
    ui.base_layout(fig, height=330, legend_title="Particle paths", n_items=len(vs_list), per_row=1, top=56,
                   title="Particle paths through the basin")
    fig.update_xaxes(**ui.style_axes(fig, automargin=False, title_standoff=14, title_text=f"Distance along the basin ({u})",
                                     range=[-0.01 * L, L * 1.01]))
    fig.update_yaxes(**ui.style_axes(fig, title_text=f"Height above the floor ({u})", range=[0, (H + fb) * 1.04],
                                     showgrid=False))
    fig.update_xaxes(showgrid=False)
    return fig


def plan_figure(d, u, k, runs):
    L, W = d["L"] * k, d["W"] * k
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, x1=L, y0=0, y1=W, fillcolor="#dbe6f3", line=dict(color=ui.INK, width=2),
                  layer="below")
    fig.add_shape(type="rect", x0=0, x1=0.08 * L, y0=0, y1=W, fillcolor="rgba(56,95,150,0.25)",
                  line=dict(color=ui.BLUE, width=1.5), layer="below")
    # launders: weir runs drawn as lines near the outlet end
    n_l = max(1, runs // 2) if runs > 1 else 0
    xs = np.linspace(0.84 * L, 0.97 * L, n_l) if n_l else []
    for x in xs:
        fig.add_shape(type="line", x0=x, x1=x, y0=0.04 * W, y1=0.96 * W, line=dict(color=ui.ORANGE, width=5))
    if runs == 1 or runs % 2:
        fig.add_shape(type="line", x0=L, x1=L, y0=0, y1=W, line=dict(color=ui.ORANGE, width=6))
    fig.add_annotation(x=0.04 * L, y=W / 2, text="inlet", textangle=-90, showarrow=False,
                       font=dict(size=14, color=ui.INK))
    fig.add_annotation(x=0.45 * L, y=W / 2, text="settling zone", showarrow=False, yshift=12,
                       font=dict(size=15, color=ui.INK))
    fig.add_annotation(x=0.56 * L, y=W / 2, ax=0.34 * L, ay=W / 2, axref="x", ayref="y", text="", showarrow=True,
                       arrowhead=3, arrowsize=1.3, arrowwidth=2.2, arrowcolor=ui.INK, yshift=-10)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=f"Outlet weirs ({runs} runs of W)",
                             line=dict(color=ui.ORANGE, width=5)))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Inlet zone",
                             marker=dict(symbol="square", size=14, color="rgba(56,95,150,0.4)", line=dict(color=ui.BLUE, width=1))))
    ui.base_layout(fig, height=int(np.clip(680 * W / L, 140, 340)), legend_title=None, n_items=2, per_row=2,
                   title="Plan view of one basin")
    fig.update_xaxes(**ui.style_axes(fig, automargin=False, title_standoff=14, title_text=f"Length, L = {L:.1f} {u}",
                                     range=[-0.01 * L, 1.01 * L]))
    fig.update_yaxes(**ui.style_axes(fig, title_text=f"W = {W:.1f} {u}", range=[-0.02 * W, 1.02 * W],
                                     scaleanchor="x", scaleratio=1, constrain="domain", showgrid=False))
    fig.update_xaxes(showgrid=False)
    return fig


def view_3d(d, u, k):
    L, W, H = d["L"] * k, d["W"] * k, d["H"] * k
    x = [0, L, L, 0, 0, L, L, 0]
    y = [0, 0, W, W, 0, 0, W, W]
    z = [0, 0, 0, 0, H, H, H, H]
    fig = go.Figure()
    for a, b in [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]]:
        fig.add_trace(go.Scatter3d(x=[x[a], x[b]], y=[y[a], y[b]], z=[z[a], z[b]], mode="lines",
                                   line=dict(color=ui.INK, width=4), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[H] * 4, color=ui.BLUE, opacity=0.35,
                            name="Water surface", showlegend=True, hoverinfo="skip"))
    fig.update_layout(
        scene=dict(xaxis_title=f"Length ({u})", yaxis_title=f"Width ({u})", zaxis_title=f"Depth ({u})",
                   aspectmode="data", bgcolor="#ffffff"),
        paper_bgcolor="#ffffff", font=dict(family=ui.FONT, color=ui.INK, size=14),
        height=520, margin=dict(l=0, r=0, t=54, b=0),
        title=dict(text="<b>3D view of one basin</b>", x=0.5, xanchor="center", y=1, yref="container", yanchor="top",
                   pad=dict(t=14), font=dict(size=17, color=ui.INK, family=ui.FONT)),
        legend=dict(x=0.01, y=0.99, bgcolor="#ffffff", bordercolor=ui.INK, borderwidth=1),
    )
    return fig


def _drawings_zip(d, u, k, fb_m, runs):
    import io, zipfile
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    rc = {"font.family": ["Open Sans", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": "#857e6e",
          "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white"}
    L, W, H, fb = d["L"] * k, d["W"] * k, d["H"] * k, fb_m * k
    figs = []
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(6.5, 3.2), layout="constrained")
        ax.add_patch(Rectangle((0, 0), L, H, fc="#dbe6f3", ec="none", label="Water"))
        ax.add_patch(Rectangle((0, 0), L, 0.06 * H, fc="#8c6b5a", ec="none", label="Sludge zone"))
        ax.add_patch(Rectangle((0, 0), L, H + fb, fc="none", ec=ui.INK, lw=1.4))
        ax.plot([0, L], [H, H], color=ui.BLUE, lw=1.2, label=f"Water surface (depth {H:.1f} {u})")
        ax.plot([0, L], [H, 0.06 * H], color=ui.INK, lw=1.2, ls="--",
                label=f"Particle settling at the overflow rate ({d['overflow']:.1f} m/d)")
        ax.set_xlim(-0.015 * L, 1.015 * L); ax.set_ylim(-0.04 * (H + fb), (H + fb) * 1.06)
        ax.set_xlabel(f"Distance along the basin ({u})", labelpad=6); ax.set_ylabel(f"Height above the floor ({u})", labelpad=8)
        fig.legend(loc="outside lower center", ncol=2, frameon=True, edgecolor=ui.INK, fancybox=False, fontsize=9)
        fig.suptitle("Side view of one basin", fontweight="bold", fontsize=12.5)
        figs.append(("basin_side_view", fig))
        fig, ax = plt.subplots(figsize=(6.5, 2.9), layout="constrained")
        ax.add_patch(Rectangle((0, 0), L, W, fc="#dbe6f3", ec=ui.INK, lw=1.4))
        ax.add_patch(Rectangle((0, 0), 0.08 * L, W, fc="#b3c6e0", ec=ui.BLUE, lw=1, label="Inlet zone"))
        n_l = max(1, runs // 2) if runs > 1 else 0
        for i, x in enumerate(np.linspace(0.84 * L, 0.97 * L, n_l) if n_l else []):
            ax.plot([x, x], [0.04 * W, 0.96 * W], color=ui.ORANGE, lw=3, label=f"Outlet weirs ({runs} runs of W)" if i == 0 else None)
        if runs == 1 or runs % 2:
            ax.plot([L, L], [0, W], color=ui.ORANGE, lw=3, label=None if n_l else f"Outlet weir ({runs} run of W)")
        ax.set_aspect("equal"); ax.set_xlim(-0.015 * L, 1.015 * L); ax.set_ylim(-0.04 * W, 1.04 * W)
        ax.set_xlabel(f"Length, L = {L:.1f} {u}", labelpad=6); ax.set_ylabel(f"Width, W = {W:.1f} {u}", labelpad=8)
        fig.legend(loc="outside lower center", ncol=2, frameon=True, edgecolor=ui.INK, fancybox=False, fontsize=9)
        fig.suptitle("Plan view of one basin", fontweight="bold", fontsize=12.5)
        figs.append(("basin_plan_view", fig))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, f in figs:
            for ext, kw in (("png", {"dpi": 300}), ("svg", {})):
                b = io.BytesIO(); f.savefig(b, format=ext, bbox_inches="tight", **kw); z.writestr(f"{name}.{ext}", b.getvalue())
            plt.close(f)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# The tool
# ---------------------------------------------------------------------------
def tool_page():
    ui.setup_page()
    _sidebar()
    st.title("Sedimentation basin design")
    md(f'<p class="lede">Size a rectangular sedimentation basin from your settling-column results: the '
       f'{T("overflow rate", "overflow")} and {T("detention time", "detention")} that give your target removal, read '
       f'from the <a href="{ISOREMOVAL_URL}">Isoremoval curves tool</a>. Each step explains what it is doing and why.</p>')

    st.header("New here? The idea in three minutes", anchor="the-idea")
    with st.expander("Read this first if you haven't designed a basin before", expanded=True):
        md(f"""
<p><b>What the basin does.</b> Water enters at one end, crosses slowly, and leaves over {T('weirs', 'weir')} at the other end. While
it crosses, particles sink. A particle is removed if it reaches the floor before the water carrying it reaches the
outlet.</p>
<p><b>The key result.</b> The water takes V ÷ Q to cross, and a particle starting at the surface must sink the full
depth H in that time. Since V = A × H, the speed it needs is H ÷ (A·H ÷ Q) = <b>Q ÷ A</b>, the
{T("overflow rate", "overflow")}. Depth cancels out: {T("removal depends on surface area", "hazen")}, not depth.
So the overflow rate you read from the column test fixes the basin's <b>surface area</b>: A = Q ÷ v₀.</p>
<p><b>Why detention time still matters.</b> Flocs keep growing while they settle, so they also need enough
<b>time</b>. The detention time from the column fixes the basin's <b>volume</b>: V = Q × t. For a chosen depth, that
is another minimum area, V ÷ H. The basin must satisfy both, so the larger area wins.</p>
<p><b>Then practical checks.</b> A sensible depth, a long narrow shape, slow-moving water and a gentle outlet. Step 4
checks each one and says what to change if it fails.</p>
""")

    # ---------------- Step 1 ----------------
    ui.step_header(1, "Your column results", "step-1")
    from_link = any(k_ in st.query_params for k_ in ("vo", "t", "R"))
    if from_link:
        st.success("Filled in from the Isoremoval curves tool. Check these match its Step 6 readout.",
                   icon=":material/check_circle:")
    else:
        md(f"Enter the two values you read off the design plots in the "
           f"<a href=\"{ISOREMOVAL_URL}\">Isoremoval curves tool</a> for your target removal. The defaults are the "
           "lecture's sample data at 70 %.")
    a, b, c_ = st.columns(3, gap="medium")
    v0 = a.number_input("Overflow rate, v₀ (m/d)", min_value=0.1, max_value=5000.0, value=_qp("vo", 43.79), step=0.5,
                        help="From the overall removal vs. overflow rate plot, at your target removal.")
    t_h = b.number_input("Detention time, t (h)", min_value=0.05, max_value=48.0, value=_qp("t", 1.422), step=0.05,
                         format="%.3f", help="From the overall removal vs. detention time plot, at the same target.")
    target = c_.number_input("Target overall removal (%)", min_value=0.0, max_value=100.0, value=_qp("R", 70.0),
                             step=1.0, help="The removal these two values give. Recorded in your summary.")
    md("These two numbers already contain the column's depth, so you don't enter it here. The basin's own depth "
       "(Step 3) can be different.")
    with st.expander("Scale up for a full-size basin (optional)"):
        md(f"<p>A lab column is perfectly still. A real basin is not, so it settles less well. A common allowance "
           f"({T('why?', 'scale')}) multiplies the column's overflow rate by <b>0.65–0.85</b> and its detention time by "
           f"<b>1.25–1.50</b> before sizing (NPTEL, <i>Wastewater Treatment</i>, IIT Kharagpur, Module 16, Lecture 21). "
           f"Use it if your instructor asks you to.</p>")
        scale = st.toggle("Apply scale-up factors", value=False)
        s1, s2 = st.columns(2)
        f_o = s1.slider("Overflow-rate factor", 0.65, 0.85, 0.75, 0.05, disabled=not scale)
        f_t = s2.slider("Detention-time factor", 1.25, 1.50, 1.40, 0.05, disabled=not scale)

    # ---------------- Step 2 ----------------
    ui.step_header(2, "Design flow", "step-2")
    md("How much water the plant must treat, and how many basins share it. Two or more basins let one be drained for "
       "cleaning while the others keep running.")
    a, b = st.columns(2, gap="large")
    c_, d_ = st.columns(2, gap="large")
    unit_q = b.selectbox("Flow units", list(bc.FLOW_TO_M3D), index=0)
    Q_in = a.number_input(f"Plant flow, Q ({unit_q})", min_value=0.001, value=10000.0 if unit_q == "m³/d" else 1.0,
                          step=100.0 if unit_q == "m³/d" else 0.1, key=f"Q-{unit_q}")
    Q = Q_in * bc.FLOW_TO_M3D[unit_q]
    n = c_.number_input("Basins in parallel", min_value=1, max_value=20, value=2, step=1)
    temp = d_.number_input("Water temperature (°C)", min_value=0.0, max_value=40.0, value=20.0, step=1.0,
                           help="Only used for the Reynolds number (colder water is more viscous).")
    st.caption((f"{Q_in:,.3g} {unit_q} = {Q:,.0f} m³/d. " if unit_q != "m³/d" else "")
               + f"Each basin takes {Q / n:,.0f} m³/d.")

    # ---------------- Step 3 ----------------
    ui.step_header(3, "Basin shape", "step-3")
    md(f"Choose the {T('side-water depth', 'swd')} and either a {T('length-to-width ratio', 'lw')} (the tool then "
       f"finds the smallest basin that meets both column values) or your own length and width, plus the "
       f"{T('freeboard', 'freeboard')} above the water.")
    a, b = st.columns(2, gap="large")
    unit_l = a.segmented_control("Show lengths in", ["m", "ft"], default="m",
                                 format_func=lambda x: "metres" if x == "m" else "feet") or "m"
    k = 1 / bc.LEN_TO_M[unit_l]
    mode = b.segmented_control("Dimensions", ["auto", "manual"], default="auto",
                               format_func=lambda x: "Let the tool size it" if x == "auto" else "Enter my own") or "auto"
    a, b, c_ = st.columns(3, gap="medium")
    H_disp = a.number_input(f"Side-water depth, H ({unit_l})", min_value=0.5 * k, max_value=10.0 * k,
                            value=round(3.5 * k, 1), step=0.1 * k, key=f"H-{unit_l}",
                            help="Typically 3–5 m (10–16 ft).")
    H = H_disp / k
    fb_disp = b.number_input(f"Freeboard ({unit_l})", min_value=0.0, max_value=3.0 * k, value=round(0.5 * k, 1),
                             step=0.1 * k, key=f"fb-{unit_l}", help="Wall height above the water. Drawings only.")
    runs = c_.number_input("Outlet weir runs", min_value=1, max_value=20, value=2, step=1,
                           help="Each run is one basin-width of weir. A launder across the basin adds two.")
    if mode == "auto":
        a, b = st.columns(2, gap="medium")
        lw = a.slider("Length : width", 2.0, 6.0, 4.0, 0.5, help="Typically 3:1 to 5:1.")
        sf = b.slider("Area safety factor", 1.0, 1.3, 1.0, 0.05, help="1.1–1.2 leaves a margin.")
        d = bc.design(Q, v0, t_h, n, H, lw, sf, scale, f_o, f_t, runs, temp)
    else:
        guide = bc.design(Q, v0, t_h, n, H, 4.0, 1.0, scale, f_o, f_t, runs, temp)
        md(f"Each basin needs at least **{guide['A_required']:,.1f} m²** of surface "
           f"({guide['A_required'] * k * k:,.0f} {unit_l}²) at this depth.")
        a, b = st.columns(2, gap="medium")
        L_disp = a.number_input(f"Length, L ({unit_l})", min_value=1.0, value=round(guide["L"] * k, 1), step=0.5,
                                key=f"L-{unit_l}")
        W_disp = b.number_input(f"Width, W ({unit_l})", min_value=0.5, value=round(guide["W"] * k, 1), step=0.5,
                                key=f"W-{unit_l}")
        sf = 1.0
        lw = L_disp / W_disp
        d = bc.design(Q, v0, t_h, n, H, 4.0, 1.0, scale, f_o, f_t, runs, temp, L_disp / k, W_disp / k)

    # ---------------- Step 4 ----------------
    ui.step_header(4, "Check the design", "step-4")
    m = st.columns(4)
    m[0].metric("Length", f"{d['L'] * k:,.1f} {unit_l}")
    m[1].metric("Width", f"{d['W'] * k:,.1f} {unit_l}")
    m[2].metric("Surface area", f"{d['A'] * k * k:,.0f} {unit_l}²")
    m[3].metric("Volume", f"{d['V']:,.0f} m³")
    ui.idea("Which requirement sets the size", f"""
<p>Per basin: the overflow rate needs {d['A_overflow']:,.1f} m² of surface (q ÷ v₀), and the detention time needs
{d['A_volume']:,.1f} m² at {H:.2f} m deep (q × t ÷ H). The larger one, the <b>{d['governs']}</b>, sets the size.
{"Making the basin deeper won't shrink it: the overflow rate depends only on surface area." if d['governs'] == 'overflow rate'
 else "A deeper basin would need less surface area, until the overflow rate takes over."}</p>""")

    rows = bc.checks(d)
    why = {
        "Overflow rate ≤ design value": f"{T('Overflow rate', 'overflow')} = q ÷ A. At or below the column value, "
                                        "particles that settle at that speed are caught.",
        "Detention time ≥ design value": f"{T('Detention time', 'detention')} = V ÷ q. At least the column value gives "
                                         "flocs time to grow and settle.",
        "Side-water depth (typical)": f"{T('Side-water depth', 'swd')}: shallow basins are easily stirred by wind; very "
                                      "deep ones cost more to build.",
        "Length : width (typical)": f"{T('Length : width', 'lw')} keeps the flow even along the basin.",
        "Horizontal velocity": f"{T('Horizontal velocity', 'vh')} = q ÷ (W × H). Slow water won't scour settled sludge.",
        "Weir loading": f"{T('Weir loading', 'weirload')} = q ÷ total weir length. Low loading keeps the outlet gentle.",
    }
    fix = {
        "Overflow rate ≤ design value": "Make the basin bigger in plan (longer or wider), or add a basin.",
        "Detention time ≥ design value": "Make the basin deeper or bigger in plan, or add a basin.",
        "Side-water depth (typical)": "Choose a depth between 3 and 5 m.",
        "Length : width (typical)": "Choose a ratio between 3:1 and 5:1.",
        "Horizontal velocity": "Make the basin wider or deeper, or add a basin.",
        "Weir loading": f"Add weir runs ({T('launders', 'launder')} across the basin), or add a basin.",
    }
    table = pd.DataFrame([{"Result": "✓ Pass" if ok else "✗ Review", "Check": name, "Target": tgt,
                           "Your design": act} for name, tgt, act, ok in rows])
    st.dataframe(table, hide_index=True, use_container_width=True)
    n_fail = sum(not ok for *_, ok in rows)
    if n_fail == 0:
        st.success("Every check passes.", icon=":material/check_circle:")
    else:
        md(f"**{n_fail} check(s) need review.** " + " ".join(
            f"<b>{name}:</b> {fix[name]}" for name, _, _, ok in rows if not ok))
    with st.expander("What each check means"):
        md("\n".join(f"- **{name}.** {why[name]}" for name, *_ in rows))
        md(f"Depth and length : width are the lecture's typical ranges. Horizontal velocity (≤ 1 ft/min) and weir loading "
           f"(≤ 20,000 gpd/ft) are the limits in Virginia's waterworks regulations (12 VAC 5-590-872), which follow the "
           f"Ten States Standards; your local code may differ.")
        md(f"For information: {T('Reynolds number', 're')} Re = {d['Re']:,.0f} (hydraulic radius {d['R_h']:.2f} m) and "
           f"{T('Froude number', 'fr')} Fr = {d['Fr']:.1e}.")
    with st.expander("The calculation, step by step"):
        sc = f" (column value × {f_o:g})" if scale else ""
        sc2 = f" (column value × {f_t:g})" if scale else ""
        md(f"1. Flow per basin: q = {Q:,.0f} ÷ {n} = **{d['q_per_basin']:,.0f} m³/d**\n"
           f"2. Design values: v₀ = {d['v_design']:.2f} m/d{sc}; t = {d['t_design']:.3f} h{sc2}\n"
           f"3. Area for the overflow rate: A = q ÷ v₀ = {d['q_per_basin']:,.0f} ÷ {d['v_design']:.2f} = "
           f"**{d['A_overflow']:,.1f} m²**\n"
           f"4. Area for the detention time: A = q × t ÷ H = {d['q_per_basin']:,.0f} × {d['t_design']:.3f} ÷ 24 ÷ "
           f"{H:.2f} = **{d['A_volume']:,.1f} m²**\n"
           + (f"5. Larger of the two × {T('safety factor', 'sf')}: A = {d['A_required']:,.1f} × {sf:g} = **{d['A']:,.1f} m²**; "
              f"W = √(A ÷ {lw:g}) = {d['W']:.2f} m, L = {lw:g} × W = {d['L']:.2f} m\n" if mode == "auto" else
              f"5. Your dimensions: A = {d['L']:.2f} × {d['W']:.2f} = **{d['A']:,.1f} m²**\n")
           + f"6. Volume: V = A × H = {d['A']:,.1f} × {H:.2f} = **{d['V']:,.0f} m³**\n"
           f"7. Check: overflow rate q ÷ A = **{d['overflow']:.2f} m/d**; detention time V ÷ q × 24 = "
           f"**{d['detention']:.2f} h**\n"
           f"8. Horizontal velocity q ÷ (W × H) = {d['vh_cm_s']:.3f} cm/s; weir loading q ÷ ({runs} × W) = "
           f"{d['weir_loading']:,.0f} m³/d per m")

    # ---------------- Step 5 ----------------
    ui.step_header(5, "See it work", "step-5")
    dist = basin_anim.parse_dist(st.query_params.get("vs", ""))
    md(f"Here is one of your basins, drawn to your dimensions, running. Particles enter across the inlet, the flow "
       f"carries them toward the outlet weir, and each sinks at its own speed. Those speeds come from "
       + ("**your own settling-column results**" if dist else "the lecture's sample settling-column results")
       + f": if the p % isoremoval curve gave an overflow rate v, then p % of the particles settle at v or faster. "
       f"Blue particles will reach the floor in time; orange ones will be carried out. Caught particles pile up as "
       f"sludge, thickest near the inlet where the fast ones land. Try the **Flow** slider: more flow means a higher "
       f"overflow rate and less time, so more particles escape.")
    components.html(basin_anim.build(d["L"], d["W"], d["H"], d["q_per_basin"], d["overflow"], d["detention"], dist,
                                     bool(dist)), height=620, scrolling=False)
    st.caption("Time is sped up so the water crosses in a few seconds; every settling speed keeps its true ratio to the "
               "overflow rate, so the share caught matches the ideal-basin removal. In a real basin, sludge is scraped "
               "to a hopper and pumped out regularly; the Remove sludge button does that here.")
    st.subheader("Test one particle")
    md(f"The side view shows one basin and the paths of particles that settle at different speeds. Water carries "
       f"each particle along while it sinks, so it moves in a straight, sloping line. This basin's overflow rate is "
       f"**{d['overflow']:.1f} m/d**: any particle at least that fast reaches the floor before the outlet, even from "
       f"the surface.")
    a, b = st.columns(2, gap="large")
    vs = a.slider("Settling speed of a particle to test (m/d)", 1.0, float(max(10.0, round(d['overflow'] * 3))),
                  float(round(d["overflow"] * 0.6, 1)), 0.5,
                  help="Compare it with the overflow rate. Slower particles are caught only if they start low enough.")
    start = b.slider("Where it starts (share of the depth above the floor)", 0.1, 1.0, 1.0, 0.05,
                     help="1.0 = at the water surface.")
    paths = [(round(d["overflow"], 1), 1.0), (vs, start)]
    pdesc = (f"Side view of one basin, {d['L'] * k:.1f} {unit_l} long and {d['H'] * k:.2f} {unit_l} deep. A particle "
             f"settling at the overflow rate, {d['overflow']:.1f} m/d, starts at the surface and just reaches the floor at "
             f"the outlet. The test particle settles at {vs:g} m/d from {start * 100:.0f} % of the depth and is "
             + ("caught." if vs >= d['overflow'] * start - 1e-9 else "carried out of the basin."))
    ui.figure_description(pdesc)
    st.plotly_chart(particle_figure(d, unit_l, k, paths, fb_disp / k), theme=None, key="particles",
                    config=ui.plot_config("basin_particle_paths"), alt=pdesc)
    caught_frac = min(1.0, vs / d["overflow"])
    ui.idea("What this shows", f"""
<p>A particle slower than the overflow rate is caught only if it starts low enough: at {vs:g} m/d, the bottom
<b>{caught_frac * 100:.0f} %</b> of the depth (that is, {vs:g} ÷ {d['overflow']:.1f}). This is exactly why
overall removal in the column test is higher than the curve's own percentage: slow particles that started part-way
down are caught too.</p>""")

    t1, t2 = st.tabs(["Plan (from above)", "3D"])
    with t1:
        pl = (f"One basin from above, {d['L'] * k:.1f} by {d['W'] * k:.1f} {unit_l}, with the inlet zone at the left and "
              f"{runs} runs of outlet weir at the right. Water flows left to right.")
        ui.figure_description(pl)
        st.plotly_chart(plan_figure(d, unit_l, k, runs), theme=None, key="plan", config=ui.plot_config("basin_plan"),
                        alt=pl)
    with t2:
        ui.figure_description("A 3D outline of one basin. Drag to turn it; the other views show the same dimensions.")
        st.plotly_chart(view_3d(d, unit_l, k), theme=None, key="three", config=ui.plot_config("basin_3d"),
                        alt="3D outline of one basin")

    # ---------------- Step 6 ----------------
    ui.step_header(6, "Summary", "step-6")
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
    st.dataframe(summary, hide_index=True, use_container_width=True)
    with st.expander("Rough material quantities"):
        wall = st.number_input("Wall and floor thickness (m)", 0.1, 1.0, 0.3, 0.05)
        Hw = d["H"] + fb_disp / k
        concrete = n * (d["L"] * d["W"] * wall + 2 * (d["L"] + d["W"]) * Hw * wall)
        excav = n * d["L"] * d["W"] * (Hw + wall)
        md(f"- Concrete for {n} basin(s): about **{concrete:,.0f} m³**\n- Excavation: about **{excav:,.0f} m³**\n"
           f"- Footprint: **{n * d['A']:,.0f} m²**")
        st.caption("A simple box estimate for comparing options; it leaves out inlet and outlet structures, sludge "
                   "hoppers and site work.")
    x = BytesIO()
    with pd.ExcelWriter(x, engine="openpyxl") as xw:
        summary.to_excel(xw, sheet_name="Summary", index=False)
        table.to_excel(xw, sheet_name="Checks", index=False)
    c1, c2 = st.columns(2)
    c1.download_button("Download summary and checks (.xlsx)", x.getvalue(), "basin_design.xlsx",
                       icon=":material/download:", use_container_width=True)
    c2.download_button("Download summary (.csv)", summary.to_csv(index=False).encode(), "basin_design.csv",
                       icon=":material/download:", use_container_width=True)
    st.download_button("Download drawings (.zip)", _drawings_zip(d, unit_l, k, fb_disp / k, runs), "basin_drawings.zip",
                       icon=":material/download:", use_container_width=True)
    st.caption("The drawings download has a report-ready side view and plan view of one basin, each as a 300 dpi PNG and "
               "a vector SVG. You can also save any drawing as shown with the camera icon at its top right.")


def accessibility_page():
    ui.setup_page()
    _sidebar()
    st.title("Accessibility")
    md("These are the choices behind this tool and where it still falls short. The target is WCAG 2.1 level AA.")
    md("- Text is set in **Open Sans** at 18 px, with lines of about 72 characters, served with the app so it looks "
       "the same on every device.\n"
       "- The tool opens in light mode (near-black on warm paper). Dark mode is in the menu at the top right, under "
       "Settings, and your choice is remembered. Both are above 4.5:1 contrast. Drawings sit on white in both modes.\n"
       "- Words with a dotted underline explain themselves: hover to preview; click, tap, Enter or Space to pin; "
       "Escape closes.\n"
       "- **Colour is never the only cue.** Checks say Pass or Review in words with a ✓ or ✗; particle paths differ "
       "in line style and end marker (a dot when caught, a cross when it escapes); legends are boxed outside the "
       "drawing.\n"
       "- Every drawing has a sentence above it saying what it shows (also its screen-reader description), and every "
       "number is in the summary table and the downloads.\n"
       "- Everything except the drawings works with a keyboard, with a thick focus outline; buttons and fields are at "
       "least 48 px tall; sections fade in as you scroll, except when your device asks for reduced motion.")
    st.subheader("What still falls short")
    md("- Drawings can't be explored with a keyboard or screen reader; the description and tables carry the same "
       "information.\n"
       "- The 3D view is hard to use without a mouse. The side and plan views show the same dimensions.\n"
       "- If something doesn't work for you, tell your instructor or open an issue on "
       "[GitHub](https://github.com/gregor-posadas/Sedimentation-Basin-Generator/issues).")
