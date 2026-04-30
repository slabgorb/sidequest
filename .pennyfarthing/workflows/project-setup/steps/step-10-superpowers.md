# Step 10: Install Superpowers Companion Plugin

<purpose>
Pennyfarthing declares `superpowers@claude-plugins-official` as a required companion Claude Code plugin. It ships generic software-craft skills — brainstorming, writing-plans, verification-before-completion, systematic-debugging, test-driven-development — that pennyfarthing forwarder commands and enforcement gates reference. Without it, `/pf-brainstorming` cannot forward and several Track 2 gates cannot verify their artifacts.
</purpose>

<instructions>
1. Tell the user to install the superpowers plugin from Claude Code's plugin registry.
2. Wait for confirmation the install succeeded.
3. Run `pf doctor` and confirm the `superpowers_plugin` check reports OK.
4. If the check fails, ask the user to retry the install command and recheck.
</instructions>

<output>
- Superpowers plugin installed.
- `pf doctor` reports `[OK] superpowers_plugin: superpowers plugin found at ...`.
</output>

## INSTALL THE PLUGIN

```
Superpowers Plugin Installation
===============================

Pennyfarthing uses skills from the superpowers plugin for
brainstorming, plan writing, code review, TDD, and verification.

Install it from inside Claude Code (NOT the shell):

  /plugin install superpowers@claude-plugins-official

Once Claude confirms the install is complete, press Enter.
```

## VERIFICATION

```bash
pf doctor
```

Expected output includes:

```
  [OK] superpowers_plugin: superpowers plugin found at /Users/<you>/.claude/plugins/cache/claude-plugins-official/superpowers
```

If you see `[FAIL] superpowers_plugin: ...`, ask the user to rerun the install command.

## CHANGING LATER

The plugin can be updated or removed via Claude Code's `/plugin` command at any time. Pennyfarthing will complain (via `pf doctor`) if it is missing.

## SUCCESS CRITERIA

- `superpowers@claude-plugins-official` plugin is installed in the user's Claude Code environment.
- `pf doctor` reports the `superpowers_plugin` check as `[OK]`.

## NEXT STEP

After confirming the plugin is installed, proceed to `step-11-complete.md` to finalize setup.
