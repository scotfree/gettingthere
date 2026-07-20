"""Getting There — pure deterministic simulation core.

No I/O, no framework, no ambient randomness: a library that turns
(world, scenario, orders) into (world', replay).
"""
from .engine import FireEvent, Replay, process_location, run_turn
from .orders import SetTransformPriority, apply_orders
from .scenario import Scenario, load_scenario, scenario_from_dict
from .world import WorldState, initial_world

__all__ = [
    "Scenario",
    "load_scenario",
    "scenario_from_dict",
    "WorldState",
    "initial_world",
    "SetTransformPriority",
    "apply_orders",
    "run_turn",
    "process_location",
    "Replay",
    "FireEvent",
]
