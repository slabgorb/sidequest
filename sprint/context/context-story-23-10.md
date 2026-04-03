---
parent: context-epic-23.md
workflow: tdd
---

# Story 23-10: Deduplicate SOUL overlap — audit Agency and Genre Truth double-injection

## Business Context

The prompt preview tool (`scripts/preview-prompt.py`) reveals that two concepts are injected twice:

1. **Agency** — `narrator_agency` (Primacy/Guardrail, ~91 tokens) AND SOUL "Agency" (Early/Soul)
2. **Genre Truth / Consequences** — `narrator_consequences` (Primacy/Guardrail, ~69 tokens) AND SOUL "Genre Truth" (Early/Soul)

This wastes ~100+ tokens of prompt budget and creates attention dilution — Claude sees the same
concept at two different attention levels. The PM assessment (23-1) noted this overlap but
deferred resolution.

## Technical Guardrails

- SOUL.md is parsed by `prompt_framework/soul.rs` and filtered per agent via `<agents>` tags
- Orchestrator injects filtered SOUL at Early/Soul zone (orchestrator.rs L268-L280)
- Narrator injects its own guardrails at Primacy/Guardrail zone (narrator.rs build_context())
- The narrator versions are **operationally richer**:
  - `narrator_agency` adds multiplayer puppeting rules (not in SOUL)
  - `narrator_consequences` adds NPC tactical behavior specifics (not in SOUL)
- SOUL versions are **abstract principles** intended for all agents

**Resolution options:**

| Option | Description | Token savings | Risk |
|--------|-------------|---------------|------|
| A. Trim SOUL | Remove Agency + Genre Truth from SOUL narrator filter | ~40 tokens | Other agents lose nothing (agents:all stays) — but narrator SOUL section shrinks |
| B. Trim narrator | Remove narrator_agency + narrator_consequences, enrich SOUL entries | ~160 tokens | SOUL becomes narrator-specific in places, muddies the "universal principles" contract |
| C. Merge into narrator, skip in SOUL | Add `<agents>narrator:skip</agents>` tag concept to SOUL parser | ~100 tokens | New filtering feature needed |
| D. Keep both, accept duplication | No change | 0 tokens | Known waste, but conceptually clean separation |

**Recommended: Option A** — Keep the richer narrator guardrails in Primacy, exclude the abstract
SOUL versions for the narrator agent only. Modify SOUL.md `<agents>` tags on Agency and Genre Truth
from `all` to `ensemble,creature_smith,dialectician,troper,world_builder,resonator` (everyone except narrator).

## Scope Boundaries

**In scope:**
- Audit exact content overlap between narrator guardrails and SOUL principles
- Decide resolution approach (A/B/C/D above)
- Implement the chosen approach
- Verify no SOUL principles are lost for non-narrator agents
- Update `scripts/preview-prompt.py` to reflect changes
- Measure token savings

**Out of scope:**
- Rewriting SOUL.md content (just tag changes)
- Changing any non-narrator agent's SOUL injection
- Adding new SOUL principles

## AC Context

1. Agency concept appears exactly once in narrator prompt (not twice)
2. Genre Truth / Consequences concept appears exactly once in narrator prompt (not twice)
3. Non-narrator agents still receive Agency and Genre Truth from SOUL
4. Total narrator prompt token count reduced by measured amount
5. `scripts/preview-prompt.py` shows deduplicated output
6. OTEL zone_distribution reflects reduced Early/Soul section
