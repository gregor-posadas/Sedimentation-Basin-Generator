# Sedimentation basin design

A learning tool for CE 323 (Environmental and Fluids Laboratory, Boise State University). It sizes a
rectangular sedimentation basin from the overflow rate and detention time read off the
[Isoremoval curves tool](https://isoremoval.streamlit.app), then checks the design and draws it.
For learning; not certified for engineering design.

## Using it

1. **Settling-column results:** the overflow rate v₀ (m/d) and detention time t (h) at your target overall
   removal. Optionally apply scale-up factors for a full-size basin (off by default).
2. **Design flow:** plant flow in m³/d, m³/h, L/s, MGD or gpm, and the number of basins in parallel.
3. **Basin shape:** side-water depth, freeboard, outlet weir runs, and either a length : width ratio
   (the tool sizes the basin) or your own length and width.
4. **Check the design:** overflow rate and detention time against your design values, plus depth, L : W,
   horizontal velocity and weir loading; each failing check says what to change.
5. **See it work:** an interactive side view where you pick a particle's settling speed and starting height
   and see whether the basin catches it, plus plan and 3D views.
6. **Summary:** a summary table and downloads.

Values can be passed in the link, for example `?vo=43.8&t=1.42&R=70`, so the isoremoval tool can open this
one already filled in.

## Method and checks

`basin_calc.py` holds the math, with the method at the top of the file. Area A = max(Q/v₀, Q·t/H) × safety
factor; L and W from the L : W ratio; then actual overflow rate Q/A and detention time A·H/Q.

| Check | Rule | Source |
|---|---|---|
| Overflow rate | ≤ design v₀ | your settling-column result |
| Detention time | ≥ design t | your settling-column result |
| Side-water depth | 3–5 m | CE 323 lecture, typical range |
| Length : width | 3:1 – 5:1 | CE 323 lecture, typical range |
| Horizontal velocity | ≤ 1.0 ft/min (0.51 cm/s) | 12 VAC 5-590-872 (follows the Ten States Standards) |
| Weir loading | ≤ 20,000 gpd/ft (248 m³/d per m) | 12 VAC 5-590-872 |

Optional scale-up factors (overflow rate × 0.65–0.85, detention time × 1.25–1.50) are from NPTEL,
*Wastewater Treatment*, IIT Kharagpur, Module 16, Lecture 21.

### Changes in October 2026

- Overflow rate and detention time are checked in the direction that matters (at most / at least the design
  value). The old checks asked for a match within 10 %, so a safely oversized basin failed.
- Horizontal velocity and weir loading have upper limits only, from published regulations.
- Weir length is basin width × number of weir runs, not two widths ("weirs at both ends").
- The Reynolds number uses the hydraulic radius and is shown for information; the old "Re < 2000 laminar"
  check failed every realistic full-size basin. Water viscosity now follows the temperature you enter.
- Defaults are realistic (the old default overflow rate was 1,200 m/d).
- Same teaching and accessibility system as the isoremoval tool: a short "the idea" section, explainer terms,
  Open Sans, light mode by default (dark in Settings), interactive drawings on white, 48 px targets, focus
  outlines, scroll reveals that switch off for reduced motion, and a description above every drawing.

## Running locally

```
pip install -r requirements.txt
streamlit run app.py
python tests/test_basin.py
```

Font: Open Sans, SIL Open Font License (`static/fonts/OFL.txt`).
