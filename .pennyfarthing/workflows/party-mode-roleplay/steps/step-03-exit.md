# Step 3: Graceful Exit

<step-meta>
number: 3
name: exit
gate: false
</step-meta>

<purpose>
Conclude the party mode session with in-character farewells, session highlights, and a structured output artifact matching the Quick variant's format (Ideas Generated, Most Promising, Wild Cards, Next Steps).
</purpose>

<instructions>
1. Select 2-3 agents who were most active in the discussion
2. Generate brief, in-character farewells from each — one sentence, reflecting their personality
3. Summarize session highlights (key topics covered, notable insights)
4. Produce structured output in the Party Mode Results format
5. If invoked from a parent workflow, return control to the parent
</instructions>

<output>
## Farewells

```
{emoji} **{Character}**: {Brief farewell in their voice — one sentence.}

{emoji} **{Character}**: {Their goodbye, maybe referencing a highlight.}

{emoji} **{Character}**: {Final thought in character.}
```

## Structured Summary

```markdown

## Farewell Guidelines

- Keep farewells short — one sentence per agent, in character
- Reference something specific from the discussion if possible
- No generic "thanks for the great discussion" filler
- The farewell should sound like that character, not like a facilitator

## Structured Output

The summary artifact is what makes roleplay sessions produce lasting value. Include:

- **Ideas Generated**: Every distinct idea that surfaced, attributed to the character who raised it
- **Most Promising**: The 3 best ideas with brief rationale for why they stand out
- **Wild Cards**: Ideas that seemed crazy but might have merit — don't filter these
- **Key Disagreements**: Where agents diverged. Both perspectives, no resolution forced
- **Next Steps**: Actionable follow-ups using PF agent commands

## Return Protocol

If this workflow was invoked from within a parent workflow:

1. Identify the parent workflow step that invoked party-mode-roleplay
2. Re-read that step file to restore context
3. Resume from where the parent workflow directed the invocation
4. Present any menus the parent workflow requires after sub-workflow completion

Do not continue conversationally — return to parent workflow control flow.

## Failure Modes

- Skipping the structured summary (the whole point of exit)
- Generic farewells that don't reflect character voice
- Not attributing ideas to specific characters
- Forcing consensus on disagreements instead of capturing both sides

## Success Metrics

- In-character farewells that feel authentic
- Structured summary captures the substance of the discussion
- Ideas properly attributed to contributing characters
- Session feels complete, not abruptly terminated
