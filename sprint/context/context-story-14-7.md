---
parent: context-epic-14.md
---

# Story 14-7: Image Scene Relevance Filter

## Business Context

Images sometimes depict subjects that aren't in the current scene — a merchant interaction
triggering a mutant monster portrait breaks immersion hard. The art prompt pipeline needs
a validation step against the current scene context.

**Playtest evidence:** "Some images with extremely weird scenes that break immersion, because
if we're dealing with a merchant and we suddenly get a picture of a huge mutant monster, the
players rightfully are going to say, what the fuck is that?"

**Depends on:** 14-6 (throttle should exist first so we're not also validating too-frequent images)

## Technical Approach

### Scene Context as Ground Truth

The scene interpreter (sidequest-daemon) extracts subjects from narration. The server
tracks current scene state: location, NPCs present, active entities, current action type.

### Validation Step

Before sending an art prompt to the daemon:

1. Extract subjects from the proposed art prompt (entities, creatures, settings)
2. Compare against current scene context:
   - NPCs present in the scene
   - Current location features
   - Active entities (monsters in combat, merchants in trade, etc.)
3. If the prompt references entities NOT in the scene context → reject and regenerate
4. If the prompt matches scene context → proceed

### Implementation

This validation happens in the orchestrator's image trigger path, between "narrator
suggests image" and "send to daemon":

```rust
fn validate_image_prompt(prompt: &str, scene: &SceneContext) -> ImagePromptVerdict {
    let prompt_subjects = extract_subjects(prompt);
    let scene_subjects = scene.active_entities();

    let mismatched: Vec<_> = prompt_subjects
        .iter()
        .filter(|s| !scene_subjects.contains_any(s))
        .collect();

    if mismatched.is_empty() {
        ImagePromptVerdict::Approved
    } else {
        ImagePromptVerdict::Rejected {
            reason: format!("Subjects not in scene: {:?}", mismatched),
        }
    }
}
```

### Fallback on Rejection

When an image prompt is rejected, don't retry — just skip the image. The throttle ensures
another opportunity will come on the next turn. Logging the rejection helps debug art
prompt quality issues.

## Scope Boundaries

**In scope:**
- Subject extraction from art prompts
- Comparison against scene context
- Reject mismatched prompts
- Logging rejected prompts for debugging

**Out of scope:**
- Rewriting rejected prompts to match the scene
- Art style validation (that's genre theming, separate issue)
- Image content analysis after generation (NSFW filtering, etc.)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Validation runs | Every art prompt checked against scene context before generation |
| Mismatch rejected | Prompt with entities not in scene is suppressed |
| Match approved | Prompt matching scene entities proceeds to daemon |
| Logged | Rejected prompts logged with reason for debugging |
| No retry | Rejected prompt doesn't trigger regeneration attempt |
| Scene-aware | Validation uses NPCs present, location, and active entities |
