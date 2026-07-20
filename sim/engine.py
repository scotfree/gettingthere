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
    priority order. A location's pool = its own current stock + every upstream
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


def _pool(current: np.ndarray, loc: int, upstream: list[int]) -> np.ndarray:
    pool = current[loc].copy()
    for u in upstream:
        pool += current[u]
    return pool


def _consume(current: np.ndarray, loc: int, upstream: list[int], amount: np.ndarray) -> None:
    """Remove `amount` per resource from the pool: local row first, then upstream in order.

    The caller guarantees the pool holds at least `amount` (n was computed
    against it), so every resource is fully satisfied.
    """
    rows = [loc, *upstream]
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
                     scenario: Scenario, loc: int) -> list:
    """Fire every transform once, in priority order. Consume from `current`, produce into `next_stock`."""
    events: list = []
    upstream = scenario.upstream[loc]
    for t in order:
        need_t = scenario.need[t]
        emit_t = scenario.emit[t]
        mask = need_t > 0
        if not mask.any():
            continue  # no "something from nothing"
        pool = _pool(current, loc, upstream)
        n = int(np.min(pool[mask] // need_t[mask]))
        if n <= 0:
            continue
        _consume(current, loc, upstream, n * need_t)
        next_stock[loc] += n * emit_t
        events.append(FireEvent(scenario.location_ids[loc], scenario.transform_names[t], n))
    return events


def run_turn(world: WorldState, scenario: Scenario, orders=(), seed: int | None = None):
    """(world, scenario, orders) -> (world', replay). Pure: the input world is not mutated."""
    new = world.copy()
    if seed is not None:
        new.seed = seed
    apply_orders(new, scenario, orders)

    current = world.stock.copy()              # depletes as inputs are consumed
    next_stock = np.zeros_like(world.stock)   # built from outputs only -> everything else decays
    events: list = []
    for loc in scenario.evaluation_order:
        events.extend(process_location(current, next_stock, new.transform_order[loc], scenario, loc))

    new.stock = next_stock
    new.tick += 1
    return new, Replay(tick=new.tick, events=events, stock_after=new.stock.copy())
