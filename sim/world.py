"""Mutable per-turn world state.

WorldState is the only thing that changes over a game: the stock matrix, the
per-location transform priority (persistent policy set by orders), plus tick and
seed. Everything structural lives in the immutable Scenario.

Priority is a *score*, not a slot. `priority[l][t]` is an accumulated signed
delta (default 0); the evaluation order at a location is the transforms sorted
by that score. A nudge (see orders.py) edits the score *once*, so the score is
the persistent state — the transform keeps its new position until some other
nudge moves it, never re-applying the delta each turn. Deltas from any number of
sources superpose commutatively (adding to a sort key is order-independent),
which is why orders need no arbitration or tiebreak rule — see IMPLEMENTATION
§3.3. The score is deliberately player-agnostic: who authored a delta never
enters the arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .scenario import Scenario


@dataclass
class WorldState:
    tick: int
    seed: int
    stock: np.ndarray                    # (L, R) int
    priority: np.ndarray                 # (L, T) int: accumulated signed priority deltas (default 0)

    def copy(self) -> "WorldState":
        return WorldState(
            tick=self.tick,
            seed=self.seed,
            stock=self.stock.copy(),
            priority=self.priority.copy(),
        )

    def order(self, loc: int) -> list[int]:
        """Transform indices for `loc` in evaluation order: highest score first.

        A higher score fires earlier (claims the shared pool first); ties fall
        back to authored order, so an all-zero row reproduces the config order
        `[0, 1, ..., T-1]` exactly. A positive delta moves a transform toward
        the front.
        """
        T = self.priority.shape[1]
        return sorted(range(T), key=lambda t: (-int(self.priority[loc, t]), t))


def initial_world(scenario: Scenario, seed: int = 0) -> WorldState:
    return WorldState(
        tick=0,
        seed=seed,
        stock=scenario.initial_stock.copy(),
        priority=np.zeros((scenario.L, scenario.T), dtype=np.int64),
    )
