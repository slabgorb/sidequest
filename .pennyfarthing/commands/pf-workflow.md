---
description: List available workflows, show current workflow details, and switch workflows mid-session. Use when checking available workflow types (TDD, trivial, agent-docs), viewing current workflow phase, switching to a different workflow pattern, or managing BikeLane stepped workflows.
---

# /workflow - Workflow Management

Load and follow the workflow skill: `.claude/skills/workflow/skill.md`

Pass any arguments provided by the user to the skill commands.

## Quick Reference

| Command | Action |
|---------|--------|
| `/pf-workflow` | List all available workflows |
| `/pf-workflow list` | List all available workflows |
| `/pf-workflow show [name]` | Show workflow details (current session if no name) |
| `/pf-workflow set <name>` | Switch to a different workflow mid-session |
| `/pf-workflow start <name> [--mode <mode>]` | Start a stepped workflow |
| `/pf-workflow resume [name]` | Resume an interrupted stepped workflow |
| `/pf-workflow status` | Show current stepped workflow progress |
