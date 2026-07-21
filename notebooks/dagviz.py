"""Notebook-only interactive DAG of resource interaction flows.

Emits a self-contained SVG + CSS + JS blob (no CDN, no extra dependencies) for
IPython.display.HTML. Two views over the same resource positions:

  * "transforms"  — bipartite / Petri-net: resource nodes and transform nodes,
                    edges are consume/produce. Exact, nothing is lost.
  * "resource flow" — collapsed: resource -> resource, with the responsible
                    transforms listed in the edge tooltip. Lossy but reads as a
                    flow diagram.

Hovering an edge dims everything else and pops a panel naming the transform(s)
responsible, the stoichiometry, the net effect, and — when a RuntimeFacts is
supplied — how much actually flowed during a replay.

Colour is the dataviz reference palette (categorical slots in fixed order, one
per resource, light and dark steps). Every node is directly labelled, so identity
never rests on colour alone.
"""
from __future__ import annotations

import html
import json
import math
import uuid

from analysis import (
    ARROW,
    bipartite_graph,
    resource_facts,
    resource_graph,
    transform_facts,
)

# dataviz reference palette, categorical slots in fixed order
PALETTE_LIGHT = ["#2a78d6", "#008300", "#e87ba4", "#eda100",
                 "#1baf7a", "#eb6834", "#4a3aa7", "#e34948"]
PALETTE_DARK = ["#3987e5", "#008300", "#d55181", "#c98500",
                "#199e70", "#d95926", "#9085e9", "#e66767"]

R_RADIUS = 36          # resource node radius
T_HEIGHT = 30          # transform node height
CURV = 0.13            # edge bow, as a fraction of edge length


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def _ring_positions(names, cx, cy, rx, ry):
    """Resources evenly around an ellipse, starting at the top."""
    n = len(names)
    pos = {}
    for i, name in enumerate(names):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pos[name] = (cx + rx * math.cos(a), cy + ry * math.sin(a))
    return pos


def _place_transforms(tfacts, res_pos, cx, cy, sizes):
    """A transform sits at the centroid of the resources it touches, then relaxes.

    Deterministic (no RNG): centroid placement is structurally meaningful — the
    node lands between the resources it links — and a few rounds of pairwise
    repulsion pull apart transforms that share a neighbour set.
    """
    pos = {}
    for i, f in enumerate(tfacts):
        touched = sorted(set(f.inputs) | set(f.outputs))
        px = sum(res_pos[r][0] for r in touched) / len(touched)
        py = sum(res_pos[r][1] for r in touched) / len(touched)
        # golden-angle nudge breaks exact ties without randomness
        a = i * 2.399963
        pos[f.name] = (px + 0.8 * math.cos(a), py + 0.8 * math.sin(a))

    names = [f.name for f in tfacts]
    boxes = [(sizes[f.name][0], sizes[f.name][1], f.name) for f in tfacts]
    others = [(R_RADIUS * 2, R_RADIUS * 2, p) for p in res_pos.values()]

    def separate(ax, ay, aw, ah, bx, by, bw, bh, padx=16, pady=12):
        """Axis-aligned overlap; push along whichever axis needs less movement."""
        dx, dy = ax - bx, ay - by
        ox = (aw + bw) / 2 + padx - abs(dx)
        oy = (ah + bh) / 2 + pady - abs(dy)
        if ox <= 0 or oy <= 0:
            return 0.0, 0.0
        if ox < oy:
            return math.copysign(ox, dx or 1.0) * 0.5, 0.0
        return 0.0, math.copysign(oy, dy or 1.0) * 0.5

    for _ in range(240):
        for a_name in names:
            ax, ay = pos[a_name]
            aw, ah = sizes[a_name]
            fx = fy = 0.0
            for bw, bh, b_name in boxes:
                if b_name == a_name:
                    continue
                bx, by = pos[b_name]
                sx, sy = separate(ax, ay, aw, ah, bx, by, bw, bh)
                fx += sx
                fy += sy
            for bw, bh, (bx, by) in others:
                sx, sy = separate(ax, ay, aw, ah, bx, by, bw, bh, padx=8, pady=6)
                fx += sx
                fy += sy
            nx_ = min(max(ax + max(-10, min(10, fx)), aw / 2 + 4), 2 * cx - aw / 2 - 4)
            ny_ = min(max(ay + max(-10, min(10, fy)), ah / 2 + 4), 2 * cy - ah / 2 - 4)
            pos[a_name] = (nx_, ny_)
    return pos


def _boundary(centre, size, toward):
    """Point on a node's edge, heading toward `toward`. size=(w,h); circles pass w==h."""
    cx, cy = centre
    dx, dy = toward[0] - cx, toward[1] - cy
    d = math.hypot(dx, dy) or 0.01
    w, h = size
    if abs(w - h) < 0.01:                       # circle
        k = (w / 2) / d
    else:                                       # rectangle
        k = 1.0 / max(abs(dx) / (w / 2), abs(dy) / (h / 2))
    return cx + dx * k, cy + dy * k


def _curve(p0, p1, s0, s1):
    """Quadratic bow, trimmed to both node boundaries. Always bows left of travel,
    so A->B and B->A separate on their own."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy) or 0.01
    mx = (p0[0] + p1[0]) / 2 - dy / d * CURV * d
    my = (p0[1] + p1[1]) / 2 + dx / d * CURV * d
    sx, sy = _boundary(p0, s0, (mx, my))
    ex, ey = _boundary(p1, s1, (mx, my))
    path = f"M {sx:.1f},{sy:.1f} Q {mx:.1f},{my:.1f} {ex:.1f},{ey:.1f}"
    label = (0.25 * sx + 0.5 * mx + 0.25 * ex, 0.25 * sy + 0.5 * my + 0.25 * ey)
    return path, label


def _self_loop(p, radius, centre):
    """Storage loop, bulging away from the diagram centre."""
    ux, uy = p[0] - centre[0], p[1] - centre[1]
    d = math.hypot(ux, uy) or 0.01
    ux, uy = ux / d, uy / d

    def rot(vx, vy, deg):
        a = math.radians(deg)
        return vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)

    a1 = rot(ux, uy, 30)
    a2 = rot(ux, uy, -30)
    s = (p[0] + a1[0] * radius, p[1] + a1[1] * radius)
    e = (p[0] + a2[0] * radius, p[1] + a2[1] * radius)
    c1 = (p[0] + a1[0] * radius * 2.9, p[1] + a1[1] * radius * 2.9)
    c2 = (p[0] + a2[0] * radius * 2.9, p[1] + a2[1] * radius * 2.9)
    path = (f"M {s[0]:.1f},{s[1]:.1f} C {c1[0]:.1f},{c1[1]:.1f} "
            f"{c2[0]:.1f},{c2[1]:.1f} {e[0]:.1f},{e[1]:.1f}")
    label = (p[0] + ux * radius * 2.35, p[1] + uy * radius * 2.35)
    return path, label


# --------------------------------------------------------------------------
# tooltip copy
# --------------------------------------------------------------------------

def _esc(s) -> str:
    return html.escape(str(s))


def _fires(runtime, name):
    return runtime.fires_by_transform.get(name, 0) if runtime else None


def _transform_tip(f, runtime):
    rows = [f"<div class='gt-tip-h'>{_esc(f.name)}</div>",
            f"<div class='gt-tip-kind'>{_esc(f.kind)}</div>",
            f"<div class='gt-tip-recipe'>{_esc(f.recipe)}</div>"]
    net = ", ".join(f"{v:+d} {r}" for r, v in f.net.items()) or "nothing (pure hold)"
    rows.append(f"<div class='gt-tip-row'><span>net</span><b>{_esc(net)}</b></div>")
    if f.catalysts:
        rows.append("<div class='gt-tip-row'><span>needs present</span>"
                    f"<b>{_esc(', '.join(f.catalysts))}</b></div>")
    for r, g in f.amplifies.items():
        rows.append(f"<div class='gt-tip-row'><span>amplifies</span>"
                    f"<b>{_esc(r)} ×{g:g}</b></div>")
    n = _fires(runtime, f.name)
    if n is not None:
        where = ", ".join(
            f"{lid} ×{c}" for (lid, tn), c in runtime.fires_by_location.items() if tn == f.name
        )
        active = sum(1 for t in runtime.fires_per_tick if t.get(f.name))
        if n:
            rows.append(f"<div class='gt-tip-obs'>fired <b>{n}×</b> over "
                        f"{active}/{runtime.ticks} ticks — {_esc(where)}</div>")
        else:
            rows.append("<div class='gt-tip-obs gt-dead'>never fired in the replay</div>")
    return "".join(rows)


def _resource_tip(rf, runtime):
    rows = [f"<div class='gt-tip-h'>{_esc(rf.name)}</div>"]
    if rf.orphan:
        status = "orphan — nothing emits it, it decays to zero"
    elif any(h.free for h in rf.holds):
        status = "self-sustaining — a free transform re-emits it"
    else:
        status = "needs upkeep every turn or it is gone"
    rows.append(f"<div class='gt-tip-kind'>{_esc(status)}</div>")
    if rf.holds:
        h = rf.holds[0]
        cost = "free" if h.free else ", ".join(f"{v:g} {r}" for r, v in h.cost.items())
        rows.append(f"<div class='gt-tip-row'><span>cheapest hold</span>"
                    f"<b>{_esc(h.transform)} ({_esc(cost)})</b></div>")
    rows.append(f"<div class='gt-tip-row'><span>emitted by</span>"
                f"<b>{_esc(', '.join(rf.emitted_by) or '—')}</b></div>")
    rows.append(f"<div class='gt-tip-row'><span>consumed by</span>"
                f"<b>{_esc(', '.join(rf.consumed_by) or '—')}</b></div>")
    rows.append(f"<div class='gt-tip-row'><span>initial</span><b>{rf.initial_total}</b></div>")
    if runtime is not None:
        totals = runtime.stock_history.sum(axis=1)[:, rf.index]
        series = " ".join(str(int(v)) for v in totals)
        rows.append(f"<div class='gt-tip-obs'>per tick: <b>{_esc(series)}</b></div>")
    return "".join(rows)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

STATIC_WIDTH = 4.4     # no replay data: every rule weighted equally
DEAD_WIDTH = 2.4       # observed, but never fired
MIN_WIDTH = 3.6        # fired at least once
SPAN_WIDTH = 7.2       # added on top, by sqrt of share of the busiest edge

ARROW_SCALE = 2.1      # arrowhead length as a multiple of stroke width...
ARROW_MIN = 14         # ...clamped to this range, in user units
ARROW_MAX = 22


def _width_for(volume, vmax):
    if volume <= 0:
        return DEAD_WIDTH
    return MIN_WIDTH + SPAN_WIDTH * math.sqrt(volume / vmax) if vmax else STATIC_WIDTH


def _svg(view, scenario, tfacts, rfacts, res_pos, t_pos, t_sizes, runtime,
         width, height, uid):
    centre = (width / 2, height / 2)
    defs, edges, nodes, tips = [], [], [], {}
    groups: dict[str, list[str]] = {}          # element id -> ids to highlight with it
    edges_of_transform: dict[str, list[str]] = {}
    seen_markers = set()

    def marker(idx, stroke_w):
        # Head size tracks the shaft but is clamped, so it always reads as an
        # arrow (never a blob on the thick edges, never a speck on the thin ones).
        # refX=10 puts the tip exactly on the trimmed path end, i.e. the node edge.
        size = round(min(ARROW_MAX, max(ARROW_MIN, ARROW_SCALE * stroke_w)))
        mid = f"{uid}-arw-{idx}-{size}"
        if mid not in seen_markers:
            seen_markers.add(mid)
            defs.append(
                f"<marker id='{mid}' viewBox='0 0 10 10' refX='10' refY='5' "
                f"markerWidth='{size}' markerHeight='{size}' orient='auto' "
                f"markerUnits='userSpaceOnUse'>"
                f"<path d='M 0 0.4 L 10 5 L 0 9.6 L 2.8 5 z' "
                f"fill='var(--gt-c{idx})'/></marker>"
            )
        return mid

    tf_by_name = {f.name: f for f in tfacts}
    rf_by_name = {r.name: r for r in rfacts}
    ridx = scenario.resource_index

    # ---- edges ---------------------------------------------------------
    # (path, label_pos, qty, colour_idx, volume, tip, owning transform or None, vmax)
    edge_specs = []
    if view == "transforms":
        G = bipartite_graph(scenario, tfacts)
        vols = []
        for _, _, d in G.edges(data=True):
            n = _fires(runtime, d["transform"])
            vols.append((n or 0) * d["qty"])
        vmax = max(vols) if vols else 0
        for (a, b, d) in G.edges(data=True):
            res, tname, qty, role = d["resource"], d["transform"], d["qty"], d["role"]
            ap = res_pos[a[1]] if a[0] == "resource" else t_pos[a[1]]
            bp = res_pos[b[1]] if b[0] == "resource" else t_pos[b[1]]
            asz = (R_RADIUS * 2, R_RADIUS * 2) if a[0] == "resource" else t_sizes[a[1]]
            bsz = (R_RADIUS * 2, R_RADIUS * 2) if b[0] == "resource" else t_sizes[b[1]]
            path, lab = _curve(ap, bp, asz, bsz)
            f = tf_by_name[tname]
            n = _fires(runtime, tname)
            vol = (n or 0) * qty
            verb = "consumes" if role == "consume" else "produces"
            tip = (f"<div class='gt-tip-h'>{_esc(tname)} {_esc(verb)} "
                   f"{qty} {_esc(res)}</div>"
                   f"<div class='gt-tip-recipe'>{_esc(f.recipe)}</div>")
            net = f.net.get(res, 0)
            tip += (f"<div class='gt-tip-row'><span>net {_esc(res)}</span>"
                    f"<b>{net:+d} per firing</b></div>")
            if res in f.catalysts:
                tip += ("<div class='gt-tip-row'><span>role</span>"
                        "<b>catalyst — passes through unchanged</b></div>")
            if n is not None:
                tip += (f"<div class='gt-tip-obs gt-dead'>never fired</div>" if not n
                        else f"<div class='gt-tip-obs'><b>{vol}</b> {_esc(res)} "
                             f"{_esc(verb.rstrip('s'))}d over {runtime.ticks} ticks "
                             f"({n} firings)</div>")
            edge_specs.append((path, lab, qty, ridx[res], vol, tip, tname, vmax))
    else:
        G = resource_graph(scenario, tfacts)
        vols = []
        for a, b, d in G.edges(data=True):
            vols.append(sum((_fires(runtime, t) or 0) for t in d["transforms"]))
        vmax = max(vols) if vols else 0
        for a, b, d in G.edges(data=True):
            names = d["transforms"]
            sz = (R_RADIUS * 2, R_RADIUS * 2)
            if a == b:
                path, lab = _self_loop(res_pos[a], R_RADIUS, centre)
            else:
                path, lab = _curve(res_pos[a], res_pos[b], sz, sz)
            vol = sum((_fires(runtime, t) or 0) for t in names)
            head = (f"{_esc(a)} {ARROW} {_esc(b)}" if a != b
                    else f"{_esc(a)} held (storage loop)")
            tip = f"<div class='gt-tip-h'>{head}</div>"
            tip += ("<div class='gt-tip-kind'>via "
                    + _esc(", ".join(names)) + "</div>")
            for tn in names:
                f = tf_by_name[tn]
                n = _fires(runtime, tn)
                obs = ""
                if n is not None:
                    obs = (f" <em class='gt-dead'>· never fired</em>" if not n
                           else f" <em>· {n}×</em>")
                tip += (f"<div class='gt-tip-line'><b>{_esc(tn)}</b> "
                        f"<span>{_esc(f.recipe)}</span>{obs}</div>")
            edge_specs.append((path, lab, None, ridx[a], vol, tip, None, vmax))

    for i, (path, lab, qty, cidx, vol, tip, tname, vmax) in enumerate(edge_specs):
        eid = f"{uid}-{view}-e{i}"
        tips[eid] = tip
        if tname:
            edges_of_transform.setdefault(tname, []).append(eid)
        dead = runtime is not None and vol == 0
        w = _width_for(vol, vmax) if runtime is not None else STATIC_WIDTH
        cls = "gt-edge" + (" gt-edge-dead" if dead else "")
        edges.append(
            f"<g class='{cls}' data-id='{eid}' data-c='{cidx}'>"
            f"<path class='gt-hit' d='{path}'/>"
            f"<path class='gt-line' d='{path}' stroke='var(--gt-c{cidx})' "
            f"stroke-width='{w:.2f}' marker-end='url(#{marker(cidx, w)})'/>"
            f"</g>"
        )
        if qty and qty > 1:
            edges.append(
                f"<g class='gt-qty' data-id='{eid}'>"
                f"<circle cx='{lab[0]:.1f}' cy='{lab[1]:.1f}' r='9'/>"
                f"<text x='{lab[0]:.1f}' y='{lab[1]:.1f}'>{qty}</text></g>"
            )

    # ---- nodes ---------------------------------------------------------
    for name, (x, y) in res_pos.items():
        nid = f"{uid}-{view}-n-{name}"
        tips[nid] = _resource_tip(rf_by_name[name], runtime)
        cidx = ridx[name]
        sub = ""
        if runtime is not None:
            totals = runtime.stock_history.sum(axis=1)[:, cidx]
            sub = (f"<text class='gt-sub' x='{x:.1f}' y='{y + 13:.1f}'>"
                   f"{int(totals[0])} {ARROW} {int(totals[-1])}</text>")
        nodes.append(
            f"<g class='gt-node gt-res' data-id='{nid}' data-c='{cidx}'>"
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{R_RADIUS}' "
            f"fill='var(--gt-c{cidx})' fill-opacity='0.14' "
            f"stroke='var(--gt-c{cidx})' stroke-width='2'/>"
            f"<text class='gt-lab' x='{x:.1f}' y='{y - (3 if sub else -4):.1f}'>"
            f"{_esc(name)}</text>{sub}</g>"
        )

    if view == "transforms":
        for f in tfacts:
            x, y = t_pos[f.name]
            w, h = t_sizes[f.name]
            nid = f"{uid}-{view}-n-t-{f.name}"
            tips[nid] = _transform_tip(f, runtime)
            # hovering a transform lights up its whole recipe: every edge it owns
            # plus the resources on both ends of them
            groups[nid] = (
                [nid]
                + edges_of_transform.get(f.name, [])
                + [f"{uid}-{view}-n-{r}" for r in sorted(set(f.inputs) | set(f.outputs))]
            )
            n = _fires(runtime, f.name)
            dead = " gt-node-dead" if n == 0 else ""
            nodes.append(
                f"<g class='gt-node gt-tr{dead}' data-id='{nid}'>"
                f"<rect x='{x - w / 2:.1f}' y='{y - h / 2:.1f}' width='{w}' height='{h}' "
                f"rx='7'/>"
                f"<text class='gt-lab' x='{x:.1f}' y='{y:.1f}'>{_esc(f.name)}</text></g>"
            )

    hidden = "" if view == "transforms" else " hidden"
    svg = (f"<svg class='gt-svg{hidden}' data-view='{view}' viewBox='0 0 {width} {height}' "
           f"preserveAspectRatio='xMidYMid meet'>"
           f"<defs>{''.join(defs)}</defs>"
           f"<g class='gt-edges'>{''.join(edges)}</g>"
           f"<g class='gt-nodes'>{''.join(nodes)}</g></svg>")
    return svg, tips, groups


_CSS = """
#UID { --gt-surface:#fcfcfb; --gt-surface2:#f2f1ee; --gt-ink:#0b0b0b;
  --gt-ink2:#52514e; --gt-muted:#898781; --gt-border:rgba(11,11,11,0.12);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--gt-ink);
  background:var(--gt-surface); border:1px solid var(--gt-border); border-radius:10px;
  padding:14px 16px 10px; max-width:100%; }
#UID .gt-head { display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  margin-bottom:2px; }
#UID .gt-title { font-size:15px; font-weight:650; letter-spacing:-0.01em; }
#UID .gt-note { font-size:12px; color:var(--gt-muted); }
#UID .gt-toggle { margin-left:auto; display:flex; gap:0; border:1px solid var(--gt-border);
  border-radius:7px; overflow:hidden; }
#UID .gt-toggle button { font:inherit; font-size:12px; padding:4px 11px; border:0;
  background:transparent; color:var(--gt-ink2); cursor:pointer; }
#UID .gt-toggle button.on { background:var(--gt-surface2); color:var(--gt-ink);
  font-weight:600; }
#UID .gt-legend { display:flex; flex-wrap:wrap; gap:4px 14px; margin:8px 0 2px;
  font-size:12px; color:var(--gt-ink2); }
#UID .gt-legend span { display:inline-flex; align-items:center; gap:6px; }
#UID .gt-sw { width:11px; height:11px; border-radius:3px; display:inline-block; }
#UID .gt-stage { position:relative; }
#UID .gt-svg { display:block; width:100%; height:auto; overflow:visible; }
#UID .gt-svg.hidden { display:none; }

#UID .gt-edge { opacity:0.85; }
#UID .gt-line { fill:none; stroke-linecap:round; }
#UID .gt-hit { fill:none; stroke:transparent; stroke-width:20; cursor:pointer; }
#UID .gt-edge-dead { opacity:0.32; }
#UID .gt-edge-dead .gt-line { stroke-dasharray:4 6; }
#UID .gt-qty circle { fill:var(--gt-surface); stroke:var(--gt-border); }
#UID .gt-qty text { font-size:11px; font-weight:650; fill:var(--gt-ink2);
  text-anchor:middle; dominant-baseline:central; pointer-events:none; }
#UID .gt-lab { font-size:12.5px; font-weight:600; fill:var(--gt-ink);
  text-anchor:middle; dominant-baseline:central; pointer-events:none; }
#UID .gt-sub { font-size:10.5px; fill:var(--gt-ink2); text-anchor:middle;
  dominant-baseline:central; pointer-events:none; font-variant-numeric:tabular-nums; }
#UID .gt-tr rect { fill:var(--gt-surface2); stroke:var(--gt-border); stroke-width:1; }
#UID .gt-node { cursor:pointer; }
#UID .gt-node-dead rect { stroke-dasharray:3 4; }
#UID .gt-node-dead .gt-lab { fill:var(--gt-muted); }

#UID.dim .gt-edge, #UID.dim .gt-node, #UID.dim .gt-qty { opacity:0.13; }
#UID.dim .gt-edge.hot, #UID.dim .gt-node.hot, #UID.dim .gt-qty.hot { opacity:1; }
/* no stroke-width override on hover: width encodes volume, so changing it lies */
#UID .gt-edge.hot .gt-line { stroke-dasharray:none; }

#UID .gt-tip { position:absolute; z-index:20; pointer-events:none; opacity:0;
  transition:opacity .09s; max-width:330px; background:var(--gt-surface);
  border:1px solid var(--gt-border); border-radius:8px; padding:9px 11px;
  box-shadow:0 6px 22px rgba(0,0,0,.16); font-size:12px; line-height:1.45;
  color:var(--gt-ink2); }
#UID .gt-tip.show { opacity:1; }
#UID .gt-tip-h { font-size:13px; font-weight:650; color:var(--gt-ink); }
#UID .gt-tip-kind { color:var(--gt-muted); margin-bottom:5px; }
#UID .gt-tip-recipe { font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11.5px; background:var(--gt-surface2); border-radius:5px;
  padding:3px 6px; margin:4px 0; color:var(--gt-ink); }
#UID .gt-tip-row { display:flex; justify-content:space-between; gap:14px; }
#UID .gt-tip-row span { color:var(--gt-muted); }
#UID .gt-tip-row b { color:var(--gt-ink); font-weight:600; text-align:right; }
#UID .gt-tip-line { margin-top:3px; }
#UID .gt-tip-line b { color:var(--gt-ink); }
#UID .gt-tip-line span { font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11px; }
#UID .gt-tip-obs { margin-top:6px; padding-top:5px; border-top:1px solid var(--gt-border); }
#UID .gt-tip-obs b, #UID .gt-tip-line em { font-style:normal; color:var(--gt-ink); }
#UID .gt-dead, #UID .gt-tip-line em.gt-dead { color:#d03b3b; }
#UID .gt-foot { font-size:11.5px; color:var(--gt-muted); margin-top:6px; }

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) #UID { COLORS_DARK }
}
:root[data-theme="dark"] #UID { COLORS_DARK }
body[data-jp-theme-light="false"] #UID { COLORS_DARK }
"""

_DARK = """--gt-surface:#1a1a19; --gt-surface2:#2c2c2a; --gt-ink:#ffffff;
  --gt-ink2:#c3c2b7; --gt-muted:#898781; --gt-border:rgba(255,255,255,0.14);"""

_JS = """
(function(){
  var root=document.getElementById("UID");
  if(!root||root.dataset.wired)return; root.dataset.wired="1";
  var tips=TIPS, groups=GROUPS, tip=root.querySelector(".gt-tip"),
      stage=root.querySelector(".gt-stage");
  function related(id){
    // a transform node carries its whole recipe; everything else is just itself
    var ids=groups[id]||[id];
    return root.querySelectorAll(ids.map(function(i){
      return '[data-id="'+CSS.escape(i)+'"]';}).join(","));
  }
  function place(ev){
    var b=stage.getBoundingClientRect(), x=ev.clientX-b.left+14, y=ev.clientY-b.top+14;
    if(x+340>b.width) x=Math.max(4, ev.clientX-b.left-340);
    tip.style.left=x+"px"; tip.style.top=y+"px";
  }
  function enter(ev){
    var g=ev.currentTarget, id=g.dataset.id; if(!tips[id])return;
    root.classList.add("dim");
    related(id).forEach(function(n){n.classList.add("hot");});
    tip.innerHTML=tips[id]; tip.classList.add("show"); place(ev);
  }
  function leave(){
    root.classList.remove("dim");
    root.querySelectorAll(".hot").forEach(function(n){n.classList.remove("hot");});
    tip.classList.remove("show");
  }
  root.querySelectorAll(".gt-edge,.gt-node").forEach(function(g){
    g.addEventListener("mouseenter",enter);
    g.addEventListener("mousemove",place);
    g.addEventListener("mouseleave",leave);
  });
  root.querySelectorAll(".gt-toggle button").forEach(function(b){
    b.addEventListener("click",function(){
      leave();
      root.querySelectorAll(".gt-toggle button").forEach(function(o){
        o.classList.toggle("on", o===b);});
      root.querySelectorAll(".gt-svg").forEach(function(s){
        s.classList.toggle("hidden", s.dataset.view!==b.dataset.view);});
    });
  });
})();
"""


def render_html(scenario, runtime=None, width=980, height=620, title=None) -> str:
    """Self-contained HTML for the interactive flow DAG. See module docstring."""
    uid = "gt" + uuid.uuid4().hex[:8]
    tfacts = transform_facts(scenario)
    rfacts = resource_facts(scenario, tfacts)

    res_pos = _ring_positions(scenario.resources, width / 2, height / 2,
                              width * 0.34, height * 0.35)
    t_sizes = {f.name: (max(70, 8.2 * len(f.name) + 26), T_HEIGHT) for f in tfacts}
    t_pos = _place_transforms(tfacts, res_pos, width / 2, height / 2, t_sizes)

    svg_a, tips_a, groups_a = _svg("transforms", scenario, tfacts, rfacts, res_pos,
                                   t_pos, t_sizes, runtime, width, height, uid)
    svg_b, tips_b, groups_b = _svg("flow", scenario, tfacts, rfacts, res_pos,
                                   t_pos, t_sizes, runtime, width, height, uid)
    tips = {**tips_a, **tips_b}
    groups = {**groups_a, **groups_b}

    n = len(scenario.resources)
    light = " ".join(f"--gt-c{i}:{PALETTE_LIGHT[i % 8]};" for i in range(n))
    dark = " ".join(f"--gt-c{i}:{PALETTE_DARK[i % 8]};" for i in range(n))

    legend = "".join(
        f"<span><i class='gt-sw' style='background:var(--gt-c{i})'></i>{_esc(r)}</span>"
        for i, r in enumerate(scenario.resources)
    )
    note = ("edge width = volume observed in the replay; dashed = never fired"
            if runtime is not None else "static config — no replay data")
    css = (_CSS.replace("COLORS_DARK", _DARK + " " + dark)
               .replace("#UID {", "#UID { " + light, 1)
               .replace("UID", uid))
    js = (_JS.replace("UID", uid)
             .replace("TIPS", json.dumps(tips))
             .replace("GROUPS", json.dumps(groups)))

    return (
        f"<style>{css}</style>"
        f"<div class='gt-root' id='{uid}'>"
        f"<div class='gt-head'>"
        f"<div class='gt-title'>{_esc(title or scenario.name)} — resource flow</div>"
        f"<div class='gt-note'>{_esc(note)}</div>"
        f"<div class='gt-toggle'>"
        f"<button class='on' data-view='transforms'>Transforms</button>"
        f"<button data-view='flow'>Resource flow</button></div></div>"
        f"<div class='gt-legend'>{legend}</div>"
        f"<div class='gt-stage'>{svg_a}{svg_b}<div class='gt-tip'></div></div>"
        f"<div class='gt-foot'>Hover any edge for the transforms responsible, or a "
        f"transform to light up its whole recipe. "
        f"Under universal decay every arrow into a resource is the only reason it "
        f"exists next turn.</div></div>"
        f"<script>{js}</script>"
    )


def show(scenario, runtime=None, **kwargs):
    """Display the DAG in a notebook."""
    from IPython.display import HTML
    return HTML(render_html(scenario, runtime=runtime, **kwargs))
