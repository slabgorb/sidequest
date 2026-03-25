# TirePump

<info>
Context clearing system. Clears the Claude session, resets stats, and reloads the current agent with fresh context. Named for reinflating a flat tire — pumping air back into the session when context runs low.
</info>

<critical>
TirePump **preserves workflow state**. Session files in `.session/` persist across reloads. Only the Claude conversation context is cleared — the agent picks up where it left off by reading session state.
</critical>

## Flow

```
User clicks TirePump (or CONTEXT_CLEAR marker fires)
  → ControlBar calls clearAndReload(agent)
  → ClaudeContext sends WebSocket: {type: 'clearAndReload', agent}
  → Server resets: context to 0%, token stats, todos, tool stats, skills
  → Server calls service.clearSessionAsync()
  → Server reloads agent with prime context
  → Broadcasts context update via /ws/context
```

## Triggers

| Trigger | How |
|---------|-----|
| Manual | TirePump button in ControlBar (pump icon) |
| Marker | `<!-- PF:CONTEXT_CLEAR:/agent -->` in agent output (BikeRack GUI protocol) |
| Plan mode | `usePlanModeExit` offers TirePump after plan approval |

## UI Behavior

- Button always visible
- Warning style (visual alert) when context >= 70%
- Disabled when no agent is loaded

## Key Files

| File | Purpose |
|------|---------|
| `packages/cyclist/src/public/components/ControlBar.tsx` | TirePump button, visibility/warning thresholds |
| `packages/cyclist/src/public/contexts/ClaudeContext.tsx` | `clearAndReload()` — sends WebSocket message, fires clear callbacks |
| `packages/cyclist/src/websocket.ts` | Handles `clearAndReload` message — resets all state, reloads agent |
| `packages/cyclist/src/public/hooks/usePlanModeExit.ts` | Offers TirePump choice after plan approval |

## What Gets Reset

| Reset | Preserved |
|-------|-----------|
| Claude conversation context | `.session/` files |
| Token counts, context % | Workflow state (phase, story) |
| Tool stats, todos | `.pennyfarthing/config.local.yaml` |
| Skills, event store | Git state, file changes |
