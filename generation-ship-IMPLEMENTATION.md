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
- Define the Order vocabulary (start tiny: zone an area, build a structure, allocate labor).
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

## 6. First session with Claude Code — concrete kickoff

Reasonable order of operations to open the project:

1. Scaffold the repo layout above; set up the test harness and CI.
2. Implement M0's `Agent`, `WorldState`, and `step()`. Nothing else.
3. Write the golden determinism test *before* adding a second job type. Make it pass, wire it into CI, and treat a red bar here as a stop-the-line event.
4. Add M1 aggregation and a tiny script that prints per-substance balances over a run — first proof the ecology emerges.
5. Only then define the initial Order vocabulary and `run_turn`.

Everything in this document is a starting hypothesis, not a spec to follow blindly — expect the data model and order vocabulary to change once M1 tells you what the aggregate behavior actually looks like.
