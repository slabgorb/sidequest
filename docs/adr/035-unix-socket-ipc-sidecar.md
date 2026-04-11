# ADR-035: Unix Socket IPC for Python Sidecar

> Retrospective — documents a decision already implemented in the codebase.

## Status
Accepted

> **Note (2026-04):** The Context below lists text-to-speech (Kokoro) and runtime
> ACE-Step music generation among the sidecar's workloads. Both are gone: Kokoro
> TTS has been removed from the system entirely, and ACE-Step is now a build-time
> pipeline (tracks are pre-rendered and played from a library, not generated at
> request time). The Unix socket IPC architecture itself is unchanged; only the
> set of inference workloads it carries has shrunk. Current production traffic
> over the socket is Flux image generation plus lore embedding jobs.

## Context

SideQuest requires ML inference for image generation (Flux), text-to-speech (Kokoro),
music generation (ACE-Step), and sentence embeddings. These workloads are best served by
Python, where model library maturity far exceeds what's available in Rust. However, the
game engine itself belongs in Rust — low latency, memory safety, async concurrency.

The split rule: if it doesn't require ML model inference, it goes in Rust. Python stays
as a sidecar exclusively for model inference, leveraging library maturity (Flux, Kokoro,
ACE-Step) that doesn't yet exist in the Rust ecosystem.

The main IPC question was: how does the Rust game engine talk to the Python daemon?

## Decision

All ML inference runs in a persistent Python daemon process (`sidequest-daemon`) that
communicates with the Rust API via a Unix domain socket at `/tmp/sidequest-renderer.sock`,
using newline-delimited JSON-RPC.

**Protocol shape:**

```json
// Request
{ "id": "uuid", "method": "render_tts", "params": { "text": "...", "voice": "..." } }

// Success response
{ "id": "uuid", "result": { ... } }

// Error response
{ "id": "uuid", "error": "description" }
```

**Python server** (`sidequest_daemon/media/daemon.py`) — `asyncio.start_unix_server`
binds the socket; each method dispatches to the appropriate inference pipeline. A
`render_lock` (`asyncio.Lock` per render type — image, TTS, music) serializes GPU
operations. Models are pre-loaded at daemon startup and held warm in GPU memory across
the entire game session.

**Rust client** (`sidequest-daemon-client/src/client.rs`) — opens `tokio::net::UnixStream`
to the socket path, sends JSON-RPC requests, awaits newline-delimited responses. The
client treats the daemon as a fully separate failure domain.

**Daemon lifecycle:** the daemon stays alive between game sessions. It is never restarted
by the game engine. Models remain in VRAM, eliminating cold-start latency on subsequent
renders.

## Alternatives Considered

- **HTTP/REST sidecar** — rejected. Adds network stack overhead (TCP, HTTP framing) with
  zero benefit for a local-only process. Unix sockets are faster and simpler.
- **gRPC** — rejected. Heavy dependency footprint (protobuf codegen, tonic on Rust side,
  grpcio on Python side) for no meaningful gain over JSON-RPC at these call volumes.
- **Embedding Python via PyO3** — rejected. Adds significant complexity to the Rust build,
  introduces GIL contention risk inside an async runtime, and tightly couples the failure
  domain. A crash in a Flux inference call should not panic the game engine.
- **Shared memory / pipes** — rejected. Harder to frame structured requests/responses;
  no meaningful throughput advantage for request-response workloads.

## Consequences

**Positive:**
- Clean failure isolation — daemon crash does not kill the game engine; the Rust client
  surfaces a `DaemonError` and play continues without media.
- Models stay warm across sessions; no cold-start penalty after first load.
- Python inference code can be updated and restarted independently of the Rust server.
- Serialization cost is negligible — inference time dominates by orders of magnitude.

**Negative:**
- Daemon must be running before API startup; missing socket produces an immediate error
  (intentional — no silent fallback).
- Debugging spans two runtimes; tracing a TTS failure requires checking both OTEL spans
  from Rust and Python logs from the daemon.
- Unix socket is not portable to Windows (not a current concern).
