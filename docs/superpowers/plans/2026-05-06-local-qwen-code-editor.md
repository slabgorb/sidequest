# Local Qwen as Code Editor (MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up Ollama + Qwen3-Coder on the Mac Studio (M3 Ultra, 96GB) and configure `qwen-code` CLI to use it as a daily local code editor.

**Architecture:** Three-layer setup: Ollama (inference runtime, listening on `localhost:11434`) hosts a Qwen3-Coder GGUF model loaded into unified memory; `qwen-code` CLI talks to Ollama's OpenAI-compatible endpoint via a `modelProviders.openai` entry in `~/.qwen/settings.json`. No code changes to qwen-code itself; this is install + configuration + verification.

**Tech Stack:** Homebrew, Ollama, `qwen-code` CLI, `~/.qwen/settings.json`, `jq` for JSON manipulation.

**Reference spec:** `docs/superpowers/specs/2026-05-06-local-qwen-code-editor-design.md`.

**Notes for the executor:**
- This plan installs and configures user-scope tooling on a single Mac. No git worktree is needed; commits in this plan are to `~/Projects/oq-1` only (for the post-validation notes file).
- Several steps (model pull, first inference) take real wall-clock time — minutes, not seconds. That's expected.
- Several steps require the human at the keyboard (running `qwen` interactively). Those are flagged as "**Manual:**" in the step.

---

## Task 1: Install Ollama and start the launchd service

**Files:**
- Modify (system): Homebrew install database, launchd service registry. No repo files touched.

- [ ] **Step 1: Check whether Ollama is already installed**

Run:
```bash
which ollama && ollama --version
```

Expected: either prints `/opt/homebrew/bin/ollama` and a version (skip to Step 4), OR prints nothing and exits non-zero (continue to Step 2).

- [ ] **Step 2: Install Ollama via Homebrew**

Run:
```bash
brew install ollama
```

Expected: download + install completes, exits 0. Re-running `which ollama` now prints a path.

- [ ] **Step 3: Verify install version**

Run:
```bash
ollama --version
```

Expected: prints `ollama version is 0.x.y` (any version is acceptable; record it).

- [ ] **Step 4: Start the Ollama launchd service**

Run:
```bash
brew services start ollama
```

Expected: prints `Successfully started ollama` (or `Service already running` — also fine).

- [ ] **Step 5: Confirm the HTTP server is up**

Run:
```bash
curl -fsS http://localhost:11434/api/tags
```

Expected: prints a JSON object like `{"models":[]}` (empty if no models yet) and exits 0. If `curl` fails with connection refused, wait 2-3 seconds and retry — the service takes a moment to bind on first start.

- [ ] **Step 6: Confirm OpenAI-compat endpoint responds**

Run:
```bash
curl -fsS http://localhost:11434/v1/models
```

Expected: prints a JSON object with an `object: "list"` field. Exit 0. This proves the OpenAI-compatible layer (which qwen-code talks to) is live.

---

## Task 2: Discover the canonical Qwen3-Coder tag and pull the model

**Files:**
- Modify (system): `~/.ollama/models/` (Ollama's local model store). Several GB of disk.

- [ ] **Step 1: List available Qwen3-Coder tags on the Ollama hub**

Open in a browser (or curl, but the web view is easier to scan):
- https://ollama.com/library/qwen3-coder

Expected: a list of available tags (e.g., `30b`, `30b-a3b`, `30b-instruct`, `latest`, with quantization variants like `q4_K_M`, `q8_0`).

**Manual selection criterion:** pick the latest 30B Instruct variant at the default quant (typically `q4_K_M`). Tag name in this plan: **`<TAG>`** — record the exact string you choose. The spec assumed `qwen3-coder:30b`; whatever the canonical equivalent is today, use that.

- [ ] **Step 2: Pull the model**

Run (substituting the chosen tag):
```bash
ollama pull qwen3-coder:30b   # replace with your <TAG> if different
```

Expected: progress bars for download (~18-25 GB depending on quant). Completes successfully. Takes 5-30 minutes depending on connection.

- [ ] **Step 3: Verify the model is registered**

Run:
```bash
ollama list
```

Expected: `qwen3-coder:30b` (or your chosen tag) appears in the table with a non-zero size and recent timestamp.

- [ ] **Step 4: Smoke test inference via the native API**

Run:
```bash
curl -fsS http://localhost:11434/api/generate -d '{
  "model": "qwen3-coder:30b",
  "prompt": "Reply with the single word: ready",
  "stream": false
}' | jq -r '.response'
```

Expected: prints something containing the word `ready` (model may add filler — that's fine). First call pays 5-15s of weight-loading time; subsequent calls are fast. Exit 0. If you get an error like `model not found`, the tag in Step 2 didn't match what you typed here — re-check.

- [ ] **Step 5: Smoke test the OpenAI-compat endpoint**

Run:
```bash
curl -fsS http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3-coder:30b",
    "messages": [{"role": "user", "content": "Reply with the single word: ready"}]
  }' | jq -r '.choices[0].message.content'
```

Expected: same single-word `ready`-containing reply. This confirms the OpenAI-compat path qwen-code will actually use is functional end-to-end.

---

## Task 3: Configure qwen-code with the local model provider

**Files:**
- Create or modify: `~/.qwen/settings.json` (user-scope qwen-code config)
- Backup: `~/.qwen/settings.json.bak.<timestamp>` (created if file already exists)

- [ ] **Step 1: Inspect the current settings file**

Run:
```bash
ls -la ~/.qwen/settings.json 2>/dev/null && echo '---' && cat ~/.qwen/settings.json 2>/dev/null
```

Expected one of:
- File does not exist → no output. Skip Step 2; create fresh in Step 3.
- File exists with content → record the existing keys. You will merge, not overwrite.

- [ ] **Step 2: Back up the existing settings (if any)**

If the file existed in Step 1, run:
```bash
cp ~/.qwen/settings.json ~/.qwen/settings.json.bak.$(date +%Y%m%d-%H%M%S)
ls -la ~/.qwen/settings.json.bak.*
```

Expected: a timestamped backup file appears alongside the original.

- [ ] **Step 3: Write or merge the modelProviders entry**

If `~/.qwen/settings.json` does **not** exist, create it with:

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

Substitute the actual chosen tag from Task 2 if it differs from `qwen3-coder:30b`.

If the file **already exists** with other content, use `jq` to merge non-destructively:

```bash
TMP=$(mktemp)
jq '
  .env.OLLAMA_API_KEY = "ollama"
  | .modelProviders.openai = (
      ((.modelProviders.openai // []) | map(select(.id != "qwen3-coder:30b")))
      + [{
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
        }]
    )
' ~/.qwen/settings.json > "$TMP" && mv "$TMP" ~/.qwen/settings.json
```

This filter (a) sets `OLLAMA_API_KEY` in the env block, (b) replaces any prior entry with the same `id`, and (c) appends the new entry without disturbing other auth types or settings.

- [ ] **Step 4: Verify the settings file is valid JSON**

Run:
```bash
jq . ~/.qwen/settings.json > /dev/null && echo "JSON OK"
```

Expected: prints `JSON OK`. If `jq` reports a parse error, restore the backup from Step 2 and re-do Step 3 carefully.

- [ ] **Step 5: Verify the new entry is present and well-formed**

Run:
```bash
jq '.modelProviders.openai[] | select(.id == "qwen3-coder:30b")' ~/.qwen/settings.json
```

Expected: prints the full provider object, with `baseUrl: "http://localhost:11434/v1"` and the `extra_body.options.num_ctx: 32768` field visible.

---

## Task 4: Smoke-test the wiring — `qwen` CLI talks to local Ollama

**Files:**
- None modified. Interactive verification only.

- [ ] **Step 1: Confirm `qwen` is on PATH**

Run:
```bash
which qwen && qwen --version
```

Expected: a path is printed and a version string is shown. If `qwen` is not on PATH, install it per the qwen-code repo README (out of scope for this plan — the user has the repo and presumably the CLI built/linked already; if not, this plan is blocked until they do).

- [ ] **Step 2: Launch qwen in a scratch directory**

**Manual:** Open a new terminal and run:
```bash
mkdir -p /tmp/qwen-local-smoke && cd /tmp/qwen-local-smoke
qwen
```

Expected: the qwen-code TUI launches. Default auth/model may be Qwen OAuth or whatever is configured globally — that's fine, we're about to switch.

- [ ] **Step 3: Switch to the local model via `/model`**

**Manual:** In the qwen TUI, type:
```
/model
```

Expected: a picker appears listing available models. The new entry **"Qwen3-Coder 30B (local Ollama)"** should be visible. Select it.

If it does **not** appear, the most likely cause is a typo or invalid auth-type key in `settings.json` — the file silently skips invalid entries (per the qwen-code docs warning). Exit, re-check Task 3 Step 5, and re-launch.

- [ ] **Step 4: Send a basic prompt to confirm round-trip**

**Manual:** Type into the qwen TUI:
```
Reply with exactly: ready
```

Expected: the model replies, containing the word `ready`. First reply may take 10-20 seconds (weight load). Subsequent replies should be a few seconds.

If the call errors out:
- "connection refused" → Ollama service died; `brew services restart ollama` and retry
- "model not found" → the `id` in `settings.json` doesn't match a tag in `ollama list`; fix and reload
- timeout → `timeout` in `generationConfig` is too short or the model is loading; retry

- [ ] **Step 5: Exit qwen cleanly**

**Manual:** Press `Ctrl-C` (or whichever exit shortcut the TUI advertises) to leave qwen. The smoke test passed if Step 4 produced a response.

---

## Task 5: Tool round-trip validation

**Files:**
- Create (in scratch dir): `/tmp/qwen-local-smoke/sample.py` (or whatever the agent decides to create), then modify it via the agent.

- [ ] **Step 1: Set up a small target file in the scratch directory**

Run:
```bash
cd /tmp/qwen-local-smoke
cat > sample.py <<'EOF'
def greet(name):
    return "Hello, " + name

print(greet("world"))
EOF
ls -la sample.py
```

Expected: `sample.py` exists, three lines of code visible.

- [ ] **Step 2: Launch qwen and confirm local model is selected**

**Manual:** From the same scratch directory:
```bash
qwen
```

If the local model isn't already the active one, run `/model` and select it (per Task 4 Step 3). Confirm the bottom-of-screen status shows the local provider.

- [ ] **Step 3: Run a multi-tool task**

**Manual:** Type into the qwen TUI:
```
Read sample.py, then change the greet function so it returns "Hello, NAME!" with an exclamation mark. After editing, run the file with `python3 sample.py` and report the output.
```

Expected behaviors to observe (this is the validation):
- The agent issues a **Read** tool call against `sample.py`
- The agent issues an **Edit** (or Write) tool call to modify the file
- The agent issues a **Bash** tool call to run `python3 sample.py`
- The agent reports the captured output (`Hello, world!`)
- No malformed tool calls, no infinite loops, no "I cannot use tools" hedging

- [ ] **Step 4: Inspect the resulting file**

After the agent reports done, **manual** in another terminal:
```bash
cat /tmp/qwen-local-smoke/sample.py
python3 /tmp/qwen-local-smoke/sample.py
```

Expected: the file contains the `!`-suffixed return and running it prints `Hello, world!`.

- [ ] **Step 5: Note the round-trip latency informally**

**Manual:** Recall how long the multi-step task took end-to-end. Record a number — e.g., "~45 seconds for read+edit+bash+report." Acceptance bar from the spec is "tens of seconds, not minutes." If the task took >2 minutes for this trivial scope, something is off (most likely `num_ctx` not being honored — see troubleshooting below).

- [ ] **Step 6: Exit qwen and clean up the scratch directory**

**Manual:** Exit qwen. Then:
```bash
rm -rf /tmp/qwen-local-smoke
```

---

## Task 6: Capture as-installed notes and commit to oq-1

**Files:**
- Create: `~/Projects/oq-1/docs/superpowers/specs/2026-05-06-local-qwen-code-editor-as-installed.md`

This file is the as-built record: the actual model tag pulled, the actual Ollama version, observed latency, and any deviations from the spec. It's small but useful for the follow-up sub-projects (SideQuest backend validation, fine-tune pipeline) which will reference the same Ollama install.

- [ ] **Step 1: Gather the as-installed facts**

Run and capture each output:
```bash
echo "=== Ollama version ==="
ollama --version
echo "=== Installed models ==="
ollama list
echo "=== qwen-code version ==="
qwen --version
echo "=== Settings entry ==="
jq '.modelProviders.openai[] | select(.id | startswith("qwen3-coder"))' ~/.qwen/settings.json
```

- [ ] **Step 2: Write the as-installed notes file**

Create `~/Projects/oq-1/docs/superpowers/specs/2026-05-06-local-qwen-code-editor-as-installed.md` with the following content (substituting actual recorded values where bracketed):

```markdown
# Local Qwen Code Editor — As-Installed Notes

**Install date:** 2026-05-06
**Host:** Mac Studio (M3 Ultra, 96GB unified memory), macOS Tahoe 26.4.1
**Spec:** `2026-05-06-local-qwen-code-editor-design.md`
**Plan:** `2026-05-06-local-qwen-code-editor.md`

## Versions

- Ollama: [version from `ollama --version`]
- qwen-code: [version from `qwen --version`]
- Model tag pulled: [exact tag, e.g. `qwen3-coder:30b`]
- Model size on disk: [from `ollama list`]

## Observed behavior

- First-call weight-load latency: [seconds]
- Steady-state inference latency on a multi-tool task (read + edit + bash): [seconds end-to-end]
- Tool round-trip: [worked / specific failures observed]
- Notable deviations from spec: [none, or describe]

## Open follow-ups

- [Anything surprising encountered during install that future sub-projects should know about]
```

- [ ] **Step 3: Verify the file was written**

Run:
```bash
ls -la ~/Projects/oq-1/docs/superpowers/specs/2026-05-06-local-qwen-code-editor-as-installed.md
head -20 ~/Projects/oq-1/docs/superpowers/specs/2026-05-06-local-qwen-code-editor-as-installed.md
```

Expected: file exists, header content visible.

- [ ] **Step 4: Commit to oq-1**

Run:
```bash
cd ~/Projects/oq-1
git add docs/superpowers/specs/2026-05-06-local-qwen-code-editor-as-installed.md
git commit -m "docs: as-installed notes for local Qwen code editor MVP

Records the actual model tag, versions, and latency observed during
install per the 2026-05-06 spec/plan. Reference for follow-up
sub-projects (SideQuest backend validation, fine-tune pipeline).
"
git status
```

Expected: clean working tree, new commit on `main`.

---

## Troubleshooting reference

These are the most likely failure modes observed in similar setups; address them at the task where they surface, not preemptively.

| Symptom | Likely cause | Fix |
|--------|-------------|------|
| `curl localhost:11434` connection refused | service not started | `brew services start ollama` |
| Local model entry missing from `/model` picker | invalid `authType` key in settings.json | confirm key is exactly `openai` (not `openai-custom`); re-validate `jq .` |
| Agent emits raw text instead of tool calls | model template doesn't expose tool-call grammar | confirm the model tag is an Instruct/tool-trained variant; if a base model was pulled by mistake, pull the Instruct variant |
| Tool calls work but agent loops | `num_ctx` truncating mid-conversation | confirm `extra_body.options.num_ctx: 32768` is in settings.json; if still failing, raise to 65536 |
| First call hangs >60s | weight load on cold model | normal — wait. If still hung after 2 minutes, check `ollama ps` for the model and `tail -F` Ollama's logs (`brew services info ollama` shows path) |
| Latency > 2 minutes for trivial tasks | likely `num_ctx` defaulting to 2048 server-side | see above; verify with `ollama show qwen3-coder:30b --modelfile` to inspect the served context size |

---

## Self-review (writing-plans skill output)

**Spec coverage:**
- §"Inference runtime: Ollama" → Task 1
- §"Model: qwen3-coder:30b" → Task 2
- §"qwen-code configuration" → Task 3
- §"Validation" 3-checkpoint list → Tasks 4, 5
- §"Risks: Ollama tag drift" → Task 2 Step 1 (manual canonical-tag selection)
- §"Risks: tool-call protocol" → Task 5 Steps 3-4 (validation that catches it) + troubleshooting table
- §"Risks: first-load latency" → Task 4 Step 4 + troubleshooting
- §"Success criteria" → Tasks 1.5 + 2.3 + 4 + 5

**Placeholder scan:** No "TBD"/"TODO"/"implement later" remain. Every step has either a concrete command or a manually-flagged interactive instruction with explicit success criteria.

**Type/identifier consistency:** Tag string `qwen3-coder:30b` and identifier `OLLAMA_API_KEY` used consistently across Tasks 2, 3, 4. The "if your chosen tag differs" guidance is repeated where each task uses the tag, so the reader can substitute correctly without back-referencing.
