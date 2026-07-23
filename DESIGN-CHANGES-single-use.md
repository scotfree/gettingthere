# Design Changes — Single-Use Rows, Fallback Survival, Cultural Orders

*Supersedes parts of IMPL §3.2–3.3. Written from the design session that started with
"unintentional longevity." Status: agreed direction, not yet implemented.*

---

## 0. The problem that started it

A transform re-emits its worker so the worker isn't destroyed — `farming: person + food
+ air + plant + energy → person + 2 food`. But under universal decay, **being in any
firing transform's output set is exactly what persistence means.** The engine writes
`next_stock[loc] += n * emit_t` unconditionally. So a person involved in *any* transform
that names them as an output survives to next turn, whether or not they were fed.

Work therefore granted free longevity, which undercuts the emergent-death design.

---

## 1. Core change: rows are single-use

**Today:** a transform fires `n = min(pool[mask] // need[mask])` times — greedy to
exhaustion. Priority means precedence, and precedence with greedy-max means the winner
takes everything it can reach.

**Change:** a priority-list entry ("row") fires **at most once** per turn. `n ∈ {0, 1}`.

Consequences:

- A token spends its whole turn on exactly one transform. Longevity is no longer free:
  you persist only if some row deliberately consumed and re-emitted you, and that cost
  the token its turn.
- Quantity is expressed by **row count**. Three `farming` rows means at most three
  farmers. The priority list is no longer a permutation of transforms — it is a
  *sequence with repeats*.
- Positional capping falls out for free: rows above `mining` claim people first, rows
  below get what's left. No cap field, no new authored number.
- Interleaving becomes expressive: `farm, mine, farm, mine` holds a ~50/50 split that
  **scales with population**, which an absolute cap cannot express.

### Code impact

`sim/engine.py` — `process_location`:

```python
n = int(np.min(pool[mask] // need_t[mask]))   # today
n = 1 if np.all(pool[mask] >= need_t[mask]) else 0   # after
```

`sim/world.py` — `WorldState.transform_order` keeps its type (`list[list[int]]`) but
loses its invariant: it is no longer a permutation of `range(T)`. Repeats are legal and
meaningful; omissions are legal and mean "this transform does not run here."

`FireEvent.count` is now always 1. Either drop the field or keep it and have the replay
serializer collapse adjacent identical events for readability.

Determinism is unaffected — still integer arithmetic in a fixed order.

---

## 2. Survival is the fallback, not a universal tax

With single-use, a person cannot both work and separately "run survival." So:

- **Work transforms embed metabolism.** `farming` already consumes the worker's
  `food + air`. This is now mandatory, not conventional.
- **`survival` (`person + food + air → person`) is the bottom-of-list fallback** — what
  a token runs when no better row claims it. Idle people still eat, drawing on the same
  food pool as workers. If "idle people survive on less" is ever wanted, that is just a
  cheaper fallback transform, no new machinery.
- Without the fallback, "no job available" would mean death. The fallback is therefore
  **load-bearing floor**, not a patch — scenario authors must include one.

### New loader invariant (proposed)

> Any transform that emits `person` must consume that person's metabolic inputs
> (`food`, `air`) in the same recipe.

This is statically checkable in `scenario_from_dict` and closes the loophole class
permanently. It also **resolves ISSUES.md #3**: person-based storage becomes legal, but
only in its honest form — `food:2, person:1, air:1 → food:1, person:1` (stores one food
net of the worker eating one). The free-survival version simply fails validation.

---

## 3. Rejected: size fields and batch flags

Considered and dropped:

- **`size` per row (`[1, ∞]`)** — N contiguous identical single-use rows and one row of
  size N produce identical results, because the pool depletes the same way and no state
  carries between fires. So size is a **lossless encoding, not a semantic concept.** It
  belongs in the loader / serializer / wire format if profiling ever demands it, and
  nowhere in the model.
- **`batch` flag per transform** — same reasoning. A greedy `air_storage` row is just a
  compressed run of single-use ones.
- **Expiry rules replacing storage transforms** — rejected because it breaks the
  single-mechanism property (decay is currently the *absence* of a mechanism), and
  because it flattens the interesting storage cases. `food + energy → food` couples
  refrigeration to power, which is exactly the fragility the game is about; a flat
  "food lasts 3 turns" severs that.

**Accepted cost:** one row per unit of persisting stock. 400 air needs 400
`air_storage` rows. This is ungainly, and it is a use case we would rather design away
from than optimise for. Revisit only if it actually shows up.

**Known residual (defer, don't forget):** rows enter one at a time via orders, but stock
can grow multiplicatively. So persistent stock is structurally capped by how fast rows
can be inserted. Invisible at MVP scale; becomes real when population growth is
something you manage. The likely future answer is a proportional order form ("insert
rows to match population") rather than ±1 nudges — revisit at M4.

---

## 4. Order vocabulary

The list is now edited structurally, not just permuted.

| Order | Status | Meaning |
|---|---|---|
| `InsertTransformRow(location, transform)` | **new** | Prepend one row at top priority. |
| `RemoveTransformRow(location, transform)` | **new** | Remove the topmost matching row. |
| `SetTransformPriority(location, order)` | **needs rework** | See below. |

**Why insert-at-top specifically:** it is *context-free*. The emitter needs to know
nothing about the current list — no matching, no lookup, no merge logic. That is what
makes it safe to fire from a cultural controller that knows nothing about the location
it affects, and it means two competing movements both prepending is well-defined.

Insert-at-top plus remove-at-top makes the list a **stack**: the most recent structural
change is the most easily undone, and older rows sediment downward into institutional
inertia. That is thematically right and costs nothing.

**Known limit:** remove-at-top cannot reach sediment, so long-run drift still grows the
list. Options when it matters: `RemoveLowestRow`, or a per-location list capacity where
insert-at-top evicts the bottom row. Deferred.

### `SetTransformPriority` must change

Current implementation assumes uniqueness — it errors on `transform '{name}' listed
twice` and reconstructs `front + rest` from `default_transform_order`. Both assumptions
break once rows repeat. Either redefine it to operate on all rows of a named transform
as a block, or retire it in favour of insert/remove plus a positional move. **Decide
before implementing.**

---

## 5. Cultural impacts are sources of orders

A cultural movement does not get its own mechanism. It **emits the same orders a player
emits**, from something other than a player.

### New turn phase

```
1. (NEW) read current stock → cultural controllers emit orders
2. apply_orders(player orders + cultural orders)   ← unchanged vocabulary
3. tick: read stock + priority → write next_stock  ← unchanged, still priority-read-only
```

This crosses a real line, worth naming: the priority list goes from **exogenous**
(written only by orders arriving from outside `run_turn`) to **endogenous** (turn N+1's
priority depends on turn N's stock). That closes a feedback loop, and feedback loops are
where "no everything's-fine-then-apocalypse" guarantees go to die.

Confining the loop to phase 1 keeps it legible: the tick itself still never writes
priority, and every culture-emitted order can be logged into the `Replay` as an event
("`back_to_land` at stock 7 emitted `InsertTransformRow(habitat, farming)`"). "Why did
priority change" stays answerable — just from the replay now, not the external order log.

### Bounding

Two bounds, both already in-thesis:

1. **Nudges are small.** Culture drifts; one row per turn, not arbitrary restructuring.
2. **A movement is a resource under universal decay.** `back_to_land` must be
   re-emitted by some transform each turn or it fades. Starve its input and the nudges
   stop. Influence is self-limiting by the same rule that governs food and people.

### Back-to-the-land, concretely

Movement stock present → emit `InsertTransformRow(location, farming)`. Farming rows
accumulate at top; more of the population farms; the movement persists only while fed.
When it decays, the rows it inserted remain — institutions outliving the movement that
created them, which is the right texture.

---

## 6. Deferred

- **Shuffle as a cultural effect.** Converts a priority list into a proportional
  sampler — row census becomes the ratio, scaling with population for free. Needs the
  seed (already threaded through `run_turn`) keyed off `(seed, tick, location)`, never
  anything ambient. Note it destroys run-contiguity, so it is in quiet tension with any
  future run-length compression of the row list.
- **List capacity / eviction.** See §4.
- **Age stages** (`child → young → middle → elder`). Orthogonal to everything here; the
  longevity fix does not depend on it. Revisit when demographic management is a layer.
- **Proportional order forms.** See §3 residual.

---

## 7. Impact on existing issues

| Issue | Status |
|---|---|
| #1 `simple-world` collapses ~tick 5 | **Rebalance required regardless.** Every persisting resource now needs a row, so initial stocks *and* initial row lists both need tuning. |
| #2 Pure-feeder locations drain in one turn | **Unaffected, still open.** Eval-order semantics are orthogonal to single-use. |
| #3 `food_storage` cost model | **Resolved** by the §2 metabolic invariant. |
| (new) Trivial storage rows clutter the UI | **File it.** `air_storage`-style self-loops should be hideable/aggregatable in the UI. This was the original observation that opened the session and it survives all of the above. |

---

## 8. Open question — scenario authoring format

Not a mechanics question, but it has to be settled before implementation, and it will
settle itself badly if ignored.

Today: `default_transform_order = list(range(T))`, and every location gets one copy
(`initial_world`). With repeatable rows, a scenario must express *how many* of each
transform each location starts with.

Proposal to evaluate: keep the global `transforms` list as the vocabulary, and give each
location an optional `transform_rows` array (transform names, in priority order,
repeats allowed) that defaults to one row per transform in global order. That keeps
`simple-world.json` nearly unchanged while making row multiplicity authorable where it
matters.

---

## 9. Implementation order

1. Single-use firing in `process_location` (§1) — smallest change, largest semantic shift.
2. Metabolic invariant in `scenario_from_dict` (§2) + fallback `survival` in the scenario.
3. Rework/retire `SetTransformPriority`; add insert/remove row orders (§4).
4. Rebalance `simple-world.json` — initial stocks *and* row lists (§7 / issue #1).
5. Cultural controller phase in `run_turn`, with emitted orders logged to `Replay` (§5).

Determinism tests should stay green throughout; if they go red at any step, stop.
