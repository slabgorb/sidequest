# Relay Mode

<info>
Automatic agent handoff execution. When enabled, Frame GUI auto-executes handoff markers without waiting for user confirmation.
</info>

<critical>
Relay Mode is **orthogonal to Permission Mode**. They control different things:
- `permission_mode` → Claude Code tool permissions (plan/manual/accept)
- `relay_mode` → automatic handoff execution (true/false)

Any combination is valid.
</critical>

## Behavior

| relay_mode | What happens on HANDOFF marker |
|------------|-------------------------------|
| `false` (default) | QuickActions shows "Continue with /agent" button — user clicks to proceed |
| `true` | QuickActions auto-executes handoff after 100ms delay — no user interaction |

## Configuration

```yaml
# .pennyfarthing/config.local.yaml
workflow:
  permission_mode: manual
  relay_mode: true
```

## Key Files

| File | Purpose |
|------|---------|
| `packages/core/src/server/settings.ts` | Settings management, legacy migration |
| `packages/core/src/server/api/settings.ts` | `GET/PATCH /api/settings` for relay_mode |
| `packages/cyclist/src/public/components/QuickActions.tsx` | Auto-execution logic on marker detection |
| `packages/cyclist/src/public/components/ControlBar.tsx` | Relay toggle (Cmd+4) |

## Legacy Migration

Old settings are auto-converted on load:

| Old Setting | Migrates To |
|-------------|-------------|
| `permission_mode: 'turbo'` | `permission_mode: 'accept'` + `relay_mode: true` |
| `handoff_mode: 'auto'` | `relay_mode: true` |
| `handoff_mode: 'manual'` | `relay_mode: false` |
| `auto_handoff: true` | `relay_mode: true` |

<info>
**ADR:** `docs/adr/0017-relay-mode-automatic-handoff.md`
</info>
