This doc is for transfer from other chats to the main project context. The top section "New Core Design Ideas" is to be directly added to the design and implmention docs. The second, "Unresolved From Conversation" and maybe the third, are notes on things that came up in conversation and we should likely add to an Open Questions section in the existing two main docs, or discard as already implemented or decided against. Once we've done that merge, I'll delete this doc.

# New Core Design Ideas to Incorporate:

## Getting There — Session Addendum (mechanics to fold into the transfer doc)

### 1. Control as a resource (the keystone)

Control over a location is not a separate permission system — it's an ordinary resource, produced and accumulated like any other.

- You build/produce a **control resource** at a location (via its own production chain — some transform outputs it).
- **Whoever holds the most control resource at a location earns the right to apply a priority move there** — i.e., to reorder that location's transform stack.
- This makes scope-of-control an *emergent, earned* thing that grows through the same resource mechanics as everything else. You extend your reach by out-producing rivals in control resource at the locations you care about.
- In multiplayer this is inherently contested: control is a majority check across whatever players have accumulated at that location, so influence footprints expand and collide geographically.

### 2. Actions as transform outputs

Transforms can output **actions**, not just resources. An action changes game state without being a storable/tradeable resource — the canonical one being a **priority move** (nudge a transform up/down the location's stack).

- The right to *apply* a priority move is gated by the control-resource majority above.
- Actions are contingent on the same input conditions as any transform output, so thresholds fall out for free ("only fires if ≥ N population / ≥ N of some cultural resource present").
- Actions are **deterministic** (for MVP).
- This is the slot where cultural effects, counter-influence operatives, etc. live — no new mechanic needed, just conditional transform outputs.

### 3. Cultural resources are just resources

No separate cultural system. A cultural resource (e.g. "back-to-the-land") is produced by its own chain (needs a specific production building, its own inputs), moves through the same logistics, and is **consumed when it takes effect** — i.e., when it triggers the action that nudges a transform stack.

- Consumption gives natural attenuation: influence tends to be local unless you invest in carrying it further, exactly like shipping any perishable resource.
- Resistance is native: break trade to starve incoming influence, or out-produce it with counter-influence. No special combat rules.
- Any "tags" on cultural resources are for visualization/summarization only — no mechanical effect of their own.

### 4. Transform input sets are tag-scoped

A transform's available input pool is the union of one or more named input sets. Two default tags always exist:

- **`local`** — resources physically in this location.
- **`nearby`** — resources in adjacent upstream locations (the symmetric, osmotic default).
- **`<TAG>`** — resources upstream along any edge carrying that tag.

Tags are **static structure** assigned at map-build time (hand-painted or algorithmically, e.g. via a distance/gradient field). They carry zero per-turn state.

### 5. Transport is just transforms (via directional tags)

Shipping is not a separate mechanic — it's a transform whose input set is a directional tag. "Pull wood from `cityward` neighbors, output it here" moves wood one hop toward the city per turn; downstream locations running the same transform carry it onward.

**Why tags are required (not optional):** most roads are symmetric edge pairs, so the raw graph is full of 2-cycles and topology alone carries no direction — a transport transform pulling on plain `nearby` would oscillate a resource back and forth. Each **tag defines an acyclic direction field** over the otherwise-cyclic graph: filter edges to `cityward` and you get a clean DAG (forest→town1→town2→town3→city) with no back-edge to pull along, so no oscillation. Counter-flow works because the reverse halves of the same roads carry the opposite tag (`forestward`), letting the same physical corridor move different resources in opposite directions with no state.

**Notes / expected costs:**
- A tag encodes flow toward **one** reference. Each distinct destination stuff should flow toward wants its own tag (or its own gradient field). Expect tags to proliferate by purpose — that's the honest cost, still fully static.
- Gradient auto-assignment: compute distance-to-target per node at build time, tag each directed edge toward-target if its head is closer than its tail. Hand-painting and distance-field are two ways to populate the same edge-tag structure.
- Location and resource tags are worth adding at the same time, but note they do *classification* work (what is this thing), distinct from edge tags doing *directional* work (which way does flow go). Same mechanism, different job.


# Unresolved From Conversation

Genuine gaps — things we gestured at but never pinned down:

The order/directive vocabulary is the big one. The whole interaction model is "assemble a rich bundle of orders," but the docs never enumerate what a player can actually do in a turn at each scale — zone an area, set a policy lever, allocate labor, etc. This is listed as an open question, but it's load-bearing for both the client and the feel of the game, and if it's blank, Claude Code will invent it.

The core-loop metrics — both the unlock metrics that gate each expansion of scope, and the victory metrics for the tiered win conditions. Right now "tiered victory" and "hit visible targets to advance" are stated as concepts with no actual numbers or criteria behind them.

A small scales-and-numbers reference. You mentioned concrete figures in passing — turn = day/week/month, journey = 100 to 1,000 years, population 10,000 down to 200 survivors — but they're scattered in prose. A tiny table of starting values saves Claude Code from guessing.

The zoom-to-cause mechanic. Following the fish vendor, tracing a ship-scale metric down to the agents producing it — that's a signature feature and arguably the heart of the experience, but the client is just described as "thin." It deserves a real paragraph, because it's also a genuine UI challenge.

Lower priority, worth a placeholder so they're not lost: multiplayer turn-resolution timing and the save/persistence model; a short non-goals / explicit-scope-boundaries section (so Claude Code doesn't gold-plate — e.g. no ship construction, no physics solver, no multiplayer in the MVP); art direction / visual tone (currently absent entirely); and a prior-art list (the other Generation Ship game, Kingdoms and Castles, Oxygen Not Included, and that climate-policy simulator you couldn't name — I think you're remembering En-ROADS, which is exactly the "pull a policy lever, watch consequences emerge" model you described).
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
