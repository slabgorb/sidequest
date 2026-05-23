# Context: Story 22-2 — Seed Trope Content for Tea & Murder

**Story ID:** 22-2
**Epic:** 22 (Seed Tropes — Narrative Variety via Schrödinger's Gun)
**Title:** Seed trope content — author 20–30 seeds for tea_and_murder (dogfood pack)
**Points:** 3
**Workflow:** trivial

## What Is This Story?

Write 20–30 seed trope entries in YAML for the `tea_and_murder` dogfood pack. A **seed trope** is a short-arc narrative seed — a deliberately vague event or situation — that is randomly dealt each session and retroactively connected by the narrator to emergent macro-trope escalations. This story is pure content authoring: no code, only YAML.

## Schema Reference

**Pydantic model:** `sidequest-server/sidequest/genre/models/tropes.py:63–82`

```python
class SeedTrope(BaseModel):
    id: str
    name: str
    description: str | None = None
    flavor_tags: list[str] = Field(default_factory=list)
    lifespan_turns: int = 0
    delivery_hints: list[str] = Field(default_factory=list)
    narrative_hint: str = ""
```

**Example (from test_seed_trope_models.py):**

```python
SeedTrope(
    id="sealed-letter",
    name="A Sealed Letter",
    description="A wax-sealed letter addressed to no one.",
    flavor_tags=["mystery", "correspondence"],
    lifespan_turns=8,
    delivery_hints=["an innkeeper hands it over", "found under a door"],
    narrative_hint="Connect to whoever the players suspect.",
)
```

## Tea & Murder Genre Constraints

**Tone:** Cosy Edwardian murder mystery (~1908), BritBox register. Conversational, social, intrigue.

**Design principle:** Social-first, not combat-first. No combat confrontations. Seeds should bias toward:
- Conversational hooks (gossip, confession, interrogation)
- Social tension (propriety violations, scandal, class friction)
- Information asymmetry (hidden secrets, misdirection, red herrings)
- Village social structures (innkeeper, vicar, constable, postmistress, estate workers as delivery vectors)

**Avoid clichéd naming:** Resist overused suffix patterns (Reach, Veil, Spire, Hollow, Drift, Mire, Shroud). Prefer period-authentic village details and social situations.

## Field Guidance

### `id`
- Slug format (lowercase, hyphenated)
- Unique within the pack
- Examples: `sealed-letter`, `missing-portrait`, `anonymous-tip`, `railway-delay`

### `name`
- Human-readable, title-case
- 3–8 words; memorable and thematic
- Examples: "A Sealed Letter", "The Missing Portrait", "An Anonymous Tip"

### `description`
- Brief, evocative, deliberately vague
- 1–2 sentences
- No specifics that constrain narrator interpretation
- Example: "A wax-sealed letter addressed to no one." (not "A letter from Lord Ashworth to the constable")

### `flavor_tags`
- 2–4 thematic keywords
- Reinforce tea_and_murder tone
- Examples: `["mystery", "correspondence"]`, `["intrigue", "propriety", "scandal"]`, `["secrets", "family"]`
- **Suggested tag vocabulary for tea_and_murder:**
  - Social: `propriety`, `scandal`, `gossip`, `reputation`, `intrigue`, `secrets`, `alliance`, `betrayal`
  - Narrative: `mystery`, `correspondence`, `inheritance`, `confession`, `misdirection`, `alibi`
  - Emotional: `suspicion`, `tension`, `trust`, `accusation`, `reconciliation`
  - Setting: `estate`, `village`, `tea-time`, `garden`, `drawing-room`, `marketplace`

### `lifespan_turns`
- Integer: typically 4–10 turns
- Shorter (4–6) for urgent seeds (letters, visitors, immediate news)
- Longer (8–10) for slow-burn seeds (subtle tensions, lingering questions)
- Example: 8 for "A Sealed Letter" (keeps it relevant through a medium-length investigation)

### `delivery_hints`
- List of 2–4 narrative hooks
- How an NPC delivers the seed to the players
- Grounded in tea_and_murder social structures
- Examples:
  - "the innkeeper hands it over with a knowing look"
  - "the postmistress mentions it casually over tea"
  - "the constable pulls you aside after church"
  - "an estate gardener leaves it under your cottage door"

### `narrative_hint`
- 1–2 sentences
- Guidance for the narrator on retroactive connection
- How to weave the seed into evolving tropes
- Examples:
  - "Connect to whoever the players suspect first."
  - "Reference when a character's alibi is questioned."
  - "Reveal the sender's identity only if the players directly ask."

## Target Pack Location

**File:** `sidequest-content/genre_packs/tea_and_murder/seed_tropes.yaml`

Structure:
```yaml
seed_tropes:
  - id: sealed-letter
    name: A Sealed Letter
    description: A wax-sealed letter addressed to no one.
    flavor_tags: [mystery, correspondence]
    lifespan_turns: 8
    delivery_hints:
      - the innkeeper hands it over with a knowing look
      - found under a cottage door
    narrative_hint: Connect to whoever the players suspect.
  
  - id: missing-portrait
    name: The Missing Portrait
    # ... continue ...
```

## Acceptance Criteria

- [ ] 20–30 seeds authored (target: 25)
- [ ] Each seed has all required fields: `id`, `name`, `description`, `flavor_tags`, `lifespan_turns`, `delivery_hints`, `narrative_hint`
- [ ] All fields non-empty (no `null` or empty list defaults)
- [ ] All seeds appropriate for tea_and_murder genre (social-first, conversational hooks)
- [ ] Flavor tags reinforce tone and narrative style
- [ ] Delivery hints grounded in village social structures (innkeeper, vicar, constable, postmistress, etc.)
- [ ] No clichéd or overused naming patterns
- [ ] YAML syntax valid and schema-conformant (validate manually: `pydantic` will reject typos and unknown fields)
- [ ] File created at `sidequest-content/genre_packs/tea_and_murder/seed_tropes.yaml`

## Related Stories

- **22-1 (done):** Seed trope schema + deck engine (server-side)
- **22-3 (backlog):** Seed trope narrator injection (VALLEY-zone context)
- **22-4 (backlog):** OTEL + GM panel visibility

## No Out-of-Scope Work

- Do NOT modify the schema (`sidequest-server/sidequest/genre/models/tropes.py`)
- Do NOT author seeds for other packs (separate stories)
- Do NOT wire the seed-loading into the server (story 22-3)
- Do NOT implement narrator injection or OTEL (stories 22-3, 22-4)

## References

- ADR-018: Trope Engine (macro-escalation system that seeds feed into)
- ADR-009: VALLEY Zone (narrative context injection point for active seeds)
- ADR-022: World Maturity Model (pacing and narrative layering)
- Project memory: `project_victoria_social_first.md` (tea_and_murder social-first design)
- Project memory: `feedback_made_up_names.md` (avoid clichéd naming)
