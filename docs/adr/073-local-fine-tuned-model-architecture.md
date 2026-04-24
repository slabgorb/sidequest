---
id: 73
title: "Local Fine-Tuned Model Architecture"
status: accepted
date: 2026-04-08
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [narrator-migration, narrator]
implementation-status: live
implementation-pointer: null
---

# ADR-073: Local Fine-Tuned Model Architecture

**Context:** OTEL observability findings, prompt framework complexity, operational cost

## Problem

The current narrator pipeline uses Claude via `claude -p` subprocess (ADR-001) with
a 5-zone prompt framework totaling ~15KB of system instructions per Full-tier turn.
This prompt mass exists to coerce a general-purpose model into emitting valid
`game_patch` JSON, maintaining genre voice, and respecting mechanical subsystems
(trope engine, tension tracker, faction agendas). Despite this scaffolding, Claude
still "wings it" — generating plausible-sounding narration with incorrect or missing
mechanical grounding. The OTEL observability principle (CLAUDE.md) diagnoses this as
structural: prompting against the model's nature rather than training the nature itself.

A fine-tuned model inverts this. Instead of 30 prompt sections constraining output,
the model learns `game_patch` schema, genre voice, and valid state transitions from
labeled training data. Prompts collapse from 15KB to ~3KB of dynamic state.

## Decision

Introduce a four-phase architecture for local fine-tuned model support:

- **Phase 0:** Wire TurnRecord capture for training data (prerequisite)
- **Phase 1:** Extract `LlmClient` trait from concrete `ClaudeClient`
- **Phase 2:** Ollama/MLX backend implementations behind the trait
- **Phase 3:** QLoRA fine-tune pipeline in `sidequest-daemon`

Target context window: **16K tokens** (4K system / 8K dynamic state / 4K response).

Claude remains the default backend. Fine-tuned local models are an alternative backend
selectable at server startup. Both emit identical telemetry for A/B comparison via OTEL.

## Design

### Context Budget (16K)

```
┌─────────────────────────────────────────────┐
│ 16,384 tokens                               │
├─────────────────┬───────────────────────────┤
│ System (~4K)    │ Condensed rules, genre     │
│                 │ voice, game_patch schema   │
│                 │ (model knows the rest)     │
├─────────────────┼───────────────────────────┤
│ Dynamic (~8K)   │ GameSnapshot, recent turns,│
│                 │ active scene, NPC state,   │
│                 │ faction agendas, tropes    │
├─────────────────┼───────────────────────────┤
│ Response (~4K)  │ Narration prose +          │
│                 │ game_patch JSON block      │
└─────────────────┴───────────────────────────┘
```

The 15KB Full-tier prompt collapses because the fine-tuned model has internalized:
- `game_patch` JSON schema and field semantics
- Genre voice and tone (via per-genre LoRA)
- Valid state transitions (trained on correct OTEL-labeled pairs)
- Subsystem interaction rules (trope triggers, tension thresholds)

### Phase 0: Training Data Capture

**Prerequisite for all other phases.** Completes the unwired TurnRecord pipeline
designed in ADR-031.

Current state: `TurnRecord` struct exists with 15 fields per ADR-031. The mpsc
channel is created in `main.rs`, the bridge task is spawned, but `process_action()`
in `orchestrator.rs` never instantiates or sends a TurnRecord. Story 3-2 is RED.

Wire it:

```
orchestrator.rs::process_action()
    ├── Construct TurnRecord with full prompt text + response text
    ├── Include snapshot_before, snapshot_after, delta
    ├── try_send_record(watcher_tx, record)
    └── Persist to JSONL on disk (~/.sidequest/training/)
```

**Output format** (one JSONL line per turn):

```json
{
  "turn_id": 14,
  "timestamp": "2026-04-08T19:30:00Z",
  "genre": "pulp_noir",
  "world": "city_of_angles",
  "prompt_tier": "Full",
  "system_prompt": "<full system prompt text>",
  "user_prompt": "<assembled user prompt>",
  "response_text": "<raw Claude response>",
  "game_patch": { "...extracted patch..." },
  "snapshot_before": { "...game state..." },
  "snapshot_after": { "...game state..." },
  "delta": { "...state changes..." },
  "classified_intent": "explore",
  "agent_name": "narrator",
  "beats_fired": [["rising_tension", 0.7]],
  "token_count_in": 12400,
  "token_count_out": 1850,
  "is_degraded": false
}
```

This serves double duty: training data for Phase 3 and session replay for debugging.

### Phase 1: LlmClient Trait Extraction

Extract `ClaudeClient` behind a trait to support multiple backends:

```rust
#[async_trait]
pub trait LlmClient: Send + Sync {
    async fn send(
        &self,
        request: &LlmRequest,
    ) -> Result<LlmResponse, LlmError>;

    async fn send_with_context(
        &self,
        request: &LlmRequest,
        context: &SessionContext,
    ) -> Result<LlmResponse, LlmError>;

    fn capabilities(&self) -> ClientCapabilities;
}

pub struct LlmRequest {
    pub system_prompt: String,
    pub user_prompt: String,
    pub tools: Vec<ToolDefinition>,
    pub model_hint: ModelHint,   // Narrator, Classifier, WorldBuilder
    pub max_tokens: Option<u32>,
}

pub struct LlmResponse {
    pub text: String,
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub session_id: Option<String>,
    pub duration_ms: u64,
    pub backend: BackendId,      // "claude-cli", "ollama", "mlx"
}

pub struct SessionContext {
    pub session_id: Option<String>,
    pub is_resume: bool,
    pub history: Option<Vec<TurnExchange>>,  // For backends without server-side sessions
}

pub struct ClientCapabilities {
    pub supports_sessions: bool,      // Claude: true, Ollama: false
    pub supports_tools: bool,         // Claude: true, varies for local
    pub max_context_tokens: usize,    // Claude: 200K, local: 16K
    pub supports_streaming: bool,
}
```

Key design decisions:

- **`SessionContext.history`** bridges Claude's opaque `--resume` and local models'
  explicit context replay. If `supports_sessions` is true, the orchestrator sends
  only `session_id`. If false, it packs recent turn history into `history` for the
  backend to prepend to context.
- **`model_hint`** decouples the orchestrator from model names. The backend maps
  `ModelHint::Narrator` to whatever model serves narration (claude-sonnet-4-6,
  llama-3.1-sidequest-narrator, etc.).
- **`BackendId` on response** enables OTEL spans to tag which backend produced
  each turn, critical for A/B telemetry comparison.
- **`capabilities()`** lets the orchestrator adapt prompt tier selection. A backend
  with `max_context_tokens: 16384` forces condensed prompts; one with 200K allows
  Full tier. The existing `select_prompt_tier()` method gains a new input.

Refactoring scope:
- `orchestrator.rs`: Change `client: ClaudeClient` → `client: Arc<dyn LlmClient>`
- `preprocessor.rs`: Accept `Arc<dyn LlmClient>` instead of constructing ClaudeClient
- `main.rs`: Factory function selects backend from config, passes to Orchestrator
- `ClaudeClient` becomes `ClaudeBackend` implementing `LlmClient`

### Phase 2: Local Model Backends

**OllamaBackend:**

```rust
pub struct OllamaBackend {
    base_url: String,          // http://localhost:11434
    model_map: HashMap<ModelHint, String>,  // Narrator → "sidequest-narrator:latest"
    lora_map: HashMap<String, String>,      // genre → LoRA adapter path
}
```

- HTTP client to Ollama REST API (`/api/generate`, `/api/chat`)
- LoRA selection per genre: Ollama supports `--lora` flag per request
- No server-side sessions — `SessionContext.history` provides context continuity
- Token counting from Ollama response metadata

**MlxBackend** (optional, Apple Silicon optimization):

- Direct MLX inference via Python bridge (sidequest-daemon endpoint)
- Lower latency than Ollama for single-user local play
- Same trait interface

**Backend selection** via server config:

```yaml
# ~/.sidequest/config.yaml
llm_backend: claude          # claude | ollama | mlx
ollama:
  url: http://localhost:11434
  narrator_model: sidequest-narrator:latest
  lora_dir: ~/.sidequest/loras/
```

### Phase 3: Fine-Tune Pipeline

Lives in `sidequest-daemon` (Python — model training is ML inference work per the
Rust/Python split).

**Training data flow:**

```
~/.sidequest/training/*.jsonl     (Phase 0 output)
         │
         ▼
    Filter & clean                 (remove degraded turns, malformed patches)
         │
         ▼
    Format as training pairs       (system + input → output)
         │
         ▼
    Base model QLoRA fine-tune     (unsloth or axolotl)
         │
         ▼
    Genre LoRA adapters            (one per genre pack, trained on genre-filtered turns)
         │
         ▼
    Serve via Ollama               (ollama create with Modelfile + LoRA)
```

**Base model candidates** (16K context, good at structured output):

| Model | Parameters | Notes |
|-------|-----------|-------|
| Llama 3.1 | 8B / 70B | Strong structured output, good fine-tune ecosystem |
| Qwen 2.5 | 7B / 72B | Excellent at JSON generation natively |
| Mistral | 7B | Fast inference, proven LoRA support |

**Minimum training data:** ~5K quality turn pairs for base fine-tune, ~500 per genre
for LoRA adaptation. At ~30 turns per hour of playtesting, that's ~170 hours for base
and ~17 hours per genre. Phase 0 capture must run through substantial playtesting
before Phase 3 begins.

**Evaluation:** A/B comparison using OTEL telemetry. Same game state fed to both
Claude and local model; compare `game_patch` validity rate, subsystem exercise
coverage, and qualitative narration review via GM panel.

## Consequences

### Positive

- **Structural `game_patch` reliability:** Model learns the schema as output structure,
  not as a prompt it's coerced into following
- **Genre voice without prompt mass:** LoRA per genre pack eliminates ~200 lines of
  tone instructions per genre
- **Mechanical grounding:** Trained on turns where subsystems produced correct state
  transitions; model learns what "valid" looks like
- **Prompt collapse:** 15KB → ~3KB dynamic state, freeing context for game state
- **Cost reduction:** Hardware-amortized inference vs per-turn API cost
- **Latency improvement:** 1-3s local vs 3-8s network (hardware dependent)
- **Offline play:** No network dependency for inference

### Negative

- **Training data dependency:** Need ~5K+ quality turns before fine-tune is viable;
  Phase 3 is months away from Phase 0
- **Narration quality ceiling:** Local models (8B-70B) won't match Opus-tier prose;
  acceptable for gameplay, may feel flat for showcase
- **Iteration friction:** Prompt changes are instant; retraining takes hours
- **Hardware requirements:** 70B model needs ~40GB VRAM; 8B fits on M-series Macs
- **Maintenance burden:** Two backends to keep working, trait abstraction overhead

### Mitigations

- Claude remains default; local model is opt-in at config level
- A/B telemetry comparison catches quality regression before shipping
- Phase 0 (training capture) provides value independently as session replay and
  debugging infrastructure
- ADR-001 is not superseded — Claude CLI remains the primary backend; this ADR
  adds an alternative

## Supersedes / Relates To

- **ADR-001** (Claude CLI Only): Not superseded. Claude remains primary. This ADR
  adds an alternative backend behind a trait abstraction.
- **ADR-031** (Game Watcher): Phase 0 completes the unwired TurnRecord pipeline.
- **ADR-066** (Persistent Opus Sessions): Session semantics abstracted by
  `SessionContext` in the `LlmClient` trait. Claude backend preserves `--resume`
  behavior; local backends use history replay.
