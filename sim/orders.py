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

Each delta is *paid for* with a `nudge` resource held at the location, one nudge
per point of movement (so `{"farming": +2}` costs two). Nudges are minted by
control terminals, are spent where they sit, and — being ordinary resources under
universal decay — evaporate if unspent. That is the whole political economy: your
turn is as large as the capacity you built.

A scenario that never declares a `nudge` resource simply cannot be nudged, and
saying otherwise is an authoring error rather than a free action.
"""
from __future__ import annotations

from dataclasses import dataclass

from .scenario import Scenario
from .world import WorldState


NUDGE = "nudge"


@dataclass
class SpendNudges:
    """Spend nudges held at a location on signed priority deltas.

    `deltas` maps transform name -> signed integer. A positive delta moves the
    transform toward the front of the location's stack (higher priority); a
    negative delta moves it back. Deltas accumulate onto the persistent score.
    Cost is the total distance moved: `sum(abs(delta))` nudges.
    """
    location_id: str
    deltas: dict  # dict[str, int]

    def cost(self) -> int:
        return sum(abs(int(d)) for d in self.deltas.values())


def apply_orders(world: WorldState, scenario: Scenario, orders) -> None:
    """Mutate `world` in place: pay for each order in nudges, then accumulate its deltas.

    Validation is all-or-nothing per order — an order that cannot be paid for
    raises rather than applying partially, so a rejected turn leaves no trace.
    """
    for order in orders:
        if not isinstance(order, SpendNudges):
            raise TypeError(f"unknown order type: {type(order).__name__}")

        loc = scenario.location_index.get(order.location_id)
        if loc is None:
            raise ValueError(f"unknown location '{order.location_id}'")
        targets = []
        for name, delta in order.deltas.items():
            if name not in scenario.transform_names:
                raise ValueError(f"unknown transform '{name}'")
            targets.append((scenario.transform_names.index(name), int(delta)))

        cost = order.cost()
        if cost:
            nudge_r = scenario.resource_index.get(NUDGE)
            if nudge_r is None:
                raise ValueError(
                    f"scenario '{scenario.name}' declares no '{NUDGE}' resource, so its "
                    "transform priorities cannot be nudged")
            held = int(world.stock[loc, nudge_r])
            if held < cost:
                raise ValueError(
                    f"location '{order.location_id}' holds {held} {NUDGE}(s) but the order "
                    f"costs {cost}")
            world.stock[loc, nudge_r] -= cost

        for t, delta in targets:
            world.priority[loc, t] += delta
