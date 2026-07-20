# Getting There — Game Design Document

*Working title. A closed-system city builder set aboard a generation starship.*

---

## 1. Vision

A city-builder that starts as a cozy, small-scale town game and gradually reveals itself to be a puzzle of closed-system survival. The player begins managing a handful of houses on what looks like ordinary land. As their scope of responsibility grows — through a political game rather than through conquering empty territory — the horizon literally and figuratively curves upward, and they come to understand they are managing a finite, sealed world hurtling between stars.

The design exists to fix the failure mode of traditional city builders (e.g. *Kingdoms and Castles*), where the only definition of progress is unbounded growth, the endgame is undefined, and constraints are either absent or feel arbitrary. The generation ship supplies all three missing ingredients for free:

- **Built-in limitation.** A sealed hull is a hard boundary. There is no unexplored frontier to expand into; everything that exists, already exists.
- **Meaningful constraints.** Ecological balance is survival. Unbounded growth is not a victory condition — it's a disaster.
- **A real arc.** The journey has a beginning, middle, and end. The ship departs, travels, and arrives. The game ends when it arrives.

### Design pillars

1. **One system, three scales.** The town game, the political game, and the ecosystem game are not three simulations bolted together — they are the same simulation observed and manipulated at three levels of abstraction.
2. **Scope, not sprawl.** You grow by taking on responsibility for more of an existing world, not by colonizing empty land.
3. **Struggle is not punished; collapse is.** The game is hard and things go wrong constantly, but failure is rare, avoidable, and never sudden.
4. **The ship is a given.** Ship configuration is authored level design, not something the player builds. This differentiates the game from build-your-own-vessel titles and enables the reveal.

### Literary touchstones

- **Aurora** (Kim Stanley Robinson) — closed-system ecological cascades, the politics of scarcity, and the mechanical unreliability that sets in as the ship decelerates and loses its rotational reference frame.
- **The Book of the Long Sun** (Gene Wolfe) — the slow-dawning reveal that the "world" is the interior of a rotating starship; the design translates this reveal from narrative surprise into mechanical discovery.

---

## 2. The Core Loop and the Reveal

### The scope-progression spine

The player does not start knowing they are on a ship — or rather, replayability means they *can* know, but it doesn't matter, because the reveal is mechanical, not a cutscene.

- **Start small.** The player manages a small settlement: cutting trees, building houses, laying roads. Familiar city-builder verbs. At this scale, systemwide concerns like oxygen availability exist in the model but are effectively solved for the player — abundant, invisible, not their problem.
- **Earn scope.** Success against a visible set of metrics unlocks responsibility for a larger area — more settlements, more of the ship. Advancement runs through a **political game**: you parlay competent management into greater authority.
- **Concerns shift, not just multiply.** Crucially, expanding scope does not mean "more of the same management." As you zoom out, *what you care about changes*. At the settlement level you count trees. At the ship level you stop caring where any given settlement gets its wood — you treat the whole civilization as a mechanism that converts carbon to oxygen (and so on), and you manage flow rates and ratios.
- **The system reveals itself as closed.** Resources that were free at small scale become precious once you're responsible for the whole loop. The open-system illusion of the early game gives way to the unmistakable reality of a sealed, finite world. That transition *is* the reveal.
- **The endgame.** The goal is to become responsible for the entire ship and guide it to its destination. Arrival ends the game.

### Political shortcut

The political game is also an express lane. A player who wants to skip the tree-cutting layer and go straight to ecosystem balance can play politics well and shortcut upward. This lets different players play the game they actually want — cozy town management, systems puzzle, or political maneuvering — without forcing everyone through the same funnel.

---

## 3. The Three Interlocking Systems

These are three lenses on one underlying agent simulation (see §6).

### 3.1 Town / settlement management
The ground-level city builder. Individual agents live, eat, breathe, farm, log, and build. The player places buildings, roads, and infrastructure. This is the *Kingdoms and Castles* register: tangible, spatial, hands-on. Even in the late game, settlements keep running themselves as live simulation — the player can always zoom in and watch.

### 3.2 Political / cultural management
The mid-scale layer. The player operates policy levers rather than placing individual buildings — tax rates, incentives, restrictions, allocations. Cultural and ideological movements arise and spread (e.g. a "back-to-the-land" movement), each reshaping how settlements behave and therefore how resources flow. Politics is both the engine of scope progression and a primary source of in-game dynamics.

### 3.3 Ecosystem management
The ship scale. Closed-loop biogeochemical cycles — carbon, oxygen, nitrogen, water, organic matter. The player treats the population as the biological machinery driving these loops and manages for *dynamic* stability: never static, always drifting, always requiring correction. Reference point: interactive global-climate policy simulators, where you pull an economic or policy lever here and watch consequences emerge somewhere unexpected — but here, on a sealed system where every output is also someone's input.

### The through-line
Concerns migrate outward as scope grows. The genius is that the levers change too: spatial placement → policy → systemic flow management. Same world, three grammars of control.

---

## 4. Dynamics, Events, and Difficulty

Late-game must not decay into watching two numbers converge. It stays alive because the system is never truly at rest, and because pressure arrives from three sources:

1. **Cultural / political shifts (preferred).** The signature obstacle. Ideological or cultural change alters how people live, which ripples into the ecosystem. A rural-migration movement might ease some pressures while breaking the efficient nutrient cycling that depended on dense settlement. These are more differentiating and more thematically apt than random disasters, and they tie the three systems together — narrative and cultural change felt as mechanical ecosystem consequence.
2. **Predictable journey events.** Baked into level design. The ship decelerates at a known point; mechanical reliability degrades; the rotational reference frame (and its Coriolis effects) weakens. Different propulsion profiles (hard initial burn vs. solar sail vs. long coast) imply different predictable stress schedules.
3. **Unpredictable shocks.** Classic catastrophe events — an asteroid strike, a disease outbreak. Present but de-emphasized in favor of the culturally-driven dynamics above.

### Turn granularity as a difficulty knob
The in-game duration of a turn (day / week / month scale) is tuned so that emerging problems are *visible and resolvable within a turn or two* — never a case where everything looks fine, you submit, and the replay is the apocalypse. This also keeps replays a comfortable length. Journey length (a ~100-year hop to the nearest star vs. a 1,000-year voyage) is a scenario-design variable that changes the whole tempo.

---

## 5. Ship Configurations & Scenarios

The physical configuration of the ship is **authored level design**, not procedurally solved at runtime. For each configuration, the winning patterns — how light, day/night, gravity, Coriolis, and agriculture behave — are worked out by hand once, and then reused.

### Configuration axis
- **Simple rotating ring / torus** — stable artificial gravity, predictable day/night, minimal exotic effects. The tutorial and MVP configuration.
- **Small clustered modules** — fragmented farmable space; agriculture becomes a placement puzzle.
- **Tumbling / unstable-gravity designs** — irregular light and pseudo-gravity zones.
- **Counter-rotating / other exotic geometries** — later expansion content.

Physics feeds directly into light direction, day/night cycles, and agricultural viability. Coriolis and rotation effects are real design inputs — acknowledged as *hard*, hence the hand-authored, per-configuration approach rather than a live physics solver.

### Origin / culture axis
The society that launched the ship sets the starting conditions:
- **Communal** — consensus-building, resource-sharing tensions; a specific set of political levers.
- **Corporate** — inequality and efficiency trade-offs; more urban, technologically focused; a "Wall Street in space" register.
- **Agrarian utopia** — dispersed, low-density, agriculture-first layout and its attendant fragilities.

Origin is not flavor — it determines initial layout, the political levers available, and which crises emerge naturally. Part of the deeper game may be *shifting* a ship's system from one mode toward another when circumstances demand it.

### MVP scenario
One configuration (simple rotating ring, normal cycles), one or two origins, a shorter journey. Exotic configurations and additional origins ship as expansion content — a natural demo-to-full-game structure.

---

## 6. Architecture (High Level)

### Agent simulation as the single source of truth
The design commits to a **bottom-up** model. Individual agents are simulated — their metabolism (food in, O₂ in, CO₂/waste out), their labor, and a small set of social/political dispositions. **Ecosystem metrics and political dynamics are aggregations of agent behavior, not separate simulations.**

Rationale:
- **Internal consistency for free.** One model means the ship-scale nitrogen cycle is literally the sum of what agents do — no risk of a separate ecology sim and a separate politics sim drifting out of agreement.
- **Explicability.** The player can zoom from a ship-scale metric down to the individual agents producing it, and see exactly where a systemic effect comes from.
- **Scales in the cloud.** More agents / bigger world → more serverless instances or a larger distributed job. Complexity is handled in code, not by assuming a single laptop.

### Turn-based with replay
The chosen interaction model, which resolves latency, scalability, multiplayer fairness, and player attention in one stroke:

- The player assembles a **rich bundle of orders / directives** — broad strategic intent, not click-by-click micromanagement — and submits it as a **turn**.
- The backend processes the turn (running the agent sim forward over the turn's in-game interval) and returns a **replay**.
- The replay is **real-time but non-interactive**: the player watches the interval unfold and can **re-watch it as many times as they like**, following any thread they choose (trail the fish vendor to learn the fish economy; watch a logger; watch a political indicator move). This deliberately **separates acting from observing** — a pain point in real-time builders where you can't just watch because you're busy issuing orders.
- **Turn cadence is configurable** (per second, per hour, per day). A daily cadence yields a board-game feel: rich, considered turns with no advantage to obsessive presence — the player chooses their level of engagement.

### Deployment shape
- **Backend:** Python modules doing the core simulation, deployed serverless (e.g. Lambda), with a distributed engine (e.g. Spark, possibly streaming Spark) available if orchestration at scale demands it.
- **Client:** Lightweight — a map view, an order-issuing interface, and a replay player. Godot, Unity, MicroStudio, or a plain web/JavaScript client all fit; the heavy logic lives server-side. A web client maximizes reach and ease of onboarding.

*Note: this is a server-authoritative, turn-based online game rather than a self-contained downloadable — worth scouting comparable commercial titles (server-side, turn/replay-based) during prototyping.*

---

## 7. Failure & Success

- **Catastrophic failure is real but rare.** If the world's systems crash past a threshold — e.g. a total decompression event kills the population — the game ends. You lost. (Exotic "the AI persists as robots" continuations are out of scope for the MVP.)
- **Struggle is expected and not punished.** Ecosystem cascades, political crises, civil wars — these are the substance of the game, problems to be faced and resolved, not death sentences.
- **Failure is never sudden.** Turn granularity guarantees the player sees trouble coming and has agency to respond. No "everything's fine → submit → apocalypse."
- **Limping in is winning.** Arriving with 200 survivors in the shattered remains of the ship is a *victory* — a lesser tier than arriving with a thriving 10,000, but a win. Expect **tiered victory conditions** rather than a single bar.

The player always has agency. Even mid-collapse, they are solving problems, not watching a defeat cutscene.

---

## 8. Multiplayer

Multiplayer is designed in **from the start**, not retrofitted — the cloud backend makes it nearly free, and it's what makes the political layer genuinely meaningful. In single-player, "politics" is negotiation with AI; with real players, it becomes real tension over shared, finite resources.

### The cooperation/competition tension
The closed system is the enforcement mechanism. Players can compete — even raid or conquer a neighbor's settlement, which is fun in the early game — but if aggression destabilizes the ship's ecology and triggers a cascade, **everyone loses**. Competition is bounded by shared survival. This is the multiplayer expression of "struggle is fine, collapse is not."

### Players at different scales
Because the three systems operate at different scales, players can interact through different registers — one focused on local settlement management, another playing the political layer, another watching the ecosystem — and their actions collide in interesting, asymmetric ways. A hundred villages could each be a player managing the same low-level game, with the political layer emerging as real negotiation *between actual people*.

### Player identity (open design question)
- **AI intelligence** — cleanly sidesteps the "one human can't live 600 years" problem; the player is a persistent intelligence managing continuity across centuries. *Leaning this way.*
- **Family dynasty** (Crusader Kings register) — play a lineage across generations; more narrative scaffolding required.

### Scenarios scale on purpose
The same core systems support different modes:
- **MVP:** single-player, ~100-year journey — a place to learn the systems.
- **Full multiplayer:** e.g. a 500-year voyage with ~10 players managing different regions, where the political layer *is* the game.

This is the key economy of the design: **one system that scales from solo to collaborative** — not two games. Single-player must stand on its own, but everything is built assuming multiple players acting across the three scales.

---

## 9. Open Questions to Resolve in Prototyping

- Where exactly does the perspective/control shift from spatial placement to policy levers, and is it gradual or stepped?
- What are the specific unlock metrics gating each expansion of scope?
- How lightweight can the agent model be while still producing believable aggregate ecology *and* politics?
- What is the concrete order/directive vocabulary at each scale?
- What do comparable server-authoritative, turn-and-replay commercial games teach us about shipping and monetization?
- How is determinism guaranteed so a submitted turn replays identically every time (see implementation guide)?
