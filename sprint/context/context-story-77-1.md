---
parent: context-epic-77.md
workflow: tdd
---

# Story 77-1: Seed-at-creation — quest_anchor + quest_log + active_stakes from PC drive/calling

## Business Context

Every SideQuest session needs a **mechanical campaign spine** — a quest, an
anchor, and current stakes — that exists from turn 1, not just as narrator
improvisation. The wry_whimsy/oz playtest (2026-06-02) is the motivating
failure: it ran 13 turns against a world whose *entire premise is a campaign
spine* — *"the traveler arrives by accident and wants only to go home"* — yet the
turn-13 snapshot showed `quest_log: {}`, `quest_anchors: []`, `active_stakes: ""`.
The player had no objective surface and the engine had no stakes to drive
pacing/escalation (ADR-024 dual-track tension, ADR-025 pacing detection) against.

This is a **mechanical-scaffold failure, not a narration-quality one** — the
fields exist; nothing fills them at session start. It is exactly the "convincing
narration with zero mechanical backing" failure the OTEL Observability Principle
(CLAUDE.md) exists to catch: the GM panel is the lie detector, and a substrate
that emits no spans can't be distinguished from Claude improvising. For
Keith-as-player (a forever-GM who knows what a good DM does), a campaign spine
silently vanishing from state is a tell no human DM would produce.

This story is the **smallest, highest-certainty half** of ADR-137's Option C: at
session init, derive **one** `quest_anchor` + a `quest_log` entry + `active_stakes`
from the PC's drive/calling, so every session starts with a non-empty spine from
turn 1. It directly closes the "empty at turn 0" hole. It is the first story in
the epic's engine-spine sequence (77-1 → 77-2 → 77-3 → 77-4); the in-play
create/evolve affordance (typed `record_quest`/`set_stakes` tools) is 77-2.

> **Numbering caveat (from epic context).** ADR-137 §Implementation Stories was
> written when the design story was 77-1, so its internal table numbers this seed
> story **77-2**. After the design story archived, the implementation stories were
> re-promoted: ADR 77-2 → sprint **77-1** (this story). Read the ADR's "77-2 —
> Seed-at-creation" row as **this** story.

## Technical Guardrails

- **Seed source is the PC's drive/calling, populated at chargen.** Confirmed
  fields: `Character.drive: str = ""` (`sidequest-server/sidequest/game/character.py:117`)
  and `Character.calling_label: str = ""` (`character.py:127`). Both **default to
  empty string**. The CharacterBuilder stamps them from drive/class scene labels
  (`builder.py:2377` `drive=acc.backstory_label or ""`, `:2383`
  `calling_label=acc.class_label or ""`), and the backstory/drive-shaped-scene
  detection is at `builder.py:1246-1264`. **Genres without a drive-shaped scene
  leave `drive` empty** (the `backstory_label` fallback comment lives at
  `builder.py:423`).

- **Add a seed-at-creation hook on the session-init/creation path** in
  `sidequest-server/sidequest/game/session.py`. The snapshot is `GameSnapshot`
  (`session.py:625`); the three target fields already exist on it:
  `quest_anchors: list[str]` (`session.py:736`), `active_stakes: str = ""`
  (`session.py:742`), and `quest_log` (a `dict[str, str]`, written via the existing
  `WorldStatePatch.quest_log` at `session.py` apply path). The seed must populate
  all three from drive/calling at creation time.

- **Empty-drive path degrades LOUDLY — No Silent Fallbacks.** When the PC's
  drive/calling are both empty (the prose-pack case), the seed must NOT silently
  no-op. It must emit the `quest.seeded_at_creation` span carrying a
  **WARNING-severity attribute** flagging the empty seed (ADR-137 OTEL table:
  attributes `quest_id`, `anchor_id`, `source_drive`, `has_stakes`). This is the
  observability tell that the seed ran but had nothing to seed from — visible on
  the GM panel, never a quiet skip.

- **OTEL span: `quest.seeded_at_creation`** (ADR-137 AC-4). This is the *only* span
  this story adds. The other epic spans (`quest.created`, `quest.updated`,
  `quest.anchor.added`, `stakes.set`) belong to 77-2/77-3 and are out of scope.
  Existing span infra to follow: `SPAN_QUEST_UPDATE` and its `SpanRoute` registration
  live at `sidequest-server/sidequest/telemetry/spans/state_patch.py:29-30` — model
  the new span's route registration on that file's pattern. Do **not** rename or
  remove `SPAN_QUEST_UPDATE` here (that's 77-3's `quest.updated` replacement).

- **Do NOT touch the orbital consumer.** `orbital/course.py:125,157` already
  consumes `quest_anchors` as beat/location ids for Hohmann course plotting
  (ADR-130). Promoting `quest_anchors` to a `WorldStatePatch` field with a real
  apply path is story **77-3**; this story writes the seeded anchor directly onto
  the snapshot at creation, it does **not** add the patch field. Leave
  `course.py` unchanged.

- **Bound the cost / drama (SOUL §Cost Scales with Drama).** This is a
  creation-time, one-shot derivation — a single anchor + a single quest entry +
  one stakes string. A quiet town walk must not mint a quest; the seed fires once
  at init, not per turn.

- **Wiring discipline (CLAUDE.md).** This must be wired into the real
  session-creation code path, not left as an isolated helper. The TDD suite needs
  at least one wiring/integration test that drives session init through the real
  creation path and asserts the span fired and the fields populated. Prefer **OTEL
  span assertions** and **fixture-driven behavior tests** over source-text greps
  (the server's "No Source-Text Wiring Tests" rule).

## Scope Boundaries

**In scope:**
- The creation-time seed of `quest_log` + `quest_anchors` + `active_stakes` derived
  from the PC's `drive`/`calling_label` at session init.
- The `quest.seeded_at_creation` OTEL span, including its **WARNING-severity
  attribute** on the empty-seed (no-drive) path, with `SpanRoute` registration in
  the `state_patch.py` span module.
- A wiring test proving the seed runs on the real session-creation path.

**Out of scope:**
- Typed runtime narrator tools `record_quest` / `set_stakes` and their spans
  (`quest.created`/`quest.updated`/`stakes.set`) — **story 77-2**. This is the
  load-bearing fix for prose packs (see Assumptions).
- Promoting `quest_anchors` to a `WorldStatePatch` field + real apply path and
  feeding `orbital/course.py` — **story 77-3**.
- One-mechanism cleanup: retiring the `quest_updates` extraction lane, stripping
  `/quest_log` + `/active_stakes` from `apply_world_patch`, replacing
  `SPAN_QUEST_UPDATE` with `quest.updated` — **story 77-4**.
- The player-facing quest/objective UI panel — **story 77-5** (ui).
- Authoring the wry_whimsy `seed_tropes` deck (the `active_seeds` carve-out,
  ADR-128) — **story 77-6** (content). `active_seeds` is a *content* gap, untouched
  by this engine story.

## AC Context

**AC-1 — No-drive prose-pack behavior is verified, not assumed.**
`Character.drive` defaults to `''` (`builder.py:423` / `character.py:117`) when the
genre has no drive-shaped scene, as in wry_whimsy. The story must verify behavior
*against that case*: seed-at-creation alone does **not** close the gap for such
packs (it has no drive to seed from), so it must not pretend to. A test should
construct a PC whose `drive`/`calling_label` are both empty and assert the seed
takes the loud-degrade path rather than fabricating a quest.
*How a test verifies:* build/inject a no-drive Character, run session init through
the real creation path, assert no fabricated quest content AND assert the
`quest.seeded_at_creation` span fired carrying its WARNING-severity empty-seed
attribute.

**AC-2 — Empty-drive path degrades LOUDLY (No Silent Fallbacks).**
On an empty drive/calling, emit `quest.seeded_at_creation` with a
**WARNING-severity attribute** marking the empty seed; never a silent no-op.
*How a test verifies:* assert the span is emitted with the severity/empty-seed
attribute present, and (mirror) that on the **populated-drive** path the span
fires *without* the warning and the three fields (`quest_log`, `quest_anchors`,
`active_stakes`) are non-empty and derived from the PC's drive/calling. Assert
span attributes match the ADR-137 contract (`quest_id`, `anchor_id`,
`source_drive`, `has_stakes`).

## Assumptions

- **Load-bearing:** Seed-at-creation does **not** close the gap for prose packs
  whose `Character.drive` defaults to `''` (e.g. wry_whimsy/oz, the originating
  failure). With nothing to seed from, this story correctly produces a loud,
  empty-seed span rather than a spine. The actual fix for prose packs is the typed
  `record_quest`/`set_stakes` tools in **77-2** (ADR-137 Option B), which let the
  narrator originate a quest *in play*. This story's job is the turn-0 spine **when
  a drive exists** plus the loud tell **when it doesn't** — not to make prose packs
  whole. Do not "fix" the empty-drive case by inventing a default quest; that would
  be a silent fallback and would mask the content/chargen gap 77-2 is meant to
  cover.
- The three target fields (`quest_log`, `quest_anchors`, `active_stakes`) already
  exist on `GameSnapshot` and need no schema addition for this story — only a
  creation-time write. `WorldStatePatch` is **not** modified here (that's 77-3).
- The span-route registration pattern in `telemetry/spans/state_patch.py` is the
  template for `quest.seeded_at_creation`; the GM panel surfaces routed spans
  without further wiring.
