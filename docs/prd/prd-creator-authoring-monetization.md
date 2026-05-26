# PRD (Discovery Brief) — Creator Authoring & Monetization

**Status:** Discovery — pre-prioritization, pre-architecture
**Author:** BA discovery, 2026-05-22
**Source:** Keith, /pf-ba session 2026-05-22

> Discovery brief, not a spec. The goal here is to expose hidden assumptions, not pick a build order. Hand off to PM for prioritization and Architect for feasibility once the open questions below have committed answers.

---

## 1. The Idea (verbatim, then refined)

**Original framing (Keith, 2026-05-22):**
> "Have worldbuilding built in. So if someone, exactly like me, forever DM wants to play, they can build a world, have all the bells and whistles, set it up, tweak it, whenever they want. If enough people play it, their world is free for their playgroup. If more people than that play it, they start getting a royalty. I think this is a big one, and I think this might be a win."

**Two clarifications immediately following:**
1. **"It would target people like me."** — The target audience for the *creator features* IS the forever-DM persona. Not casual players, not the household audience.
2. **"We would not be able to provide that for free, though proven authors may get deals or something."** — The "free for your playgroup if it gets traction" tier is **out**. Per-session AI cost is real and the platform cannot eat it for someone else's friend group. What survives is some form of **discretionary deal for proven authors** — royalty, comped credits, partner program, status. Specifics deferred.

**Net concept (post-clarification):**
SideQuest exposes its authoring stack to forever-DMs as a first-class product surface. Anyone with the patience to build can build a world (and possibly a genre pack). Their friends play it on the platform like any other content — they pay to play. If a creator's world develops genuine traction, the platform signs a **deal** with them — terms case-by-case.

This is not a UGC marketplace with free tiers. It is a **prosumer authoring tool with a creator partner program on top of it.** A different category, a different competitive set, and dramatically different unit economics than the original framing.

### 1.1 The actual reframe (2026-05-22, mid-discovery)

> "We already have a wizard for my use. This is me realizing that *I* am the target demographic, not the players." — Keith

This is the load-bearing insight, not a side comment. For most of SideQuest's development the implicit funnel has been:

> **player wants an AI DM → SideQuest provides one → player invites friends → SideQuest grows.**

That model is *wrong* for this product. The actual funnel — the one already operating, evidenced by the 141-turn after-hours session, the household nonadoption, and the design of the GM panel — is:

> **forever-DM wants to play in their own world → SideQuest gives them the wizard + the GM that runs it → DM brings their playgroup → playgroup pays to play.**

The paying customer is the **DM-builder**, not the player. Players are *acquired by the DM*. This is the same dynamic as a private DM in tabletop: the DM does the work, the table shows up. SideQuest's commercial wrapper monetizes the DM's effort by hosting the world *and* running the game for them, both of which are infeasible without the platform.

This is consistent with — and arguably the *commercial articulation of* — memory [[project_gm_panel_audience]] (GM panel is a dev tool for Keith). The GM panel isn't a debug surface to hide; it is the **product surface for the paying customer.** Same for sq-world-builder, sq-audit, sq-poi, sq-music, conlang corpus tools, OTEL spans, scenario fixtures, and every other piece of "infrastructure" that's actually authoring/observability. Those tools are not internal scaffolding — they are *the product*, ergonomically dressed.

The implications cascade:

- **CLAUDE.md "Who This Is For" framing is incomplete.** It treats the playgroup as the audience. It is *the consumer of the product the customer builds.* Section needs revision to distinguish customer from consumer.
- **Acquisition cost = the cost of acquiring one DM, not one player.** A DM is one customer that brings 2-6 players for free. CAC math is dramatically friendlier than per-player models suggest.
- **Pricing should target the DM.** Possibly per-seat (DM + table), possibly per-world, possibly tiered by playgroup size. Player-level pricing is the wrong altitude.
- **Marketing channel is DM-shaped, not player-shaped.** Reddit r/DnDBehindTheScreen, r/RPGdesign, World Anvil community, OSR blogs — not r/rpg, not Twitch, not "AI Dungeon Reddit." Different community, different vocabulary, different objections.
- **The original question (§9) dissolves.** "Authoring-first vs partner-program-first" was framed as if those were separate priorities. With the reframe, **authoring IS the product** — it's what the customer is buying. The partner program is a downstream monetization layer for hits, not a separate strategic bet. Authoring-first is the only coherent answer once you accept that the DM is the customer.

---

## 2. Persona Anchor — Forever-DM (Keith)

The Doctor explicitly said the target = "people like me." That's load-bearing. The persona has been described in CLAUDE.md "Who This Is For" and is unusually well-specified:

- 40 years behind the screen, wants to play without losing depth
- High reading tolerance, high mechanical *and* narrative engagement
- Tarn-from-Dwarf-Fortress builder profile: builds *for himself first*, then others
- Already authoring worlds in SideQuest via AI-assisted tooling (sm-world-builder, sq-poi, sq-music, conlang) — glenross, beneath_sunden, coyote_star, tea_and_murder are the existence proofs
- The product is **literally a generalization of what Keith already does in this repo, opened to other people in his cohort.**

**Implication:** the bar for "discoverable / accessible" is forever-DM-tolerable, not new-player-tolerable. Onboarding friction can be substantial; reading load can be high; mechanical depth is a feature, not a wall.

**Adjacent personas this design must NOT serve at the expense of the core:**
- Casual player who wants to dip into "any" UGC world (this would be the Roblox model — wrong audience, wrong shape)
- Existing tabletop-DM-but-not-in-product (would need to import; out of scope for v1)
- Asset-creator (mapmaker, portrait artist) — the platform already has its own pipeline; not the wedge

---

## 3. Steelman FOR

1. **The authoring stack already exists in this repo.** Worlds are YAML-on-disk; the content team already authors them; the AI tooling for legends/NPCs/factions/POIs/music/voice/maps is real and shipping. The lift is *exposing* the stack, not building it. SideQuest could move into this faster than any competitor could clone it.
2. **AI-assisted worldbuilding is qualitatively new.** Worldbuilders today (World Anvil, Worldspinner, Inkarnate) sell tooling to humans who do the heavy lifting. SideQuest's tooling is *AI as co-author* — describe what you want, the system materializes it. That collapses the time-to-playable from months to evenings. A forever-DM can have a playable world by Friday night.
3. **The play layer is the moat.** Foundry and Roll20 sell you a virtual tabletop and let you find your own players and your own DM. SideQuest provides both the tooling *and* the GM. Nobody else gives a forever-DM a way to build a world AND have it played *without them having to run it themselves.* This is the single thing Keith built SideQuest to solve. That moat is real.
4. **Persona-product fit is exact.** "People like me" is the persona. The persona is already in the product. The persona is already authoring. We are not guessing at user behavior — we are looking at it.
5. **Viral seed shape matches observed evidence.** Sebastien's 141-turn / 5-hour after-hours session with a friend (2026-05-17) is the *exact* dynamic this product would lean on — friend-of-a-player viral acquisition. Memory note [[project_monetization_signal_141_turns]] anchors this. A world that hits 5 playgroups by word-of-mouth is the proof point; a partner deal lets the creator share in that.
6. **Creator partner program (vs. open marketplace) avoids the worst UGC pathologies.** Discretionary deals → no Sybil resistance crisis, no algorithmic fairness debate, no rev-share law-of-large-numbers. The platform picks the partners it wants to back. Simpler legally, simpler reputationally, simpler financially.

## 4. Steelman AGAINST

1. **Worldbuilding tooling has a long history of niche outcomes.** World Anvil, Worldspinner, Inkarnate, Wonderdraft — all real, all small businesses, none became platforms. The audience that loves the craft is small and price-insensitive but also slow-growing. The persona that buys these tools is *exactly* Keith — and Keith is rare.
2. **Forever-DM ≠ forever-builder.** Many DMs *run* games but don't enjoy *world authoring*. The Venn overlap of "wants to play in SideQuest" ∩ "wants to author worlds" is unknown and might be smaller than the persona statement implies. Sebastien wants to play — he's not signalling interest in authoring. The household isn't even playing yet.
3. **Cost mechanics may not work even without the free playgroup tier.** Even paying players, every narration is a token bill. A world with 50 cumulative players burns 50× more credits than a single playgroup. The platform must price *play* high enough to fund *narration*. If pricing must rise to cover hits, the wedge against casual competitors widens unfavorably.
4. **Quality variance is the actual product risk.** A new user landing on the platform may pick a UGC world and have a mediocre first session — fault attributed to SideQuest, not the creator. Curation, surfacing, and "official vs. community" labeling become load-bearing UX problems. (See ADR-079 genre-theme system for how official packs assert visual identity — what does that look like for a UGC world?)
5. **The creator-partner-program is real work and a separate business.** Reviewing creators, structuring deals, managing IP/licensing, handling tax (royalties = 1099/W-9/W-8BEN), arbitrating disputes — none of this is engineering, all of it is operations that the team doesn't have today.
6. **AI-co-authoring quality is uneven on the depth axis.** AI is good at breadth (generate 30 NPCs, populate a city) and weak at depth (a 30-year intrigue with eight named agendas that all cohere). The forever-DM persona is precisely the one who notices the depth gap. A worldbuilding tool that hits a wall at intermediate depth will frustrate Keith — and Keith *is* the persona.
7. **Competes with our own polished packs.** A new user can pick a polished pack (caverns_and_claudes, tea_and_murder) or a creator's first-time effort. Why would they pick the latter? "Creator partner" worlds need a quality signal that distinguishes them from "official, polished" worlds.
8. **N=1 evidence base.** Keith is one person. Sebastien's 141-turn session is one data point. Real validation = *another forever-DM, not in Keith's family, builds a world and runs it.* That has not happened yet. Until it does, this remains an inferred opportunity.

---

## 5. Hidden Assumptions — surface and decide

| # | Assumption | Decision needed before build |
|---|---|---|
| H1 | The unit of authorship is **a world** (not a genre, not a scenario, not a campaign). | Need explicit grain. Worlds layer onto genres per ADR-003. Can creators add genres? Add worlds within official genres? Both? |
| H2 | AI-assisted authoring is the killer feature, not from-scratch tooling. | If the wedge is "build a world in an evening with AI help," tooling must lean *all the way* into the AI partner UX — not a wiki with an AI tab. |
| H3 | Creators pay for tooling; players pay for play. | Is creation free (cost absorbed as acquisition) or paid (sub or per-world fee)? Different funnel shapes. |
| H4 | The platform owns hosting and narration; the creator owns the world content. | IP terms must be explicit. Creator can leave with their YAML? Platform can host without creator? Both? |
| H5 | "Proven author" = discretionary. | Or is there a transparent ladder (e.g., 100 unique playgroups = sign)? Discretionary is simpler legally but riskier reputationally. |
| H6 | Royalty/deal is paid in cash. | Could be platform credits, reduced fees, free Opus minutes, status badges, or cash. Each has different tax + retention shape. |
| H7 | The narration cost is mostly token cost, and 60-1 (cache-write fix) is sufficient to make unit econ work. | Need the cost-after-60-1 number against an assumed price per session to know if any of this is solvent at the player layer. **This is the single most decision-critical unknown.** |
| H8 | Creators want their worlds played by strangers (not just their friends). | The original framing implied playgroup-only. If creators want privacy, the "hit" signal is invisible and the partner program has nothing to react to. |
| H9 | A creator's playgroup will pay to play in their friend's world. | Versus expecting comp because "I know the author." The 2026-05-22 clarification rules out platform comp, but creator-comp ("the author gives me a code") is a different question. |
| H10 | Content moderation can be handled by the creator partner program (small N, hand-curated). | This is true *for partners*. Pre-partner authoring with AI tooling = potential for offensive worlds in the system. Where's the gate? |

---

## 6. Where this connects to existing project context

| Connection | What it tells us |
|---|---|
| **ADR-003 Genre Pack Architecture** | Genres define mechanics, worlds define flavor. UGC at the *world* layer is much smaller surface than at the *genre* layer. Likely v1 = worlds only. |
| **ADR-059 Monster Manual + ADR-087 Post-Port Restoration** | Procedural world-grounding (weather, NPCs, schedules, economy) is being built as platform infrastructure — exactly what a creator would want for "I designed a city, populate it." This is the substrate the authoring tool sits on. |
| **ADR-101 Anthropic SDK + 60-1 cache-write fix** | Direct cost lever. Unit economics for UGC depend on this work landing well. Defer the creator-economy build until cost is understood. |
| **Memory: 141-turn after-hours session [[project_monetization_signal_141_turns]]** | The acquisition shape this PRD assumes (friend-of-a-friend viral). The existence proof, narrow as it is. |
| **Memory: Durable retention [[feedback_durable_retention]]** | Worlds are years-not-weeks artifacts. The creator's world is part of *their* legacy — design retention/portability accordingly. |
| **Memory: GM panel is for Keith [[project_gm_panel_audience]]** | The authoring/observability tools the platform builds for itself (GM panel, OTEL, sm-world-builder, sq-audit, sq-wire-it, sq-playtest) are exactly the toolkit a creator would want. The creator UX is largely the *dev UX* with sharper edges. |
| **Memory: World axes don't normalize [[feedback_world_axes_dont_normalize]]** | Worlds have their own tonal vocabulary. A creator authoring a world must control axes, not just NPCs. UI cannot assume a canonical axis set. |
| **CLAUDE.md "Who This Is For"** | Persona section already defines Keith as the load-bearing user. This PRD is the commercial extension of that. |

---

## 7. What this is NOT

- Not a Roblox-style UGC marketplace for the general public.
- Not a free-to-play model with creator comp tiers (clarification 2 killed that).
- Not an asset marketplace (portraits, maps, music). Those exist in our own pipeline and aren't the wedge.
- Not a virtual tabletop. SideQuest is the GM; the play layer differs fundamentally from Foundry/Roll20.
- Not a tool for porting existing tabletop worlds at scale (separate problem, harder, lower-leverage at this stage).
- Not a v1 feature. This is a *strategic direction*, not a sprint.

---

## 8. Recommended next discovery moves

Before this turns into stories, three things should happen — in order:

1. **Resolve H7 (cost economics).** Land 60-1 (cache-write fix) → measure cost per session on the live tea_and_murder playtest → model unit economics at 1, 5, 20, 100 cumulative playgroups per world. If the math doesn't work at the player layer, the creator-partner program is moot. *Cost: existing story, already in backlog.*
2. **Persona validation: find a second forever-DM.** Identify one person outside Keith's household who is a forever-DM and would build a world in SideQuest if given access to the tooling. Talk to them. The N=1 problem (§4.8) is the single biggest qualitative risk. *Cost: 1-2 interviews, no engineering.*
3. **Resolve H1 (grain of authorship).** Is the unit a world, a scenario, a genre, a campaign arc? This decision shapes every downstream concern (pricing, IP, partner program, UX). Should be an architect-led design doc, possibly an ADR. *Cost: 1-week discovery, no engineering yet.*

After those three, PM can prioritize and Architect can scope. Until then, this brief is the artifact.

---

## 9. Resolved: customer = DM, not player

Original §9 question (authoring-first vs partner-program-first) was dissolved by the 2026-05-22 mid-discovery reframe in §1.1. Authoring-first is the only coherent answer once you accept that the DM is the customer. The partner program is a downstream monetization layer for hits, not an independent strategic axis.

**What this changes for the next agents in this chain:**

- **PM (prioritization)** should evaluate every story in the backlog against the question *"does this serve the DM-as-customer?"* — not just *"does this serve the player?"* Stories that polish the GM panel, the world authoring wizard, the OTEL surface, the dev-tool ergonomics, the scenario fixtures, the conlang corpus tooling — those go up in priority because they now have a commercial line to them, not just a developer-productivity line.
- **Architect** should treat the existing authoring stack (sq-world-builder, sq-poi, sq-music, sq-audit, sq-wire-it, conlang, GM panel, OTEL dashboard) as **a v0 of the customer-facing product surface**, not as internal-only tooling. An ADR explicitly mapping internal tools → customer-facing equivalents would be useful: what stays Keith-only, what gets graduation to first-party UI, what gets cleaner ergonomics, what needs multi-tenant safety.
- **Whoever runs marketing/positioning discovery** should target DM communities (World Anvil, r/DnDBehindTheScreen, OSR blogs, the Tarn-Adams adjacency), not player communities.
- **The "Who This Is For" section in CLAUDE.md** should be updated to distinguish customer (the DM-builder) from consumer (the playgroup served by that DM). Both still matter, but for different reasons and at different revenue altitudes.

## 10. Derivative Works — multi-level royalty splits

**Source:** Keith, 2026-05-22 mid-discovery
> "I want to do a multi level thing where derivative works of their originals split royalties."

This adds a structural layer to the creator partner program: creators can build *on top of* other creators, and the resulting works pay royalties up the chain.

### 10.1 Why this is structurally interesting

This is the commercial articulation of three SideQuest principles that have so far lived only in design philosophy:

- **MUSH principle / "Yes, And":** SOUL.md says the best worlds are built collaboratively. Today that's intra-session (a player canonizes a suspension pod and the world grows). Multi-level derivative royalty extends collaborative authorship from *one table* to *the platform*, and makes it a cash flow.
- **Diamonds and Coal:** A minor detail becomes a diamond when players engage with it. Derivative royalty extends that *across creators* — a minor NPC in one world becomes a load-bearing recurring character in someone else's. The original author gets paid for having seeded a diamond.
- **"Crunch in the genre, flavor in the world" (ADR-003):** Derivation at genre level propagates new mechanics across *all* worlds in that genre. Derivation at world level propagates flavor only within one. These have **very different royalty implications.** A new mechanic by creator A used in creator B's, C's, D's worlds yields multiplicatively wider royalty obligation than a forked map. The grain matters, again.

### 10.2 The royalty model — **DECIDED 2026-05-22**

**Royalty mechanic: single-hop only.** Each parent collects from their immediate child fork. Royalties do not stack across multiple levels. A grandparent does not collect from a grandchild.

```
Original A
  └─ derived B   (B pays A on B's revenue)
       └─ derived C   (C pays B; C pays NOTHING to A)
            └─ derived D   (D pays C; D pays NOTHING to A or B)
```

This is computationally trivial, requires no cap-table negotiation, and avoids the "share of nothing at depth 6" pathology that geometric-decay schemes hit. It is a deliberate trade-off of **attribution depth for system simplicity** — a 4th-generation fork pays nothing to its great-grandparent. The platform is accepting that loss of upstream incentive in exchange for a model creators can understand without a calculator.

Three classes of IP ownership layer on top of the single-hop mechanic:

#### Class 1 — Keith-authored worlds (root IP)
*Worlds Keith built using SideQuest's existing tooling: glenross, beneath_sunden, coyote_star, tea_and_murder, caverns_and_claudes, road_warrior, etc.*

- A creator forks Keith's world → creator pays Keith on that fork's revenue (single hop).
- A fork-of-fork pays its direct parent (Class 1 derivative author), **not Keith.** Keith earns from level-1 derivatives only.
- Keith is also the house, so platform-level fees on play apply on top of any royalty. (See open question Q-A below.)

#### Class 2 — Creator-built worlds in Keith's genres (most common case)
*A creator authors an original world using one of Keith's genre packs (e.g., a new world in the tea_and_murder genre).*

- **Genres are free substrate. Keith does not extract royalty for genre use.** This is structurally important — it removes friction from the most common authoring path and is consistent with treating SideQuest's genre packs as the rule-book layer (ADR-003) rather than monetizable IP.
- The creator owns their world. Forks of the creator's world pay royalty back to the creator.
- Fork-of-fork pays its direct parent (the level-1 forker), not the original creator. Same single-hop mechanic, applied per link.
- Platform-level fees on play still apply (platform funds itself).

#### Class 3 — Signed partner contributors (whole genre packs, code + mechanics)
*Partners who can deliver at the level Keith does: complete new genre packs including code and mechanics, not just YAML flavor. Treated "same as if Keith did it" — peer-tier authorship.*

- These are **signed partners**, not anyone who uploads. Discretionary deal, platform-side decision.
- Keith takes a **house cut** on partner pack revenue (publisher fee for distribution).
- The partner is "Class 1" for their own pack: forks of partner-authored worlds pay back to the partner with single-hop royalty.
- Worlds built in the partner's genre (the equivalent of Class 2 for the partner's IP) follow the same mechanic: genre is free substrate, creators own their worlds, single-hop royalty to direct parent.
- "Code AND mechanics" implies the partner contributes engine-level work — not just YAML. **This is a much higher-trust relationship than world authoring.** Has security, code quality, and review implications. See Q-D below.

### 10.2a What the three-class model assumes

| | Class 1 (Keith's worlds) | Class 2 (worlds in Keith's genres) | Class 3 (signed partner pack) |
|---|---|---|---|
| **IP root** | Keith | Creator | Partner |
| **House cut on revenue** | (Keith = house) | Platform fee on play | Yes — Keith collects publisher cut |
| **Genre is substrate, free?** | n/a (Keith owns) | Yes (Keith's genre) | Yes (partner's genre) |
| **Royalty depth** | Single-hop | Single-hop per link | Single-hop |
| **Trust level** | Highest (self) | Medium (creator) | Highest (signed) |
| **Onboarding** | Already done | Open / self-serve | Signed contract |
| **Mechanical surface contributed** | World only | World only | Genre + code + mechanics |

### 10.3 What "derivative" must mean to make this work

Derivative-royalty depends on the system *knowing* derivation occurred. Three viable detection models, in decreasing order of cleanness:

1. **Fork-as-explicit-operation.** A creator clicks "fork this world" and the system records the lineage. Clean, gameable only by *not* forking and re-authoring from scratch.
2. **Asset-import telemetry.** A creator imports an NPC, faction, scenario, or trope from another creator's work. System records the import. Clean for tracked assets, opaque for re-implemented ones.
3. **AI-similarity heuristic.** System detects textual/structural overlap between worlds. *Bad idea.* Two creators independently asking Claude for "a fishing village with a smuggling problem" can produce textually similar output without either knowing the other exists. AI co-authoring makes similarity a weak provenance signal. Drop this option.

**Recommendation embedded in the discovery:** detection is fork-explicit + asset-explicit *only.* If you didn't fork or import via the platform, no royalty owed even if your world coincidentally reads like someone else's. This is the only sane choice, but it has to be stated.

### 10.4 Hidden assumptions — decisions and open items

**Resolved 2026-05-22:**

| # | Original assumption | Resolution |
|---|---|---|
| ~~H12~~ | Royalty curve shape | **DECIDED: single-hop only.** Each parent collects from immediate child only. No stacking, no decay, no depth cap. |
| ~~H15~~ | Platform-pack treatment | **DECIDED: Keith's packs are Class 1 (root IP), forkable.** First-level forks pay Keith. Sub-derivations do not. Genres themselves are free substrate for Class 2 / Class 3 world authoring (no royalty for using the genre). |
| ~~H20~~ | Derivation chains persist | **DECIDED implicitly:** single-hop royalty requires permanent parent→child lineage tracking to enforce. Authors cannot delete their lineage. |

**Still open (renumbered from 10-2026 BA review):**

| # | Assumption | Decision needed |
|---|---|---|
| H11 | Forking is at **world grain**, not asset grain. | Sharpens H1. Class 3 (partner-contributed genre packs) is the only mechanism for genre-grain derivation, and it's gated by signed-partner status. Asset-grain forking (taking one NPC from a world) is out of v1 per H16. |
| H13 | Creators can opt out of being forked. | Default-allow with opt-in restrictions (CC-BY-SA shape) vs. default-deny. Single-hop royalty is simple enough that default-allow seems right — but some creators will insist on no-forks. Needs explicit creator-control. |
| H14 | Royalty terms are immutable per-fork, set at fork time. | If a creator changes their default terms later, existing forks stay on the old terms. Cannot retroactively re-tax. |
| H16 | Asset-level derivation (importing one NPC from another world) deferred indefinitely. | World-grain only for v1. |
| H17 | Players who "Yes, And" content into a world do not earn derivative royalty. | Must be in creator ToS. Creators may credit/comp contributing players at discretion, but no automatic split. |
| H18 | Sale/transfer of a creator account redirects downstream royalties to the new owner. | Or sticks with the original author? |
| H19 | "No-derivative" worlds still permit ordinary play. | Opt-out of derivation is separable from opt-out of being playable. |

**Resolved 2026-05-22 (continued):**

| # | Question | Resolution |
|---|---|---|
| ~~Q-A~~ | Per-turn play fee separate from royalty? | **DECIDED: yes. Per-turn rate is charged on play in every class. Genre use is free; *playing* is not.** Creators building in Keith's genres (Class 2) own their worlds and owe no genre royalty, but their playgroups still pay the platform's per-turn cost-recovery fee. |

**New design decision 2026-05-22 — Royalty-credit-against-own-token-cost (RCATC):**

> Royalty payments owed to a DM are FIRST applied as credit against that DM's own playgroup token usage. Only the surplus is disbursed as cash.

This is structurally important enough to call out as a first-class mechanic, not an accounting footnote. It resolves the tension between the original framing ("if your world is popular, your playgroup plays free") and the platform-can't-absorb-cost clarification, by routing the comp through the *derivative creators' royalty payments* instead of platform absorption.

| Property | Effect |
|---|---|
| Source of comp | The fork-authors' royalty obligations, netted against the original's own token bill. Platform is the netting agent, not the payer. |
| Outcome at high royalty income | DM plays free, plus cash payout for surplus. Identical to the original "free for your playgroup" intuition. |
| Outcome at mid royalty income | DM gets a partial discount; pays the difference. Fair, predictable, no surprise bills. |
| Outcome at low/no royalty income | DM pays normal per-turn rate, same as any non-creator user. No penalty for being a creator. |
| Effect on cash payouts | Minimized. Royalty income gets consumed by token bills before becoming a 1099/tax event. Dramatically reduces payout volume and tax-reporting burden. |
| Effect on retention | Direct visible feedback loop: invoice shows credit applied. Successful creators see their cost go down as traction grows. |
| Effect on platform margins | Platform still collects per-turn revenue from the derivative-creator's playgroup; that revenue funds the credit being applied to the original creator. Net cash flow is balanced inside the platform. |

**Implementation hook:** RCATC requires the billing system to know two things about every account — (1) cumulative per-turn cost incurred this billing period, and (2) cumulative royalty income earned this billing period — and to compute the net before disbursing. This is normal SaaS billing territory, not exotic. Worth flagging as a billing-system requirement, not a creator-tool requirement.

**Scope boundary — RCATC covers PLAY ONLY, not WORLDGEN.** Keith, 2026-05-22:
> "What we can't comp is WORLDGEN as that will be extremely computationally expensive."

World generation (LLM passes for legends/NPCs/factions/scenarios, Flux/Z-Image asset generation, ACE-Step music, conlang corpus runs, POI rendering, etc.) is a categorically different cost shape from play: bursty, capital-expenditure, GPU-heavy, one-time-per-asset. Letting royalty income offset worldgen would create a perverse incentive — successful creators would churn endless worldgen on the platform's dime because their royalty pool covers it. Hard separation:

| Cost stream | Class 1 (Keith) | Class 2 (self-serve creator) | Class 3 (trusted partner) |
|---|---|---|---|
| **Per-turn play** | n/a (platform-internal) | Charged. RCATC applies — royalty income credits against play bill. | Charged. RCATC applies. |
| **Worldgen** | Comped (Keith is platform) | **Out-of-pocket.** Per-asset or per-credit-pack pricing. Not covered by RCATC. | **Comped (trusted-dev perk).** |

**Trusted-dev worldgen comp** (Keith, 2026-05-22: *"we comp that for the trusted devs only"*) makes the Class 3 signed-partner relationship materially valuable beyond the publisher-deal structure. The partner gets free GPU/asset generation — the equivalent of a record label giving a signed artist unlimited studio time. This is a real recruitment lever for high-value contributors and worth treating as a first-class benefit of partnership, not a footnote in the contract.

The two-tier creator economy this produces is clean:

- **Class 2 — self-serve creators (open).** Anyone can sign up and build a world. They pay-as-they-go for worldgen, and RCATC covers their play costs if their world catches on. Open funnel; the platform earns from both their worldgen spend and their playgroup's per-turn fees. Quality varies — most of the discovery surface should *not* be these creators by default.
- **Class 3 — signed partner contributors (curated).** Hand-picked dev-tier authors who deliver complete genre packs (code + mechanics + content). Comped worldgen, comped play (RCATC), plus publisher-cut on their pack's downstream revenue. Few in number; the discovery surface *can* default to these.

This separation enforces intentional creator spend on worldgen for the open tier (you choose what to generate, you pay for it) while preserving the elegance of self-funded play (you stop paying to *run* your world once it catches on, but you never stop paying to *build* it — unless you're a trusted partner, in which case you don't pay for either). It also keeps platform unit economics clean — GPU bursts have to be paid for at the point of consumption for the open tier; the platform consciously absorbs trusted-dev bursts as a curated investment.

Surplus royalty (royalty income exceeding play-cost in a billing period) pays out as cash, **not** as a worldgen credit for the Class 2 self-serve tier. Letting creators opt to "convert surplus into worldgen credits" is a possible later UX choice but adds accounting complexity for marginal benefit; out of scope for v1.

| # | Question | Decision needed |
|---|---|---|
| Q-B | What does the **house cut** on Class 3 partner packs look like? | Industry comparables: music labels 50-80%, Steam 30%, Apple 30%, Spotify ~30-40%. The platform/partner split shape will determine partner deal attractiveness. Not BA's call — flagging that this number is materially load-bearing for whether partner deals exist at all. |
| Q-C | Can a Class 3 partner pack inherit mechanics from Keith's existing packs (e.g., "based on tea_and_murder confrontation engine")? | The honest sub-derivation question. If partner X's new genre re-uses Keith's combat mechanics, is partner X's pack subject to royalty back to Keith on mechanic-level reuse? This is the *only* form of multi-level inheritance the single-hop rule is silent on, because it operates at the mechanics layer, not the fork-tree layer. Best handled at contract time per partner, not by automated split. |
| Q-D | Class 3 partners contribute **code AND mechanics** — what does that imply operationally? | Engine-level commits/PRs require security review, code-quality gating, ADR-fit, regression testing. Are partners working in the OQ repo? A fork? A plugin layer? This is an engineering question with substantial implications. Architect/DevOps territory. |
| Q-E | Who is "the platform" if Keith is also the Class 1 root? | When derivative royalty flows back to Keith's worlds, are those payouts going to Keith-the-creator (taxable as creator income) or Keith-the-platform (corporate revenue)? Boring but real. Probably solved by the corporate structure once the platform incorporates. |
| Q-F | What happens to cross-class derivation chains? | A creator builds world W in Keith's `tea_and_murder` (Class 2). Partner X (Class 3) creates a new genre Y. Another creator builds world W' that explicitly forks W's *plot* into genre Y (different mechanics, similar story). Is W' a derivative of W? Probably yes, since the fork operation must be explicit. Edge case worth nailing. |

### 10.4a Edge cases worth recording

- **Mechanic-level inheritance is unhandled.** The single-hop rule operates on world forks. If partner X's whole new genre is mechanically derivative of Keith's, the system has no mechanism to detect or split. This is the implicit cost of the rule's simplicity — and Class 3 is signed deal anyway, so contract terms can handle it case by case.
- **The deeper the tree, the cheaper the input.** A 4th-generation fork inherits all the upstream creative work but pays only its direct parent. Some creators may resent being "great-grandparented out" of the chain. The brief notes this is a *deliberate* trade-off — simplicity over attribution depth.
- **Class 2 is the most common path AND the lowest creator-incentive root.** Creators building in Keith's genres own their world fully and owe nothing to Keith for genre use. This is *generous*. It assumes the volume of Class 2 worlds drives platform play-fee revenue, which is where Keith earns instead of royalty. **Unit economics on Class 2 play-fees must be solid (Q-A) or this generosity is unsustainable.**

### 10.5 Why this hardens H1 (grain of authorship)

The original H1 asked whether the unit of authorship is a world, scenario, genre, or campaign. Without derivation, that question is mainly about UX and storage. With derivation, **the grain *is* the fork primitive.** Whatever you can fork is what royalties flow on. Whatever you can't fork can be copied freely without compensation.

A consequence: **the grain decision is now load-bearing for the creator economy, not just for the authoring UX.** Architect ADR is now a higher-priority deliverable than it was an hour ago.

### 10.6 Why this is structurally aligned with SideQuest

A small but real consideration: SideQuest *already separates content from runtime*. Genre packs are YAML on disk in `sidequest-content/`. Worlds are subdirectories. NPCs, factions, legends, scenarios, conlang corpora, audio, image assets — all are addressable, versionable, forkable artifacts at well-defined paths. The substrate for explicit fork-as-operation **already exists in the file layout.** This is rare in software-mediated creator economies (most platforms have to retrofit content addressability onto a database; SideQuest has it natively in the file system). That is a structural advantage and worth noting.

### 10.7 Closest precedents — and what we'd be doing differently

| System | Pattern | What's similar | What's different |
|---|---|---|---|
| **OGL (Open Game License)** | Tabletop content can be freely reused under license terms | Derivative tabletop content is the precedent | OGL has *no* royalty back to the original. SideQuest's model is "OGL but with cash flow." |
| **Creative Commons CC-BY-SA** | Share-alike with attribution | Default-allow-with-restrictions shape | CC has no payout layer. SideQuest's is monetary. |
| **Music sampling royalty splits** | Mechanical/publishing rights split between sampler and sample-owner | Direct precedent for "derivative pays parent" | Music is contractual per-license; SideQuest would be automatic per-fork. |
| **Scratch (MIT Media Lab)** | Remix tree visible per project | Visible derivation lineage as a feature | Scratch is non-commercial. SideQuest's is the commercial version. |
| **NFT royalty chains** | On-chain royalty splits to original minter | Direct mechanical analog of multi-level split | NFT royalties broke in practice (marketplaces stopped enforcing them). SideQuest enforces internally because the platform *is* the marketplace. |
| **AO3 fanwork "Related Works"** | Lineage declared by author | Declarative provenance | AO3 has no royalty; declared not enforced |
| **Bandcamp / Splice samples** | Pre-cleared sample royalty regime | Closest commercial analog | Pre-licensed pool; SideQuest's is per-creator |

The closest existing system is probably **NFT royalty chains but enforced because the platform is the only seller** — which is a much better position than NFTs ended up in. This is a real structural advantage of running on-platform.

## 11. Followups still open

- H1 (grain of authorship — world, scenario, genre, campaign?) — still needs an ADR.
- H7 (cost-after-60-1) — still gating all unit economics.
- H8/H9 (creator-comp vs platform-comp; do strangers play UGC worlds at all?) — still need answers.
- N=1 persona validation — find a second forever-DM, not in Keith's household, who would author. Still the largest qualitative risk.
- CLAUDE.md "Who This Is For" rewrite — small surgical change, but load-bearing for orientation of future agents.

---

## 12. Competitive Landscape & Differentiation

**Source:** BA competitive scan, 2026-05-25 (/pf-ba session, Keith). Triggered by Keith's hypothesis that SideQuest's effort went disproportionately into *flexibility*. The scan tested that hypothesis against the live AI-DM field and forced a reframe.

### 12.1 The competitive set

| Tool | Input model | Mechanical backing | Rules system | Multiplayer | Creator content | Creator $$ |
|---|---|---|---|---|---|---|
| **AI Dungeon** | Freeform NL | None ("no dice, no sheets, no skill checks") | None | Yes (shared session) | Scenario library, story cards | No |
| **Voyage** | Freeform NL | Proprietary "World Engine" | Non-traditional | Yes | Community worlds | No |
| **AI Realm** | Freeform NL | D&D 5e SRD, character sheets | D&D 5e | Up to 4 | NPC cards | No |
| **Friends & Fables** | Freeform NL + tactical battlemap | Structured DB state, rules enforcement | D&D 5e (locked) | Up to 6 (Discord) | "Thousands" of player worlds, generators, map editor, sharing | **No** |
| **RoleForge** | Freeform NL + real dice | Dice-resolved | Multi-system | Roadmap (solo-first) | None | No |
| **SideQuest** | Freeform NL | Genre-pack mechanics + OTEL-verified | **Swappable per genre pack (not 5e-locked)** | Sealed simultaneous rounds + asymmetric info | World + **genre/mechanics-layer** authoring | **Single-hop royalty / RCATC (designed)** |

### 12.2 The reframe: flexibility is table stakes, not a moat

The hypothesis going in was "we win on flexibility." The scan refuted it as a *headline* claim: **every serious competitor already accepts freeform natural-language input.** The Zork Problem (SOUL.md's founding wedge — removing the finite verb set) was genuinely novel when AI Dungeon shipped it in 2019; by 2026 the entire field solved it. Nobody gates players behind menus anymore.

What's actually true is that the field forked into a trade-off SideQuest is the only one refusing:

- **Pure-freeform camp (AI Dungeon, Voyage):** maximum flexibility, *no* mechanical backing — hallucinates, no durable consistency, no real resolution.
- **Rules-enforced camp (Friends & Fables, AI Realm, RoleForge):** real mechanics and structured state, but **chained to D&D 5e.**

SideQuest is the only entrant with **open player action AND real mechanical scaffold AND a swappable, non-5e rulebook** (genre packs, ADR-003). The differentiator is the *combination*, never "flexibility" as a standalone axis. Marketing "we're more flexible" loses — AI Dungeon is strictly more freeform. Marketing "flexible *and* mechanically honest *and* genre-agnostic" wins, and the OTEL lie-detector is what makes the "honest" half provable where competitors can only assert it.

### 12.3 Reasons not to lose vs. reasons to win

Keith's instinct surfaced four claimed differentiators. The scan re-tagged them. **Three are "reasons not to lose" — table stakes you must match to stay credible. Two are "reasons to win" — uncontested or architecturally uncopyable.** (Multiplayer appears in both columns because the bare word is table stakes; the *kind* of multiplayer is a reason to win — see 12.4.)

| Claimed differentiator | Verdict | Why |
|---|---|---|
| Better flexibility | ❌ Not a standalone moat | Field-wide table stakes. Reframe as the *combination* (12.2). |
| Better recordkeeping / consistency / long-term | ⚠️ Contested | F&F makes the **identical** pitch ("purpose-built DB… prevents hallucinations… state checks"). Win on *degree + provability*: durable years-not-weeks retention ([[feedback_durable_retention]]), KnownFacts/footnotes coherence (ADR-100), OTEL-verifiable state. Not on existence. |
| Multiplayer (bare) | ⚠️ Table stakes | F&F (6), AI Realm (4), AI Dungeon, Voyage all have it. The *word* loses. |
| **Concurrent + asymmetric multiplayer** | ✅ **Reason to win** | See 12.4. Architecturally uncopyable by chat-bot competitors. |
| **Bring-your-own-content** | ✅ **Reason to win (qualified)** | See 12.5. World-flavor BYOC is crowded; *genre/mechanics-layer* authoring + creator economy is open water. |

### 12.4 Reason to win #1 — Concurrent, asymmetric-information multiplayer

Keith's sharpening: *"players taking turns talking isn't really multiplayer."* Correct, and it splits the category into two axes competitors conflate:

- **Concurrency.** SideQuest uses sealed simultaneous rounds (ADR-036): everyone submits, *then* the world resolves — **in every scene.** Competitors are sequential. F&F's case is now confirmed (Keith, firsthand, 2026-05-25): it only enforces "wait for your turn" **in combat**, via standard 5e initiative order — i.e. one player at a time, the *opposite* of sealed-simultaneous. Two consequences fall out, and both favor SideQuest:
  - **In combat:** F&F = sequential initiative (take turns talking, just ordered). SideQuest = simultaneous submission. Different model.
  - **Out of combat:** F&F *does* batch — it collects player input, heuristically infers "this is a turn," and submits the batch to the narrator. So the models are **somewhat** similar at the batching layer. The decisive difference is the **fairness lock**: F&F's boundary is an inferred signal with **no roster-keyed barrier and no per-player screen-time guard** — nothing structurally prevents one player from dominating the batch and driving every turn. SideQuest's sealed round is a *completion-gated barrier keyed to the seated roster*: resolution blocks until every seated player has submitted, and parity is enforced by a lock, not by hoping a heuristic happened to be fair. This is the difference between "we batch input" and "we guarantee each player a turn." The Alex constraint (no fast-typist monopoly, never rush a slow player) is enforced **structurally** in SideQuest; in F&F it is left to chance.
- **Asymmetric information** — *the architectural moat.* SideQuest can show player A what player B cannot see (ADR-104/105 perception firewall). **A shared-channel/Discord competitor physically cannot do this** — every player reads every message. Per-player private info requires per-player rendering + a server-side perception layer, i.e. you cannot be a chat-room bot. This is written into SOUL.md as the thesis ("Tabletop First, Then Better… asymmetric message passing (private info per player)"): the medium exceeding a human DM, who can only pass clumsy secret notes.

**Latent differentiator — sealed-letter (hidden simultaneous submission).** Players submit without seeing each other's actions until the round resolves. Almost certainly **novel vs. the entire field** — no shared-buffer/Discord competitor can offer it (everyone reads every message). Status, stated precisely so nobody markets it prematurely:
  - **Not live today, but planned — deferred, not rejected.** ADR-036's 2026-05-03 amendment deliberately keeps peer action text *visible* during the wait phase (collaborative visibility; "sealed visibility" is PvP-reserved). So sealed-letter is **not a current capability** and must not be claimed as one until content requiring it ships.
  - **Deferred for a primary-audience preference, not a technical barrier.** Keith's playgroup dislikes PvP-style sealed play; *other DMs' tables want it.* Under this PRD's own reframe (customer = the DM, not Keith-the-player), **those DMs are customers** — this is a capability the primary audience gates but the customer base demands. A clean case of customer ⊋ primary-player.
  - **Sealed was the original behavior; visibility is the *additive* feature.** History (Keith, 2026-05-25): the first implementation was *completely sealed*. Peer-action visibility was added later as an **extra feature** because the co-op playgroup struggled to coordinate team/group actions without it. So sealed-letter is not an unbuilt capability — it is **proven prior behavior currently masked by the additive visibility layer.** PvP mode = turn the extra feature *off*. This is lower-risk than net-new work: the mechanic already ran in production.
  - **It unlocks a genre category, not just a mode.** Hidden simultaneous submission *is* the core mechanic of social-deduction play (Mafia / Werewolf / hidden-traitor). In those games coordination-blindness is the point — the visible-peer co-op model structurally *cannot* host them. Sealed-letter therefore opens an entire genre family the field's shared-buffer competitors cannot serve at all. Frame it as genre-reach (new content surface for creators), not a UI preference.
  - **Net:** a reason-to-win that (a) the field structurally cannot match, (b) already shipped once so it's proven, and (c) re-enables by subtraction. Still *latent* in current default UX — market it only once content that uses it ships, but treat the build cost as near-zero and the genre upside as real.

**Positioning rule:** never market the bare word "multiplayer" (everyone sounds identical). Market "concurrent, asymmetric-information multiplayer" and let the competition's turn-passing read as the budget option.

### 12.5 Reason to win #2 — Genre-layer authoring + creator economy

World-*flavor* BYOC is crowded: F&F advertises "thousands" of player worlds plus generators, map editors, and sharing; Voyage has community worlds; AI Dungeon has a scenario library. SideQuest does **not** win on "users can make worlds." The genuine whitespace, confirmed by the scan:

1. **Authoring at the genre/mechanics layer.** Every rules-enforced competitor is D&D-5e-locked — you can build a *world*, never a new *rulebook*. SideQuest genre packs are complete rule systems. **Nobody else lets a creator ship new mechanics.** This is the answer to §4.7's "competes with our own polished packs" — the external counter to F&F's "thousands of worlds" is *"ours are rulebooks, theirs are reskins,"* which only lands if genre-layer authoring is actually exposed to creators (gated on H1).
2. **Creator monetization.** Searched specifically: the **entire category has zero creator-earnings program.** F&F has world-sharing but no royalty. SideQuest's single-hop royalty / RCATC / Class 1-2-3 model (§10) is in open water — the commercial articulation of the play layer's structural advantage (content is already forkable YAML on disk, §10.6).

### 12.6 The one-line positioning that falls out

> **SideQuest is the only AI Game Master that refuses the freeform-vs-rigorous trade — open player action, real swappable mechanics, concurrent asymmetric-information multiplayer, and the only creator economy in the category.**

Both reasons-to-win share a property that *validates the §1.1 reframe*: they are differences a **forever-DM notices and a casual player doesn't** (private-info play; authoring at the rulebook layer; getting paid for a hit). The moat is not the play experience for casuals (contested) — it is the **creator-economy-on-genre-layer-authoring** plus **table-grade multiplayer**, aimed squarely at the customer the PRD already identified as the DM-builder.

### 12.7 Evidence gaps before any public claim

- **F&F turn-model: confirmed sequential (combat-only "wait for turn"), per Keith firsthand 2026-05-25.** The "only real multiplayer" claim is safe *against F&F*. **AI Realm's model remains inferred** (D&D 5e SRD + 4-player → likely initiative-order, unverified) — confirm before a category-wide claim. Also confirm none of the freeform tools (AI Dungeon, Voyage) quietly added simultaneous submission.
- **F&F creator monetization** read as absent from public marketing as of 2026-05; confirm they haven't launched a quiet royalty/partner program before claiming "only creator economy."
- Scan is a point-in-time snapshot (2026-05-25). Pricing and feature claims drift fast in this category (F&F already raised prices Dec 2025); re-scan before any positioning doc goes to market.

**Sources:** [RoleForge five-tool comparison](https://roleforge.ai/blog/best-ai-game-master-tools-compared/) · [Friends & Fables — how it differs from ChatGPT/AI Dungeon/NovelAI](https://fables.gg/blog/how-is-friends-and-fables-different-from-chatgpt-ai-dungeon-or-novelai) · [Friends & Fables](https://fables.gg/) · [AIDungeonMaster.ai 2026 roundup](https://aidungeonmaster.ai/blog/best-ai-dungeon-masters-2026/) · [StoryRoll platform comparison](https://storyroll.app/blog/best-ai-dungeon-masters-2026)
