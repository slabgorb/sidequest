---
id: 46
title: "GPU Memory Budget Coordinator"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [transport-infrastructure]
implementation-status: live
implementation-pointer: null
---

# ADR-046: GPU Memory Budget Coordinator

> Retrospective — documents a decision already implemented in the codebase.

## Context
The media daemon runs three ML backends: Flux (image generation, ~24GB), ACE-Step (music generation, ~16GB), and Kokoro (TTS, ~2GB). On Apple Silicon M3 Max with 128GB unified memory, these share a single physical memory pool — there is no separate VRAM. An 80GB budget is allocated to ML models, leaving headroom for OS, UI, and game process.

Without coordination, loading Flux while ACE-Step is already resident can exceed the budget and trigger kernel-level memory pressure: swapping, slowdowns, or OOM kills. The models can't all live in memory simultaneously at peak, but they don't all need to be active simultaneously either — TTS runs continuously, image generation runs at scene transitions, music generation runs at session start and major beats.

## Decision
A `ModelMemoryManager` maintains a registry of loaded models and their declared memory footprints. Before loading any model, a backend requests the budget allocation. If the load would exceed the 80GB ceiling, the manager evicts the least-recently-used loaded model by calling `shutdown()` on it, then approves the load.

```python
class ModelMemoryManager:
    BUDGET_GB = 80.0

    def request_load(self, model_id: str, size_gb: float) -> None:
        while self._used_gb() + size_gb > self.BUDGET_GB:
            lru = self._evict_lru()
            lru.shutdown()
        self._registry[model_id] = ModelEntry(size_gb=size_gb, last_used=now())

    def touch(self, model_id: str) -> None:
        self._registry[model_id].last_used = now()
```

Each ML backend registers its footprint at init and calls `touch()` on every inference request. LRU order reflects actual usage recency, not load order.

The 80GB constant is hardware-specific and declared as a named constant — it is not a default, not a config value, not auto-detected. It is a deployment assumption for the dev machine.

Implemented in `sidequest_daemon/ml/memory_manager.py`.

## Alternatives Considered

- **Load all models at startup** — Exceeds the 80GB budget. Flux + ACE-Step + Kokoro exceeds ~42GB combined, but with OS and game process overhead and memory fragmentation, full concurrent residency causes pressure events.
- **Load/unload per request (no LRU)** — Every request pays the cold start penalty (10-30 seconds for Flux). Unacceptable for scene transition latency.
- **Separate GPU processes with fixed allocation** — Not possible on Apple Silicon unified memory. The OS doesn't partition unified memory into per-process GPU quotas; all ML frameworks draw from the same pool.
- **Auto-detect available memory** — Unreliable. OS-reported free memory doesn't account for GPU framework allocations or memory fragmentation. An explicit budget is predictable; auto-detection produces intermittent failures.

## Consequences

**Positive:**
- OOM kills eliminated: the manager guarantees the budget ceiling is never exceeded by coordinated allocation.
- LRU keeps the most-used model (Kokoro for TTS) resident, minimizing eviction frequency.
- `shutdown()` contract gives each backend a clean teardown path — no leaked GPU allocations.
- Adding a fourth ML backend requires only registering its footprint; no coordination logic changes.

**Negative:**
- 80GB constant is hardcoded to dev machine specs — deployment to different hardware requires a code change, not a config change.
- Eviction is synchronous in the request path — the requesting backend blocks until `shutdown()` completes on the evicted model.
- No preemptive warming: the manager doesn't predict upcoming loads (e.g., pre-load Flux when combat starts), it only reacts to requests.
- Footprint declarations are self-reported by backends — an inaccurate declaration can still cause budget overrun.
