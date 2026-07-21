"""Notebook-only static + observed analysis of a Scenario.

Pure derivation: everything here reads a Scenario (and optionally replays turns
through the engine) and returns plain data or Markdown. No rendering, no
mutation. Kept OUT of sim/ alongside viz.py for the same reason.

The interesting derivations are the ones universal decay makes load-bearing:
a resource exists next turn only if some transform emits it, so "what emits
this, and what does that cost" is the whole economy.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np

ARROW = "→"


# --------------------------------------------------------------------------
# static facts
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class TransformFacts:
    index: int
    name: str
    inputs: dict[str, int]
    outputs: dict[str, int]
    net: dict[str, int]              # non-zero net change per firing
    catalysts: tuple[str, ...]       # present in both sides at equal quantity
    consumed: tuple[str, ...]        # net negative
    produced: tuple[str, ...]        # net positive
    amplifies: dict[str, float]      # resource -> out/in ratio, where out > in > 0
    kind: str
    recipe: str


@dataclass(frozen=True)
class HoldPath:
    """A way to carry a resource into the next turn, and what it costs."""
    transform: str
    emitted: int                     # units of the resource emitted per firing
    cost: dict[str, float]           # other resources spent, per unit carried

    @property
    def free(self) -> bool:
        return not self.cost


@dataclass(frozen=True)
class ResourceFacts:
    index: int
    name: str
    initial_total: int
    emitted_by: tuple[str, ...]
    consumed_by: tuple[str, ...]
    net_producers: tuple[str, ...]
    net_consumers: tuple[str, ...]
    holds: tuple[HoldPath, ...]      # cheapest first
    orphan: bool                     # nothing emits it: decays to zero, always
    inert: bool                      # nothing needs it


@dataclass(frozen=True)
class LocationFacts:
    index: int
    id: str
    initial: dict[str, int]
    upstream: tuple[str, ...]
    downstream: tuple[str, ...]
    eval_position: int
    drained_by: tuple[str, ...]      # consumers evaluated before this location


def _nz(vec, resources) -> dict[str, int]:
    return {resources[i]: int(v) for i, v in enumerate(vec) if v}


def _fmt_side(counts: dict[str, int]) -> str:
    if not counts:
        return "nothing"
    return " + ".join(f"{q} {r}" for r, q in counts.items())


def _fmt_num(x: float) -> str:
    return f"{x:g}"


def transform_facts(scenario) -> list[TransformFacts]:
    out: list[TransformFacts] = []
    for t, name in enumerate(scenario.transform_names):
        need = scenario.need[t]
        emit = scenario.emit[t]
        inputs = _nz(need, scenario.resources)
        outputs = _nz(emit, scenario.resources)
        net = _nz(emit - need, scenario.resources)

        catalysts = tuple(r for r in inputs if outputs.get(r) == inputs[r])
        consumed = tuple(r for r, v in net.items() if v < 0)
        produced = tuple(r for r, v in net.items() if v > 0)
        amplifies = {
            r: outputs[r] / inputs[r]
            for r in inputs
            if outputs.get(r, 0) > inputs[r] > 0
        }

        if inputs == outputs:
            kind = "free storage"
        elif produced and not consumed:
            kind = "free production"
        elif produced and consumed:
            kind = "conversion"
        elif catalysts:
            kind = "upkeep"
        else:
            kind = "sink"

        out.append(TransformFacts(
            index=t, name=name, inputs=inputs, outputs=outputs, net=net,
            catalysts=catalysts, consumed=consumed, produced=produced,
            amplifies=amplifies, kind=kind,
            recipe=f"{_fmt_side(inputs)} {ARROW} {_fmt_side(outputs)}",
        ))
    return out


def resource_facts(scenario, tfacts: list[TransformFacts] | None = None) -> list[ResourceFacts]:
    tfacts = tfacts or transform_facts(scenario)
    totals = scenario.initial_stock.sum(axis=0)
    out: list[ResourceFacts] = []

    for i, name in enumerate(scenario.resources):
        emitted_by = tuple(f.name for f in tfacts if f.outputs.get(name, 0) > 0)
        consumed_by = tuple(f.name for f in tfacts if f.inputs.get(name, 0) > 0)

        holds: list[HoldPath] = []
        for f in tfacts:
            e = f.outputs.get(name, 0)
            if e <= 0:
                continue
            cost = {}
            for r, q in f.inputs.items():
                if r == name:
                    continue
                spent = q - f.outputs.get(r, 0)
                if spent > 0:
                    cost[r] = spent / e
            holds.append(HoldPath(transform=f.name, emitted=e, cost=cost))
        holds.sort(key=lambda h: (len(h.cost), sum(h.cost.values())))

        out.append(ResourceFacts(
            index=i, name=name, initial_total=int(totals[i]),
            emitted_by=emitted_by, consumed_by=consumed_by,
            net_producers=tuple(f.name for f in tfacts if f.net.get(name, 0) > 0),
            net_consumers=tuple(f.name for f in tfacts if f.net.get(name, 0) < 0),
            holds=tuple(holds),
            orphan=not emitted_by,
            inert=not consumed_by,
        ))
    return out


def location_facts(scenario) -> list[LocationFacts]:
    position = {loc: p for p, loc in enumerate(scenario.evaluation_order)}
    out: list[LocationFacts] = []
    for i, lid in enumerate(scenario.location_ids):
        drained = tuple(
            scenario.location_ids[d]
            for d in scenario.destinations[i]
            if position[d] < position[i]
        )
        out.append(LocationFacts(
            index=i, id=lid,
            initial=_nz(scenario.initial_stock[i], scenario.resources),
            upstream=tuple(scenario.location_ids[u] for u in scenario.upstream[i]),
            downstream=tuple(scenario.location_ids[d] for d in scenario.destinations[i]),
            eval_position=position[i],
            drained_by=drained,
        ))
    return out


def resource_graph(scenario, tfacts: list[TransformFacts] | None = None) -> nx.DiGraph:
    """Collapsed view: resource A -> resource B if some transform eats A and emits B.

    Each edge carries `transforms`: the list of transform names responsible.
    """
    tfacts = tfacts or transform_facts(scenario)
    G = nx.DiGraph()
    for r in scenario.resources:
        G.add_node(r)
    for f in tfacts:
        for a in f.inputs:
            for b in f.outputs:
                if G.has_edge(a, b):
                    G[a][b]["transforms"].append(f.name)
                else:
                    G.add_edge(a, b, transforms=[f.name])
    return G


def bipartite_graph(scenario, tfacts: list[TransformFacts] | None = None) -> nx.DiGraph:
    """Petri-net view: resource nodes and transform nodes, edges are consume/produce."""
    tfacts = tfacts or transform_facts(scenario)
    G = nx.DiGraph()
    for r in scenario.resources:
        G.add_node(("resource", r), kind="resource", label=r)
    for f in tfacts:
        G.add_node(("transform", f.name), kind="transform", label=f.name)
        for r, q in f.inputs.items():
            G.add_edge(("resource", r), ("transform", f.name),
                       qty=q, resource=r, transform=f.name, role="consume")
        for r, q in f.outputs.items():
            G.add_edge(("transform", f.name), ("resource", r),
                       qty=q, resource=r, transform=f.name, role="produce")
    return G


def feedback_loops(scenario, tfacts: list[TransformFacts] | None = None,
                   max_len: int = 4, limit: int = 12) -> list[list[str]]:
    """Multi-resource cycles in the collapsed graph (self-loops are storage, not loops)."""
    G = resource_graph(scenario, tfacts)
    G.remove_edges_from(nx.selfloop_edges(G))
    cycles = [c for c in nx.simple_cycles(G) if 2 <= len(c) <= max_len]
    cycles.sort(key=lambda c: (len(c), c))
    return cycles[:limit]


# --------------------------------------------------------------------------
# observed behaviour
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class RuntimeFacts:
    ticks: int
    fires_by_transform: dict[str, int]
    fires_by_location: dict[tuple[str, str], int]     # (location, transform) -> count
    fires_per_tick: list[dict[str, int]]              # transform -> count, per tick
    stock_history: np.ndarray                         # (ticks+1, L, R)
    never_fired: tuple[str, ...]
    first_zero: dict[str, int]                        # resource -> first tick total hit 0


def run_and_observe(scenario, ticks: int = 8, seed: int = 0, orders=()) -> RuntimeFacts:
    """Replay `ticks` turns and record what actually fired.

    Orders are applied on the first turn only; transform priority persists, so
    that is enough to hold a policy for the whole run.
    """
    from sim import initial_world, run_turn

    world = initial_world(scenario, seed=seed)
    history = [world.stock.copy()]
    fires_by_transform: dict[str, int] = {n: 0 for n in scenario.transform_names}
    fires_by_location: dict[tuple[str, str], int] = {}
    fires_per_tick: list[dict[str, int]] = []

    for tick in range(ticks):
        world, replay = run_turn(world, scenario, orders=orders if tick == 0 else ())
        this_tick: dict[str, int] = {}
        for e in replay.events:
            fires_by_transform[e.transform] += e.count
            key = (e.location_id, e.transform)
            fires_by_location[key] = fires_by_location.get(key, 0) + e.count
            this_tick[e.transform] = this_tick.get(e.transform, 0) + e.count
        fires_per_tick.append(this_tick)
        history.append(world.stock.copy())

    stock_history = np.array(history)
    totals = stock_history.sum(axis=1)                 # (ticks+1, R)
    first_zero: dict[str, int] = {}
    for i, name in enumerate(scenario.resources):
        zeros = np.flatnonzero(totals[:, i] == 0)
        if zeros.size and totals[0, i] != 0:
            first_zero[name] = int(zeros[0])

    return RuntimeFacts(
        ticks=ticks,
        fires_by_transform=fires_by_transform,
        fires_by_location=fires_by_location,
        fires_per_tick=fires_per_tick,
        stock_history=stock_history,
        never_fired=tuple(n for n, c in fires_by_transform.items() if c == 0),
        first_zero=first_zero,
    )


# --------------------------------------------------------------------------
# markdown report
# --------------------------------------------------------------------------

def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(none)_\n"
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def _hold_str(h: HoldPath) -> str:
    if h.free:
        return f"`{h.transform}` (free)"
    cost = ", ".join(f"{_fmt_num(v)} {r}" for r, v in h.cost.items())
    return f"`{h.transform}` ({cost} per unit)"


def rules_summary(scenario, description: str = "") -> str:
    tf = transform_facts(scenario)
    rf = resource_facts(scenario, tf)
    lf = location_facts(scenario)

    md = [f"## {scenario.name}\n"]
    if description:
        md.append(f"_{description}_\n")
    md.append(
        f"**{scenario.R} resources · {scenario.T} transforms · {scenario.L} locations**\n"
    )

    md.append("### Transforms\n")
    md.append(_table(
        ["transform", "recipe", "kind", "net effect", "notes"],
        [[
            f"`{f.name}`",
            f.recipe,
            f.kind,
            ", ".join(f"{v:+d} {r}" for r, v in f.net.items()) or "none (pure hold)",
            ", ".join(
                [f"amplifies {r} ×{_fmt_num(g)}" for r, g in f.amplifies.items()]
                + ([f"needs {', '.join(f.catalysts)} present"] if f.catalysts else [])
            ) or "—",
        ] for f in tf],
    ))

    md.append("### Resources — persistence under universal decay\n")
    md.append(
        "Nothing carries over on its own. A resource survives the turn only if a "
        "transform emits it, so the *cheapest hold* column is the actual cost of "
        "simply existing.\n"
    )
    rows = []
    for r in rf:
        if r.orphan:
            status = "**orphan — nothing emits it, decays to zero**"
        elif any(h.free for h in r.holds):
            status = "self-sustaining"
        else:
            status = "needs upkeep every turn"
        rows.append([
            f"`{r.name}`",
            str(r.initial_total),
            ", ".join(f"`{n}`" for n in r.emitted_by) or "—",
            ", ".join(f"`{n}`" for n in r.consumed_by) or "—",
            _hold_str(r.holds[0]) if r.holds else "—",
            status,
        ])
    md.append(_table(
        ["resource", "initial", "emitted by", "consumed by", "cheapest hold", "status"],
        rows,
    ))

    md.append("### Systems\n")
    free_energy = [f.name for f in tf if f.kind == "free production"]
    amps = [(f.name, r, g) for f in tf for r, g in f.amplifies.items()]
    loops = feedback_loops(scenario, tf)
    G = resource_graph(scenario, tf)

    sys_lines = []
    if free_energy:
        sys_lines.append(
            "- **Free production:** " + ", ".join(f"`{n}`" for n in free_energy)
            + " — output with no net input. These are the only true sources; "
            "everything else is a redistribution."
        )
    if amps:
        sys_lines.append(
            "- **Amplifiers:** "
            + ", ".join(f"`{n}` grows {r} ×{_fmt_num(g)}" for n, r, g in amps)
            + " — the only way the economy expands."
        )
    for cycle in loops:
        hops = []
        for a, b in zip(cycle, cycle[1:] + cycle[:1]):
            hops.append(f"{a} {ARROW}[{'/'.join(G[a][b]['transforms'])}]{ARROW} {b}")
        sys_lines.append("- **Loop:** " + " · ".join(hops))
    md.append("\n".join(sys_lines) + "\n" if sys_lines else "_(no loops or sources)_\n")

    md.append("### Locations\n")
    md.append(_table(
        ["location", "eval #", "initial stock", "upstream (pool it may draw from)", "feeds"],
        [[
            f"`{l.id}`",
            str(l.eval_position),
            _fmt_side(l.initial),
            ", ".join(f"`{u}`" for u in l.upstream) or "—",
            ", ".join(f"`{d}`" for d in l.downstream) or "—",
        ] for l in lf],
    ))

    warnings = []
    for r in rf:
        if r.orphan and r.initial_total:
            warnings.append(
                f"- `{r.name}` starts with {r.initial_total} but no transform emits it — "
                "it is gone after one turn."
            )
    for l in lf:
        for consumer in l.drained_by:
            warnings.append(
                f"- `{l.id}` feeds `{consumer}`, but `{consumer}` is evaluated first and "
                f"draws from `{l.id}`'s pool. `{l.id}` may be empty by its own turn, "
                "making it a one-turn pass-through buffer rather than a producer."
            )
    if warnings:
        md.append("### Warnings\n")
        md.append("\n".join(warnings) + "\n")

    return "\n".join(md)


def observed_summary(scenario, runtime: RuntimeFacts) -> str:
    tf = {f.name: f for f in transform_facts(scenario)}
    md = [f"## Observed over {runtime.ticks} ticks\n"]

    md.append("### What actually fired\n")
    rows = []
    for name, total in runtime.fires_by_transform.items():
        per_loc = ", ".join(
            f"{lid} ×{c}" for (lid, tname), c in runtime.fires_by_location.items()
            if tname == name
        )
        ticks_active = sum(1 for t in runtime.fires_per_tick if t.get(name))
        rows.append([
            f"`{name}`",
            tf[name].kind,
            str(total),
            f"{ticks_active}/{runtime.ticks}",
            per_loc or "**never fired**",
        ])
    rows.sort(key=lambda r: -int(r[2]))
    md.append(_table(["transform", "kind", "total fires", "ticks active", "where"], rows))

    if runtime.never_fired:
        md.append(
            "**Dead rules:** " + ", ".join(f"`{n}`" for n in runtime.never_fired)
            + " never fired — defined but inert in this scenario.\n"
        )

    md.append("### Totals per tick\n")
    totals = runtime.stock_history.sum(axis=1)
    md.append(_table(
        ["tick"] + [f"`{r}`" for r in scenario.resources],
        [[str(t)] + [str(int(v)) for v in totals[t]] for t in range(totals.shape[0])],
    ))

    if runtime.first_zero:
        md.append(
            "**Ran out:** "
            + ", ".join(f"`{r}` at tick {t}" for r, t in sorted(runtime.first_zero.items(),
                                                               key=lambda kv: kv[1]))
            + "\n"
        )
    return "\n".join(md)
