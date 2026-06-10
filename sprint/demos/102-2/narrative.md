# Narrative

## Problem Statement
Problem: In-combat cast_spell via the dice path routes to the WN cast spine — add spell selection (spell_id) to DiceThrowPayload + ConfrontationOverlay so the 'Work a Spell' beat fires wwn.spell.cast and spends Effort/casts instead of resolving as a generic INT dice throw (today _resolve_wwn_cast_for_beat only runs on the narrator apply_beat path). AC5b spellcast blocker. server,ui.. Why it matters: users needed a better interface.

## What Changed
We implemented: In-combat cast_spell via the dice path routes to the WN cast spine — add spell selection (spell_id) to DiceThrowPayload + ConfrontationOverlay so the 'Work a Spell' beat fires wwn.spell.cast and spends Effort/casts instead of resolving as a generic INT dice throw (today _resolve_wwn_cast_for_beat only runs on the narrator apply_beat path). AC5b spellcast blocker. server,ui..

## Why This Approach
This approach prioritizes user experience and accessibility.
