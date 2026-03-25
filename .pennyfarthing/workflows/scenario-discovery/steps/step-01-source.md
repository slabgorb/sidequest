# Step 1: Source Real-World Finding

<step-meta>
step: 1
workflow: scenario-discovery
agent: orchestrator
name: source
gate: true
next: step-02-prepare
</step-meta>

<purpose>
Identify a real-world finding to build a benchmark scenario from. The finding must come
from actual observed behavior -- never invented. This is the primary defense against the
"God lifting rocks" problem (LLMs designing tests they already know how to pass).
</purpose>

<instructions>
1. Ask the user what source type they're working from
2. Based on source type, help them locate and extract the specific finding
3. Capture the finding with enough context to build a scenario
4. Determine the scenario family (detection or divergent)
</instructions>

## Source Types

Present these options to the user:

### Detection Sources (code with seeded/real bugs)
| Source | Where to Find | Example |
|--------|---------------|---------|
| **Lang-review gate** | `{gates_root}/{language}.md` | Rust check #8: `#[derive(Deserialize)]` bypassing validation |
| **Production bug** | Git blame, PR history, incident reports | Race condition found in orc-ax-2 |
| **Orc-ax finding** | Consumer project sessions, reviewer feedback | Silent error swallowing in async handler |
| **SWE-bench issue** | `pennyfarthing/benchmarks/test-cases/swe-bench/` | Real open-source bug reproduction |
| **OWASP/CWE pattern** | OWASP Top 10, CWE database | CWE-89: SQL injection via string formatting |

### Divergent Sources (open-ended decisions)
| Source | Where to Find | Example |
|--------|---------------|---------|
| **Project history** | Sprint sessions, ADRs, real decisions made | The Frame bundle packaging decision |
| **Sprint conflict** | Sprint retrospectives, blocked stories | Competing priorities with limited capacity |
| **Architecture trade-off** | ADRs, architect sessions | Monorepo vs polyrepo for consumer projects |
| **Stakeholder tension** | PM sessions, backlog prioritization | Feature requests vs tech debt paydown |

## Capture Format

For each finding, capture:

```yaml
source:
  type: lang-review | production-bug | orc-ax-finding | swe-bench | owasp-cwe | project-history | sprint-conflict | architecture-tradeoff | stakeholder-tension
  reference: "specific file, PR, gate check number, or decision"
  context: "what was happening when this was discovered"
  ground_truth: "what the correct answer/behavior actually is (for detection) or what actually happened (for divergent)"
  family: detection | divergent
```

<actions>
- Read: `{gates_root}/` for available language review gates
- Read: Specific gate file if user selects lang-review source
- Read: Sprint archive or session files if user selects project history
</actions>

<output>
Captured source finding with:
- Source type and reference
- Context of discovery
- Ground truth (known correct behavior or actual outcome)
- Family determination (detection or divergent)
</output>

<gate>
## Completion Criteria
- [ ] Source type identified from valid options
- [ ] Specific finding captured with reference
- [ ] Ground truth documented (what the right answer is, or what actually happened)
- [ ] Family determined (detection or divergent)
- [ ] Source is real-world (not hypothetical or invented)
</gate>

<next-step>
After source is captured, proceed to step-02-prepare.md to prepare the party mode stimulus.
</next-step>

## Failure Modes

- Accepting a hypothetical scenario without real-world grounding
- Skipping ground truth documentation (makes scoring impossible later)
- Confusing detection and divergent families
