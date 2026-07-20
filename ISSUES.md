# Open Issues

Lightweight issue log (GitHub API was unreachable when these were filed — promote
to GitHub issues when convenient). Newest concerns first.

---

## 1. `simple-world` collapses around tick 5 (unbalanced scenario)

**Type:** balance / tuning
**Where:** `scenarios_data/simple-world.json`

Running the default scenario forward, the population dies at tick 5. The failure
is a decay cascade, not an engine bug:

- By ~tick 3 the habitat has no spare **energy**, so `food_storage`
  (`food + energy → food`) can't fire → the food stockpile decays to zero →
  by tick 4 nobody can eat → both people starve at tick 5.
- Compounding it: the **greenhouse fully drains into the habitat on turn 1**
  (see issue #2), so it never builds a sustaining energy/plant supply.

Universal decay makes the world unforgiving — every kept resource needs a live
production/storage path *every turn*, and a one-turn energy dip cascades into
starvation two turns later.

**Fix direction:** give the greenhouse enough throughput to survive the turn-1
drain and feed the habitat a reliable energy stream so `food_storage` never
fails; or rethink initial stocks. Needs iteration in the notebook.

---

## 2. Pure-feeder locations drain in one turn (eval-order interaction)

**Type:** design / mechanics question
**Where:** `sim/engine.py` (evaluation order), `scenarios_data/simple-world.json`

With `evaluation_order: ["habitat", "greenhouse"]`, the downstream habitat is
processed first and consumes the greenhouse's plant/energy from the shared
upstream pool. When the greenhouse's own turn comes, its stock is gone, so it
runs none of its own transforms and emits nothing — it decays to empty every
turn, acting purely as a one-turn buffer.

**Decision needed:** is that intended (upstream nodes are just pass-through
buffers), or should upstream locations be evaluated *before* their downstream
consumers so a feeder can run its own production first? This is a real semantic
lever and interacts with issue #1.

---

## 3. Decide the `food_storage` cost model

**Type:** design decision
**Where:** `scenarios_data/simple-world.json`, IMPL §3.3 open questions

`food_storage` is currently `food + energy → food` (a deviation from the original
`food + person → food + person` intent). The person-based version creates a
free-survival loophole under universal decay: a person "assigned to food storage"
is consumed and re-emitted, so they persist without ever running survival —
i.e. workers never starve, which undercuts the emergent-death design.

**Decision needed:** keep energy-based storage (current), or accept person-based
storage and the "productive people don't starve" rule that comes with it. If the
latter, either embed metabolism (`food + air`) into every person transform or
accept the loophole deliberately.
