"""Hand-worked mechanical cases for the universal-decay engine."""
import numpy as np

from sim import initial_world, run_turn, scenario_from_dict, SpendNudges


def _stock(world, scenario, location, resource):
    return int(world.stock[scenario.location_index[location], scenario.resource_index[resource]])


def test_unreemitted_resources_decay():
    # air_storage keeps air; nothing re-emits the plant, so it vanishes next turn.
    scenario = scenario_from_dict({
        "resources": ["plant", "air"],
        "transforms": [{"name": "air_storage", "inputs": {"air": 1}, "outputs": {"air": 1}}],
        "locations": [{"id": "loc", "resources": {"plant": 5, "air": 2}, "destinations": []}],
        "evaluation_order": ["loc"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "loc", "air") == 2    # persisted by storage
    assert _stock(world, scenario, "loc", "plant") == 0  # decayed


def test_no_same_turn_chaining():
    # photosynthesis makes energy into next_stock; a same-turn energy consumer can't see it.
    scenario = scenario_from_dict({
        "resources": ["plant", "energy", "food"],
        "transforms": [
            {"name": "photosynthesis", "inputs": {"plant": 1}, "outputs": {"plant": 1, "energy": 1}},
            {"name": "convert", "inputs": {"energy": 1}, "outputs": {"food": 1}},
        ],
        "locations": [{"id": "loc", "resources": {"plant": 3, "energy": 0}, "destinations": []}],
        "evaluation_order": ["loc"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "loc", "energy") == 3  # produced this turn
    assert _stock(world, scenario, "loc", "food") == 0    # convert saw no current energy -> no chaining


def test_population_declines_under_shortage():
    # THE payoff of universal decay: unfed people are not re-emitted, so they die.
    scenario = scenario_from_dict({
        "resources": ["person", "food", "air"],
        "transforms": [
            {"name": "survival", "inputs": {"person": 1, "food": 1, "air": 1}, "outputs": {"person": 1}},
        ],
        "locations": [{"id": "hab", "resources": {"person": 5, "food": 2, "air": 5}, "destinations": []}],
        "evaluation_order": ["hab"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "hab", "person") == 2  # only 2 could be fed; other 3 decayed


def test_work_transform_consumes_metabolism():
    # farming embeds eating: the worker consumes food+air, so working is not free survival.
    scenario = scenario_from_dict({
        "resources": ["person", "food", "air", "plant", "energy"],
        "transforms": [
            {"name": "farming",
             "inputs": {"person": 1, "food": 1, "air": 1, "plant": 1, "energy": 1},
             "outputs": {"person": 1, "food": 2}},
        ],
        "locations": [{"id": "hab",
                       "resources": {"person": 1, "food": 1, "air": 1, "plant": 1, "energy": 1},
                       "destinations": []}],
        "evaluation_order": ["hab"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "hab", "person") == 1  # fed and re-emitted
    assert _stock(world, scenario, "hab", "food") == 2    # ate 1, produced 2
    assert _stock(world, scenario, "hab", "air") == 0     # breathed it (consumed, not stored)


def test_transform_order_changes_outcome():
    data = {
        "resources": ["plant", "energy", "air"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
        ],
        "locations": [{"id": "green", "resources": {"plant": 4, "energy": 3}, "destinations": []}],
        "evaluation_order": ["green"],
    }
    scenario = scenario_from_dict(data)
    # growth is authored first (index 0); a +1 nudge lifts atmosphere (index 1) above it.
    growth_first, _ = run_turn(initial_world(scenario), scenario)
    atmo_first, _ = run_turn(initial_world(scenario), scenario,
                             orders=[SpendNudges("green", {"atmosphere": +1})])
    assert _stock(growth_first, scenario, "green", "air") == 0
    assert _stock(atmo_first, scenario, "green", "air") == 3
    assert not np.array_equal(growth_first.stock, atmo_first.stock)


def test_priority_persists_across_turns():
    scenario = scenario_from_dict({
        "resources": ["plant", "energy", "air"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
        ],
        "locations": [{"id": "green", "resources": {"plant": 40, "energy": 40}, "destinations": []}],
        "evaluation_order": ["green"],
    })
    green = scenario.location_index["green"]
    world = initial_world(scenario)
    # Nudge once; the score edit persists, so later plain turns keep the new order
    # without the delta being re-applied.
    world, _ = run_turn(world, scenario, orders=[SpendNudges("green", {"atmosphere": +1})])
    assert scenario.transform_names[world.order(green)[0]] == "atmosphere"
    world, _ = run_turn(world, scenario)   # no order this turn
    assert scenario.transform_names[world.order(green)[0]] == "atmosphere"


def test_priority_deltas_superpose():
    # Two nudges onto the same score commute: applying +2 then -1 gives the same
    # persistent state as -1 then +2, and both net +1 (atmosphere ahead of growth).
    def make():
        return scenario_from_dict({
            "resources": ["plant", "energy", "air"],
            "transforms": [
                {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
                {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
            ],
            "locations": [{"id": "green", "resources": {"plant": 40, "energy": 40}, "destinations": []}],
            "evaluation_order": ["green"],
        })

    scenario = make()
    green = scenario.location_index["green"]

    a = initial_world(scenario)
    a, _ = run_turn(a, scenario, orders=[SpendNudges("green", {"atmosphere": +2}),
                                         SpendNudges("green", {"atmosphere": -1})])
    b = initial_world(scenario)
    b, _ = run_turn(b, scenario, orders=[SpendNudges("green", {"atmosphere": -1}),
                                         SpendNudges("green", {"atmosphere": +2})])

    assert np.array_equal(a.priority, b.priority)         # arrival order irrelevant
    assert a.order(green) == b.order(green)
    assert int(a.priority[green, scenario.transform_names.index("atmosphere")]) == 1  # net +1
    assert scenario.transform_names[a.order(green)[0]] == "atmosphere"


def test_upstream_pool_and_downstream_migration():
    # habitat consumes greenhouse's plant across the edge; produced food lands in habitat.
    scenario = scenario_from_dict({
        "resources": ["person", "food", "plant"],
        "transforms": [
            {"name": "harvest", "inputs": {"person": 1, "plant": 1}, "outputs": {"person": 1, "food": 1}},
        ],
        "locations": [
            {"id": "greenhouse", "resources": {"plant": 5}, "destinations": ["habitat"]},
            {"id": "habitat", "resources": {"person": 2}, "destinations": []},
        ],
        "evaluation_order": ["habitat", "greenhouse"],
    })
    world, replay = run_turn(initial_world(scenario), scenario)
    assert replay.events[0].count == 2                          # min(person 2, plant 5)
    assert _stock(world, scenario, "habitat", "food") == 2      # produced downstream
    assert _stock(world, scenario, "habitat", "person") == 2    # re-emitted
    assert _stock(world, scenario, "greenhouse", "plant") == 0  # 2 consumed, 3 decayed
