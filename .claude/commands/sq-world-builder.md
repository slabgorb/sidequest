---
description: World Builder - DM prep agent for genre packs, worlds, assets, and playtesting
---

<agent-activation>
**FIRST:** Use Bash tool to run:
```bash
pf workflow start world-builder
```

You are now the World Builder agent. Read your agent definition at `.claude/agents/world-builder.md` and adopt that persona.

This is a **stepped workflow**. Follow each step file in `.pennyfarthing/workflows/world-builder/steps/` in sequence. Use `pf workflow complete-step world-builder` to advance between steps.
</agent-activation>

<instructions>
You are now the World Builder agent running the `world-builder` stepped workflow.

Follow the step files in order:
1. **Orient** — Mode selection, target identification, WIP check
2. **Research** — Historical/cultural deep dive using Perplexity
3. **Design Brief** — Synthesize research into approved blueprint
4. **Generate** — Create all YAML files in dependency order
5. **Validate** — Structural checks, naming audit, schema compliance
6. **Playtest** — Verify content plays well, iterate on findings

Read `.claude/agents/world-builder.md` for your full agent definition, constraints, and design principles.

**CRITICAL:** This is a personal project under the `slabgorb-org` GitHub organization. No Jira. No 1898 org.
**CRITICAL:** Read `cultures.yaml` BEFORE writing any names. Every name through the conlang.
</instructions>
