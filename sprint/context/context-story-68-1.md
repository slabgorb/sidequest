---
parent: context-epic-68.md
workflow: tdd
---

# Story 68-1: Per-genre survivability-pool label reskin — social packs show Composure/Standing/Poise (paired content+server field, extra=forbid)

> Authored by TEA during the RED phase — `sm-setup` created the session file but
> did not emit this context document (the gate's sanctioned `create_context`
> recovery). Grounded in a live codebase audit, not boilerplate.

## Business Context

Epic 68 keeps mechanics legible without breaking genre tone. Playtest-3 surfaced
that the survivability pool is labeled "HP" / "Vitality" everywhere — fine for a
dungeon crawl, tonally wrong for a drawing-room social game. In `tea_and_murder`
(Sonia's love-letter pack) and other social-register packs, what depletes when a
character is cornered is their **Composure / Standing / Poise**, not their hit
points. This is the "Crunch in the Genre, Flavor in the World" principle applied
to a single label: the *mechanic* (an ablative survivability pool, ADR-114) is
shared; the *word* on it is genre flavor. The fix serves the mechanics-first
players (Sebastien, Jade) who want the pool legible in-tone in the **player UI**
— not a dev/OTEL concern.

## Technical Guardrails

**This is a paired content+server field — both halves are mandatory.**

- **Server model (the load-bearing constraint):** `RulesConfig`
  (`sidequest-server/sidequest/genre/models/rules.py:971`) is
  `model_config = {"extra": "forbid"}` (line 974). A content-only YAML change
  would be **rejected at pack load** (No Silent Fallbacks). The new field must be
  declared on `RulesConfig` itself — e.g. `survivability_pool_label: str | None = None`
  near the existing label fields (`race_label`, `class_label`,
  `chargen_field_labels` at lines 995–1007). Optional + None-default so the ~all
  mechanical packs are unaffected.
- **Established label-resolution pattern:** genre labels are resolved
  **server-side** —
  `sidequest/server/dispatch/chargen_summary.py::field_label` resolves
  `chargen_field_labels` / `race_label` / `class_label` to display strings. The
  survivability label should follow the same "resolve to a string, default when
  absent" shape. The natural default is `"HP"`.
- **Survivability VALUES already flow** per-character on
  `PartyMember.current_hp/max_hp` (`sidequest/protocol/models.py`, built in
  `sidequest/server/views.py::build_party_member` ~line 517) → fanned into
  `CharacterSummary.hp/hp_max` in the UI (App.tsx). The **label** is currently
  hardcoded UI-side ("HP"). The open design choice (see session Delivery
  Findings) is the transport for the resolved label: ride the party payload
  (per-member, uniform-but-redundant) vs. a genre/theme payload (genre-level,
  cleaner).
- **The pool itself is implemented** (ADR-114 Part 1, `creature_core.py::HpPool`).
  This story touches only the *label*, never the pool mechanics.
- **OTEL: not required.** Both server and UI `CLAUDE.md` exempt cosmetic label
  changes from the OTEL Observability Principle.

## Scope Boundaries

**In scope:**
- Add `survivability_pool_label` to `RulesConfig` (typed, optional, None default).
- Set the field in social-pack content (`tea_and_murder/rules.yaml`; consider
  pulp_noir-style social packs) to a sanctioned social term.
- Resolve + transport the label to the UI and render it across the
  survivability-pool surfaces (character sheet, HUD, narration-adjacent):
  `HpPipScale`, the `CharacterPanel` HP badge (`EdgeBadge`/`FolioEdgeTicks`),
  `CavernActionPanel`, `TacticalGridRenderer`, `Dashboard/tabs/StateTab`.
- Mechanical packs keep the default "HP" with no content change.

**Out of scope:**
- Any change to the HP/survivability *mechanic* (pool size, ablation, depletion
  win-condition) — label only.
- Reskinning the confrontation **Edge** dual-dial (a distinct metric, not the
  survivability pool).
- The wider Epic 68 work (stale mechanical tokens in ability prose 68-2 *done*;
  aside happy-path 68-3 *done*).

## AC Context

1. **AC1 — Content field:** A genre pack can declare a per-pack survivability-pool
   label in `rules.yaml`. *Test:* real-pack load asserts the field is present.
2. **AC2 — Server accepts it (extra=forbid):** `RulesConfig` declares the field;
   a *typo'd* key still raises (proving the field was added explicitly, not via
   `extra="allow"`). *Tests:* `test_rules_config_accepts_survivability_pool_label`,
   `test_rules_config_still_forbids_unknown_field`.
3. **AC3 — Social packs reskinned:** `tea_and_murder` carries a label in
   {Composure, Standing, Poise} (exact word a content choice; note "Standing" is
   already a social-capital *resource* there, so Composure/Poise reads cleaner).
   *Test:* `test_tea_and_murder_pack_has_social_survivability_label`.
4. **AC4 — UI surfaces the label:** all survivability-pool displays render the
   reskinned label. *Test (primary surface):* `HpPipScale.test.tsx` pins the
   `survivabilityLabel` render + aria contract; remaining four surfaces flagged
   for Dev (session Delivery Findings + a logged partial-coverage deviation).
5. **AC5 — Non-social unaffected:** mechanical packs keep default "HP/Vitality".
   *Tests:* `test_caverns_and_claudes_keeps_default_survivability_label` (server
   → None) and the UI "falls back to 'HP'" guard.
