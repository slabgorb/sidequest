# Step 2: Discussion Orchestration

<step-meta>
number: 2
name: discussion
gate: false
next: step-03-exit
</step-meta>

<purpose>
Orchestrate a sustained multi-round discussion between agents with intelligent selection, natural cross-talk, and authentic in-character responses. This is the core loop — it repeats until the user exits.
</purpose>

<instructions>
1. Analyze each user message for domain and expertise requirements
2. Select 2-3 agents whose roles and personas best match the topic
3. Generate in-character responses using each agent's theme persona (character name, communication style) and role expertise
4. Enable cross-talk — agents reference each other, build on points, respectfully disagree
5. Handle questions appropriately (direct-to-user pauses the round; inter-agent flows naturally)
6. Present `[E] Exit` option after each response round
7. Repeat until user selects Exit or triggers an exit condition
</instructions>

<actions>
- Read: Agent roster built in step 1 (maintained in conversation context)
- Read: Conversation history for context continuity
</actions>

<output>
Each response round follows this format:

```
{emoji} **{Character Name}**: {In-character response reflecting their communication
style, role expertise, and persona. References the topic with domain knowledge.}

{emoji} **{Character Name}**: {Response that may build on, agree with, or challenge
the previous agent's point. Natural cross-talk.}

{emoji} **{Character Name}**: {Third perspective if warranted. Not every round
needs three agents — pick the right number for the topic.}

---
Continue the discussion, or:
[E] Exit Party Mode — end with summary
```
</output>

## Agent Selection

For each user message:

**Relevance analysis:**
- What domains does this touch? (technical, business, process, quality, UX, ops)
- Which agents have primary expertise here?
- Who would offer a valuable contrasting perspective?

**Selection rules:**
- Pick 2-3 agents per round (never all of them — that's noise, not discussion)
- If the user names a specific agent/character, prioritize them + 1-2 complementary agents
- Rotate participation over time so all agents get airtime across rounds
- Don't repeat the same 2-3 agents every round unless the topic demands it

## Character Consistency

Each agent response must:
- Use the agent's theme character name (not the role name)
- Reflect their communication style from the theme persona
- Draw from their role expertise for substance
- Maintain a consistent voice across rounds — the character should feel like one person

## Cross-Talk Patterns

Agents interact naturally:
- **Build:** "As {Character} mentioned, and building on that..."
- **Agree:** "I'm with {Character} on this — and I'd add..."
- **Disagree:** "I see it differently than {Character}. Here's why..."
- **Question:** "{Character}, how would you handle {specific aspect}?"
- **Synthesize:** "Taking {Character}'s point and {Character}'s concern together..."

## Question Handling

**Direct questions to the user:**
When an agent asks the user a specific question:
1. End the response round immediately after the question
2. Highlight: **{Character Name} asks: {question}**
3. Wait for user input before continuing

**Rhetorical questions:**
Agents can think aloud without pausing the round.

**Inter-agent questions:**
Agents can question each other and respond within the same round.

## Exit Detection

Check after each round:
- User selects `[E]` → proceed to step-03-exit.md
- User message contains exit triggers (`*exit`, `goodbye`, `end party mode`, `quit`) → proceed to step-03-exit.md
- Conversation naturally concludes → ask conversationally if they'd like to continue or wrap up

<collaboration-menu>
- **[E] Exit** — End the discussion and produce a structured summary
</collaboration-menu>

<next-step>
When user exits, proceed to step-03-exit.md for farewells and structured summary.
</next-step>

## Moderation

- If discussion becomes circular, have the Orchestrator character summarize and redirect
- If an agent's expertise is being stretched beyond their domain, acknowledge the boundary
- Balance depth with breadth — follow the user's energy
- Keep rounds focused; don't pad with filler perspectives

## Failure Modes

- Generic responses that don't reflect character personality
- Selecting agents that don't match the topic
- Not enabling cross-talk (isolated responses that don't reference each other)
- Continuing after exit trigger without acknowledging it
- Every round using the exact same agent selection

## Success Metrics

- Agents feel like distinct characters with authentic voices
- Cross-talk creates genuine conversation, not serial monologues
- Agent selection matches topic expertise
- User controls the pace and direction
- Exit is always available and respected
