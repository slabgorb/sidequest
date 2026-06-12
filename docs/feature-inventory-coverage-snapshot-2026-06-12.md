# Feature-Inventory Coverage Snapshot — 2026-06-12

> **What this is:** a *one-time census* (the "P1" option), not standing machinery.
> It answers one question — **"what is the total feature surface, and how much of
> it can the span-anchored `feature-inventory` even see?"** — and then stops. It is
> a point-in-time photograph; it will go stale and that is fine. If we ever want a
> *continuously enforced* denominator, that is the deferred "full completeness
> engine" (P3), and it should be its own spec, not this doc.
>
> Produced by the PM during the 2026-06-12 feature-inventory audit. Read-only
> enumeration; no code shipped.

---

## Headline

- The `feature-inventory` generator verifies **rows you write**; it has **no denominator**, so any feature nobody listed — span-emitting or not — is invisible.
- Its evidence anchor is **OTEL spans**, which exist in **one repo** (server). Four of five repos emit **zero game spans by construction**.
- **Currently inventoried: 1 of 121 server span namespaces** (`encounter`, via the lone migrated manifest category). The other 120 namespaces, all of UI, all of content, and all of composer are **not in any manifest**.

Effective coverage of the machine-verified inventory today: **~0.8% of the server's spanned surface, 0% of everything else.**

---

## The denominator — feature-bearing units per repo

| Repo | Feature-bearing units (the denominator) | Span coverage | Natural evidence anchor | In a manifest today |
|------|----------------------------------------|---------------|-------------------------|---------------------|
| **server** | **121 span namespaces** (the inventoriable runtime surface) | spans ✅ | `spans` | **1** (`encounter`) |
| **ui** | **124** = 90 components + 12 screens + 22 hooks | **0 — structural** (client emits no server OTEL) | `wiring_tests` (233 exist) | 0 |
| **content** | **12 packs · 22 worlds** | **0** | `draft_world` flag / asset gate | 0 |
| **daemon** | **33 modules** (10 touch watcher/otel via ADR-131 bridge) | partial | spans (partial) + wiring | 0 |
| **composer** | **1 CLI command** (`render`), 12 modules | **0** (standalone, no game spans) | unit/CLI smoke | 0 |

### Server — the 121 span namespaces (the only inventoriable-by-span surface)

`✅` = covered by a manifest. Everything else is **uninventoried**.

```
agent  ahead  apply_world_patch  aside  audio  awn  barrier  bloc
build_protocol_delta  cartography  catch_up  cavern_room  chargen  chart
chase  claude-cli  clock  combat  command_points  compose  compute_delta
confrontation  container  content  continuity  cookbook  course  crisis
cwn  dice  dice_replay  dispatch_engagement  disposition  dogfight  dungeon
encounter ✅  equip  frontier  game  innate_v1  intent_router  interior
inventory  item  journal  jump  lagging  ledger  lobby  location  lore
magic  merchant  mm  monster_manual  movement  mp  music  music_classify_mood
music_evaluate  namegen  narrator  narrator_proactive  npc  npc_merge_patch
npcs  opening  orbital  orchestrator  pacing  pack  pack_declares_no_classes
participant  persistence_delete  persistence_load  persistence_save  pregen
premise  projection  prompt  quest  quest_update  quests  rag
recent_narrative_context_injected  region  relationship  relationships
reminder_fired  reminder_spawned  render  rig  rig_pool  room  scenario
scrapbook  script_tool  seed  server  session  setpiece  shuffle_fallback
sidequest  snapshot  stakes  state_patch  string  swn  sync  table  tool
trope  trope_activate  trope_resolve  trope_tick  turn  turn_manager  world
world_grounding  world_history  wwn
```

> Note: a namespace existing ≠ every span in it fires. A separate audit of the
> `encounter` family (the one covered) found **5 declared-but-never-emitted** spans
> (`encounter.phase_transition`, `encounter.check_resolved`,
> `encounter.saving_throw_resolved`, `encounter.beat_failure_branch`,
> `tool.write.advance_encounter_beat`). The generator would bless any of those as
> `live_wired` — it checks *declaration*, not *emission*. That is a separate finding;
> see the audit thread.

---

## The blind list — what a span-anchored inventory cannot see

1. **All of UI (124 units).** The client emits no server spans, ever. The hand-written inventory's "UI" column was *prose*, never a checkable anchor. To inventory UI you must use its 233 `wiring_tests`, which the verifier already supports but the one manifest barely uses.
2. **All of content (12 packs / 22 worlds).** Features here are packs/worlds, anchored by `draft` flags and asset gates — not spans.
3. **All of composer.** Deterministic PD-audio CLI; no game spans by design.
4. **Most of daemon.** Only ~10/33 modules touch the watcher bridge.
5. **120 of 121 server namespaces.** Spanned and *inventoriable*, but nobody has written manifest rows for them. This is the cheapest, highest-value migration surface — the features are already observable; they just aren't catalogued.

---

## Coverage math

- **Machine-verified feature rows today:** 8 (all in the one `confrontation-engine.yaml` category).
- **Server runtime inventoried:** 1 / 121 namespaces (**0.8%**).
- **Non-server repos inventoried:** 0%.
- **Hand-written prose categories not yet migrated:** ~11 (carry no checkable anchor; silently drift).

---

## PM conclusion

The census answers the question that started this: **we are "talking about" ~258 feature-bearing units across five repos (121 server namespaces + 124 UI + 12 packs + 22 worlds + composer/daemon), of which exactly one server namespace is machine-inventoried.** The span-only approach is *structurally* capped at one repo's runtime slice.

Two follow-ons fall out of this snapshot — **neither is started; both are PM-deferred pending an explicit decision:**

- **P2 (small–medium, candidate):** stop calling this a universal "feature inventory." Right-size the generator as a **span-backed *server-subsystem* inventory**, and migrate the 120 already-spanned server namespaces (cheap — the observability exists). Inventory UI/content/composer by their *native* anchors in separate honest surfaces.
- **P3 (large, deferred):** a continuously-enforced cross-repo denominator + discovery + coverage reports. Real maintenance tax; this is dev/QA tooling, not a player feature, so the bar is high. Do not start without a concrete recurring pain that justifies it.

**Recommendation:** bank this snapshot as the answer, fold P2 into the backlog as a sized story if/when the server inventory is worth completing, and leave P3 parked.
