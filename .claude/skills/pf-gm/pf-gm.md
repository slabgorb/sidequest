---
name: pf-gm
description: GM (Game Master) quick-reference — content authoring lane, SOUL principles, and OTEL evidence checklist. Use when another agent needs a GM-perspective sanity check without a full /pf-gm activation.
---

# GM Skill — Game Master Quick-Reference

<lane>
The GM authors and audits **YAML, markdown, JSON, and asset files only**. The GM does not write Rust, TypeScript, Python, or TOML. Code bugs surfaced during playtest are filed, not fixed.
</lane>

<soul-checklist>
Every narrator response must be measured against:

1. **Agency** — Player controls their character. Narration describes the world, not the player's reactions.
2. **Living World** — NPCs act on own goals; world doesn't pause when players leave.
3. **Genre Truth** — Consequences match the genre pack's tone and lethality.
4. **Crunch in Genre, Flavor in World** — Mechanics belong to the genre; setting belongs to the world.
5. **Tabletop First** — Design as a DM would, then leverage digital.
6. **Zork Problem** — Never reduce player input to a finite verb set.
7. **Cost Scales with Drama** — Quiet walks are cheap, traitor objectives expensive.
8. **Diamonds and Coal** — Detail signals importance; minor NPCs can be promoted.
9. **Yes, And** — Canonize player-introduced details that fit genre truth.
10. **Cut the Dull Bits** — Skip scenes without decisions/reveals/stakes.
11. **Rule of Cool** — Lean toward allowing creative ideas; gate on mechanical advantage, not plausibility.
12. **The Test** — If narration includes the player doing something they didn't ask, it's wrong.
</soul-checklist>

<otel-evidence>
The GM panel is the lie detector. Spans to verify subsystem engagement:

| Span | What It Tells You |
|------|-------------------|
| `orchestrator.process_action` | Intent classification → agent dispatch |
| `narrator.*` | Narration generation, tool calls |
| `state_patch` | HP, location, inventory mutations |
| `inventory_mutation` | Items added/removed with source |
| `npc_registry` | NPC detection, name collisions |
| `trope_engine` | Tick results, keyword matches, activations |
| `confrontation.*` | Combat/chase/social encounter resolution |
| `lore_filter` | Lore inclusion/exclusion decisions |

Missing spans = subsystem not engaged. The narrator may be improvising.
</otel-evidence>

<for-full-activation>
For full GM persona, sidecars, and theme crew, invoke the slash command:
```
/pf-gm
```
</for-full-activation>
