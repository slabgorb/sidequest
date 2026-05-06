# Local Qwen Code Editor — As-Installed Notes

**Install date:** 2026-05-06
**Host:** Mac Studio (M3 Ultra, 96GB unified memory), macOS Tahoe 26.4.1
**Spec:** `2026-05-06-local-qwen-code-editor-design.md`
**Plan:** `2026-05-06-local-qwen-code-editor.md`

## Versions

- Ollama: **0.23.1** (Homebrew)
- qwen-code: **0.15.6** (installed via `npm install -g @qwen-code/qwen-code`)
- Model tag pulled: **`qwen3-coder:30b`** (image id `06c1097efce0`)
- Model size on disk: **18 GB**

## Configuration

- `~/.qwen/settings.json` created fresh (no prior file existed). Contains a single `modelProviders.openai[]` entry for `qwen3-coder:30b` with `baseUrl: http://localhost:11434/v1`, `extra_body.options.num_ctx: 32768`, and `OLLAMA_API_KEY=ollama` placeholder env value.

## Validation results

| Step | Result |
|------|--------|
| Ollama service responds on `/api/tags` | ✅ `{"models":[{"name":"qwen3-coder:30b",...}]}` |
| OpenAI-compat `/v1/models` responds | ✅ valid JSON list |
| Native `/api/generate` smoke (1-token reply) | ✅ returns `ready` |
| OpenAI-compat `/v1/chat/completions` smoke | ✅ returns `ready` |
| `qwen --auth-type openai --model qwen3-coder:30b -y "..."` non-interactive single-turn | ✅ returns `ready` |
| Multi-tool round-trip (read + edit + bash + report) | ✅ all four tools fired correctly; output reported accurately |

## Observed latency

- **First-call weight load**: ~5-10 seconds (first `/api/generate` after model pull)
- **Steady-state single-turn smoke** (`Reply with: ready`): a few seconds end-to-end
- **Multi-tool task end-to-end** (read sample.py → edit → run → report): **34 seconds wall-clock** for a 4-tool-call sequence. Comfortably within the spec's "tens of seconds, not minutes" acceptance bar.

## Deviations from spec

- **qwen-code CLI was not pre-installed.** The plan flagged this as a possible blocker (Task 4 Step 1) and recommended installing per the qwen-code repo README. Resolution: `npm install -g @qwen-code/qwen-code` (5 packages, completed in 1 second). The local `~/Projects/qwen-code/` checkout was not used for the install — the published package serves the daily-driver use case fine; rebuild from source if needed for development.
- **Tasks 4-5 driven non-interactively.** The plan specified manual TUI interaction for Tasks 4-5, but qwen-code supports a non-interactive prompt mode (positional prompt + `-y` for yolo/auto-approve). All validation was driven via `qwen --auth-type openai --model qwen3-coder:30b -y "<prompt>"` rather than the interactive TUI. Manual TUI verification is a one-line follow-up the user can run any time (`qwen` in a project dir, then `/model` to confirm the entry appears in the picker).

## Open follow-ups

- **Verify `/model` picker UX in interactive mode.** The non-interactive path proved the wiring works, but the user has not yet seen the entry render in the TUI's `/model` picker. If for some reason the picker filters this entry (e.g., a settings-key typo this side of the validation didn't catch), it would be a small follow-up fix. Low risk.
- **Sub-project A1** (separate spec): validate `SIDEQUEST_LLM_BACKEND=ollama` end-to-end with the locked-spec model `qwen2.5:7b-instruct` pulled alongside `qwen3-coder:30b`. Independent of this MVP.
- **Sub-project B**: run `sidequest-train` on accumulated corpus; close the MLX → Ollama serving gap (Group F territory).
- **Sub-project C**: structured A/B eval harness — same prompt to both Claude and local Qwen, diff outputs.

## Cost / resource notes

- Disk used: ~18 GB for the model + ~200 MB for Ollama itself.
- Memory: model is ~18 GB resident when loaded; idle eviction default behavior keeps it warm for ~5 min after last call.
- Headroom on this hardware: ~70 GB unified memory still free after model load. Plenty of room to add `qwen2.5:7b-instruct` (~5 GB) and `qwen3:32b` (~20 GB) for future sub-projects without contention.
