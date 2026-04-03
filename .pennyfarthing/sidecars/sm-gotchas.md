## SM Gotchas

- **Never suggest deferring work.** Keith decides priorities. Don't say "park it," "post-X problem," or "feature gap — deprioritizing." Just execute.
- **Never editorialize about task types.** Route for execution, don't filter by priority or type.
- **Branch before editing.** Create feature branch BEFORE making changes, not after. This is a consistent failure pattern — hitting a hook block, then scrambling.
- **Git stash is forbidden.** Use temp branches or manual re-apply. Never `git stash`, `git stash pop`, or `git stash apply`.
- **No destructive git commands.** Never `reset`, `checkout -- .`, `clean`, or force anything. Push before reorganizing. If you say "actually simpler" — STOP, you're about to improvise.
- **Finish flow is fragile.** Session archive and YAML status update are separate steps. If one fails, the other doesn't compensate. Verify both after `pf sprint story finish`.
- **`depends_on` validator is global.** Stories referencing siblings in a backlog epic break all `pf sprint story update` commands if the targets aren't in the current sprint.
