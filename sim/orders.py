"""Order vocabulary.

MVP has exactly one order: nudge the transform priority at a location. An order
carries signed *priority deltas* — `{transform_name: delta}` — which are added to
the location's persistent priority scores.

Deltas superpose and persist:
  - **Superpose:** several sources nudging the same transform simply sum (a
    player's +3 and a rival movement's -2 net +1). Adding to a sort key is
    commutative, so there is no arbitration, no majority check, and no tiebreak
    rule — application order never changes the result.
  - **Persist:** the delta edits the score *once*, at submission. The score is
    the world's persistent state, so the transform keeps its new position until
    some other nudge moves it. Nothing re-applies the delta each turn.

The order is named `SpendNudges` because in the full design (IMPLEMENTATION §3.1,
GDD §6) each delta is paid for with a `nudge` resource held at the location. That
resource — and the "do you hold k nudges here?" check — is a designed-but-not-yet-
implemented extension; v0 applies the deltas directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from .scenario import Scenario
from .world import WorldState


@dataclass
class SpendNudges:
    """Apply signed priority deltas to the transforms at a location.

    `deltas` maps transform name -> signed integer. A positive delta moves the
    transform toward the front of the location's stack (higher priority); a
    negative delta moves it back. Deltas accumulate onto the persistent score.
    """
    location_id: str
    deltas: dict  # dict[str, int]


def apply_orders(world: WorldState, scenario: Scenario, orders) -> None:
    """Mutate `world` in place, accumulating each priority delta onto the score."""
    for order in orders:
        if isinstance(order, SpendNudges):
            loc = scenario.location_index.get(order.location_id)
            if loc is None:
                raise ValueError(f"unknown location '{order.location_id}'")
            for name, delta in order.deltas.items():
                if name not in scenario.transform_names:
                    raise ValueError(f"unknown transform '{name}'")
                t = scenario.transform_names.index(name)
                world.priority[loc, t] += int(delta)
        else:
            raise TypeError(f"unknown order type: {type(order).__name__}")
