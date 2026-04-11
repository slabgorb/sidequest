# Kokoro Voice Research: Conlang Pronunciation + Non-Human Voices

Status: **HISTORICAL** — Kokoro TTS was removed from SideQuest in 2026-04.
This document is preserved as a reference for any future voice-synthesis
reintroduction, but it no longer describes a live subsystem. See
`docs/adr/076-narration-protocol-collapse-post-tts.md` for the removal
decision. The IPA pronunciation and voice-blending research below may still
inform whichever TTS engine replaces Kokoro, if one is brought in later.

## The Discovery

Misaki (Kokoro's G2P engine) supports markdown link syntax for IPA pronunciation overrides:

```
[Tsveri](/tsvˈɛɹi/) warriors guard the [Xal'thek](/zɑlθˈɛk/) passage.
```

Without overrides, unknown words (conlang terms) become `❓` and are silently skipped.
With overrides, Kokoro pronounces them exactly as specified via IPA.

### Verified Syntax (tested locally 2026-03-26)

| Syntax | Effect |
|--------|--------|
| `[word](/IPA/)` | Override pronunciation with exact IPA phonemes |
| `[text](-1)` | Lower stress by 1 level (primary → secondary) |
| `[text](-2)` | Lower stress by 2 levels (remove stress entirely) |

### Conlang Integration Pipeline (proposed)

1. Conlang generator creates words with phonology rules (already exists in genre packs)
2. Build `pronunciation.yaml` per genre pack mapping conlang terms → IPA
3. TTS preprocessor auto-wraps conlang words before synthesis: `Tsveri` → `[Tsveri](/tsvˈɛɹi/)`
4. Kokoro/misaki picks up IPA directly — no guessing, perfect pronunciation

### TODO: Research

- [ ] What does the existing conlang system generate? How close is it to IPA already?
- [ ] Can we auto-generate IPA from conlang phonology rules?
- [ ] Map the conlang phoneme inventory against Kokoro's supported IPA symbols
- [ ] Prototype: pronunciation.yaml for one genre pack (space_opera Tsveri language?)
- [ ] Test end-to-end: conlang word → IPA → markdown syntax → Kokoro audio

---

## Non-Human Voice Techniques

### Level 1: Post-Synthesis Effects (what we have now)

Genre pack `creature_voice_presets` apply pitch/rate/filters AFTER synthesis.
Current presets: dragon, goblin, undead, synthetic, xeno_deep, xeno_light, mutant_brute, rad_ghoul, sentient_ooze.

Limited — sounds like a human with effects.

### Level 2: Voice Tensor Blending (Kokoro-FastAPI technique)

Kokoro voices are `511 x 1 x 256` PyTorch tensors. Weighted blending happens BEFORE synthesis in embedding space:

```
af_bella(2)+am_fenrir(1)  →  67%/33% tensor mix  →  genuinely different voice
```

Blended voices saved as `.pt` files for reuse. This is the same principle as our conlang blending feature.

### Level 3: Advanced Tensor Manipulation

- **Slerp** (spherical interpolation) — smoother than linear blending
- **Extrapolation** — interpolation parameter outside [0,1] pushes past known voices
- **KVoiceWalk** (github.com/RobViren/kvoicewalk) — random walk voice cloning via tensor mutation
- **Semantic directions** — compute `V_deep - V_bright` to find "depth axis", add to any voice
- **KokoVoiceLab** (github.com/RobViren/kokovoicelab) — SQLite voice DB, interpolation explorer

### Proposed: Combined Approach for Non-Human Voices

```yaml
creature_voice_presets:
  droid:
    blend: "am_echo(3)+am_onyx(2)+af_nova(1)"   # Level 2: tensor blend
    pitch: 1.0
    rate: 0.92
    effects:                                       # Level 1: post-processing
      - type: pitch_quantize
        params: { interval_hz: 50 }
      - type: highpass_filter
        params: { cutoff_hz: 180 }
```

### TODO: Research

- [ ] Can kokoro-onnx (what our engine uses) do tensor blending, or only Kokoro-FastAPI?
- [ ] Prototype: blend 2-3 voices for a droid preset, compare against current `synthetic` preset
- [ ] Explore cross-language blending for alien voices (e.g., Japanese + English voice tensors)
- [ ] Test Slerp vs linear interpolation quality difference
- [ ] Profile performance: does blending add latency to the synthesis pipeline?

---

## Key Repos

- **Kokoro-FastAPI**: github.com/remsky/Kokoro-FastAPI — production voice blending API
- **KVoiceWalk**: github.com/RobViren/kvoicewalk — random walk voice cloning
- **KokoVoiceLab**: github.com/RobViren/kokovoicelab — voice interpolation explorer
- **Misaki**: github.com/hexgrad/misaki — G2P engine with IPA override syntax
- **Kokoro model**: huggingface.co/hexgrad/Kokoro-82M
- **ComfyUI-Geeky-Kokoro-TTS**: github.com/GeekyGhost/ComfyUI-Geeky-Kokoro-TTS — node-based voice workflow

## Dependencies Installed

- `misaki[en]` 0.9.4 installed in sidequest-daemon/.venv (includes spacy, num2words)
