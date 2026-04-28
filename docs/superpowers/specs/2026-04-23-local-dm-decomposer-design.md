> **Superseded 2026-04-28** — see [`2026-04-28-localdm-offline-only-design.md`](2026-04-28-localdm-offline-only-design.md). This spec's "LocalDM is on the live critical path" assumption no longer holds; LocalDM is now dormant on the live turn and used offline only via the corpus miner.

# Local DM Decomposer — Design

**Date:** 2026-04-23
**Status:** Approved — ready for implementation-plan decomposition
**Authors:** architect (The Ministry of Silly Walks Official) + Keith
**Relates to:** ADR-010 (superseded intent routing), ADR-028 (Perception Rewriter — asymmetric narration), ADR-029 (Guest NPC Players — inverted perception), ADR-031 (Game Watcher Telemetry), ADR-036 (Multiplayer Turn Coordination), ADR-037 (Shared-World / Per-Player State), ADR-039 (Narrator Structured Output), ADR-041 (Genie-Wish Consequences), ADR-056/057 (tool pattern, superseded), ADR-058 (Claude subprocess OTEL), ADR-059 (Monster Manual — server-side pregen + injection), ADR-066 (Persistent Opus Sessions), ADR-067 (Unified Narrator Agent), ADR-073 (Local Fine-Tuned Model Architecture), 2026-04-22 Multiplayer Session Model spec + Plan 03 (mp-03-filtered-sync-and-projections), CLAUDE.md, SOUL.md

## 1. Problem

The shipping system has a **split-brain intent/flag pipeline** that is nominally present but mechanically inert, and the narrator is doing work it is structurally unsuited for. The pain concentrates in three places:

**1a. The `action_flags` pipeline is write-only.** Five booleans (`is_power_grab`, `references_inventory`, `references_npc`, `references_ability`, `references_location`) are emitted by the Opus narrator inline with its structured output, wrapped in an `ActionFlags` dataclass, serialized into the `turn_complete` watcher event — and **read nowhere** (`orchestrator.py:1336-1338` constructs them; no non-test consumer reads them across server, UI, or daemon; verified by grep). The narrator is paying tokens and attention to emit fields nothing consumes.

**1b. `classified_intent` is a hardcoded constant.** `orchestrator.py:1200` returns `"exploration"` unconditionally with an ADR-067 comment ("all intents route to narrator"). The UI has a `classified_intent === "Combat"` branch at `TimelineTab.tsx:297` that is **dead code** — it can never fire. The intent-routing layer intended by ADR-010 and inherited by the Python port is structurally absent.

**1c. The narrator is a monolith under dual-task load.** On every turn Opus is asked to simultaneously: (a) read natural-language player input, (b) resolve pronouns and ellipsis against game state, (c) decide which NPCs act and how, (d) initiate confrontations, (e) adjudicate lethality/consequences, (f) write prose, (g) emit a ~15-field structured block. ADR-057 diagnosed this as a dual-task penalty; ADR-059 empirically confirmed it for the tool-calling axis ("`claude -p` is a prose generation task. Tool calling is an interruption Claude can skip"). The same incentive gradient that makes Claude skip tool calls makes it **hallucinate referents** ("Let's go!" → invents a follower because the pronoun-resolution slot demands a filler and prose-generation treats it as creative latitude).

**1d. The narrator is too helpful.** Claude's RLHF trains pro-player lenience. Under ambiguity it softens consequences, pulls combat punches, invents cooperative NPCs, and narrates player survival through mechanically-lost scenes. This breaks SOUL.md's Genre Truth and Living World principles directly. Keith's playtest test — *"good enough to fool a career GM"* — cannot be met by a model that defaults to making the player feel good. Sebastien's mechanical-visibility affordance (the GM panel as Illusionism detector, per CLAUDE.md) cannot see the lie because no upstream layer emits a falsifiable mechanical claim.

## 2. Design Principles

**Honored (load-bearing constraints):**

- **ADR-059 injection pattern.** Claude in `claude -p` mode does not reliably call tools. The production pattern is: server-side subsystems run eagerly, their outputs are injected into `<game_state>` as world-truth, and the narrator reads them as ground truth. This design extends that pattern — it does not reopen the tool-calling question.
- **ADR-066 persistent sessions.** The narrator runs on a resumed Opus session with cached context. The decomposer will use the same pattern.
- **ADR-073 local fine-tune direction.** The decomposer is the ideal fine-tune target: narrow, structured, high-volume, with ADR-031 TurnRecord capture as the training data source.
- **SOUL.md Zork Problem.** Player input is open-ended natural language; the decomposer cannot be keyword rules, regex, or a fixed-taxonomy multi-label classifier. It must be a reader.
- **SOUL.md Living World + Genre Truth.** The decomposer is the impartiality layer. It is **not helpful to the player**; it is fair to the world.
- **Sealed-letter multiplayer pacing.** Alex cannot be put on a blocking clarification path. The table does not wait.

**Explicitly rejected:**

- **Claude as tool-calling agent (Sonnet or otherwise).** ADR-059 proved this doesn't work in `claude -p` mode. Not revisited here.
- **BERT multi-label flag classifier.** Closed-taxonomy pattern-matching fails the Zork test even with embeddings. An encoder cannot emit structured dispatch; it can only bucket.
- **Keyword / regex fallbacks.** Same Zork failure mode.
- **Embedding-based retrieval as primary routing.** Fuzzy pattern-matching is still pattern-matching.
- **Narrator self-reporting of intent/flags.** Source of today's hallucinations; retire.
- **Blocking clarification modals to individual players.** Breaks sealed-letter pacing.

## 3. Architecture

### 3.1 Overview

```
                     ┌─────────────────────────────────────────┐
                     │ SEALED-LETTER PHASE (existing)          │
                     │ Wait for all N player submissions        │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │ LOCAL DM (decomposer) — NEW              │
                     │ ONE batched call over N actions          │
                     │ Reads game state + all submissions       │
                     │ Emits: DispatchPackage                    │
                     │   - resolved referents (per action)       │
                     │   - subsystem dispatches                  │
                     │   - lethality verdicts                    │
                     │   - visibility tags (per-recipient)       │
                     │   - narrator instructions                 │
                     │ Haiku or local fine-tune (ADR-073)       │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │ SUBSYSTEM FAN-OUT (parallel, existing)  │
                     │ namegen, encountergen, NPC agency,       │
                     │ affinity, trope beats, monster manual,   │
                     │ lore RAG, roll outcome, ...              │
                     │ Outputs collected into injection payload │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
                     ┌─────────────────────────────────────────┐
                     │ NARRATOR (Opus, persistent session)      │
                     │ Composes ONE canonical narration          │
                     │ Receives <game_state> + injected facts + │
                     │ narrator_instructions (incl. lethality)  │
                     │ Canonical = omniscient server truth       │
                     │ No more JSON sidecar flags               │
                     └────────────────────┬────────────────────┘
                                          │  canonical narration +
                                          │  DispatchPackage visibility tags
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ PER-RECIPIENT FAN-OUT (ADR-028 + Plan 03 — existing design)          │
   │ For each of N players in parallel:                                    │
   │   1. Perception Rewriter — apply status effects                       │
   │      (charmed / blinded / deafened / frightened / invisible)          │
   │      AND asymmetric-information filter                                │
   │   2. ProjectionFilter — final include/redact/omit gate                │
   │      against decomposer's visibility tags                             │
   │ Produces N filtered narrations, each deliberately different           │
   └──────────────────────────────────────────────────────────────────────┘
```

**This shape resolves the "narrator × N?" question.** The narrator runs **once, canonically**. The N-fan-out happens at the Perception Rewriter / ProjectionFilter layer, which is ADR-028 + Plan 03 — existing design, partially built in the Rust codebase, not a new invention. The decomposer's job is to produce authoritative **visibility tags** that the downstream filter layer consumes as ground truth — so a perception rewriter cannot leak info a character shouldn't know, and a projection filter has a concrete rule set rather than PassThrough defaults.

### 3.2 The Decomposer's Responsibilities

1. **Read** each player action in game-state context.
2. **Resolve referents** — pronouns, ellipses, demonstratives — grounded in the NPC registry, party composition, recent narration, inventory, nearby locations. Every resolution carries a confidence score and plausible alternatives. Never blocks on ambiguity; always picks the best-available and surfaces the assumption.
3. **Decompose into subsystem dispatches** — which server-side subsystems should fire for this action, with what parameters. One action can fan out to many dispatches (e.g., "I tell foo to attack the bar" → npc_agency + confrontation_init + affinity_delta × N + witness_propagation).
4. **Arbitrate lethality and adverse consequences.** This is the central impartiality role (see §4).
5. **Produce narrator instructions** — a short injected directive telling the narrator what *must* happen in the prose, what confidence level to communicate, and what the universe is forcing on the player regardless of their wishes.
6. **Emit authoritative visibility tags per event.** Who sees what, at what fidelity, with what asymmetric spin (per-recipient). This is the ground-truth feed for the downstream ADR-028 Perception Rewriter and Plan 03 ProjectionFilter (see §3.3).

The decomposer **does not write prose.** It produces a structured artifact. That is precisely why it escapes the `claude -p` tool-skip failure mode in ADR-059: there is no prose task to fall back to.

### 3.3 The Decomposer as Authoritative Visibility Source (load-bearing)

Asymmetric information is a shipping-blocker feature per the 2026-04-22 multiplayer spec and ADR-028. The architecture already specifies:

- **One canonical narration** produced by the narrator, treating the server as omniscient
- **Per-recipient Perception Rewriter** that re-voices the narration per player's status effects (charmed → enemies appear allied; blinded → visual details removed; etc.) running concurrently per ADR-028
- **ProjectionFilter** as the final include/redact/omit gate per recipient before the socket send (Plan 03 `mp-03-filtered-sync-and-projections`)
- **Per-player save files** that are deliberate projections of canonical state through the player's asymmetric-information filter, not replicas

What's missing from this design today is a clean upstream source of **authoritative visibility data** — "who saw this, from where, with what clarity, with what spin." Plan 03 ships a `PassThroughFilter` as the default because there's nothing upstream producing real visibility metadata.

**The decomposer produces that metadata as part of its regular output.** Every `SubsystemDispatch`, `LethalityVerdict`, and `CrossAction` carries visibility tags (see §5). The rewriter and filter layers become deterministic consumers of this metadata rather than inference engines trying to guess what a player should know.

This gives us three hardening wins for free:

- **Leak hygiene.** The narrator's canonical output can be audited against the decomposer's visibility tags. If the narrator prose mentions a fact tagged `visibility: player:Alice_only`, the ProjectionFilter redacts it from other recipients' stream. The narrator cannot accidentally leak a secret it was told, because the upstream tagging is authoritative.
- **Inverted perception for guest NPC players (ADR-029).** A guest NPC player receives narration re-voiced from the NPC's perspective. The decomposer already knows which events the NPC witnessed (via its authorship of NPC agency dispatches); inverting the visibility tag set for that seat is a local transform, not a new subsystem.
- **Region co-location becomes cheap.** ADR-037's `resolve_region()` already handles "these two players are in different regions." The decomposer's visibility tags extend this to event-level granularity within a shared region (line-of-sight, earshot, fog-of-war) without rewriting the region model.

## 4. Lethality Arbitration (the "let the player die" layer)

### 4.1 Why this lives in the decomposer, not the narrator

Claude is too helpful. Its training biases it toward:
- Having the sword bounce off at the last second
- Inventing cinematic escapes
- Letting the villain monologue instead of striking
- Softening confrontation outcomes
- Narrating survival through scenes that were mechanically lost

Prompting does not correct this reliably (same incentive-gradient failure as ADR-059 tool-calling). The **only durable fix** is to remove the decision from the narrator. The narrator is told *what* happens; it only decides *how to describe it*.

### 4.2 What the decomposer decides

The decomposer consumes deterministic subsystem outputs (HP deltas, confrontation beat failures, resource pool depletion, genie-wish consequence triggers per ADR-041, roll outcomes per ADR-074) and issues a **lethality verdict** per affected entity, with explicit witness scope for the asymmetric-info pipeline:

```
{
  entity: "player:Alice",
  verdict: "dead" | "dying" | "maimed" | "defeated" | "captured" | "humiliated" | "unscathed",
  cause: "Salt Burrower mandible crush, 34 dmg, HP -8",
  reversibility: "permanent" | "reversible_with_cost" | "narrative_only",
  narrator_directive: "Alice is dead. Compose a genre-true death. Do NOT narrate survival. Do NOT have an ally intervene. The Salt Burrower does not hesitate.",
  soul_md_constraint: "genre_truth:lethal_for_this_genre",

  # Asymmetric-info ground truth
  witness_scope: {
    direct_witnesses: ["player:Alice"],        # who saw it happen
    indirect_witnesses: ["player:Bob"],        # heard the scream, saw the flash, felt the ground shake
    unaware: ["player:Cass", "player:Dan"],    # not present; won't learn until discovered
    perception_fidelity: {                     # what each witness actually perceives
      "player:Alice": "full",
      "player:Bob": "audio_only_muffled"
    }
  }
}
```

The narrator sees this in its injected context as a **non-negotiable world fact** and composes ONE canonical death scene. The Perception Rewriter then produces per-recipient versions: Alice's stream shows the death in full; Bob's stream shows the muffled echo; Cass and Dan hear nothing. The ProjectionFilter can even delay the "character_dead" UI signal for Cass/Dan until they discover the body — sharp asymmetric horror that is, as SOUL.md's "Tabletop First, Then Better" names it, "asymmetric message passing that exceeds what a tabletop GM could manage."

The `<game_state>` authority pattern (ADR-059) means Claude treats the verdict as ground truth rather than creative latitude. The `witness_scope` means other players' feeds are not lied to — they are correctly told nothing.

### 4.3 The impartiality training objective

The decomposer is **trained to be fair to the universe, not fair to the player.** This is not cruelty — it is the tabletop-DM stance that a good session requires stakes that can actually land.

Phrased as a training objective:

> Given action + game state + deterministic subsystem outputs, emit the dispatch that a **career tabletop DM who is impartial between player and world** would produce. The DM is fair to NPC agendas, fair to genre lethality, fair to the physics of the fiction, and fair to the player — in that order when they conflict. The DM does not soften outcomes to spare the player. The DM also does not invent hostile outcomes the dice did not produce; impartiality cuts both ways.

Training data implications:

- **Existing save.db corpus is the primary source, bootstrappable today.** Real playthrough data is already accumulated in `~/.sidequest/saves/` across at least 4 genres (caverns_and_claudes, mutant_wasteland, space_opera, plus dated slug games/). Each save carries:
  - `events` table — `seq`, `kind`, `payload_json`, `created_at` — the server event log. This is already the TurnRecord-shaped capture ADR-031 intended, under a different table name. No wiring work required to start mining.
  - `narrative_log` — `round_number`, `author`, `content` — paired prose per round; the decomposer learns to produce dispatches consistent with the narration that followed.
  - `game_state`, `lore_fragments`, `scenario_archive`, `scrapbook_entries`, `session_meta` — state snapshots and context.
- **Per-player save divergence = visibility ground truth for free.** Multiple save.db files exist for the same genre/world under different player names (e.g., `caverns_and_claudes/mawdeep/keith/save.db` + `caverns_and_claudes/mawdeep/slabgorb/save.db`; `mutant_wasteland/flickering_reach/rux/save.db` + `.../slabgorb/save.db`). Diffing these per-player projections against each other for the same event_seq **reveals the visibility pattern that was applied at play time** — labeled asymmetric-info training data with no additional labeling effort. The Sunday `mutant_wasteland/flickering_reach` session that CLAUDE.md names as reference data for James (Rux) is a multi-seat example directly usable.
- **Keith-as-gold-standard labeler** — Keith's 40 years of tabletop are the impartiality-rubric gold standard. Labeling load is **lower than it looks** because:
  - The corpus is already there; Keith doesn't play N new sessions, he tags existing turns
  - Most turns are unambiguous (quiet exploration, clear combat mechanics) — those don't need labeling; they're ground truth as-captured
  - Only the *disputed* turns need Keith's pass: narrator hallucinations, pulled punches, invented cooperatives, mis-resolved referents — a reviewer tool highlights these heuristically (per the "negative examples" bullet below)
- **Mine the codebase + save corpus for negative examples automatically.**
  - Every turn where post-hoc Monster Manual lookup failed (narrator invented an NPC not in the Manual) is a labeled hallucination.
  - Every turn where `action_flags absent from extraction` warned (`orchestrator.py:1291`) is a labeled dual-task failure.
  - Every turn where a player's next submission was a retarget correction ("no, the bandit — I swing at him") is a labeled mis-resolution of the prior turn's referent.
  - Every turn where a subsequent GM-panel override happened is labeled by construction.
- **Synthesize adversarial examples** — for gaps the corpus doesn't cover (first-time power-grab consequences, unprecedented lethal scenarios). Use published-adventure DM commentary, classic module outcomes (the **original** Tomb of Horrors, not its softened reprints), and Keith's playgroup notes.
- **Explicitly exclude RLHF-shaped Claude traces from the impartiality training data.** The narrator's past outputs *as-generated* carry the helpfulness bias. They can appear as **negative** examples paired with the corrected impartial dispatch; they must not appear as positive examples.

### 4.4 The distillation framing: "Opus is already training up a model"

Every Opus narrator turn shipped today is already producing `(action + state, structured outcome)` pairs inside the save.db `events` + `narrative_log` tables. The local model is a **distilled student** of Opus, with the impartiality correction layered on top. Two passes:

**First pass — schema + fluency distillation (cheap):** Opus is the teacher. Student learns the DispatchPackage output shape, the subsystem vocabulary, the referent-resolution patterns, the dispatch ordering. This is where Opus is actually good — it reads natural language and produces structured understanding competently. The student learns to emit the same shape faster, locally, and cheaply. Good first pass. Gets us 80% of the behavior we want.

**Second pass — impartiality tuning (the real work):** Opus's bias toward player-helpful outcomes is what we're removing, so we cannot train the student to be a faster Opus. Three correction signals stack on top of the distilled base:
1. **Keith-labeled rubric corrections** — Keith reviews disputed turns from the corpus and rewrites the dispatch with the career-DM impartial call. These are high-signal, low-volume (most turns don't need correction; only the disputed ones).
2. **Auto-mined negative pairs** — Monster Manual mismatches, retarget corrections, GM panel overrides, dual-task extraction failures. High-volume, mechanically labeled.
3. **Adversarial synthesis for coverage gaps** — scenarios the corpus hasn't produced yet (genre-pack-specific lethal situations, power-grab genie-wish backfires).

The spec's phased delivery in §7 / §10 matches this: Phase A ships Haiku-as-decomposer *with the Opus-produced corpus already being captured*; Phase B trains the local student from that corpus plus the correction signals; Phase C adds per-genre LoRA specialization.

**Why this is the right pattern rather than training from scratch:** Opus handles the open-ended natural-language reading well enough that starting from its output reduces training data requirements by roughly an order of magnitude. Without distillation, a 1-3B local model would need ~100k labeled turns to approximate Opus's reading competence alone. With distillation, it needs ~10k, and those turns can focus on teaching impartiality rather than basic reading comprehension.

### 4.4 Who can override (and what scales impartiality by setting)

- **Rule of Cool (SOUL.md)** — if a player action is creative and costs nothing mechanical, say yes. The decomposer enforces this *against* the universe when appropriate. Yes-And is its own kind of impartiality.
- **Genre-pack content model** — the "asshole-axis" is not a new knob. Every genre pack already encodes its own harshness across multiple load-bearing structures:
  - **Power tiers + archetype stat ranges** (per ADR-007 unified character model) determine how hard hits land
  - **Confrontation resource pools** (ADR-033) define how far past zero consequences extend
  - **Trope definitions** (ADR-018) encode what *kind* of bad things happen in this genre
  - **Genie-wish consequence tiers** (ADR-041) define the monkey's-paw curvature
  - **Tone axes + cultural attitudes** in the theme YAML set the emotional register of failure
  - **Progression system shape** (ADR-021) determines whether defeat is reversible
  - `caverns_and_claudes` reads as comedic death (one-liner, back next session) from its tropes and tier tuning; `pulp_noir` reads as brutal permanent death from its same structures with different values; `elemental_harmony` may produce no permadeath at all from its pack content alone. **The decomposer reads these existing fields** — no new schema required beyond a small `lethality_policy` summarizer if the implicit signal proves ambiguous.
- **GM panel override** — Keith can override a verdict manually from the GM panel. The override writes a TurnRecord training signal.

## 5. Output Contract (DispatchPackage)

```
DispatchPackage {
  turn_id: uuid,
  per_player: [
    PlayerDispatch {
      player_id: str,
      raw_action: str,
      resolved: [
        Referent {
          token: str,                    # e.g. "let's", "him", "that"
          resolved_to: entity_id | null, # null = reflect absence
          confidence: float,             # 0.0 - 1.0
          alternatives: [entity_id],     # plausible others for distinctive prose
          resolution_note: str | null    # audit trail
        }
      ],
      dispatch: [
        SubsystemDispatch {
          subsystem: str,                # e.g. "npc_agency", "confrontation_init"
          params: dict,
          depends_on: [dispatch_id],     # serial dependencies within the bank
          idempotency_key: str,
          visibility: VisibilityTag      # see below; consumed by Perception Rewriter + ProjectionFilter
        }
      ],
      lethality: [LethalityVerdict],     # see §4.2 (includes witness_scope)
      narrator_instructions: [
        NarratorDirective {
          kind: "must_narrate" | "must_not_narrate" | "distinctive_detail_for_referent"
              | "canonical_only_do_not_reveal_to_others",
          payload: str,
          visibility: VisibilityTag
        }
      ]
    }
  ],
  cross_player: [                         # actions that interact across players
    CrossAction {
      participants: [player_id],
      witnesses: [player_id],             # who sees the interaction (may exceed participants)
      dispatch: [SubsystemDispatch]       # each dispatch carries its own visibility
    }
  ],
  confidence_global: float,               # how confident the decomposer is in the whole batch
  degraded: bool,                         # true if the decomposer had to guess heavily
  degraded_reason: str | null
}

VisibilityTag {
  # Ground truth for Perception Rewriter + ProjectionFilter
  visible_to: [player_id] | "all",        # recipients who get the event at all
  perception_fidelity: {                  # per-recipient clarity
    player_id: "full" | "audio_only" | "audio_only_muffled"
             | "visual_only" | "periphery_only" | "inferred_from_aftermath"
  },
  secrets_for: [player_id],               # players who receive MORE detail than others (GM reveals,
                                          # asides, private objectives for guest NPC players per ADR-029)
  redact_from_narrator_canonical: bool    # true for secrets that must not be in canonical narration at all
                                          # (narrator must not see them; decomposer routes directly to recipient)
}
```

**Visibility defaults are explicit, not implicit.** Every dispatch names its visibility. `visible_to: "all"` is a conscious choice, not a fallback — it's the assertion that this event is public information within the shared region. No dispatch ships without a visibility tag; the output contract enforces it.

## 6. Per-Turn Flow

### 6.1 Happy path (high-confidence resolution, multiplayer batched)

```
T0   All N sealed letters in.
T1   Decomposer call: context+state+N_actions → DispatchPackage.   (~1s cached Haiku; <200ms local fine-tune target)
T2   Subsystem fan-out:
       - Independent dispatches run concurrently
       - depends_on edges serialize within the bank (NPC agency before
         confrontation_init, since foo must decide before combat starts)
       - Each subsystem emits OTEL span; outputs collected
T3   Injection payload assembled from subsystem outputs + narrator_instructions
T4   Narrator (Opus, persistent session) composes prose. No JSON sidecar.
T5   Post-narration gates (existing): NPC registry reconciliation,
     state delta commit, TurnRecord capture for training.
```

Expected added latency vs today: **~1s with Haiku + caching, <200ms with local fine-tune.**

### 6.2 Ambiguous pronoun ("Attack him!" with three hostiles)

- Decomposer resolves to most-plausible target (confidence=0.45, alternatives=[goblin_1, goblin_3, bandit_1])
- Narrator instruction: `distinctive_detail_for_referent(target=goblin_2, detail_hint="broken tooth")`
- Narrator prose names the target distinctively: *"You swing at the nearest goblin — the one with the broken tooth..."*
- If the player meant the bandit, next turn's submission ("no, the bandit — I swing at him instead") is itself a retarget dispatch. State rewinds the misdirected attack or reframes it.

### 6.3 Unresolvable referent ("Let's go!" with no party)

- Decomposer: `addressees=[]`, `confidence=0`, `dispatch=[{subsystem: "narrator_reflect_absence"}]`
- Narrator instruction: `must_not_narrate("inventing an NPC follower"); must_narrate("the empty room answering back")`
- Narrator prose: *"You call out, but the tavern is empty. The door does not open."*
- No hallucinated follower. The absence is the scene.

### 6.4 Lethal path (PC goes to zero)

- HP subsystem reports Alice at -8 after Salt Burrower crit
- Decomposer emits `LethalityVerdict(entity=Alice, verdict=dead, reversibility=permanent, narrator_directive="Alice is dead. Compose a genre-true death...")`
- Narrator receives the verdict as injected ground truth
- Narrator composes the death scene — with genre-appropriate gravity, without the sword bouncing off, without an ally arriving, without a saving throw the rules didn't grant.

### 6.5 Asymmetric path (P1 assassinates NPC in the shadows)

- Alice sneaks into the warehouse alone while Bob, Cass, Dan are at the inn
- Alice's sealed letter: "I slit the guard's throat from behind"
- Decomposer:
  - Resolves `the guard` via state (one guard in warehouse scene)
  - Dispatches: `stealth_roll_check` → success → `npc_agency(guard, state=unalerted)` → `lethal_strike` → `lethality_verdict(guard, verdict=dead, witness_scope={direct: [Alice], unaware: [Bob, Cass, Dan]})`
  - `narrator_instructions`: `canonical_only_do_not_reveal_to_others` on the assassination
  - Visibility: `visible_to: [Alice]` on the kill event
- Narrator composes ONE canonical narration including the kill (it knows everything, like an omniscient DM)
- Perception Rewriter produces four streams:
  - **Alice:** the assassination in full
  - **Bob:** "The evening at the inn drags on. Harlan tells a joke." (the canonical kill is redacted from her stream)
  - **Cass:** same as Bob's stream, rewritten again for Cass's POV
  - **Dan:** same
- ProjectionFilter confirms the redaction: `visibility.visible_to=[Alice]` means no event reaches the other three sockets for this action
- Next day in-fiction, when the body is found, a *new* turn generates visibility for the discovery event — reaching whoever is present — and the story propagates asymmetrically from there

This is the SOUL.md payoff: *"asymmetric message passing that exceeds what a tabletop GM could manage."* The tabletop DM has to note-pass. The server just redacts per-recipient.

### 6.6 Degraded path (decomposer unavailable or times out)

- Fall back to a **minimal static injection** (current behavior) and run the narrator
- `degraded=true, degraded_reason="decomposer_timeout"` logged
- OTEL span records the degradation for the GM panel
- Turn completes; table does not block

## 7. Model Tier and Deployment (Phased)

### Phase A — Haiku on a resumed session
- `claude -p --model haiku --resume $DECOMPOSER_SESSION_ID`
- Game-state prefix cached; per-turn delta is the action block + batch framing
- Target latency: ~1s p50, <3s p99
- Structured JSON output contract; the existing `extract_structured_from_response` infrastructure (ADR-039) handles it
- **This is the shippable MVP.** Cheap, bounded risk, unblocks retiring the dead flags and the hardcoded `classified_intent`.

### Phase B — Local fine-tune per ADR-073
- Collected TurnRecord corpus labeled by Keith (impartiality rubric) and the hallucination-negative mining described in §4.3
- Target model: 1-3B parameters, QLoRA fine-tune, runs on the existing sidequest-daemon GPU (the one already serving Z-Image + ACE-Step)
- Target latency: <200ms p50
- Cost: free-at-runtime once trained
- Structured JSON output contract identical to Phase A; swap is one env var

### Phase C — Specialization (optional; prefer prompt over LoRA)
- **Default position: start with base impartial decomposer + rich genre-pack context injection.** Empirical finding from the image-generation side: Z-Image + good genre-pack-driven prompts outperforms Flux + per-genre LoRA for most genre content (LoRA retains value only for narrow stylistic distributions). The analogous bet for the decomposer: base model + structured pack content in the prompt likely outperforms base + per-genre LoRA for impartiality tuning, because the pack content is already rich and the decomposer is reading it directly.
- **Add per-genre LoRA only if behavior diverges meaningfully** after Phase B. If the base model consistently fails to match `pulp_noir` brutality or `caverns_and_claudes` comedic beats even with pack-context injection, introduce LoRA adapters then. Don't build LoRA infrastructure for the decomposer on spec.
- If LoRA is needed later, ADR-083/084 stacking machinery is available for reuse.

## 8. Coordination Correctness (the hard part of async)

The latency math is the easy part. These are the real bugs waiting to happen:

- **Timeout policy.** Decomposer has a hard deadline (e.g., 3s). On timeout → degraded path (§6.5). Narrator still runs. Turn does not block.
- **Partial subsystem failures.** If affinity-updater crashes on one of three affinity events, the other two commit; the failed one logs an error span and the turn continues. Subsystem outputs are independent; no all-or-nothing.
- **Dispatch ordering.** Within the parallel bank, `depends_on` edges serialize specific pairs (NPC agency → confrontation_init). Topological sort at T2.
- **Idempotency.** Every SubsystemDispatch carries an `idempotency_key`. Subsystems check before applying. A retry after a flaky failure must not double-apply.
- **Multiplayer cross-action consistency.** If P1's action affects P2 (shove into bar fight), the decomposer emits a `cross_player` dispatch explicitly; subsystems that mutate shared state lock or serialize on those.
- **Retarget-on-correction.** When turn N+1 retargets turn N's misdirected action (§6.2), state rewind/reframe is its own subsystem; it is not inline narrator magic.

## 9. Non-Goals

- **Not** a Claude tool-calling agent. ADR-059 settled that.
- **Not** an MCP integration. `claude -p` does not support MCP; see ADR-056 Alternatives.
- **Not** a BERT / encoder classifier. Closed-taxonomy pattern-matching fails the Zork test.
- **Not** a replacement for the narrator. The narrator composes prose. The decomposer reads + arbitrates.
- **Not** a GM-panel interactive agent. Keith's GM-panel overrides are a manual feedback signal, not a live agent.
- **Not** a destination for the existing `action_flags` booleans. Those are **retired**, not migrated.
- **Not** a blocking clarification system. Ambiguity is resolved with surfaced confidence, never a modal prompt.

## 10. Migration Path

**Story group A — Dead-code demolition (trivial, independent of decomposer):**
- Remove `action_flags` emission from narrator prompt
- Remove `ActionFlags` dataclass + extraction
- Remove `classified_intent = "exploration"` hardcode and its UI branches (e.g., `TimelineTab.tsx:297`)
- Retire the dormant `preprocess_action()` in `agents/preprocessor.py`
- Update ADR-067 to note the inline-flag retirement

**Story group B — Decomposer MVP (Phase A, Haiku):**
- Define `DispatchPackage` types in `sidequest/protocol/`
- Build `LocalDM` class in `sidequest/agents/local_dm.py` with a single `decompose(turn_state, submissions) -> DispatchPackage` async method
- Wire it between `TurnPhase.InputCollection` completion and `TurnPhase.AgentExecution` in the session handler
- Implement three initial subsystems as targets: `reflect_absence` (new), `distinctive_detail_hint` (narrator directive only), existing `npc_agency` (wrap the existing NPC disposition code)
- Wire `narrator_instructions` into the existing `<game_state>` injection block via a new directives section
- OTEL spans on every dispatch; GM panel tab to view them
- Tests: unit (pronoun resolution cases), integration (full turn with happy + ambiguous + absence paths), wiring (spans actually fire)

**Story group C — Lethality arbitration:**
- Add `LethalityVerdict` to DispatchPackage contract
- Build verdict producer that consumes HP/confrontation/roll-outcome subsystem outputs
- Wire `narrator_directive` injection with `must_narrate` and `must_not_narrate` semantics
- Genre packs: add `lethality_policy` YAML field read by the verdict producer
- Per-genre smoke tests: PC at HP 0 in each pack produces genre-appropriate verdict shape

**Story group D — Training corpus mining + labeling surface:**
- Write a corpus-miner that reads the existing `~/.sidequest/saves/*/save.db` files (`events` + `narrative_log` tables) and emits `(input, output)` training pairs for distillation.
- Write per-player save diff utility: pairs same-event_seq records across per-player saves for the same genre/world to derive visibility ground truth automatically (see §4.3).
- Auto-mine negative examples: Monster Manual mismatches, retarget-correction pairs, GM-panel overrides, `action_flags absent from extraction` log warnings.
- **Standalone labeling tool** (user-preferred): lightweight web UI separate from the game session. Loads a corpus file, shows one disputed turn at a time (action + state + Opus's call + proposed correction fields), Keith tags impartiality corrections. Exports labeled pairs back to the corpus.
- Extend going-forward capture: add decomposer I/O to the `events` stream — `dispatch_package`, `narrator_instructions_used`, `verdict_overrides` — so corpus growth from Phase A onward carries the richer signal.

**Story group E — Local fine-tune (ADR-073 Phases 1-3):**
- LlmClient trait extraction (Phase 1 of ADR-073, unchanged)
- Ollama/MLX backend behind the trait (Phase 2)
- QLoRA fine-tune on captured + Keith-labeled corpus (Phase 3)
- A/B against Haiku via OTEL parity spans

**Story group F — Specialization (optional):**
- Per-genre LoRA adapters (see Phase C — only if base + context injection proves insufficient)
- Per-player impartiality-tuning (learn that Sebastien wants harder rulings; Alex wants pacing patience)
- **In-game player feedback affordance** (future, not-important-yet per Keith): a lightweight per-turn thumb / checkmark UI so playgroup members can flag "yep, got it right" or "no, that wasn't what I meant" on narration turns. Each flag becomes a labeled training pair. Turns the playgroup into passive labelers without breaking their immersion. Sits downstream of the standalone labeling tool (Story group D) — same corpus, different collection surface.

**Story group G — Asymmetric-info wiring (LOAD-BEARING, not optional):**
- Adopt the existing location-scoped lore-visibility code as the template/precedent for event-level visibility tagging. Extend it; don't parallel it.
- Add visibility-baseline fields to genre-pack and world YAML (sane defaults per tone); decomposer reads these as the authority.
- Wire `DispatchPackage.visibility` tags into the existing ADR-028 Perception Rewriter as the authoritative visibility source (replacing status-effect-only rewrites with full visibility-aware rewrites).
- Wire `DispatchPackage.visibility` into Plan 03 (`mp-03-filtered-sync-and-projections`) `ProjectionFilter` protocol — implement `VisibilityTagFilter` replacing `PassThroughFilter`.
- **Structural information hiding (primary defense):** events tagged `redact_from_narrator_canonical: true` never enter the narrator's prompt context — decomposer routes them directly to the recipient's projection stream. The narrator cannot leak what it was never told.
- **Canonical-narrator leak audit (safety-net only):** scan canonical prose against `redact_from_narrator_canonical: true` tags; emit OTEL span on any violation. Should catch zero real leaks if structural hiding is correct; exists to detect architecture holes.
- Wire inverted perception for ADR-029 guest NPC players — flip visibility tag set on the NPC seat's rewriter.
- Per-player save projection: peer saves receive only the filtered event stream per the 2026-04-22 multiplayer spec; canonical save is the union on the narrator-host.
- Ship no-cannot-exist-without: cannot release multiplayer without this group working end-to-end. Tests: (a) P1 assassinates NPC in shadows, P2-P4 receive nothing in their streams *and* in their local save; (b) P1 blinded sees no visual details in narration; (c) Guest NPC player sees NPC POV while protagonists see only visible behavior; (d) structurally-hidden secret never appears in narrator prompt inputs (unit-test at the prompt-builder layer).

## 11. Open Questions

1. ~~**Per-player narration fan-out.**~~ **RESOLVED.** One canonical narrator call per turn + N Perception Rewriter calls (ADR-028) + N ProjectionFilter passes (Plan 03). The decomposer produces authoritative visibility tags (§3.3, §5) that the downstream fan-out consumes. This is existing architecture; the decomposer's role is to feed it properly instead of leaving it on `PassThroughFilter` defaults.
2. ~~**Visibility rule authorship.**~~ **RESOLVED.** Genre + world YAML carry the baseline visibility model (sane defaults per tone); the existing "lore visibility by location" infrastructure already in the codebase is the precedent/template and the decomposer extends that pattern event-wise. Decomposer fills in event-level tags against the pack+world baseline. GM panel can override per-turn. Story-group G reuses the existing location-scoped lore visibility code rather than inventing a parallel system.
3. **Decomposer session persistence.** Does the decomposer get its own persistent Haiku session (`--resume`) paralleling the narrator's, or run stateless per turn? Stateful = faster + cache-friendly. Stateless = simpler + no context-drift risk. *Start stateful; fall back to stateless if drift bugs surface.*
4. **Idempotency on retarget.** When a turn-N misdirected attack is rewound by a turn-N+1 retarget, is the rewind a first-class subsystem or a narrative handwave? If narrative, we save code; if subsystem, we get clean state. *Recommend subsystem; defer decision to story-group B review.*
5. ~~**Labeling throughput for training.**~~ **RESOLVED.** Corpus already exists in `~/.sidequest/saves/` (see §4.3). Opus is the distillation teacher for the first pass (§4.4); Keith's rubric pass handles disputed turns only; auto-mined negatives cover the bulk. **Labeling UI is standalone** — quick to build, independent of session state, usable offline. A lightweight playgroup-labeling surface for James/Sebastien is still plausible but downstream.
6. ~~**Canonical-leak audit policy.**~~ **RESOLVED — architecture makes it structurally impossible, audit is safety-net only.** Primary defense is **information hiding on the server side**: secrets tagged `redact_from_narrator_canonical: true` are never placed in the narrator's prompt at all — the decomposer routes them directly to the recipient's projection stream, bypassing the canonical narration entirely. The narrator physically cannot leak what it was never told. Story-group G implements this as the primary mechanism. The automated leak audit still exists as a safety-net OTEL invariant for architecture holes we didn't anticipate, but it is not the guarantee — it's the smoke detector.

## 12. Glossary

- **Decomposer / Local DM** — the new layer. A structured-output reader that runs server-side between sealed-letter completion and narrator invocation.
- **DispatchPackage** — the decomposer's output contract. Per-player referent resolutions + subsystem dispatches + lethality verdicts + narrator instructions.
- **Narrator instruction / directive** — a short injected phrase telling the narrator what must or must not appear in prose. Ground truth, not suggestion.
- **Lethality verdict** — non-negotiable world fact about an entity's state post-resolution.
- **Impartiality** — the decomposer's stance: fair to NPC agendas, fair to genre lethality, fair to physics, fair to the player — in that order when they conflict.
- **Reflect absence** — narrator directive to describe emptiness honestly rather than invent a filler for an unresolved referent.
- **Visibility tag** — authoritative metadata on every dispatch naming who sees what at what fidelity. Produced by the decomposer, consumed by Perception Rewriter (ADR-028) and ProjectionFilter (Plan 03).
- **Canonical narration** — the omniscient-server truth produced once per turn by the narrator. Never sent to clients directly — always filtered through per-recipient rewriter + projection gate.
- **Per-recipient filtered narration** — what each player actually sees. Derived from canonical + visibility tags via the rewriter/filter pipeline.
