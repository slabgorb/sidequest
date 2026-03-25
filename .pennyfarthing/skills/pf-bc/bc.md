---
name: bc
description: |
  Panel focus management for BikeRack. Set which panel BikeRack should focus on,
  or clear the focus setting. Save and load named layouts. Writes to `.pennyfarthing/config.local.yaml`.
args: "[panel|reset|save|load|list|clear|clear-all] [name]"
---

# /bc - Panel Focus & Layout Management

Set or clear the focused panel in BikeRack. Save and restore named layouts.

## Quick Reference

### Panel Focus

| Command | CLI | Purpose |
|---------|-----|---------|
| `/bc sprint` | `pf bc sprint [--dry-run]` | Focus Sprint panel |
| `/bc git` | `pf bc git [--dry-run]` | Focus Git panel |
| `/bc diffs` | `pf bc diffs [--dry-run]` | Focus Diffs panel |
| `/bc todo` | `pf bc todo [--dry-run]` | Focus Todo panel |
| `/bc workflow` | `pf bc workflow [--dry-run]` | Focus Workflow panel |
| `/bc background` | `pf bc background [--dry-run]` | Focus Background panel |
| `/bc audit-log` | `pf bc audit-log [--dry-run]` | Focus Audit Log panel |
| `/bc changed` | `pf bc changed [--dry-run]` | Focus Changed panel |
| `/bc ac` | `pf bc ac [--dry-run]` | Focus Acceptance Criteria panel |
| `/bc debug` | `pf bc debug [--dry-run]` | Focus Debug panel |
| `/bc settings` | `pf bc settings [--dry-run]` | Focus Settings panel |
| `/bc reset` | `pf bc reset [--dry-run]` | Clear focus setting |

### Named Layouts

| Command | CLI | Purpose |
|---------|-----|---------|
| `/bc save <name>` | `pf bc save <name> [--dry-run]` | Save current layout from running server |
| `/bc load <name>` | `pf bc load <name> [--dry-run]` | Load a saved layout |
| `/bc list` | `pf bc list` | List all saved layouts |
| `/bc clear <name>` | `pf bc clear <name> [--dry-run]` | Delete a saved layout |
| `/bc clear-all` | `pf bc clear-all [--dry-run]` | Delete all saved layouts |

### Notes

- The `message` panel (sacred center) is not focusable
- Config written to `.pennyfarthing/config.local.yaml` under `focus` / `named_layouts` keys
- `save` requires a running BikeRack server

---

**Detailed options and behavior:** [usage.md](usage.md)
**Practical examples:** [examples.md](examples.md)
