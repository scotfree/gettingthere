"""The determinism anchor. If this ever goes red, the replay guarantee is broken."""
from pathlib import Path

import numpy as np

from sim import initial_world, load_scenario, run_turn

SCENARIO = Path(__file__).resolve().parent.parent / "scenarios_data" / "simple-world.json"


def test_run_turn_is_deterministic():
    scenario = load_scenario(SCENARIO)
    a = initial_world(scenario, seed=0)
    b = initial_world(scenario, seed=0)
    for _ in range(50):
        a, ra = run_turn(a, scenario)
        b, rb = run_turn(b, scenario)
        assert np.array_equal(a.stock, b.stock)
        assert [(e.location_id, e.transform, e.count) for e in ra.events] == \
               [(e.location_id, e.transform, e.count) for e in rb.events]


def test_run_turn_does_not_mutate_input():
    scenario = load_scenario(SCENARIO)
    world = initial_world(scenario, seed=0)
    before = world.stock.copy()
    run_turn(world, scenario)
    assert np.array_equal(world.stock, before)
    assert world.tick == 0
