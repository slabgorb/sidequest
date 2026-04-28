# Image Rendering — Sequence

> One scene image's life, from narrator intent to pixels in the player's gallery.
> Spans server (`sidequest-server`), media daemon (`sidequest-daemon`), and UI
> (`sidequest-ui`). Related ADRs: 035 (Unix socket IPC), 046 (GPU memory budget),
> 050 (image pacing throttle), 070 (MLX renderer).

## System Overview

```mermaid
flowchart LR
    subgraph Server[sidequest-server]
        N[Narrator<br/>Claude CLI]
        O[Orchestrator<br/>VisualScene extract]
        SH[Session Handler<br/>_maybe_dispatch_render]
        TH[ImagePacingThrottle<br/>ADR-050]
        DC[DaemonClient<br/>Unix socket]
        RM[RenderMounts<br/>path to URL]
        WS[WebSocket Room<br/>broadcast]
    end

    subgraph Daemon[sidequest-daemon]
        DSV[Daemon JSON-RPC<br/>render method]
        BF[Beat Filter]
        SI[Scene Interpreter]
        SX[Subject Extractor<br/>fallback Claude CLI]
        PC[Prompt Composer<br/>genre+world catalog]
        ZW[ZImageMLXWorker<br/>mflux, 8 steps]
        FS[(tmpdir<br/>render_uuid.png)]
    end

    subgraph UI[sidequest-ui]
        IB[ImageBusProvider<br/>two-pass merge]
        SG[ScrapbookGallery<br/>img tag, lazy]
    end

    N -->|game_patch| O
    O -->|VisualScene| SH
    SH --> TH
    TH -.suppress.-> SH
    SH -->|RENDER_QUEUED| WS
    SH --> DC
    DC <-->|/tmp/sidequest-renderer.sock| DSV
    DSV --> BF --> SI --> PC --> ZW --> FS
    SI -.miss.-> SX --> PC
    DSV -->|absolute path| DC
    DC --> RM
    RM -->|/renders/...| WS
    WS -->|IMAGE| IB
    WS -->|SCRAPBOOK_ENTRY| IB
    IB --> SG
```

## Phase Map

| Phase | Owner | What happens |
|-------|-------|--------------|
| 1. Origination | Narrator | Emits `visual_scene` block in `game_patch` |
| 2. Dispatch decision | Server | Feature flag, daemon health, throttle check |
| 3. IPC | Server / Daemon | Unix socket JSON-RPC, per-request connection |
| 4. Render pipeline | Daemon | Filter → interpret → compose → MLX render → write file |
| 5. URL resolution | Server | Self-healing static mount, absolute path → `/renders/*` |
| 6. Broadcast | Server | `IMAGE` message to all room players |
| 7. Display | UI | Merge with scrapbook metadata, render in gallery |

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant N as Narrator (Claude)
    participant O as Orchestrator
    participant SH as Session Handler
    participant TH as ImagePacingThrottle
    participant DC as DaemonClient
    participant D as Daemon
    participant ZW as ZImageMLXWorker
    participant FS as Filesystem
    participant RM as RenderMounts
    participant WS as Room (WebSocket)
    participant IB as ImageBusProvider
    participant SG as ScrapbookGallery

    Note over N,SG: Phase 1 — Origination

    N-->>O: game_patch { visual_scene: { subject, tier, mood, tags } }
    O->>SH: NarrationTurnResult.visual_scene

    Note over SH,WS: Phase 2 — Dispatch Decision

    SH->>SH: render_enabled() feature flag
    SH->>SH: daemon socket reachable?
    SH->>TH: should_render()

    alt cooldown active
        TH-->>SH: { render: false, reason: "cooldown_active",<br/>cooldown_remaining_seconds }
        SH->>SH: OTEL: image_pacing.suppressed
        Note over SH: No daemon call.<br/>UI never sees this scene.
    else cleared (first_render or cooldown_elapsed)
        TH-->>SH: { render: true }
        SH->>SH: allocate render_id
        SH->>WS: RENDER_QUEUED { render_id, tier }
        WS-->>IB: RENDER_QUEUED (skipped at narrativeSegments.ts)
        SH->>SH: build params { tier, subject, mood, tags,<br/>location, narration, genre, world,<br/>characters?, pc_descriptor?, subject_name? }
        SH->>SH: asyncio.create_task(_run_render)
        SH->>TH: record_render() (post-dispatch)
    end

    Note over DC,D: Phase 3 — IPC (ADR-035)

    DC->>D: open_unix_connection<br/>/tmp/sidequest-renderer.sock
    DC->>D: { id, method: "render", params }

    Note over D,FS: Phase 4 — Daemon Pipeline (under render_lock)

    alt narration + game_state present
        D->>D: BeatFilter.is_visual_beat()
        alt non-visual beat
            D-->>DC: { status: "skipped", reason: "beat_filter" }
            Note over DC,SH: Background task ends.<br/>No IMAGE message emitted.
        end
    end

    D->>D: SceneInterpreter.interpret() (rule-based StageCue)

    alt no subject extracted
        D->>D: SubjectExtractor (claude -p, 30s timeout)
        Note over D: Returns { subject, tags, tier, mood }<br/>or None on failure.
    end

    alt subject + world + genre + no positive_prompt
        D->>D: PromptComposer.try_compose_prompt_for()
        alt catalog match
            D->>D: set positive_prompt, clip_prompt,<br/>negative_prompt, seed
        else catalog miss
            Note over D: Silent fallback to prose-subject<br/>prompt. Candidate for OTEL miss event.
        end
    end

    D->>ZW: pool.render(params)
    Note over ZW: Z-Image Turbo via mflux<br/>8 steps, CFG 0.0, ~30s on M3 Max<br/>per-process singleton (Story 43-5)
    ZW->>FS: write render_<uuid8>.png to output_dir
    ZW-->>D: { image_url: <absolute>, width, height, elapsed_ms }
    D-->>DC: { id, result: { image_url, width, height, elapsed_ms } }

    Note over DC,RM: Phase 5 — URL Resolution

    DC-->>SH: render reply
    SH->>RM: ensure_render_mount(app, image_url)

    alt root not yet registered
        RM->>RM: register_root() — append to<br/>StaticFiles.all_directories
        RM->>RM: emit render_assets.mount_remounted<br/>(daemon restart self-heal)
    end

    RM-->>SH: /renders/<rel>

    Note over SH,SG: Phase 6 — Broadcast

    SH->>WS: ImageMessage { url, render_id, tier,<br/>width, height, alt?, caption?, handout? }
    WS->>WS: room.broadcast(msg)
    Note over WS: All players in the room<br/>receive the same scene image.

    par Image frame
        WS-->>IB: IMAGE { url, render_id, turn_number, ... }
    and Scrapbook frame (separate, per-turn)
        WS-->>IB: SCRAPBOOK_ENTRY { turn_id, scene_title,<br/>location, npcs, world_facts, image_url? }
    end

    Note over IB,SG: Phase 7 — Display

    IB->>IB: Pass 1 — index SCRAPBOOK_ENTRY by turn_id
    IB->>IB: Pass 2 — for each IMAGE: dedupe by render_id,<br/>merge with scrapbook by turn_number
    IB->>IB: Pass 3 — emit metadata-only cards<br/>for orphan scrapbook rows
    IB-->>SG: GalleryImage[]
    SG->>SG: <img src={url} loading="lazy">
    Note over SG: No service worker, no blob URLs,<br/>no client cache. Browser handles HTTP.
```

## Failure & Suppression Modes

| Path | Where | Player visible? |
|------|-------|-----------------|
| Throttle cooldown | `image_pacing.py:88` | No — OTEL only |
| Daemon unreachable | `_maybe_dispatch_render` health check | No — render skipped |
| Beat filter rejects | `daemon.py:329` | No — empty reply |
| Subject extraction fails | `subject_extractor.py` (Claude CLI 30s timeout) | No — render skipped |
| Catalog miss | `prompt_composer.py` | Yes — styleless prose-subject prompt |
| Daemon restart mid-session | `render_mounts.py:172` | Yes — mount re-registers, next render works |
| Worker exception | `_run_render` task | No — error logged, no IMAGE emitted |

## Tier-Specific Forks

The dispatch builds different params per tier:

- **`portrait`** — adds `subject_name` (initials overlay) and `pc_descriptor` (PC catalog ref `pc:<slug>`); `characters: ["pc:<slug>"]`.
- **`scene_illustration` / `landscape` / `text_overlay` / `fog_of_war`** — base params only.
- **`portrait_square`** — fixed 1024x1024 dimensions per `zimage_config.py`.

> The `cartography` tier and the `MAP_UPDATE` wire pipeline that fed
> `MapOverlay` were removed 2026-04-28 with the rest of the cartography
> subsystem (see ADR-019, superseded). The live world-map view did not
> survive the Rust → Python port (ADR-082). World-topology authoring
> via `world.cartography.yaml` and `CartographyConfig` is unaffected
> and remains owned by ADR-055 (room graph navigation).

## Channels Compared

| Image source | Transport | Display |
|--------------|-----------|---------|
| Scene illustrations, landscapes | `IMAGE` message + `SCRAPBOOK_ENTRY` | `ScrapbookGallery` |
| Character portraits | `PARTY_STATUS.portrait_url` | `CharacterPanel` |
| World hero (lobby) | REST genres metadata | `WorldPreview` |
| Render in flight | `RENDER_QUEUED` | Discarded by client (transient state only) |

## Key Files

| Component | Path |
|-----------|------|
| Narrator visual_scene contract | `sidequest-server/sidequest/agents/orchestrator.py:151` |
| Server dispatcher | `sidequest-server/sidequest/server/websocket_session_handler.py:2072` |
| Throttle (ADR-050) | `sidequest-server/sidequest/server/image_pacing.py` |
| Daemon client | `sidequest-server/sidequest/daemon_client/client.py` |
| Render mounts (URL) | `sidequest-server/sidequest/server/render_mounts.py` |
| Image protocol | `sidequest-server/sidequest/protocol/messages.py:357` (`ImagePayload`), `:710` (`ImageMessage`) |
| Daemon JSON-RPC | `sidequest-daemon/sidequest_daemon/media/daemon.py:327` |
| Beat filter | `sidequest-daemon/sidequest_daemon/renderer/beat_filter.py` |
| Scene interpreter | `sidequest-daemon/sidequest_daemon/media/scene_interpreter.py` |
| Subject extractor | `sidequest-daemon/sidequest_daemon/media/subject_extractor.py` |
| Prompt composer | `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` |
| MLX worker (ADR-070) | `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py` |
| Tier configs | `sidequest-daemon/sidequest_daemon/media/zimage_config.py` |
| GPU memory manager (ADR-046) | `sidequest-daemon/sidequest_daemon/ml/memory_manager.py` |
| Image bus (UI consolidation) | `sidequest-ui/src/providers/ImageBusProvider.tsx` |
| Gallery display | `sidequest-ui/src/components/GameBoard/widgets/ScrapbookGallery.tsx` |
