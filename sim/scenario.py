"""Scenario loading and compilation.

A scenario JSON is compiled once into integer arrays; the tick loop is pure
integer arithmetic over these (see engine.py). Nothing here does I/O beyond
reading the file, and nothing mutates after construction.

Two structural ideas beyond the resource/transform/location basics
(IMPLEMENTATION §3.1):

  - **Tagged edges.** Edges are directed and may carry tags. A symmetric road is
    two edges carrying opposite directional tags, which is what lets a transport
    transform pull one way without oscillating: filtering the graph to one tag
    leaves an acyclic direction field. `destinations` remains sugar for one
    untagged edge.
  - **Input sets.** A transform draws from the *union* of named pools rather
    than a fixed neighbourhood. `local` is the location's own stock, `nearby` is
    every location with an edge into it (the v0 default, and exactly the old
    behaviour), and any other tag restricts to edges carrying it. The rows a
    transform may consume are precomputed per (transform, location) at load, so
    the tick loop stays integer indexing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LOCAL = "local"
NEARBY = "nearby"
DEFAULT_INPUT_SETS = (LOCAL, NEARBY)


@dataclass(frozen=True)
class Scenario:
    name: str
    resources: list[str]                 # index i <-> resource name (the enum)
    resource_index: dict[str, int]
    transform_names: list[str]           # index t <-> transform name
    need: np.ndarray                     # (T, R) int: inputs
    emit: np.ndarray                     # (T, R) int: outputs
    actions: list[list[tuple]]           # per transform: (target transform index, delta) per firing
    input_sets: list[tuple]              # per transform: the pool tags it draws from
    location_ids: list[str]              # index l <-> location id
    location_index: dict[str, int]
    initial_stock: np.ndarray            # (L, R) int
    upstream: list[list[int]]            # per location: indices feeding into it (locations-list order)
    destinations: list[list[int]]        # per location: downstream indices
    upstream_by_tag: dict                # tag -> per location: upstream indices along edges with that tag
    consume_rows: list[list[list[int]]]  # [t][l] -> stock rows transform t may draw from at l
    evaluation_order: list[int]          # location indices, turn processing order

    @property
    def R(self) -> int:
        return len(self.resources)

    @property
    def T(self) -> int:
        return len(self.transform_names)

    @property
    def L(self) -> int:
        return len(self.location_ids)


def _vec(counts: dict, resource_index: dict[str, int], R: int, ctx: str) -> np.ndarray:
    v = np.zeros(R, dtype=np.int64)
    for name, qty in counts.items():
        if name not in resource_index:
            raise ValueError(f"{ctx}: unknown resource '{name}'")
        v[resource_index[name]] = qty
    return v


def _compile_actions(data: dict, transform_index: dict[str, int]) -> list[list[tuple]]:
    """Per transform: the (target transform, delta) pairs it emits per firing.

    Resolved after all names are known, because an action may target any
    transform, including one declared later.
    """
    actions: list[list[tuple]] = [[] for _ in transform_index]
    for t in data["transforms"]:
        for a in t.get("actions", []):
            kind = a.get("type", "priority_nudge")
            if kind != "priority_nudge":
                raise ValueError(f"transform '{t['name']}': unknown action type '{kind}'")
            target = a["transform"]
            if target not in transform_index:
                raise ValueError(
                    f"transform '{t['name']}' action: unknown target transform '{target}'")
            actions[transform_index[t["name"]]].append((transform_index[target], int(a["delta"])))
    return actions


def _compile_edges(data: dict, location_index: dict[str, int], L: int):
    """(destinations, upstream_by_tag) from `destinations` sugar plus explicit `edges`.

    `upstream_by_tag[tag][l]` is every location feeding `l` along an edge carrying
    `tag`; `nearby` collects all edges regardless of tag, which is why an untagged
    scenario behaves exactly as before.
    """
    destinations: list[list[int]] = [[] for _ in range(L)]
    # `nearby` always exists, even with no edges, so the default input set resolves
    tagged: dict[str, list[list[int]]] = {NEARBY: [[] for _ in range(L)]}

    def add_edge(src: int, dst: int, tags, ctx: str) -> None:
        if dst not in destinations[src]:
            destinations[src].append(dst)
        for tag in (NEARBY, *tags):
            if tag == LOCAL:
                raise ValueError(f"{ctx}: '{LOCAL}' is reserved and cannot tag an edge")
            rows = tagged.setdefault(tag, [[] for _ in range(L)])
            if src not in rows[dst]:
                rows[dst].append(src)

    for i, loc in enumerate(data["locations"]):
        for dst in loc.get("destinations", []):
            if dst not in location_index:
                raise ValueError(f"location '{loc['id']}': unknown destination '{dst}'")
            add_edge(i, location_index[dst], (), f"location '{loc['id']}'")

    for e in data.get("edges", []):
        for end in ("from", "to"):
            if e[end] not in location_index:
                raise ValueError(f"edge {e['from']}->{e['to']}: unknown location '{e[end]}'")
        add_edge(location_index[e["from"]], location_index[e["to"]], e.get("tags", []),
                 f"edge {e['from']}->{e['to']}")

    # keep every per-tag upstream list in locations-list order, so consumption is stable
    for rows in tagged.values():
        for l in range(L):
            rows[l].sort()
    for l in range(L):
        destinations[l].sort()
    return destinations, tagged


def _compile_consume_rows(input_sets, upstream_by_tag, T: int, L: int) -> list[list[list[int]]]:
    """[t][l] -> the stock rows transform t may draw from at location l.

    The union of the named sets, local row first so consumption drains local
    stock before reaching upstream (preserving the v0 draw order).
    """
    rows: list[list[list[int]]] = []
    for t in range(T):
        per_loc: list[list[int]] = []
        for l in range(L):
            chosen: list[int] = []
            for tag in input_sets[t]:
                if tag == LOCAL:
                    candidates = [l]
                else:
                    if tag not in upstream_by_tag:
                        raise ValueError(
                            f"transform index {t}: input set '{tag}' matches no edge tag")
                    candidates = upstream_by_tag[tag][l]
                for row in candidates:
                    if row not in chosen:
                        chosen.append(row)
            # local first, then upstream in locations-list order
            per_loc.append(sorted(chosen, key=lambda r: (r != l, r)))
        rows.append(per_loc)
    return rows


def scenario_from_dict(data: dict) -> Scenario:
    resources = list(data["resources"])
    resource_index = {r: i for i, r in enumerate(resources)}
    R = len(resources)

    transform_names: list[str] = []
    need_rows, emit_rows = [], []
    input_sets: list[tuple] = []
    for t in data["transforms"]:
        transform_names.append(t["name"])
        need_rows.append(_vec(t.get("inputs", {}), resource_index, R, f"transform '{t['name']}' inputs"))
        emit_rows.append(_vec(t.get("outputs", {}), resource_index, R, f"transform '{t['name']}' outputs"))
        input_sets.append(tuple(t.get("input_sets", DEFAULT_INPUT_SETS)))
    T = len(transform_names)
    transform_index = {n: i for i, n in enumerate(transform_names)}
    if len(transform_index) != T:
        raise ValueError("transform names must be unique")
    need = np.array(need_rows, dtype=np.int64).reshape(T, R)
    emit = np.array(emit_rows, dtype=np.int64).reshape(T, R)
    actions = _compile_actions(data, transform_index)

    location_ids = [loc["id"] for loc in data["locations"]]
    location_index = {lid: i for i, lid in enumerate(location_ids)}
    L = len(location_ids)

    initial_stock = np.zeros((L, R), dtype=np.int64)
    for i, loc in enumerate(data["locations"]):
        initial_stock[i] = _vec(loc.get("resources", {}), resource_index, R, f"location '{loc['id']}' resources")

    destinations, upstream_by_tag = _compile_edges(data, location_index, L)
    upstream = upstream_by_tag.get(NEARBY, [[] for _ in range(L)])
    consume_rows = _compile_consume_rows(input_sets, upstream_by_tag, T, L)

    eval_names = data["evaluation_order"]
    if sorted(eval_names) != sorted(location_ids):
        raise ValueError("evaluation_order must list every location exactly once")
    evaluation_order = [location_index[n] for n in eval_names]

    return Scenario(
        name=data.get("name", "unnamed"),
        resources=resources,
        resource_index=resource_index,
        transform_names=transform_names,
        need=need,
        emit=emit,
        actions=actions,
        input_sets=input_sets,
        location_ids=location_ids,
        location_index=location_index,
        initial_stock=initial_stock,
        upstream=upstream,
        destinations=destinations,
        upstream_by_tag=upstream_by_tag,
        consume_rows=consume_rows,
        evaluation_order=evaluation_order,
    )


def load_scenario(path) -> Scenario:
    return scenario_from_dict(json.loads(Path(path).read_text()))
