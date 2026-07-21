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

Mechanically this is **not a separate system**: a cultural movement is a resource produced by a chain and consumed when it takes effect, and a policy lever is a *nudge* — a small priority delta produced by a control terminal you built. Spread, attenuation, and resistance all fall out of ordinary production and logistics. See §6, *Control, actions, and culture*.

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

### The universal transform system (v0 substrate)

The minimal mechanical core beneath everything is a single mechanism: **resources** and **transforms**, evaluated over a graph of **locations**.

- **Resources** are named, counted tokens — `person`, `food`, `plant`, `energy`, `air`. Everything in the world is a resource count at some location: people, political **control**, and **cultural movements** are all ordinary resources, produced by their own chains and subject to the same decay and logistics as grain. There is no second kind of thing.
- **Transforms** are the only rule type: an input multiset and an output multiset, e.g. `farming: person + food + air + plant + energy → person + 2 food`. There are no special-case mechanics layered on top:
  - *Catalysts* are just resources present in both input and output (the person in farming is required and re-emitted, so they persist).
  - *Energy costs* are just energy in the input list.
  - *Survival itself* is a transform — `person + food + air → person` — so population decline under food or air shortage is emergent, not a scripted rule.
- **Transforms can output actions, not just resources.** An action changes game state without being a storable token — the canonical one being a **priority nudge** (shift a transform up or down a location's stack by a delta). Because an action is just another output, it inherits the input conditions of its transform, so thresholds fall out for free: *"only fires if ≥ N population and ≥ N of some cultural resource is present."* Actions are deterministic in the MVP. This is the slot where cultural effects, counter-influence operatives, and policy levers live — no new mechanic required.
- **Universal decay is the master rule.** Each turn a location's next contents are *exactly* what its transforms produce; anything not re-emitted is gone. There are no passive stockpiles — a resource persists only because some transform re-creates it. **Storage is therefore itself a transform:** `air → air` is free-standing atmosphere; `food + energy → food` is refrigeration that costs power; a future "granary" building is just a source of a cheaper storage transform. This is what makes death fall out for free — a person with no food or air runs no survival transform, is not re-emitted, and is simply absent next turn — and it makes conservation a property you *engineer* with transforms rather than get by default.
- **One activity per token per turn.** Because outputs land in a fresh next-turn buffer, a token drives at most one transform per turn: a person farms *or* idles-and-survives, not both. Work transforms embed metabolism (they consume the worker's food and air) so that being productive is not a way to dodge starvation. Labor is a real throughput constraint — jobs compete for the finite population.
- **Locations** are nodes in a graph of **tagged edges**, and a transform's available pool is the union of one or more **named input sets** rather than a fixed neighbourhood. Two tags always exist: `local` (resources physically here) and `nearby` (resources in adjacent upstream locations — the symmetric, osmotic default). Any other tag `<TAG>` means "resources upstream along edges carrying that tag." Tags are static structure assigned at map-build time and carry zero per-turn state. See *Tagged edges and transport* below.
- **Priority is specificity, and priority is a score.** Transforms are evaluated in priority order, by convention sorted in descending input-size order: the most demanding recipes claim the pool first, storage and generic recipes mop up what's left. Authored position sets the default score and breaks ties. Nudging a location's stack is the entire MVP order vocabulary, and it is genuinely expressive because transforms contend for shared inputs — but the ability to nudge is *produced*, not assumed. See *Control, actions, and culture* below.

### Tagged edges and transport

Shipping is not a separate mechanic. **Transport is a transform whose input set is a directional tag:** "pull wood from `cityward` neighbours, output it here" moves wood one hop toward the city per turn, and downstream locations running the same transform carry it onward. Logistics is thus made of the same parts as everything else.

**Why tags are required rather than optional.** Most roads are symmetric edge pairs, so the raw location graph is full of 2-cycles and topology alone carries no direction — a transport transform pulling on plain `nearby` would slosh a resource back and forth forever. Each tag defines an **acyclic direction field** over the otherwise-cyclic graph: filter the edges down to `cityward` and you get a clean DAG (forest → town1 → town2 → city) with no back-edge to pull along, and therefore no oscillation. Counter-flow works because the reverse halves of the same roads carry the opposite tag (`forestward`), letting one physical corridor move different goods in opposite directions with no per-turn state at all.

The honest cost: **a tag encodes flow toward one reference**, so each destination that stuff needs to flow toward wants its own tag or its own gradient field. Expect tags to proliferate by purpose. They stay fully static, which is what keeps them cheap.

Tags can be hand-painted or generated: compute a distance-to-target field per node at build time, then tag each directed edge as toward-target where its head is closer than its tail. Both approaches populate the same edge-tag structure. Location and resource tags are worth adding at the same time, with one distinction kept clear — **edge tags do directional work** (which way does flow go) while location and resource tags do **classification work** (what kind of thing is this). Same mechanism, different jobs.

*Status:* the v0 engine implements the `nearby` default only — today's "pool = own stock + all upstream stock" behaviour is exactly that one tag. Everything above is the design the engine grows into; see the implementation guide.

### Control, actions, and culture

**Control over a location is not a permission system — it is an ordinary resource, and nobody has to win it.** The chain runs: something expensive produces a **control terminal**; a transform consuming that terminal produces a **nudge**; a nudge is spent to shift one transform's priority at that location by a small delta. Every step is an ordinary transform over ordinary resources.

The move that makes this work is that **priority is a delta, not a setting.** Nudges do not claim a location or override each other — they *superpose*. If your terminals generate +3 toward farming while a rival's cultural push generates −2, the location gets +1 and gets on with its turn. There is no majority check, no threshold, no arbitration over who holds a place: contention is arithmetic, and a location can be pushed by several sources at once without any of them needing authority over the others.

Two kinds of nudge feed one pool:

- **Blank-cheque nudges** come from control terminals and arrive *unspecified*. The world produces the capacity; the player supplies the intent. Filling them in is most of what submitting a turn actually is — *this one is farming +1, this one is logging +1* — which is how player agency enters a system that otherwise runs itself. Blank nudges are **spent where they are produced**: authority is bureaucratic and does not travel.
- **Pre-targeted nudges** come from cultural resources and arrive already specified, because a movement knows what it wants. They need no player at all, which is what lets the world push back on its own.

Both land in the same list of deltas, applied together before the next turn's transforms run. A player's turn and a cultural movement's effect are the same kind of object, resolved by the same rule.

**Cultural movements are resources**, produced by their own chain, needing their own building and inputs, and **consumed when they take effect**. Unlike nudges, culture *travels* — it moves through the same logistics as grain, so you spread an ideology by shipping it. That asymmetry is the whole influence-at-a-distance story: you cannot govern a distant settlement by decree, but you can send it a movement. Consumption gives attenuation for free (influence fades unless you keep paying to carry it further), and resistance is native — break the trade route to starve incoming influence, or out-produce it with counter-influence. No combat rules, no separate ideology system.

Any tags on a cultural resource are for visualisation and summarisation only; they carry no mechanical effect of their own.

*Known consequence:* a priority delta persists until pushed back the other way. Because the delta only ever acts as a **sort key**, this saturates rather than running away — once a transform is first, further nudges change nothing — but it does mean entrenched positions have **hysteresis**: dislodging one costs roughly what was spent building it. That is arguably correct for political inertia on a centuries-long voyage; if it proves too stiff, clamping the score to a bounded range is the cheap fix.

A scenario is therefore pure data — resource vocabulary, transform list, locations and tagged edges, initial stocks, evaluation order — which is the concrete form of "ship configuration is authored level design" (§5). See the implementation guide for the format and `scenarios_data/simple-world.json` for the minimal example.

*Relation to the agent model:* in v0 a person is an undifferentiated token, which collapses the agent layer into resource counts. This is deliberate MVP compression, not a change of thesis — when the political layer needs individuals (dispositions, movements), person tokens become individual records participating in the same transforms, and the aggregation story is unchanged.

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

### Contested control
Because control is a resource and priority is a delta (§6), multiplayer influence needs **no arbitration at all**. Two players investing in the same settlement do not race for a majority and there is no winner — their nudges simply sum, and the location does whatever the arithmetic says. Influence footprints expand, overlap, and interfere as a consequence of where each player chose to build, with no separate diplomacy or conquest layer, and no rule anywhere that decides who a place "belongs to."

This makes partial influence real and continuous: you can meaningfully tilt a settlement you do not dominate, and a rival can feel your presence without being locked out. Starving a rival's supply route is a legitimate and fully mechanical counter-move — as is out-producing them in cultural resource and shipping it into the settlement they thought was theirs.

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

### Load-bearing — a blank here gets invented for us

These are gaps the build will hit head-on. If they are still empty when the work starts, whoever (or whatever) is implementing will fill them in by guessing.

- **The order/directive vocabulary at each scale.** §6 now fixes the *shape* of a turn — spend the nudges you produced on signed priority deltas — but not what that means at settlement versus ship scale, nor whether the older register (zone an area, build a structure, allocate labour) survives alongside it or reduces to nudges too. Still load-bearing for both the client and the feel of the game.
- **Core-loop metrics, both halves.** The unlock metrics that gate each expansion of scope, *and* the victory metrics behind the tiered win conditions (§7). "Tiered victory" and "hit visible targets to advance" are currently concepts with no numbers or criteria behind them.
- **A scales-and-numbers reference.** Concrete figures exist in prose but are scattered: turn = day/week/month, journey = 100–1,000 years, population 10,000 down to 200 survivors. A small table of starting values prevents guesswork.
- **The zoom-to-cause mechanic.** Following the fish vendor; tracing a ship-scale metric down to the agents producing it. This is a signature feature and arguably the heart of the experience, but the client is described only as "thin." It needs a real design paragraph, because it is also a genuine UI challenge.
- Where exactly does the perspective/control shift from spatial placement to policy levers, and is it gradual or stepped?
- How lightweight can the agent model be while still producing believable aggregate ecology *and* politics?

### Raised by control, actions, and tagged edges (§6)

- **Does scope growth change the verb, or just multiply it?** §2 promises that expanding scope changes *what you care about*, but control-as-a-resource scales the quantity of one verb — more places you may nudge. The likely resolution is that higher scope nudges **aggregate** stacks (a region's, not a village's), so the grammar holds while the referent changes level. That needs deciding, because it also decides whether regions are real locations in the graph or a view over them.
- **What gates scope in single-player?** With no rival, nudges are uncontested, so nothing external limits reach. The implicit gate is that control terminals are expensive and only a healthy settlement has the surplus to build them — competence gating by economics rather than by a metric threshold. Worth confirming that this actually bites at the table.
- What produces a control terminal, and at what rate? Cheap terminals make political capital trivial; dear ones make the map ossify. This is the main balance dial for the whole political layer.
- Do cultural resources decay in transit, or only on use? Attenuation is claimed to be natural, but under universal decay the actual falloff curve depends on the storage transforms available along the route.
- Does a nudge's delta need clamping? Deltas persist, and although they saturate as a sort key, entrenched positions gain hysteresis (§6). A bounded score range is the hedge if that proves too stiff.
- How many tags does a real map need before authoring them becomes the bottleneck? The gradient-field generator is the hedge; it needs testing on a non-trivial map.

*Resolved in design, kept here as a note:* control-majority tie-breaking and latching are moot — superposing deltas removed the majority check entirely. Influence at a distance is answered by asymmetry: blank nudges are spent where produced, cultural resources travel, so you send a movement rather than a decree.

### Lower priority — placeholders so they are not lost

- Multiplayer turn-resolution timing, and the save/persistence model.
- A short **non-goals / scope-boundaries** section, so the build does not gold-plate: no ship construction, no physics solver, no multiplayer in the MVP.
- Art direction and visual tone — currently absent from this document entirely.
- A prior-art list: the other Generation Ship game, *Kingdoms and Castles*, *Oxygen Not Included*, and the climate-policy simulator behind §3.3's reference point — most likely **En-ROADS**, which matches the described "pull a policy lever, watch consequences emerge" model, though this needs confirming.
- What do comparable server-authoritative, turn-and-replay commercial games teach us about shipping and monetization?
- How is determinism guaranteed so a submitted turn replays identically every time (see implementation guide)?
