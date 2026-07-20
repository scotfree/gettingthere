"""Mutable per-turn world state.

WorldState is the only thing that changes over a game: the stock matrix, the
per-location transform priority (persistent policy set by orders), plus tick and
seed. Everything structural lives in the immutable Scenario.
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
    transform_order: list[list[int]]     # per location: priority permutation of transform indices

    def copy(self) -> "WorldState":
        return WorldState(
            tick=self.tick,
            seed=self.seed,
            stock=self.stock.copy(),
            transform_order=[list(o) for o in self.transform_order],
        )


def initial_world(scenario: Scenario, seed: int = 0) -> WorldState:
    return WorldState(
        tick=0,
        seed=seed,
        stock=scenario.initial_stock.copy(),
        transform_order=[list(scenario.default_transform_order) for _ in range(scenario.L)],
    )
