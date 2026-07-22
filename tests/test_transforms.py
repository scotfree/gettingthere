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
        "resources": ["plant", "energy", "air", "nudge"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
        ],
        "locations": [{"id": "green", "resources": {"plant": 4, "energy": 3, "nudge": 1},
                       "destinations": []}],
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
        "resources": ["plant", "energy", "air", "nudge"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
        ],
        "locations": [{"id": "green", "resources": {"plant": 40, "energy": 40, "nudge": 1},
                       "destinations": []}],
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
            "resources": ["plant", "energy", "air", "nudge"],
            "transforms": [
                {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
                {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 1, "air": 1}},
            ],
            "locations": [{"id": "green", "resources": {"plant": 40, "energy": 40, "nudge": 3},
                           "destinations": []}],
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


# --- tagged edges and input sets -------------------------------------------

def _wood_world(haul_input_set, storage=True):
    """forest <-> town as a symmetric road, tagged in opposite directions."""
    transforms = [{"name": "haul", "input_sets": [haul_input_set],
                   "inputs": {"wood": 1}, "outputs": {"wood": 1}}]
    if storage:
        transforms.append({"name": "store", "input_sets": ["local"],
                           "inputs": {"wood": 1}, "outputs": {"wood": 1}})
    return scenario_from_dict({
        "resources": ["wood"],
        "transforms": transforms,
        "locations": [
            {"id": "forest", "resources": {"wood": 4}},
            {"id": "town", "resources": {}},
        ],
        "edges": [
            {"from": "forest", "to": "town", "tags": ["cityward"]},
            {"from": "town", "to": "forest", "tags": ["forestward"]},
        ],
        "evaluation_order": ["town", "forest"],
    })


def test_directional_tag_moves_goods_one_hop_and_holds():
    # Pulling along `cityward` only: wood walks forest -> town, then stays put.
    scenario = _wood_world("cityward")
    world = initial_world(scenario)

    world, _ = run_turn(world, scenario)
    assert _stock(world, scenario, "town", "wood") == 4
    assert _stock(world, scenario, "forest", "wood") == 0

    world, _ = run_turn(world, scenario)     # nothing upstream of town along cityward
    assert _stock(world, scenario, "town", "wood") == 4    # held by local storage
    assert _stock(world, scenario, "forest", "wood") == 0


def test_untagged_pull_flows_back_which_is_why_tags_exist():
    # The symmetric road is a 2-cycle, so topology alone carries no direction
    # (GDD §6). Same graph, same turn count, only the input set differs: pulling
    # on `nearby` lets the wood walk home again, pulling on `cityward` does not.
    # Storage is omitted deliberately — with a local store the downstream
    # location claims the goods before the back-pull is ever evaluated, which
    # hides the difference rather than removing it.
    def after_two_turns(tag):
        scenario = _wood_world(tag, storage=False)
        world = initial_world(scenario)
        for _ in range(2):
            world, _ = run_turn(world, scenario)
        return _stock(world, scenario, "forest", "wood")

    assert after_two_turns("nearby") == 4      # pulled straight back to the forest
    assert after_two_turns("cityward") == 0    # no back-edge carries the tag


def test_local_input_set_cannot_reach_upstream():
    scenario = scenario_from_dict({
        "resources": ["wood"],
        "transforms": [{"name": "hoard", "input_sets": ["local"],
                        "inputs": {"wood": 1}, "outputs": {"wood": 1}}],
        "locations": [
            {"id": "forest", "resources": {"wood": 5}, "destinations": ["town"]},
            {"id": "town", "resources": {}},
        ],
        "evaluation_order": ["town", "forest"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "town", "wood") == 0     # never saw the forest's stock
    assert _stock(world, scenario, "forest", "wood") == 5   # kept its own


def test_default_input_sets_reproduce_upstream_pool():
    # No input_sets and no edges tags: identical to the pre-tag behaviour.
    scenario = scenario_from_dict({
        "resources": ["person", "food", "plant"],
        "transforms": [{"name": "harvest", "inputs": {"person": 1, "plant": 1},
                        "outputs": {"person": 1, "food": 1}}],
        "locations": [
            {"id": "greenhouse", "resources": {"plant": 5}, "destinations": ["habitat"]},
            {"id": "habitat", "resources": {"person": 2}},
        ],
        "evaluation_order": ["habitat", "greenhouse"],
    })
    world, _ = run_turn(initial_world(scenario), scenario)
    assert _stock(world, scenario, "habitat", "food") == 2
    assert _stock(world, scenario, "greenhouse", "plant") == 0


# --- actions ----------------------------------------------------------------

def _agitator_scenario():
    # photosynthesis regenerates energy and holds plant, so the world survives long
    # enough for a nudge landing at end of turn 1 to matter in turn 2.
    return scenario_from_dict({
        "resources": ["plant", "energy", "air", "zeal"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1},
             "outputs": {"plant": 1, "air": 1}},
            {"name": "photosynthesis", "inputs": {"plant": 1},
             "outputs": {"plant": 1, "energy": 1}},
            {"name": "agitate", "inputs": {"zeal": 1}, "outputs": {},
             "actions": [{"type": "priority_nudge", "transform": "atmosphere", "delta": 1}]},
        ],
        "locations": [{"id": "green", "resources": {"plant": 40, "energy": 4, "zeal": 2}}],
        "evaluation_order": ["green"],
    })


def test_action_nudges_priority_only_from_next_turn():
    scenario = _agitator_scenario()
    green = scenario.location_index["green"]
    atmosphere = scenario.transform_names.index("atmosphere")

    world = initial_world(scenario)
    world, _ = run_turn(world, scenario)
    # growth is authored first and claimed the whole pool, so the nudge emitted
    # this turn cannot have reordered the pass that emitted it
    assert _stock(world, scenario, "green", "air") == 0
    # ...but it landed, scaled by the 2 firings of agitate
    assert int(world.priority[green, atmosphere]) == 2

    world, _ = run_turn(world, scenario)
    assert scenario.transform_names[world.order(green)[0]] == "atmosphere"
    assert _stock(world, scenario, "green", "air") > 0


def test_action_targeting_unknown_transform_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="unknown target transform"):
        scenario_from_dict({
            "resources": ["zeal"],
            "transforms": [{"name": "agitate", "inputs": {"zeal": 1}, "outputs": {},
                            "actions": [{"type": "priority_nudge",
                                         "transform": "nope", "delta": 1}]}],
            "locations": [{"id": "green", "resources": {"zeal": 1}}],
            "evaluation_order": ["green"],
        })


# --- the nudge economy ------------------------------------------------------

def _nudgeable():
    return scenario_from_dict({
        "resources": ["plant", "energy", "air", "nudge"],
        "transforms": [
            {"name": "growth", "inputs": {"plant": 1, "energy": 1}, "outputs": {"plant": 2}},
            {"name": "atmosphere", "inputs": {"plant": 1, "energy": 1},
             "outputs": {"plant": 1, "air": 1}},
        ],
        "locations": [{"id": "green", "resources": {"plant": 9, "energy": 9, "nudge": 2}}],
        "evaluation_order": ["green"],
    })


def test_nudges_are_paid_for_and_then_gone():
    scenario = _nudgeable()
    world, _ = run_turn(initial_world(scenario), scenario,
                        orders=[SpendNudges("green", {"atmosphere": +2})])
    # both nudges spent; nothing re-emits a nudge, so the stock is empty either way
    assert _stock(world, scenario, "green", "nudge") == 0
    assert scenario.transform_names[world.order(scenario.location_index["green"])[0]] == "atmosphere"


def test_order_costing_more_than_held_is_rejected_whole():
    import pytest
    scenario = _nudgeable()
    world = initial_world(scenario)
    before = world.stock.copy()
    with pytest.raises(ValueError, match="costs 3"):
        run_turn(world, scenario, orders=[SpendNudges("green", {"atmosphere": +2, "growth": -1})])
    assert np.array_equal(world.stock, before)          # caller's world untouched
    assert not world.priority.any()


def test_scenario_without_nudge_resource_cannot_be_nudged():
    import pytest
    scenario = scenario_from_dict({
        "resources": ["plant"],
        "transforms": [{"name": "hold", "inputs": {"plant": 1}, "outputs": {"plant": 1}}],
        "locations": [{"id": "green", "resources": {"plant": 1}}],
        "evaluation_order": ["green"],
    })
    with pytest.raises(ValueError, match="declares no 'nudge' resource"):
        run_turn(initial_world(scenario), scenario, orders=[SpendNudges("green", {"hold": +1})])
