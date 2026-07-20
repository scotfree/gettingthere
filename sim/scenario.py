"""Scenario loading and compilation.

A scenario JSON is compiled once into integer arrays; the tick loop is pure
integer arithmetic over these (see engine.py). Nothing here does I/O beyond
reading the file, and nothing mutates after construction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Scenario:
    name: str
    resources: list[str]                 # index i <-> resource name (the enum)
    resource_index: dict[str, int]
    transform_names: list[str]           # index t <-> transform name
    need: np.ndarray                     # (T, R) int: inputs
    emit: np.ndarray                     # (T, R) int: outputs
    location_ids: list[str]              # index l <-> location id
    location_index: dict[str, int]
    initial_stock: np.ndarray            # (L, R) int
    upstream: list[list[int]]            # per location: indices feeding into it (locations-list order)
    destinations: list[list[int]]        # per location: downstream indices
    default_transform_order: list[int]   # config order == priority
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


def scenario_from_dict(data: dict) -> Scenario:
    resources = list(data["resources"])
    resource_index = {r: i for i, r in enumerate(resources)}
    R = len(resources)

    transform_names: list[str] = []
    need_rows, emit_rows = [], []
    for t in data["transforms"]:
        transform_names.append(t["name"])
        need_rows.append(_vec(t.get("inputs", {}), resource_index, R, f"transform '{t['name']}' inputs"))
        emit_rows.append(_vec(t.get("outputs", {}), resource_index, R, f"transform '{t['name']}' outputs"))
    T = len(transform_names)
    need = np.array(need_rows, dtype=np.int64).reshape(T, R)
    emit = np.array(emit_rows, dtype=np.int64).reshape(T, R)

    location_ids = [loc["id"] for loc in data["locations"]]
    location_index = {lid: i for i, lid in enumerate(location_ids)}
    L = len(location_ids)

    initial_stock = np.zeros((L, R), dtype=np.int64)
    destinations: list[list[int]] = [[] for _ in range(L)]
    for i, loc in enumerate(data["locations"]):
        initial_stock[i] = _vec(loc.get("resources", {}), resource_index, R, f"location '{loc['id']}' resources")
        for dst in loc.get("destinations", []):
            if dst not in location_index:
                raise ValueError(f"location '{loc['id']}': unknown destination '{dst}'")
            destinations[i].append(location_index[dst])

    # upstream[l] = every location that lists l as a destination, in locations-list order
    upstream: list[list[int]] = [[] for _ in range(L)]
    for i in range(L):
        for dst in destinations[i]:
            upstream[dst].append(i)

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
        location_ids=location_ids,
        location_index=location_index,
        initial_stock=initial_stock,
        upstream=upstream,
        destinations=destinations,
        default_transform_order=list(range(T)),
        evaluation_order=evaluation_order,
    )


def load_scenario(path) -> Scenario:
    return scenario_from_dict(json.loads(Path(path).read_text()))
