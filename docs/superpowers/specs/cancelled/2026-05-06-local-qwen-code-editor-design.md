# Local Qwen as Code Editor (MVP)

**Date:** 2026-05-06
**Author:** Keith Avery
**Status:** Draft
**Related:** ADR-073 (local fine-tuned model architecture); 2026-04-23 Group E plan (LlmClient abstraction + Ollama backend + training pipeline)

## Goal

Stand up local Qwen on the Mac Studio (M3 Ultra, 96GB unified memory) and wire `qwen-code` CLI to use it as a daily code editor. Outcome: typing `qwen` in any terminal opens an agentic coding session backed by a Qwen model running entirely on this machine, with no cloud calls and no API costs. This gives a non-Claude code-editor for cross-model evaluation of prompting and agent behavior, and is the first concrete deliverable toward a broader local-LLM foundation.

## Non-Goals

- **SideQuest narrator backend validation.** ADR-073 Phases 1–2 already shipped this; running the existing `SIDEQUEST_LLM_BACKEND=ollama` path end-to-end is a separate sub-project.
- **Fine-tuning pipeline.** Group E shipped `sidequest-train`; running it on real corpus and closing the MLX→Ollama serving gap is a separate sub-project (Group F territory).
- **A/B evaluation harness.** Comparing local-Qwen vs. Claude on identical inputs is a separate sub-project.
- **Modifying the qwen-code repo itself.** This spec only touches user-scope config (`~/.qwen/settings.json`, env vars, Ollama installation). The qwen-code source tree is consumed as-is from upstream.

## Background: the three layers

The naming overlap between "Qwen," "Ollama," and "qwen-code" hides three independent layers:

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT             qwen-code CLI                       │
│                     (TUI agent, speaks OpenAI API)      │
├─────────────────────────────────────────────────────────┤
│  INFERENCE RUNTIME  Ollama                              │
│                     (HTTP server wrapping llama.cpp)    │
├─────────────────────────────────────────────────────────┤
│  MODEL WEIGHTS      Qwen3-Coder-30B (GGUF, 4-bit)       │
│                     (Alibaba Qwen team)                 │
├─────────────────────────────────────────────────────────┤
│  HARDWARE           M3 Ultra, 96GB unified memory       │
└─────────────────────────────────────────────────────────┘
```

Each layer is independent. qwen-code talks to Ollama over HTTP using the OpenAI-compatible endpoint at `http://localhost:11434/v1`; Ollama loads the GGUF weights into unified memory and runs inference via Metal.

## Design

### 1. Inference runtime: Ollama

Install via Homebrew and run as a launchd service so it's always available:

```bash
brew install ollama
brew services start ollama
```

Ollama listens on `http://localhost:11434` by default. The OpenAI-compatible endpoint is at `/v1/chat/completions`.

**Why Ollama and not MLX directly:**
- Drop-in OpenAI-compat surface — qwen-code wires up with zero code changes
- Same runtime that ADR-073 Phase 2 already targets in `sidequest-server`
- Mature model registry (`ollama pull` is one command per model)
- Metal-backed via `llama.cpp`; fast on Apple Silicon for inference workloads

MLX may still come in later for fine-tuning (per Group E plan, `sidequest-train` already uses `mlx-lm`), but inference goes through Ollama.

### 2. Model: `qwen3-coder:30b`

Qwen3-Coder 30B-A3B Instruct (Mixture-of-Experts).

```bash
ollama pull qwen3-coder:30b
```

**Rationale:**
- Latest Qwen-family code-specialized model
- MoE architecture: only ~3B parameters active per token → fast inference on Apple Silicon
- ~18-20GB resident at 4-bit quantization → fits comfortably with ~70GB headroom for context, OS, and other workloads
- Built for tool-use (which qwen-code requires for file edits, bash, etc.)
- Native 32K+ context window

If the canonical Ollama tag at install time differs (e.g., `qwen3-coder:30b-a3b`, or a newer point release), pin to whatever is current and update the settings.json `id` field to match.

### 3. qwen-code configuration

Add a `modelProviders.openai` entry to `~/.qwen/settings.json` (user scope so it's available across all projects on this machine):

```json
{
  "env": {
    "OLLAMA_API_KEY": "ollama"
  },
  "modelProviders": {
    "openai": [
      {
        "id": "qwen3-coder:30b",
        "name": "Qwen3-Coder 30B (local Ollama)",
        "description": "Local Qwen3-Coder via Ollama on this Mac",
        "envKey": "OLLAMA_API_KEY",
        "baseUrl": "http://localhost:11434/v1",
        "generationConfig": {
          "timeout": 300000,
          "maxRetries": 1,
          "contextWindowSize": 32768,
          "samplingParams": {
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 8192
          },
          "extra_body": {
            "options": {
              "num_ctx": 32768
            }
          }
        }
      }
    ]
  }
}
```

**Critical detail — context window:** Ollama's server defaults to `num_ctx: 2048`, which is way too small for an agent doing real code-editing work. The `extra_body.options.num_ctx` field tells Ollama (via its OpenAI-compat layer's options pass-through) to allocate a larger window per request. `contextWindowSize: 32768` on the client side ensures qwen-code doesn't pre-truncate prompts.

**Why user scope:** The point is using local Qwen as a daily editor across all projects, not just inside qwen-code's own source tree. Per qwen-code's docs, defining `modelProviders` at user scope (`~/.qwen/settings.json`) is the recommended approach to avoid project/user merge conflicts.

**API key note:** Ollama doesn't authenticate, but the `openai` SDK requires *some* key value to construct a client. `"ollama"` is the conventional placeholder; any non-empty string works.

**Sampling params:** Temperature 0.2 / top_p 0.8 is a coding-task default — deterministic enough to follow tool-use protocols reliably, with a hair of variation. These are tunable knobs to revisit after real use.

### 4. Validation

Three checkpoints, in order:

1. **Ollama health.** `curl http://localhost:11434/api/tags` returns the installed model list including `qwen3-coder:30b`.
2. **Model picker.** Launch `qwen` in a scratch directory; run `/model`; the new local entry appears and can be selected.
3. **Tool round-trip.** Ask the agent to do something that exercises the tool surface — e.g., "list the files in this directory, read README.md, propose a one-line change, write it." Confirm:
   - File reads/writes work
   - Bash commands work
   - The agent doesn't get stuck in a tool-call loop or emit malformed tool calls
   - Round-trip latency feels usable (informally — "tens of seconds per turn for a multi-step task" is the rough acceptable bar; if it's minutes, something is wrong)

If validation passes, the MVP is complete and the foundation is in place for the SideQuest-backend and fine-tuning sub-projects.

## Risks & Open Questions

- **Ollama tag drift.** Model tags on the Ollama hub get renamed/superseded. The exact `qwen3-coder:30b` tag may be `qwen3-coder:30b-a3b-instruct-q4_K_M` or similar by the time of install. Mitigation: pin to whatever is canonical at install time and update the settings entry to match.
- **Tool-call protocol compatibility.** qwen-code's OpenAI SDK path expects standard OpenAI tool-call message shapes. Ollama's OpenAI-compat layer supports tool calls for models that have them in their template, but edge cases (parallel tool calls, streaming tool deltas) can be flaky. If the agent fails on tool round-trip, fall back to disabling parallel tool calls in `samplingParams` or downgrading to a model with a more conservative template.
- **First-load latency.** First request after Ollama starts (or after idle eviction) will pay 5-15 seconds of weight-loading time. Subsequent requests are fast. Document this so it doesn't read as a config bug.
- **Context window cost.** A 32K context with this model uses several GB of KV cache. At 96GB unified memory, this is fine, but if other workloads (image gen, music gen — `sidequest-daemon`) compete for memory, contention could surface. Not an MVP problem; flag for future tuning.

## Out-of-scope follow-ups (separate specs)

- **Sub-project A1:** Validate `SIDEQUEST_LLM_BACKEND=ollama` end-to-end with a real Qwen 2.5 7B model pulled (the locked Group E base model). Independent of this MVP.
- **Sub-project B:** Run `sidequest-train` on accumulated corpus; close the MLX→Ollama serving gap (Group F).
- **Sub-project C:** Structured A/B eval harness — same prompt to both Claude and local Qwen, diff outputs.

## Success Criteria

- [ ] `ollama list` shows `qwen3-coder:30b` (or current canonical tag) installed.
- [ ] `~/.qwen/settings.json` contains the `modelProviders.openai` entry above.
- [ ] `qwen` launched in any directory and `/model`-switched to the local entry produces a successful agentic coding session: reads files, makes edits, runs bash commands, all via local inference.
- [ ] Round-trip latency on a typical multi-tool task is in the tens-of-seconds range, not minutes.
