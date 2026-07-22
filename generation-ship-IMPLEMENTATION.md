# Getting There — Implementation Startup Guide

*A build-oriented companion to the GDD, written to hand directly to Claude Code. Read the GDD first for the "why"; this document is the "how do we start."*

---

## 0. Guiding architectural decision

**One agent simulation is the single source of truth.** Ecosystem metrics and political dynamics are *aggregations* of individual agent state and behavior — never separate simulations. Every feature decision should preserve this. If you ever find yourself writing a standalone "ecology model" or "politics model" that holds its own authoritative state, stop: that state must derive from agents.

This gives us three things we care about: internal consistency (the ship-scale nitrogen number is *by construction* the sum of agent metabolism), explicability (zoom from a macro metric to the agents producing it), and horizontal scalability (more agents → more compute, handled in code).

---

## 1. Target architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT (lightweight)                                    │
│  - Map / world view                                      │
│  - Order-issuing UI (assemble a turn = bundle of orders) │
│  - Replay player (real-time, non-interactive, scrubbable)│
│  Godot / web-JS / Unity / MicroStudio — thin.            │
└───────────────┬─────────────────────────────────────────┘
                │  submit Turn (orders)  ▲  receive Replay + new WorldState
                ▼                        │
┌─────────────────────────────────────────────────────────┐
│  BACKEND (Python, server-authoritative)                  │
│  - Turn processor: apply orders → run N deterministic    │
│    ticks → emit Replay + next WorldState                 │
│  - Agent simulation core (source of truth)               │
│  - Aggregation layer (ecosystem + political metrics)     │
│  - Scenario/config loader (ship geometry + origin)       │
│  Serverless (Lambda) now; Spark/streaming if scale needs │
└───────────────┬─────────────────────────────────────────┘
                ▼
        Persistence (WorldState snapshots, turn log, replays)
```

### Interaction model
Turn-based with replay. The client never runs authoritative logic. A turn is a **bundle of high-level directives**, not per-tick input. The backend advances the sim over the turn's in-game interval and returns a **deterministic replay** the client renders and the player can re-watch freely.

### Non-negotiable technical constraint: determinism
Replay only works if a turn produces the *exact same* sequence of events every time it runs. This shapes the core from day one:
- **Seeded RNG**, threaded explicitly through the sim (no global/ambient randomness).
- **Fixed, deterministic tick order** over agents (stable ordering, no dict/set iteration-order dependence, no wall-clock, no floating-point nondeterminism across platforms — prefer integer/fixed-point for anything that must replay identically, or pin the math).
- A turn = `(WorldState_in, Orders, seed) → (WorldState_out, Replay)` as a **pure function**. Same inputs, same outputs, always. This also makes the whole thing trivially testable and trivially parallelizable across matches.

---

## 2. Recommended stack for the MVP

| Layer | Choice | Why |
|---|---|---|
| Sim core | **Python** | Matches your backend strength; fast enough for MVP agent counts; refactor hot paths later. |
| Turn/API | Python serverless (Lambda) behind a thin HTTP/JSON API | You've built lots of these; no game-server infra to invent. |
| Persistence | Simple document/KV store for WorldState + append-only turn log | Snapshots are cheap; turn log enables audit & re-derivation. |
| Client | **Web (JS)** for MVP; Godot as a strong alternative | Web maximizes reach and onboarding; the client is thin either way. |
| Scale-out (later) | Spark / streaming Spark | Only if/when agent counts demand distributed ticking. Don't build this for the MVP. |

**Deliberately deferred:** multiplayer netcode, exotic ship geometries, Coriolis/physics authoring, distributed compute. The MVP proves the core thesis on a single scenario, single player.

---

## 3. Data model sketch (starting point, expect to evolve)

> **v0 note:** the transform system in §3.1–§3.3 below supersedes the agent-centric sketch for M0–M2. A person is a resource token, not an `Agent` object; individual agent records return when the political layer needs them (M4) and slot into the same transform engine.

```python
# --- The world ---
WorldState:
    tick: int
    seed: int
    scenario: ScenarioConfig          # ship geometry + origin culture (loaded, fixed)
    agents: list[Agent]
    resources: ResourceField          # spatial nodes: trees, soil, water, etc.
    structures: list[Structure]        # houses, farms, infra
    stocks: dict[Substance, float]     # DERIVED aggregate reservoirs: O2, CO2, N, H2O...
    # stocks are recomputed from agents+environment, never hand-edited

# --- The unit of truth ---
Agent:
    id: int
    position / home
    metabolism: {o2_rate, co2_rate, food_rate, waste_rate}
    labor: current job (log / farm / build / idle)
    needs: {food, air, ...}            # satisfied or not
    dispositions: {political / cultural leanings}   # small vector; seeds the political layer
    alive: bool

# --- What the player submits ---
Turn:
    world_id
    turn_number
    orders: list[Order]                # broad directives, not per-tick clicks
    # e.g. ZoneFor(area, purpose), SetPolicy(lever, value),
    #      AllocateLabor(...), Build(structure, site)

# --- What comes back ---
Replay:
    frames: list[Frame]                # per-tick deltas the client renders
    summary_metrics: TimeSeries        # ecosystem + political indicators over the interval
    events: list[Event]                # crises, movements, milestones surfaced to player
NextWorldState: WorldState
```

**Aggregation layer** is a set of pure functions `WorldState -> metrics`:
```python
ecosystem_metrics(world)  -> per-substance production/consumption/net-drift
political_state(world)    -> movement strengths, factional balance (from agent dispositions)
```
These read agent state; they never own state.

### 3.1 Scenario configuration format (v0)

One JSON file per scenario, four sections. Authoring uses human-friendly count-dicts; the loader compiles everything to integer vectors (§3.2).

```json
{
  "resources": ["person", "food", "plant", "energy", "air"],
  "transforms": [
    { "name": "survival",
      "inputs":  { "person": 1, "food": 1, "air": 1 },
      "outputs": { "person": 1 } }
  ],
  "locations": [
    { "id": "greenhouse",
      "resources": { "plant": 8, "energy": 4 },
      "destinations": ["habitat"] }
  ],
  "evaluation_order": ["habitat", "greenhouse"]
}
```

- **`resources`** — the global vocabulary. Its order defines the resource enumeration used everywhere else at runtime.
- **`transforms`** — ordered list; **authored position is the default priority**. Convention: sorted descending by total input count (most specific/demanding first, generic mop-ups like photosynthesis last). Priority is a *score* rather than a slot so that nudges (below) superpose commutatively: the stored score is a signed **delta defaulting to 0**, and evaluation order is `sorted(-score, authored index)` — so a **positive delta moves a transform toward the front**, and an all-zero row reproduces the authored order exactly. Catalysts appear in both `inputs` and `outputs`; consumption is absence from `outputs`. No other transform semantics exist.
- **`locations`** — graph nodes. `destinations` are location ids (edges point downstream). Initial stocks live here. **v0 assumes the graph is acyclic**, which is what makes a single evaluation pass well-defined; the general design allows symmetric edge pairs and recovers direction from tags instead (see the extensions below).
- **`evaluation_order`** — explicit total order over location ids for turn processing. Explicit rather than derived so scenario authors control contention priority.

The reference example is `scenarios_data/simple-world.json`.

#### Extensions: tagged edges and action outputs

*Implemented. A scenario using none of these behaves exactly as before, because the default input set is `local` + `nearby` and `nearby` is every edge regardless of tag. `scenarios_data/ring-valley.json` exercises all of it; `simple-world.json` uses none of it.*

```json
{
  "transforms": [
    { "name": "haul_food_cityward",
      "input_sets": ["cityward"],
      "inputs":  { "food": 1, "person": 1 },
      "outputs": { "food": 1, "person": 1 } },

    { "name": "staff_control_terminal",
      "inputs":  { "control_terminal": 1, "person": 1, "energy": 1 },
      "outputs": { "control_terminal": 1, "person": 1, "nudge": 1 } },

    { "name": "back_to_the_land_agitates",
      "inputs":  { "back_to_the_land": 1, "person": 2 },
      "outputs": { "person": 2 },
      "actions": [ { "type": "priority_nudge", "transform": "farming", "delta": 1 } ] }
  ],
  "edges": [
    { "from": "forest", "to": "town", "tags": ["cityward"] },
    { "from": "town", "to": "forest", "tags": ["forestward"] }
  ]
}
```

- **`edges`** — replaces `destinations` as the general form; `"destinations": ["x"]` stays as sugar for one untagged edge, which participates in `nearby`. Edges are directed and a symmetric road is two of them, each carrying the opposite directional tag. Tags are **static structure** with zero per-turn state, so they compile once into per-tag upstream lists exactly like `upstream` today.
- **`input_sets`** — the named pools a transform may draw from, defaulting to `["local", "nearby"]` (current behaviour). `local` is this location's own stock; `nearby` is every location with an edge into this one; any other tag is the upstream set restricted to edges carrying that tag. The available pool is the **union** of the listed sets.
- A **transport transform** is nothing special: it names a directional tag in `input_sets`, and consumes-then-re-emits the goods, moving them one hop per turn. Its worker is a catalyst; the hop is the whole effect.

**The two nudge channels.** Both produce priority deltas; they differ only in who supplies the target.

- **`nudge` is an ordinary resource** — a blank cheque. `staff_control_terminal` above shows the shape: a terminal plus a worker plus power yields one unspecified nudge per turn, with the terminal as a catalyst. Being a resource means it obeys everything else — it appears in `stock`, it is validated by ordinary arithmetic, and **an unspent nudge decays like anything else**, so political capital is use-it-or-lose-it. Nudges are **spent at the location holding them**; they are deliberately *not* shippable, which keeps blank-cheque authority local (see §3.4). In multiplayer the `control_terminal` carries an **owning player**, and the blank nudges it mints inherit that owner — that is who may collapse them into concrete deltas. Single-player needs no such field (one owner everywhere); it is noted here so the resource shape anticipates it.
- **`actions`** — an output channel parallel to `outputs`, for effects that are not storable tokens. `priority_nudge` is the canonical (and for the MVP, likely only) type, carrying a `transform` and a signed `delta`. This is the pre-targeted channel: a cultural resource knows what it wants, so it names the target itself and needs no player. Actions fire under the same `n`-firings arithmetic as resource outputs, which is what gives thresholds for free — the agitation transform above simply does not fire below 2 people.

**The order vocabulary is then one verb:** spend `k` nudges held at a location on signed deltas, e.g. `SpendNudges("town", {"farming": +2, "logging": -1})`. Validation is a resource check (do you hold 3 nudges there?), and the result joins the pre-targeted deltas in a single list.

### 3.2 Runtime representation

Compile the config once at load; the tick loop is pure integer array arithmetic (which also kills a whole class of float-determinism problems):

- **Resource enum:** `resources` list → index `0..R-1`.
- **World stock:** an `L × R` integer matrix `stock[l][r]`. This *is* the mutable world state (plus tick counter and RNG seed).
- **Transforms:** two `T × R` integer matrices, `need` and `emit`.
- **Availability pool** for location `l`: `avail = stock[l] + Σ stock[u]` over upstream locations `u` (those listing `l` as a destination). Never materialized as a merged collection — it's a vector sum.
  - Under tagged edges (§3.1) this generalizes to *per input set*: precompute `upstream_by_tag[tag][l]` at load time, then `avail = Σ stock[u]` over the union of the sets the transform names. Union, not sum — a location reachable by two tags must be counted once. `local` is the singleton `[l]`; `nearby` is today's `upstream[l]`. The pool is therefore per-`(location, transform)` rather than per-location, which is the one real cost of the change.
- **Firing count:** transform `t` fires `n = min over resources of floor(avail[r] / need[t][r])` times at `l` — the number of *simultaneous* firings the pool supports (0 if any need exceeds supply).
- **Firing:** subtract `n * need[t]` from `current` (this turn's depleting stock; see §3.3 for which rows), add `n * emit[t]` to `next_stock[l]`.
- **Aggregation:** ship-wide totals are column sums of `stock`; per-location and per-region metrics are row slices. The M1 ecosystem metrics fall out of this for free.

Dense vectors assume a modest global vocabulary (dozens to low hundreds of resources) — revisit only if that assumption breaks.

### 3.3 Turn evaluation semantics — universal decay (provisional, validate in M0)

The turn is a **double-buffer with universal decay**: inputs come from this turn's
stock, outputs go to a fresh next-turn stock, and *anything not re-emitted is
gone*. Next-turn contents are exactly what the transforms produced.

1. Start `next_stock` at all zeros. Keep a working copy `current` of this turn's stock, which depletes as transforms consume it.
2. Locations are processed in `evaluation_order`; within a location, transforms in priority order — one single pass per turn.
3. **Batch firing.** When transform `t` comes up, compute `n` (§3.2) against the current pool, then consume `n * need` from `current` and add `n * emit` to `next_stock[l]`.
4. **No same-turn reuse or chaining.** Because outputs land in `next_stock`, not in `current`, a token drives at most one transform per turn and no transform can feed another (or itself) this turn. Termination is trivial — autocatalytic recipes cannot run away. The cost is that a person does *one* thing per turn, so work transforms must embed metabolism (consume the worker's `food + air`) or working becomes a free way to survive.
5. **Universal decay ⇒ storage is a transform.** At end of turn `stock = next_stock`; every un-re-emitted token decays. A resource persists only via a transform that re-creates it: `air → air` (free), `food + energy → food` (powered storage), `plant + energy → plant`. Population decline is emergent — an unfed person runs no person-emitting transform and is simply absent from `next_stock`. No explicit death rule.
6. When consuming from the pool, decrement the local row of `current` first, then upstream rows in `locations`-list order. Consuming upstream + producing into `next_stock[l]` locally is how resources migrate down the DAG.

7. **No action ever mutates state the current pass reads.** This is the invariant, and `priority_nudge` satisfies it by construction: a nudge produced during turn N cannot affect turn N, because the turn model already separates producing from acting. A transform firing `n` times emits its actions `n` times, but those deltas are for *next* turn's stack. Nothing self-modifies mid-pass, so the pass stays a pure read of a fixed order and "one pass per turn" holds unchanged.

   **All priority deltas take effect between passes**, in the gap where nothing is running: pre-targeted deltas from `actions` land at the close of the turn that produced them (so the player can see the new order in the replay and respond to it), and player `SpendNudges` deltas land in `apply_orders` at the open of the next turn. Nothing evaluates in between, so the two compose into a single application.

   **Determinism needs no ordering rule**, which is the real payoff of deltas over slot moves. Adding to a score is commutative, so deltas from any number of sources — a player's nudges, three cultural movements, a rival — sum to the same result regardless of arrival order. There is no tiebreak to get wrong and no dict-iteration hazard. Contrast slot-swapping ("move farming up one"), which is *not* commutative and would have needed exactly the kind of total-order rule this avoids.

   Deltas **persist** until pushed back the other way (matching today's `SetTransformPriority` policy semantics). Because the score is only ever a sort key, this saturates rather than running away, at the cost of hysteresis on entrenched positions — see the open questions in §6.

**Open questions carried into M0:** initial-stock tuning for a viable steady state (with decay, every kept resource needs a live storage/production path each turn — issue #1), whether upstream feeders should be evaluated before their consumers (issue #2), and whether a person-based storage recipe (`food + person → food + person`) is worth allowing despite letting that worker dodge starvation (issue #3).

### 3.4 Control, and why there is no arbitration

Priority nudges are *produced* rather than freely issued, but **nothing decides who "controls" a location** — there is no majority check, no threshold, and no ownership rule to implement. Deltas from every source superpose (§3.3 step 7), so a location pushed by a player and two cultural movements at once simply sums them.

This is worth stating plainly because it deletes machinery a permission system would need:

- **No per-location owner**, no tie-breaking, no latch-versus-recheck question.
- **No player dimension on the priority score**, and therefore none on ordinary `stock`, which stays `(L, R)`. Deltas superpose commutatively no matter who authored them, so the arithmetic that produces a location's order needs no owner. This is the property that removes *arbitration*, and it is separate from *attribution* below.
- **Influence at a distance still works**, via the asymmetry: culture travels, authority does not. You ship a cultural resource into a distant settlement and it generates pre-targeted nudges locally. Reach is a logistics problem, exactly like everything else.

**Arbitration is gone; attribution is not.** Superposition answers "how do authored deltas combine" without an owner. It does *not* answer "who may collapse a *blank-cheque* nudge into a concrete delta" — that is a question only in multiplayer, but it has a decided answer: **a blank nudge is owned by the control terminal that emitted it**, and only that terminal's player may spend it. It is not answered by location ownership, because two players can each run a control terminal in the same location, and a per-location owner cannot then say whose blank nudge is whose. The owner therefore rides on the terminal (and is inherited by the blank nudges it mints), not on the location and not on the priority score. In single-player this is moot — one player owns every terminal — which is why v0 carries no player field anywhere; the point is that the score staying player-agnostic (`(L, T)`, above) is forward-compatible with adding terminal ownership later without touching the delta arithmetic.

The player's turn is therefore not a separate code path. `SpendNudges` consumes a resource the world produced and emits deltas into the same list that `actions` feed, so `run_turn(world, orders, seed)` keeps one set of rules to test rather than two.

*Multiplayer note:* the open question is not arbitration but **attribution** — if two players run control terminals in the same location, the submission API needs to know which player may spend which blank nudge. The answer is that the **control terminal carries the owning player**, and the blank nudges it mints inherit it; nudge-spending rights follow from terminal ownership, not from any per-location or per-`stock` owner. Location ownership was considered and rejected: it cannot disambiguate two players' terminals in one location, which is precisely the case attribution exists to handle. Deferred with the rest of multiplayer, but the format above does not preclude it — the terminal is an ordinary resource, and giving that one resource an owner field is the whole change.

---

## 4. Build order (milestones)

Each milestone is independently demoable and de-risks the *next* one. Ship nothing speculative.

### M0 — Deterministic agent core (the whole bet)
- A small map, a handful of resource nodes (trees), N agents with metabolism and one job (logging or farming).
- Deterministic tick loop, seeded RNG, pure `step(state, seed) -> state`.
- **Golden test:** run 1,000 ticks twice from the same seed; assert byte-identical state and event streams. If this ever fails, everything downstream is unsafe. Lock it in CI.
- *Proves:* determinism + the atom of the simulation.

### M1 — Aggregation proves the thesis
- Derive O₂/CO₂ (and one nutrient, e.g. nitrogen) balances purely from agent metabolism + environment.
- Expose a "zoom": given a macro number, list the agents contributing to it.
- *Proves:* the closed-system ecology genuinely emerges from agents — the core design claim.

### M2 — Turn processor + replay
- Define the Order vocabulary. The transform-system answer is one verb — spend nudges on signed priority deltas (§3.1) — which shares an application path with transform-emitted actions (§3.4), so there is one set of rules rather than two.
- Implement `run_turn(world, orders, seed) -> (world', replay)`.
- Serialize a replay as per-tick frames + summary time series.
- *Proves:* the turn/replay loop end-to-end, headless.

### M3 — Thin client
- Map view, order-issuing UI, replay playback with scrub + re-watch, and the zoom-to-cause view.
- Talk to the backend over JSON.
- *Proves:* the actual play experience of "issue a rich turn → watch it unfold → learn → issue the next."

### M4 — Scope progression + first politics
- Metric-gated unlocks: hit visible targets → responsibility expands to more settlements.
- Introduce agent dispositions and one cultural movement (e.g. back-to-the-land) that shifts behavior and ripples into the ecosystem.
- Introduce the first policy levers (control by policy, not placement) at the expanded scope.
- *Proves:* the "concerns shift as scope grows" spine and politics-drives-ecology dynamic.

### M5 — The closed-system reveal + failure/success
- Enforce ship boundaries: finite stocks, resources that were "free" now bite once you own the loop.
- Catastrophic-failure threshold (population collapse → game over) and tiered victory on arrival (including "limped in with survivors").
- Predictable journey event (e.g. deceleration → reliability stress) wired into scenario config.
- *Proves:* the full single-player arc on one scenario. **This is the MVP.**

### Post-MVP (design already anticipates, don't build yet)
- Multiplayer: the pure-function turn model already makes matches isolatable; add player identity (AI vs. dynasty), shared-world turns, and the "destabilize the ship → everyone loses" constraint.
- Additional ship geometries + origin cultures as authored scenarios.
- Spark/streaming scale-out if agent counts demand it.

---

## 5. Suggested repository layout

```
generation-ship/
├── sim/                      # PURE, deterministic, no I/O, no framework
│   ├── core/                 # Agent, WorldState, step()
│   ├── aggregation/          # ecosystem_metrics(), political_state()
│   ├── orders/               # Order types + application to world
│   ├── turn.py               # run_turn(world, orders, seed) -> (world', replay)
│   └── scenarios/            # ship geometry + origin config loaders (data-driven)
├── backend/                  # thin serverless handlers over sim/
│   ├── api/                  # submit_turn, get_state, get_replay
│   └── persistence/          # WorldState snapshots, turn log, replays
├── client/                   # thin: map, order UI, replay player
├── scenarios_data/           # authored scenario files (JSON/YAML)
└── tests/
    ├── determinism/          # golden replay tests (CI-critical)
    └── ...
```

Keep `sim/` ruthlessly pure: no network, no clock, no framework imports, no ambient randomness. It's a library that turns `(state, orders, seed)` into `(state, replay)`. Everything else is plumbing around that.

---

## 6. Open questions with implementation consequences

Design-side questions live in GDD §9. These are the ones that change what gets built, and they should be answered before the milestone that depends on them.

- **The Order vocabulary itself** (blocks M2). §3.1 now fixes the *shape* — spend nudges on signed deltas — but not the contents at larger scope. Whether a ship-scale turn is "many nudges at many locations" or "nudges at aggregate locations" is the open half, and it is the same question as GDD §9's verb-changes-with-scope tension.
- ~~**Priority as a score, confirmed against a real scenario**~~ — *done.* `test_priority_deltas_superpose` asserts an identical stack under both arrival orders, and `test_action_nudges_priority_only_from_next_turn` pins that a nudge emitted during a pass cannot reorder the pass that emitted it.
- **Nudge economics** (blocks M4). What a control terminal costs, and how many nudges per turn it yields. This is the main balance dial for the whole political layer — cheap terminals make political capital trivial, dear ones ossify the map — and there is currently no number attached to it.
- **Delta clamping** (blocks nothing yet). Deltas persist and saturate as a sort key, but entrenched positions gain hysteresis proportional to how long they were held. Bounding the score range is the hedge if that proves too stiff at the table.
- **Nudge attribution in multiplayer** (blocks multiplayer, post-MVP) — *resolved in design.* Not arbitration (that is gone), but which player may collapse which blank nudge when two run terminals in one location. **The control terminal carries the owning player and the blank nudges inherit it.** Location ownership was considered and rejected: it cannot disambiguate two players' terminals in the same location. Implementation is deferred with the rest of multiplayer, but the decision is made; see §3.4.
- ~~**Per-`(location, transform)` pools**~~ — *done.* Resolved by precomputing `consume_rows[t][l]` at load, so the tick loop still indexes rather than recomputing set unions. Cost is memory proportional to `T x L`, not inner-loop work.
- **Save/persistence model and multiplayer turn-resolution timing.** Deferred, but the append-only turn log in §2 is the assumed substrate, and the pure-function turn model is what makes it re-derivable.
- **A non-goals section.** Explicitly out for the MVP: ship construction, a physics solver, multiplayer netcode, exotic geometries. Written down so the build does not drift into them.

---

## 7. First session with Claude Code — concrete kickoff

Reasonable order of operations to open the project:

1. Scaffold the repo layout above; set up the test harness and CI.
2. Implement M0's `Agent`, `WorldState`, and `step()`. Nothing else.
3. Write the golden determinism test *before* adding a second job type. Make it pass, wire it into CI, and treat a red bar here as a stop-the-line event.
4. Add M1 aggregation and a tiny script that prints per-substance balances over a run — first proof the ecology emerges.
5. Only then define the initial Order vocabulary and `run_turn`.

Everything in this document is a starting hypothesis, not a spec to follow blindly — expect the data model and order vocabulary to change once M1 tells you what the aggregate behavior actually looks like.
