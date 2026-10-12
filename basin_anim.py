"""Animated, interactive side view of the designed basin (HTML/canvas component).

Particles enter across the inlet, are carried toward the outlet at the basin's flow-through speed, and sink at
settling speeds drawn from the settling-column results: if the p % isoremoval curve gave an overflow rate v_p,
then p % of the particles settle at v_p or faster. Particles that reach the floor join the sludge, which builds
up (thickest near the inlet, where the fast ones land); the rest leave over the outlet weir. Time is scaled so
water crosses in a few seconds; every speed keeps its true ratio to the overflow rate, so the share caught is the
ideal-basin removal. Lab-scale and full-scale numbers stay honest: only time is compressed.
"""
import json

# The lecture's sample data: (percent of particles settling at least this fast, speed in m/d)
SAMPLE_DIST = [(20, 240.0), (30, 130.9), (40, 81.1), (50, 51.4), (60, 35.0), (70, 20.6), (80, 8.5)]


def parse_dist(s):
    try:
        pts = sorted((float(a), float(b)) for a, b in (x.split(":") for x in s.split(",") if ":" in x))
        pts = [(p, v) for p, v in pts if 0 < p < 100 and v > 0]
        return pts if len(pts) >= 2 else None
    except Exception:
        return None


def build(L, W, H, q, overflow, detention_h, dist=None, from_column=False):
    data = {"L": L, "W": W, "H": H, "q": q, "v0": overflow, "td": detention_h,
            "dist": [list(p) for p in (dist or SAMPLE_DIST)], "fromColumn": bool(from_column)}
    return HTML.replace("__DATA__", json.dumps(data))


HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:"Open Sans";font-weight:400;src:url("/app/static/fonts/open-sans-latin-400-normal.woff2") format("woff2")}
@font-face{font-family:"Open Sans";font-weight:700;src:url("/app/static/fonts/open-sans-latin-700-normal.woff2") format("woff2")}
:root{--ink:#1b1a17;--ink2:#4d4a43;--rule:#d4ccbb;--focus:#0072b2}
*{box-sizing:border-box}
html,body{margin:0;background:#fff;color:var(--ink);font:16px/1.4 "Open Sans",system-ui,sans-serif}
.wrap{border:1px solid var(--rule);border-radius:8px;padding:12px 14px 10px;background:#fff}
canvas{display:block;width:100%}
.bar{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;margin-top:8px}
button{font:inherit;min-height:44px;padding:0 14px;border:1.5px solid var(--ink);background:#fff;color:var(--ink);border-radius:6px;cursor:pointer}
button.primary{background:var(--ink);color:#fff}
.flow{display:flex;align-items:center;gap:8px;flex:1 1 260px}
.flow input{flex:1;height:44px;accent-color:#385F96;min-width:140px}
label.ck{display:inline-flex;gap:6px;align-items:center;min-height:44px}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.note{font-size:14px;color:var(--ink2);margin:4px 0 0}
</style></head><body><div class="wrap">
<canvas id="cv" role="img" aria-label="Animated side view of one basin with particles settling and sludge building up."></canvas>
<div class="bar">
  <button id="play" class="primary" type="button" aria-pressed="true">❚❚ Pause</button>
  <button id="scrape" type="button">Remove sludge</button>
  <div class="flow"><label for="flow">Flow</label><input id="flow" type="range" min="0.5" max="2" step="0.05" value="1"><span id="flowv">1.00 × design</span></div>
  <label class="ck"><input id="fate" type="checkbox" checked> Colour by fate</label>
  <label class="ck"><input id="crit" type="checkbox" checked> Show overflow-rate path</label>
</div>
<p class="note" id="live" aria-live="polite"></p>
</div>
<script>
const D = __DATA__;
const cv = document.getElementById("cv"), g = cv.getContext("2d");
const C = {ink:"#1b1a17", ink2:"#4d4a43", blue:"#385F96", orange:"#B8481A", water:"#dbe6f3", sludge:"#8c6b5a", rule:"#d4ccbb", grey:"#5d5a52"};
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
let Wc = 800, Hc = 400, playing = !reduce, last = null, simT = 0;
const TCROSS = 7;            // seconds for water to cross at the design flow
const NB = 80;               // sludge bins along the length
function rng(s){return ()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
// settling-speed distribution: exceedance fraction F (0-1) -> speed, log-linear between column points
const PTS = D.dist.map(([p, v]) => [p / 100, Math.log(v)]).sort((a, b) => a[0] - b[0]);
function speedFor(F){
  const n = PTS.length; let i = 0; while (i < n - 2 && F > PTS[i + 1][0]) i++;
  const [f0, l0] = PTS[i], [f1, l1] = PTS[i + 1]; const lv = l0 + (l1 - l0) * (F - f0) / (f1 - f0);
  return Math.min(Math.max(Math.exp(lv), 0.3), 5000);
}
function expectedRemoval(v0){ let s = 0, N = 4000; for (let k = 0; k < N; k++) { const v = speedFor((k + 0.5) / N); s += Math.min(1, v / v0); } return s / N * 100; }
let state;
function reset(seed = 9){ state = {r: rng(seed), parts: [], acc: 0, caught: 0, escaped: 0, sludge: new Float32Array(NB), spawned: 0}; simT = 0; }
function flow(){ return +document.getElementById("flow").value; }
function geom(){
  const left = 70, right = Wc - 90, top = 60, avail = Hc - 120;
  const Lpx = right - left; const ex = Math.max(1, Math.min(8, (avail / D.H) / (Lpx / D.L)));
  const Hpx = D.H * (Lpx / D.L) * ex; return {left, right, top, Lpx, Hpx, ex, bottom: top + Hpx};
}
function sludgeH(x01){ const b = Math.min(NB - 1, Math.max(0, Math.floor(x01 * NB))); return state.sludge[b]; }
function step(dt){
  const f = flow(), Tc = TCROSS / f, v0 = D.v0 * f;
  state.acc += dt * 34;
  while (state.acc >= 1) { state.acc -= 1; const r = state.r;
    const F = r(); const v = speedFor(F); state.parts.push({x: 0, z: r() * 0.985, v, F, life: 0}); state.spawned++; }
  const keep = [];
  for (const p of state.parts) {
    p.x += dt / Tc;
    p.z += dt * (p.v / v0) / Tc;                       // fraction of depth per second
    const floor = 1 - sludgeH(p.x);
    if (p.z >= floor) { const b = Math.min(NB - 1, Math.floor(Math.min(p.x, 0.999) * NB));
      state.sludge[b] = Math.min(0.45, state.sludge[b] + 0.0016); state.caught++;
      if (b > 0) state.sludge[b - 1] = Math.min(0.45, state.sludge[b - 1] + 0.0005);
      if (b < NB - 1) state.sludge[b + 1] = Math.min(0.45, state.sludge[b + 1] + 0.0005); continue; }
    if (p.x >= 1) { state.escaped++; continue; }
    keep.push(p);
  }
  state.parts = keep; simT += dt;
}
function fnt(sz, w=400){ g.font = `${w} ${sz}px "Open Sans", system-ui, sans-serif`; }
function txt(s,x,y,o={}){ g.save(); fnt(o.size||14,o.w||400); g.fillStyle=o.c||C.ink; g.textAlign=o.a||"left"; g.fillText(s,x,y); g.restore(); }
function resize(){ const w = cv.parentElement.clientWidth - 28; const dpr = window.devicePixelRatio || 1;
  Wc = Math.max(300, w); Hc = Wc < 600 ? 330 : 420; cv.width = Wc*dpr; cv.height = Hc*dpr; cv.style.height = Hc + "px"; g.setTransform(dpr,0,0,dpr,0,0); draw(); }
function draw(){
  const G = geom(), f = flow(), v0 = D.v0 * f;
  g.clearRect(0, 0, Wc, Hc);
  // tank
  g.fillStyle = C.water; g.fillRect(G.left, G.top, G.Lpx, G.Hpx);
  // sludge polygon
  g.fillStyle = C.sludge; g.beginPath(); g.moveTo(G.left, G.bottom);
  for (let b = 0; b < NB; b++) { const x = G.left + (b + 0.5) / NB * G.Lpx; g.lineTo(x, G.bottom - state.sludge[b] * G.Hpx); }
  g.lineTo(G.right, G.bottom); g.closePath(); g.fill();
  // flow arrows
  for (let k = 0; k < 4; k++) { const x = G.left + 40 + ((k * G.Lpx / 4 + simT * 60 * f) % (G.Lpx - 80)); const y = G.top + 16;
    g.strokeStyle = "rgba(56,95,150,0.45)"; g.lineWidth = 2; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 30, y); g.stroke();
    g.beginPath(); g.moveTo(x + 30, y); g.lineTo(x + 22, y - 5); g.lineTo(x + 22, y + 5); g.closePath(); g.fillStyle = "rgba(56,95,150,0.45)"; g.fill(); }
  // critical path
  if (document.getElementById("crit").checked) { g.setLineDash([7, 5]); g.strokeStyle = C.ink; g.lineWidth = 1.6; g.beginPath(); g.moveTo(G.left, G.top); g.lineTo(G.right, G.bottom); g.stroke(); g.setLineDash([]);
  }
  // particles
  const fate = document.getElementById("fate").checked;
  for (const p of state.parts) {
    // caught if it can sink to the sludge surface before the water carries it to the outlet
    const xl = Math.min(0.999, p.x + (1 - p.z) * v0 / p.v);
    const willCatch = p.z + (1 - p.x) * p.v / v0 >= 1 - sludgeH(xl);
    const col = !fate ? C.grey : willCatch ? C.blue : C.orange;
    const r = 1.6 + 2.4 * Math.min(1, Math.log10(p.v + 1) / Math.log10(600));
    g.beginPath(); g.arc(G.left + p.x * G.Lpx, G.top + p.z * G.Hpx, r, 0, 6.283); g.fillStyle = col; g.fill();
  }
  // walls, weir, labels
  g.strokeStyle = C.ink; g.lineWidth = 2.5; g.strokeRect(G.left, G.top - 14, G.Lpx, G.Hpx + 14);
  g.strokeStyle = C.blue; g.lineWidth = 2; g.beginPath(); g.moveTo(G.left, G.top); g.lineTo(G.right, G.top); g.stroke();
  g.fillStyle = C.orange; g.fillRect(G.right - 4, G.top - 14, 8, 14);
  txt("inlet", G.left - 8, G.top + 18, {a: "right", size: 13, c: C.ink2}); txt("outlet weir", G.right + 8, G.top + 4, {size: 13, c: C.ink2});
  txt(`${D.L.toFixed(1)} m long, ${D.H.toFixed(2)} m deep` + (G.ex > 1.05 ? ` (depth drawn ×${G.ex.toFixed(1)})` : "") +
      (document.getElementById("crit").checked ? `. Dashed line: a particle settling at exactly the overflow rate, ${v0.toFixed(1)} m/d.` : ""), G.left, G.bottom + 26, {size: 13, c: C.ink2});
  // counters
  const tot = state.caught + state.escaped, pct = tot ? state.caught / tot * 100 : 0, exp = expectedRemoval(v0);
  const ready = state.escaped > 0 && tot > 60;   // wait until particles have had time to cross
  const bx = Wc < 600 ? G.left : G.right - 330, by = 8;
  txt(`Caught ${ready ? pct.toFixed(0) : "–"} %  ·  expected ${exp.toFixed(0)} %`, Wc < 600 ? G.left : G.right, by + 16, {size: 15, w: 700, a: Wc < 600 ? "left" : "right"});
  if (fate) { const lx = G.left, ly = by + 16; g.fillStyle = C.blue; g.beginPath(); g.arc(lx + 5, ly - 5, 5, 0, 6.283); g.fill(); txt("will be caught", lx + 14, ly, {size: 13});
    g.fillStyle = C.orange; g.beginPath(); g.arc(lx + 130, ly - 5, 5, 0, 6.283); g.fill(); txt("will escape", lx + 139, ly, {size: 13}); }
  const sl = state.sludge.reduce((a, b) => a + b, 0) / NB;
  txt(sl > 0.12 ? "Sludge is filling the basin: remove it." : "Sludge builds up where particles land: mostly near the inlet.", G.left, G.bottom + 44, {size: 13, c: sl > 0.12 ? C.orange : C.ink2, w: sl > 0.12 ? 700 : 400});
}
function announce(){ const f = flow(), v0 = D.v0 * f, tot = state.caught + state.escaped;
  document.getElementById("live").textContent = `At ${f.toFixed(2)} times the design flow the overflow rate is ${v0.toFixed(1)} m/d and the detention time ${(D.td / f).toFixed(2)} h. ` +
    `Ideal removal: ${expectedRemoval(v0).toFixed(0)} % of particles` + (tot ? `; caught so far ${(state.caught / tot * 100).toFixed(0)} % of ${tot}.` : "."); }
function tick(ts){ if (!playing) { last = null; return; } if (last != null) step(Math.min(0.05, (ts - last) / 1000)); last = ts; draw(); requestAnimationFrame(tick); }
const playBtn = document.getElementById("play");
function setPlay(on){ playing = on; playBtn.textContent = on ? "❚❚ Pause" : "▶ Play"; playBtn.setAttribute("aria-pressed", on ? "true" : "false"); if (on) requestAnimationFrame(tick); else announce(); }
playBtn.onclick = () => setPlay(!playing);
document.getElementById("scrape").onclick = () => { state.sludge.fill(0); draw(); announce(); };
document.getElementById("flow").oninput = () => { document.getElementById("flowv").textContent = `${flow().toFixed(2)} × design`; state.caught = 0; state.escaped = 0; draw(); };
document.getElementById("flow").onchange = announce;
["fate", "crit"].forEach(id => document.getElementById(id).onchange = draw);
window.addEventListener("resize", resize);
/* recording hook: deterministic frame at time tt seconds from a fresh start, at flow factor fl */
window.__anim = { render: (tt, fl) => { if (fl) { document.getElementById("flow").value = fl; document.getElementById("flowv").textContent = `${(+fl).toFixed(2)} × design`; }
  playing = false; reset(); const dt = 1 / 30; for (let k = 0; k < Math.round(tt / dt); k++) step(dt); draw(); } };
reset(); resize(); announce();
if (!reduce) { for (let k = 0; k < 90; k++) step(1 / 30); requestAnimationFrame(tick); } else { for (let k = 0; k < 240; k++) step(1 / 30); draw(); }
</script></body></html>"""
