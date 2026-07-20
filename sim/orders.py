"""Order vocabulary.

MVP has exactly one order: reprioritize the transforms at a location. Orders are
applied to the world at the start of a turn and *persist* — a priority change
stays in effect until changed again (it is policy, not a one-shot command).
"""
from __future__ import annotations

from dataclasses import dataclass

from .scenario import Scenario
from .world import WorldState


@dataclass
class SetTransformPriority:
    """Raise the named transforms to the front of a location's priority list.

    `order` is a partial list of transform names: they take the top priority
    slots in the given order, and any transforms not named keep their default
    (config) order behind them. Pass all names for a full permutation.
    """
    location_id: str
    order: list  # list[str]


def apply_orders(world: WorldState, scenario: Scenario, orders) -> None:
    """Mutate `world` in place, persisting each priority change."""
    for order in orders:
        if isinstance(order, SetTransformPriority):
            loc = scenario.location_index.get(order.location_id)
            if loc is None:
                raise ValueError(f"unknown location '{order.location_id}'")
            front: list[int] = []
            seen: set[int] = set()
            for name in order.order:
                if name not in scenario.transform_names:
                    raise ValueError(f"unknown transform '{name}'")
                t = scenario.transform_names.index(name)
                if t in seen:
                    raise ValueError(f"transform '{name}' listed twice")
                seen.add(t)
                front.append(t)
            rest = [t for t in scenario.default_transform_order if t not in seen]
            world.transform_order[loc] = front + rest
        else:
            raise TypeError(f"unknown order type: {type(order).__name__}")
