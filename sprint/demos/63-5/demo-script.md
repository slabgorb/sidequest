# Demo Script — 63-5

**Total runtime: ~6 minutes**

### Scene 1 — Title (Slide 1)
*30 seconds*
"Epic 63 wrapped up the v3 reference pages — per-pack chrome theming, wiki-style anchor links, structured lore and rules sections. Story 63-5 is the final gate: a live-pack validator, tropes cleanup, and a small dead-code removal."

### Scene 2 — Problem (Slide 2)
*1 minute*
"Two things were wrong before this landed. First: no automated way to tell whether a pack's theme.yaml had everything the reference renderer needed. A pack author would find out the page was broken at render time, not at authoring time. Second: the rules reference pages were showing trope tables — that's GM content, not player content. The renderer was treating tropes.yaml the same as rules files."

Fallback: Show Slide 2 bullets if the live demo environment isn't available.

### Scene 3 — Live validator demo (Slide 3)
*2 minutes*

Type this in the orchestrator root:
```bash
just content-validate
```

Show the output — each live pack prints an `[OK]` line with its name. Then demonstrate failure:
```bash
# Temporarily rename a field to simulate a broken pack
cd sidequest-content/genre_packs/tea_and_murder
cp theme.yaml theme.yaml.bak
# Edit theme.yaml — remove the display_font_family field, then run:
cd /path/to/oq-1
just content-validate
```
Expected output:
```
[FAIL] tea_and_murder: missing field: display_font_family
```
Exit code is non-zero. Restore the file immediately after:
```bash
cd sidequest-content/genre_packs/tea_and_murder && mv theme.yaml.bak theme.yaml
```

Fallback: If the live packs aren't accessible, show the test output from `uv run pytest tests/cli/test_validate_reference_chrome.py -v` — 14 passing tests, each named for the specific missing-field scenario it covers.

### Scene 4 — Tropes exclusion (Slide 3 continued)
*1 minute*
"Before this change, if a pack had a tropes.yaml, the confrontations/tropes section would appear on the rules reference page — GM content next to player-facing rules. Now it's explicitly excluded."

Show the three-line diff in `reference_renderer.py` — `tropes.yaml` moved from `RULES_FILES` to `EXCLUDED_FILES`. No new mechanism, just a name moved between lists.

Fallback: Show Slide 4 (Why This Approach) and explain the exclusion mechanism verbally.

### Scene 5 — Wrap (Slide 6 / Roadmap)
*30 seconds*
"This closes epic 63. The validator is now part of `just content-validate` — every time a pack author adds a new genre or edits a theme, one command tells them whether the reference pages will render correctly."

---
