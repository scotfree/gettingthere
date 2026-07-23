"""The tick engine: universal decay over a location DAG.

Turn semantics (implementation guide §3.3):
  - A turn is a double-buffer: inputs are drawn from this turn's stock (`current`,
    which depletes as transforms consume it); outputs are written to a fresh
    `next_stock` that starts empty. At the end, `next_stock` becomes the world.
  - UNIVERSAL DECAY: anything not re-emitted by some transform is gone next turn.
    A resource persists only if a transform produces it — passive stockpiles do
    not exist; storage is itself a transform (e.g. `air -> air`, `food + energy
    -> food`). Population decline is emergent: a person no transform re-emits
    (because there was no food/air to run survival) simply is not in next_stock.
  - Because outputs land in the *next* buffer, there is no same-turn reuse or
    chaining: each token drives at most one transform per turn, and autocatalytic
    recipes cannot feed themselves (termination is trivial).
  - Locations are processed in evaluation_order; within a location, transforms in
    priority order — derived each turn from the persistent per-location score
    (`world.order(loc)`), so nudges that shifted the scores in earlier turns keep
    their effect. A location's pool = its own current stock + every upstream
    location's current stock. Consumption draws local stock first, then upstream
    in locations-list order; outputs land locally. Consuming upstream + producing
    locally is how resources migrate down the DAG.

Pure integer arithmetic, no RNG (seed is threaded for when randomness arrives),
so a turn replays identically.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .orders import apply_orders
from .scenario import Scenario
from .world import WorldState


@dataclass
class FireEvent:
    location_id: str
    transform: str
    count: int


@dataclass
class Replay:
    tick: int                # tick AFTER this turn
    events: list             # list[FireEvent], in evaluation order
    stock_after: np.ndarray


def _pool(current: np.ndarray, rows: list[int]) -> np.ndarray:
    """Sum of the stock rows a transform may draw from (its input sets, precompiled)."""
    pool = np.zeros(current.shape[1], dtype=current.dtype)
    for row in rows:
        pool += current[row]
    return pool


def _consume(current: np.ndarray, rows: list[int], amount: np.ndarray) -> None:
    """Remove `amount` per resource from the pool, draining `rows` in order.

    `rows` is local-first then upstream in locations-list order, so local stock
    goes before a neighbour's. The caller guarantees the pool holds at least
    `amount` (n was computed against it), so every resource is fully satisfied.
    """
    for r in range(amount.shape[0]):
        remaining = int(amount[r])
        if remaining == 0:
            continue
        for row in rows:
            if remaining == 0:
                break
            take = int(min(current[row, r], remaining))
            current[row, r] -= take
            remaining -= take


def process_location(current: np.ndarray, next_stock: np.ndarray, order: list,
                     scenario: Scenario, loc: int, pending: list | None = None) -> list:
    """Fire every transform once, in priority order. Consume from `current`, produce into `next_stock`.

    `pending`, if given, collects `(location, target transform, delta)` triples for
    priority nudges emitted by the transforms that fired. They are *not* applied
    here: nothing may mutate the order this pass is reading (IMPLEMENTATION §3.3).
    """
    events: list = []
    for t in order:
        need_t = scenario.need[t]
        emit_t = scenario.emit[t]
        mask = need_t > 0
        if not mask.any():
            continue  # no "something from nothing"
        rows = scenario.consume_rows[t][loc]
        pool = _pool(current, rows)
        n = int(np.min(pool[mask] // need_t[mask]))
        if n <= 0:
            continue
        print(f"T ({scenario.location_ids[loc]}): {scenario.transform_names[t]}: {','.join( [scenario.resources[k] for k in need_t] )} -> {','.join( [scenario.resources[k] for k in emit_t] )}")
        _consume(current, rows, n * need_t)
        next_stock[loc] += n * emit_t
        if pending is not None:
            for target, delta in scenario.actions[t]:
                pending.append((loc, target, delta * n))
        events.append(FireEvent(scenario.location_ids[loc], scenario.transform_names[t], n))
    return events


def run_turn(world: WorldState, scenario: Scenario, orders=(), seed: int | None = None):
    """(world, scenario, orders) -> (world', replay). Pure: the input world is not mutated."""
    new = world.copy()
    if seed is not None:
        new.seed = seed
    apply_orders(new, scenario, orders)

    # orders already applied, so `new.stock` reflects any nudges paid for this turn
    current = new.stock.copy()                # depletes as inputs are consumed
    next_stock = np.zeros_like(world.stock)   # built from outputs only -> everything else decays
    events: list = []
    pending: list = []                        # priority nudges emitted by transforms this turn
    for loc in scenario.evaluation_order:
        events.extend(process_location(current, next_stock, new.order(loc), scenario, loc, pending))

    # Applied only once the pass is over, so no location's stack changed under its
    # own evaluation. Deltas are additive, so the order of `pending` is irrelevant.
    for loc, target, delta in pending:
        new.priority[loc, target] += delta

    new.stock = next_stock
    new.tick += 1
    return new, Replay(tick=new.tick, events=events, stock_after=new.stock.copy())
