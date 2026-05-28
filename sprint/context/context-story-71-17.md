---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-17: ADR-092 — resolve scene-harness dev-gate doctrine (Cloudflare-only vs DEV_SCENES env gate)

## Business Context

ADR-092 (Scene Harness — Dev-Gated HTTP Endpoint) decided the fixture-hydration
endpoints would be gated by a `DEV_SCENES=1` environment variable so they carry
**zero production surface**. The code diverged: the endpoints are now *always*
registered, and the `DEV_SCENES` gate was deliberately removed in favor of
Cloudflare Zero Trust access control at the tunnel layer. The code comment is
explicit that the env var "added zero security value."

That may well be the right call — but right now the decision-of-record (ADR-092)
and the deployed reality disagree, and nobody has *ratified* which is correct. This
is a small but real security-surface question: `POST /dev/scene/{name}` can hydrate
an arbitrary fixture into a playable save, so "who can reach it, and how is that
enforced" must be a decision someone made on purpose, not an undocumented drift.
This story closes that loop with a deliberate ruling.

## Technical Guardrails

**Provenance — do NOT re-investigate.** Surfaced by the ADR-accuracy audit
(Architect, 2026-05-28). The reconciliation pass verified the endpoint is mounted
and working (correcting an earlier false "not wired" finding). ADR-092 carries a
2026-05-28 amendment noting the gate divergence. This story is the *decision +
alignment*, not a rediscovery.

### Current state (file:line pinned)

- `sidequest/server/app.py:299-300` — comment: "Always registered — Cloudflare Zero
  Trust gates access at the tunnel layer; the former DEV_SCENES env var added zero
  security value."
- `sidequest/server/app.py:301,305` — `create_scene_harness_router()` imported and
  `app.include_router(...)` unconditionally.
- `sidequest/server/scene_harness_router.py:64` — `POST /dev/scene/{name}`
  (fixture hydrate); `:178` — `GET /dev/scenes` (fixture list).
- ADR-092 Decision still specifies `DEV_SCENES=1` gating + "zero production surface."

### Decision to make (this is the chore)

Pick ONE, then align code + ADR-092 to match:

- **(A) Ratify Cloudflare-Zero-Trust-only.** Accept tunnel-layer gating as
  sufficient. Update ADR-092's Decision (not just the amendment) to record that the
  env gate was retired and why, and confirm no production deployment profile exposes
  `/dev/scene*` without the tunnel in front. Remove any stale `DEV_SCENES`
  references from docs/code.
- **(B) Defense-in-depth.** Re-introduce a lightweight server-side gate
  (env/config flag) *in addition to* Cloudflare, so a misconfigured tunnel doesn't
  expose fixture hydration. Wire it fail-loud (endpoint absent/403 when the flag is
  off), update ADR-092 accordingly.

The Architect's lean is **(A)** if and only if every deployment path that serves
this app sits behind the Zero Trust tunnel; if any path can serve it directly, **(B)**.

### Constraints

- **No silent fallbacks (CLAUDE.md).** Whichever way: the gate behavior must be
  explicit and, if a flag is involved, fail loud (no "default open").
- **Decision-of-record must match reality.** End state: ADR-092 Decision and the
  code agree. No lingering `DEV_SCENES` half-references.
- **Don't break the harness.** The scene fixtures are dev tooling the team uses; the
  endpoints must remain reachable for authorized dev use.

## Scope Boundaries

**In scope:**
- A recorded decision (A or B) on scene-harness gating.
- Aligning `app.py` / `scene_harness_router.py` to the decision (remove stale gate
  refs, or add the defense-in-depth flag).
- Updating ADR-092's Decision section to match (beyond the existing amendment).
- Confirming no production profile exposes `/dev/scene*` unguarded.

**Out of scope:**
- The fixture hydration logic / scene catalog itself (works; not touched).
- The UI scene-picker.
- Broader auth/Zero-Trust architecture beyond this endpoint pair.

## AC Context

1. **Decision recorded:** A or B is chosen and written into ADR-092's Decision
   section (superseding the env-gate language), with rationale.
2. **Code matches decision:** If (A), stale `DEV_SCENES` references removed and a
   note/assertion that the tunnel is the gate; if (B), a fail-loud server-side gate
   is wired (endpoint absent/403 when off) alongside Cloudflare.
3. **No unguarded production surface:** Verified that no deployment profile serves
   `POST /dev/scene/{name}` / `GET /dev/scenes` without the chosen gate in front.
4. **ADR ↔ code parity:** ADR-092 Decision and the implementation no longer
   disagree; the 2026-05-28 amendment is reconciled into the Decision.

### Verification Guidance (trivial workflow)
- Confirm the gating behavior matches the decision (manual check or a small test
  asserting endpoint reachability under the chosen profile).
- Grep confirms no orphaned `DEV_SCENES` references remain after alignment.

### Files to Modify
- `sidequest/server/app.py` — router registration / gate.
- `sidequest/server/scene_harness_router.py` — gate enforcement if (B).
- `docs/adr/092-scene-harness-http-endpoint.md` — Decision section reconciliation.

## Assumptions

- Cloudflare Zero Trust is in fact the access control in front of the deployed app
  (per the app.py comment); if that is not universally true across deployment
  profiles, the decision must be (B).
- This is a low-risk, dev-surface decision (p3); it is filed for hygiene and
  decision-of-record integrity, not because an active exploit is known.
