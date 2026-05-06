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

- `~/.qwen/settings.json` created fresh (no prior file existed). Contains a single `modelProviders.openai[]` entry for `qwen3-coder:30b` with `baseUrl: http://localhost:11434/v1`, `contextWindowSize: 262144` (256K — the model's native max), and `OLLAMA_API_KEY=ollama` placeholder env value.
- **No `num_ctx` override sent per request.** The original spec/plan called for `extra_body.options.num_ctx: 32768` based on outdated docs warning that Ollama defaults to a 2K context. **Ollama 0.23.1 actually loads this model at its native 262144 (256K) by default** — `ollama ps` confirms `CONTEXT 262144` on a fresh load with no client-side override. Sending a `num_ctx` value in `options` triggers a model reload on every request (~28s cost per call), so the override was removed. See "Key learning" below.

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
- **Cold load with full 256K KV cache allocation**: ~80 seconds (one-time, first request after Ollama service start or model unload)
- **Steady-state single-turn (curl direct, 1-token reply at 256K context)**: **86-162 ms** across three back-to-back calls
- **Multi-tool task end-to-end via qwen CLI** (read sample.py → edit → run → report): **34 seconds wall-clock** for a 4-tool-call sequence at the original 32K config. Most of this is qwen-code CLI process overhead per non-interactive invocation, not inference. Interactive sessions amortize the overhead across many turns.

## Memory footprint

| Loaded context | Resident size | Free of 96 GB |
|---------------:|--------------:|--------------:|
| 32K (initial)  | ~18 GB        | ~78 GB        |
| 256K (current) | ~33 GB        | ~63 GB        |

256K is the model's native max; Ollama allocates the full KV cache at load time. No reason to constrain on this hardware.

## Key learning: Ollama context defaults

The original spec/plan was written assuming Ollama still defaults to `num_ctx: 2048` (a long-standing footgun in older versions). The recommended fix was to send `extra_body.options.num_ctx` per request from qwen-code to override the default.

**Ollama 0.23.1 changes this behavior**: a fresh `ollama serve` + first request to `qwen3-coder:30b` loads the model at the model-card native context (262144 = 256K) by default. `ollama ps` confirms.

Worse, sending `num_ctx` in the request `options` field — even a value within the model's range — triggers a KV cache reallocation. Observed cost: a 1-token reply that ran in ~100 ms with no override took ~28 seconds with `"num_ctx": 131072` in options. Every call paid that penalty.

**Recommendation for any future spec touching Ollama context configuration:**
1. Don't assume the 2K default — check `ollama ps` after a fresh load
2. Configure context size at load time (custom Modelfile with `PARAMETER num_ctx`) if you need to constrain below the model's max, **not** per-request via OpenAI-compat options
3. Per-request `num_ctx` in OpenAI-compat options forces a reload on each call — avoid

This learning applies to ADR-073 / Group E's `OllamaClient` (`sidequest-server`) too: the client should not route `num_ctx` through per-request options if the server's loaded context already covers the prompt size. Worth a follow-up when SideQuest's Ollama backend is exercised.

## Deviations from spec

- **qwen-code CLI was not pre-installed.** The plan flagged this as a possible blocker (Task 4 Step 1) and recommended installing per the qwen-code repo README. Resolution: `npm install -g @qwen-code/qwen-code` (5 packages, completed in 1 second). The local `~/Projects/qwen-code/` checkout was not used for the install — the published package serves the daily-driver use case fine; rebuild from source if needed for development.
- **Tasks 4-5 driven non-interactively.** The plan specified manual TUI interaction for Tasks 4-5, but qwen-code supports a non-interactive prompt mode (positional prompt + `-y` for yolo/auto-approve). All validation was driven via `qwen --auth-type openai --model qwen3-coder:30b -y "<prompt>"` rather than the interactive TUI. Manual TUI verification is a one-line follow-up the user can run any time (`qwen` in a project dir, then `/model` to confirm the entry appears in the picker).

## Bonus capability: Claude Code itself routed at local Qwen

Discovered after the MVP shipped: Ollama 0.23.x ships a built-in `ollama launch claude --model <model>` integration that does the Anthropic-API ↔ Ollama protocol translation in-process. No third-party proxy needed.

Day-to-day usage:

```bash
ollama launch claude --model qwen3-coder:30b
```

This injects `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN=ollama` into Claude Code's environment, points it at a local gateway port the launcher spawns, and starts Claude Code's TUI normally. No `ANTHROPIC_API_KEY` required. Other supported integrations advertised by `ollama launch --help` (as of 0.23.1): `claude-desktop`, `cline`, `codex`, `copilot`, `droid`, `kimi`, `opencode`, `vscode`.

**Validation status:** wiring proven end-to-end via headless smoke test (Read tool fired through the gateway, response returned, ~100-130s cold-start latency dominated by Claude Code TUI startup). Edit/Bash tool validation deferred to first interactive use — Claude Code's headless `--print` mode blocks edits without explicit `--permission-mode bypassPermissions`, which is appropriate behavior; in interactive TUI mode the user approves via prompts as usual.

This capability is **incidental** to the MVP (which targeted qwen-code CLI specifically) but realizes the same goal — a local code editor — through the user's existing daily-driver tool. Worth knowing about for the cross-model "truthiness check" use case: now the user can drive *both* `qwen` and `claude` against the same local model and compare prompting behavior across CLI agents.

## Open follow-ups

- **Verify `/model` picker UX in interactive mode.** The non-interactive path proved the wiring works, but the user has not yet seen the entry render in the TUI's `/model` picker. If for some reason the picker filters this entry (e.g., a settings-key typo this side of the validation didn't catch), it would be a small follow-up fix. Low risk.
- **Sub-project A1** (separate spec): validate `SIDEQUEST_LLM_BACKEND=ollama` end-to-end with the locked-spec model `qwen2.5:7b-instruct` pulled alongside `qwen3-coder:30b`. Independent of this MVP.
- **Sub-project B**: run `sidequest-train` on accumulated corpus; close the MLX → Ollama serving gap (Group F territory).
- **Sub-project C**: structured A/B eval harness — same prompt to both Claude and local Qwen, diff outputs.

## Cost / resource notes

- Disk used: ~18 GB for the model + ~200 MB for Ollama itself.
- Memory: model is ~18 GB resident when loaded; idle eviction default behavior keeps it warm for ~5 min after last call.
- Headroom on this hardware: ~70 GB unified memory still free after model load. Plenty of room to add `qwen2.5:7b-instruct` (~5 GB) and `qwen3:32b` (~20 GB) for future sub-projects without contention.
