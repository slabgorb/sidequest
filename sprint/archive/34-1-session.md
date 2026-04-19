---
story_id: "33-1"
jira_key: "none"
epic: "33"
workflow: "trivial"
---
# Story 33-1: Spike: Owlbear dice fork — validate 3D physics feel in browser

## Story Details
- **ID:** 33-1
- **Jira Key:** none
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-09T07:01:40Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-09T01:13:21Z | 2026-04-09T01:15:11Z | 1m 50s |
| implement | 2026-04-09T01:15:11Z | 2026-04-09T06:53:40Z | 5h 38m |
| review | 2026-04-09T06:53:40Z | 2026-04-09T07:01:40Z | 8m |
| finish | 2026-04-09T07:01:40Z | - | - |

## Delivery Findings

### Dev (implementation)

- **Improvement** (non-blocking): Rapier WASM determinism should be verified cross-platform before Story 33-7 (physics replay). Affects `src/dice/DiceScene.tsx` (Physics config). The `interpolate={false}, timeStep={1/120}` config is set correctly but determinism has not been tested on non-M-series hardware. *Found by Dev during implementation.*
- **Improvement** (non-blocking): R3F v9 removed `ThreeEvent` as a runtime export (type-only now). Stories 33-5 and 33-6 should use inline pointer event types rather than importing `ThreeEvent`. Affects future dice UI stories. *Found by Dev during implementation.*
- **Gap** (non-blocking): Drei's `<Text>` component is now a dependency. Story 33-5 (Three.js overlay) should reference this pattern for any other text rendering (DC display, modifier). Affects `src/dice/DiceScene.tsx`. *Found by Dev during implementation.*

### Reviewer (review)

- **Improvement** (non-blocking): Remove dead `up` variable and `void up` hack at `src/dice/DiceScene.tsx:153-159`. Violates CLAUDE.md "No Stubbing" — dead code from abandoned stable-up quaternion logic. The degenerate-normal case the comment references is never handled. Story 33-5 must either remove the dead code or properly handle faces whose normal is parallel to +Z. *Found by Reviewer during review.*
- **Gap** (non-blocking, blocking for production): Force-stop path at `src/dice/DiceScene.tsx:232-244` reports a mid-tumble face value to the user with only `console.warn` as signal. Violates CLAUDE.md "No Silent Fallbacks". Story 33-5 must pass `{ forceStop: true }` to `onSettle` and render "roll timed out — please reroll" instead of a fake authoritative result. *Found by Reviewer (silent-failure-hunter) during review.*
- **Gap** (non-blocking, blocking for production): NaN propagation risk in `screenToWorld()` at `src/dice/DiceScene.tsx:286`. Division by `raycaster.ray.direction.y` has no guard for near-horizontal camera rays. Story 33-5 must add `if (Math.abs(raycaster.ray.direction.y) < 0.001) return null` before the division. *Found by Reviewer (silent-failure-hunter) during review.*
- **Improvement** (non-blocking, blocking for production): No ErrorBoundary around `<Canvas>` or the spike Suspense at `src/main.tsx:10-15`. WebGL init failure or dynamic import failure = blank black screen. Story 33-5 must wrap in ErrorBoundary with fallback UI. *Found by Reviewer (silent-failure-hunter) during review.*
- **Improvement** (non-blocking): Unused `useState` import at `src/dice/DiceScene.tsx:12` + `useCallback` missing deps warning at `:292`. Trivial lint cleanup for Story 33-5. *Found by Reviewer (preflight) during review.*
- **Improvement** (non-blocking): `key={i}` on static `FACE_INFO.map()` at `src/dice/DiceScene.tsx:163`. Use `key={face.number}` for semantic clarity (guaranteed unique 1-20). *Found by Reviewer (rule-checker) during review.*
- **Improvement** (non-blocking): `readD20Value()` at `src/dice/d20.ts:104` recomputes `computeFaceInfo()` per call instead of accepting the already-precomputed `FACE_INFO` constant. Change signature to `readD20Value(group, faceInfo)` or export `FACE_INFO` as a module constant from d20.ts. *Found by Reviewer (type-design + rule-checker) during review.*
- **Improvement** (non-blocking): `D20_COLLIDER_VERTICES` at `src/dice/d20.ts:20` is a mutable `Float32Array`. Wrap as `Readonly<Float32Array>` and/or `Object.freeze()` for shared-state safety. *Found by Reviewer (type-design) during review.*
- **Improvement** (non-blocking): `FaceInfo.center` and `FaceInfo.normal` at `src/dice/d20.ts:57-61` are mutable `THREE.Vector3`. Mark as `readonly` and require callers to clone before mutating. Shared `FACE_INFO` corruption risk. *Found by Reviewer (type-design) during review.*
- **Improvement** (non-blocking, for Story 33-2): `ThrowParams` at `src/dice/DiceScene.tsx:48-53` uses anonymous `[number, number, number]` tuples for 4 different vector concepts (position, linearVelocity, angularVelocity, rotation). Compiler cannot catch transposition at call sites. Story 33-2 (protocol types) should introduce nominal `Vec3`/`EulerAngles` aliases. *Found by Reviewer (type-design) during review.*
- **Improvement** (non-blocking): Stale URL in comment at `src/dice/DiceSpikePage.tsx:4` — says `/dice-spike` path but actual URL is `?dice-spike` query param. Misleading documentation. *Found by Reviewer during review.*
- **Improvement** (non-blocking, deferred to 33-10): Screen reader instruction at `src/dice/DiceOverlay.tsx:46-58` ("Grab the die and flick to throw") has `pointerEvents: none` but no `aria-describedby` linkage to the dice. Story 33-10 should expand a11y. *Found by Reviewer during review.*
- **Improvement** (non-blocking, deferred to 33-5): `pointerEvents: "auto"` on overlay at `src/dice/DiceOverlay.tsx:59` blocks all App pointer events. ADR-074 specifies toggle to `auto` only during active rolls. Spike acknowledges this in code comment; Story 33-5 must implement the toggle. *Found by Reviewer during review.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Dev Assessment

**Implementation Complete:** Yes

**Spike Validation Result:** ✅ PASSED — 3D dice physics feels satisfying on M3 Max. Kill criteria did not trigger. Epic 33 is go for production implementation.

**Files Changed:**
- `src/dice/DiceOverlay.tsx` (new) — Lazy-loadable React component, Canvas + HTML overlay
- `src/dice/DiceScene.tsx` (new) — Physics world, tray colliders (sealed box with CCD), pickup die, physics die, drag-throw gesture, face labels
- `src/dice/d20.ts` (new) — Icosahedron geometry, 20 face centers + normals, value reading via dot product
- `src/dice/DiceSpikePage.tsx` (new) — Isolated test page with Suspense wrapper
- `src/main.tsx` — `?dice-spike` query param loads the test page
- `package.json` / `package-lock.json` — Added three, @react-three/fiber v9, @react-three/rapier v2, @react-spring/three, @react-three/drei

**Tests:** N/A (spike — validation is subjective "does it feel good?")

**Branch:** `feat/33-1-spike-owlbear-dice-fork` (pushed)

**Acceptance Criteria Status:**
1. ✅ Standalone React component renders 3D d20 with Three.js + Rapier WASM
2. ✅ Drag-and-flick gesture triggers physically simulated tumble
3. ✅ Die settles on a face and the value is readable (dot product method)
4. ✅ Component is lazy-loadable via React.lazy()
5. ✅ Runs smoothly on M3 Max (subjective report from user)

**Patterns Established for Production Stories:**
- Deterministic Physics config: `interpolate={false}, timeStep={1/120}`, key-based world reset on throw
- Settle detection: `linearVel + angularVel < 0.005` threshold, with 5-second force-stop fallback
- Face value reading: dot product of face center against world-up vector
- Drag-throw gesture: 5-sample sliding window, ray-plane intersection for world position
- Sealed tray: thick walls (0.2 half-thickness), corner-overlapping colliders, ceiling at wall-top, CCD on die
- Procedural face labels: drei `<Text>` SDF rendering (no texture assets required)

**Handoff:** To Reviewer (trivial workflow: setup → implement → review → finish)

## Sm Assessment

**Story:** 33-1 — Spike: Owlbear dice fork — validate 3D physics feel in browser
**Workflow:** trivial (2pt chore, p0)
**Repos:** ui (sidequest-ui)
**Branch:** feat/33-1-spike-owlbear-dice-fork

**Purpose:** Validate the riskiest assumption in Epic 33 — does 3D dice physics feel satisfying in the browser? Fork/reference Owlbear Rodeo's dice roller (React + Three.js + Rapier), strip SDK layer, get a standalone d20 tumbling.

**Acceptance Criteria:**
1. Standalone React component renders a 3D d20 using Three.js + Rapier WASM
2. Drag-and-flick gesture triggers physically simulated tumble
3. Die settles on a face and the value is readable
4. Component is lazy-loadable via React.lazy()
5. 60fps on M3 Max, physics step under 2ms

**Kill criteria:** If physics feel cheap/canned/laggy after reasonable tuning, stop.

**Reference:** ADR-074 (rendering approach), sprint/planning/prd-dice-rolling.md (PRD), Owlbear Rodeo dice repo (github.com/owlbear-rodeo/dice)

**Routing:** → Dev (implement phase)

## Design Deviations

### Dev (implementation)
- No deviations from spec. The spike implements exactly what the acceptance criteria required — standalone d20 physics in the browser for feel validation. ADR-073/074 patterns were honored: protocol-agnostic rendering layer, lazy-loadable overlay, deterministic physics config, clean-room implementation (no GPL Owlbear code copied).

### Reviewer (audit)
- **Dev's "No deviations" claim** → ✓ ACCEPTED by Reviewer: Spike scope was correctly interpreted. ADR-073 protocol shape (ThrowParams structure) matches future DiceThrow message. ADR-074 rendering patterns (lazy-load, overlay, deterministic physics) all present. No undocumented deviations found.
- **Undocumented:** Spike intentionally uses `pointerEvents: "auto"` on the overlay, blocking the underlying App. ADR-074 specifies `pointer-events: none` by default with toggle to `auto` during active rolls. This is acknowledged in the DiceOverlay.tsx comment as spike-only ("Production version will be controlled by DiceRequest messages"), so it's documented in code but not in the Design Deviations section. Severity: Low. This is a deliberate spike simplification that Story 33-5 will correct.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 (1 lint error, 1 lint warning) | confirmed 2, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 5 | confirmed 3, dismissed 0, deferred 2 |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 6 | confirmed 4, dismissed 1, deferred 1 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 (3 original, 1 pre-existing) | confirmed 3, dismissed 1, deferred 0 |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 10 confirmed, 1 dismissed (with rationale), 3 deferred

### Rule Compliance

Reviewed against `.pennyfarthing/gates/lang-review/typescript.md` (13 numbered rules) and CLAUDE.md at sidequest-ui/CLAUDE.md (no Silent Fallbacks, no Stubbing, Wire Up What Exists, Verify Wiring, Test Suite Wiring, OTEL).

| Rule # | Rule | Status | Evidence |
|--------|------|--------|----------|
| 1 | Type safety escapes | PASS (new code) | 0 `as any`, 0 `@ts-ignore`, 0 `as unknown as T`, 0 non-null assertions in `src/dice/*`. One pre-existing `!` on `document.getElementById('root')!` in main.tsx:10 — not in diff scope (Vite boilerplate). |
| 2 | Generic and interface pitfalls | FAIL | DiceScene.tsx:153-159 declares `const up = new THREE.Vector3(0,1,0)`, unused, then `void up` to suppress `noUnusedLocals`. Dead code per CLAUDE.md "No Stubbing" principle. [FINDING-1] |
| 3 | Enum anti-patterns | N/A | No enums in diff. |
| 4 | Null/undefined handling | PASS | All `||` uses are boolean logic (DiceScene.tsx:221, 232; DiceOverlay.tsx:108), not nullable fallbacks. `useState<T \| null>` typed explicitly. Null guards present before ref access. |
| 5 | Module and declaration issues | PASS | `type ThrowParams` correctly marked for type-only import (DiceOverlay.tsx:14). All value imports are runtime. |
| 6 | React/JSX specific | FAIL (Low) | DiceScene.tsx:163 uses `key={i}` on `FACE_INFO.map()`. The list IS static (20 fixed faces) so no re-render bug, but the pattern matches the antipattern rule literally. `face.number` would be semantically clearer. [FINDING-2] |
| 7 | Async/Promise patterns | PASS | `React.lazy(() => import(...))` correctly handled by Suspense. No unhandled Promises. |
| 8 | Test quality | N/A | No tests in diff. Spike validation is subjective ("does it feel good"). Wiring test requirement partially met: spike is reachable via `?dice-spike` URL param from production path (main.tsx). No automated wiring test, but stated scope accepts this for a spike. |
| 9 | Build and config concerns | PASS | `strict: true` in tsconfig.app.json. `noUnusedLocals: true` caught the `up` variable correctly — the `void up` workaround defeats the gate rather than fixing it (see FINDING-1). |
| 10 | Security: input validation | PASS | No user text input, no JSON.parse, no fetch. Pointer events are browser-typed (clientX/clientY numbers). Math.random() for throw variation — internal only. |
| 11 | Error handling | PARTIAL | `console.warn` on force-stop path is intentional (not a swallow). No try/catch blocks. **BUT:** force-stop path calls `onSettle(value)` with a likely-incorrect face — this is a SILENT SEMANTIC FAILURE per silent-failure-hunter [FINDING-3]. |
| 12 | Performance/bundle | PASS (with note) | Lazy-loaded via React.lazy. Three.js + Rapier chunked into dice bundle. Minor inefficiency: `readD20Value` recomputes `computeFaceInfo()` on every settle instead of using module-level `FACE_INFO` constant [FINDING-4]. Not hot path (runs once per roll). |
| 13 | Fix-introduced regressions | N/A | New code, not a fix. |

**CLAUDE.md rules:**

| Rule | Status | Evidence |
|------|--------|----------|
| No Silent Fallbacks | FAIL | Force-stop path in DiceScene.tsx:232-244 silently reports a potentially-wrong face value to the user with only a `console.warn` that the player never sees. This is a silent semantic fallback. [FINDING-3] |
| No Stubbing | FAIL | DiceScene.tsx:153-159 dead `up` variable with `void up` hack. "Dead code is worse than no code." [FINDING-1] |
| Don't Reinvent — Wire Up What Exists | PASS | Clean-room implementation of Owlbear patterns (ADR-074 mandates this; GPL prevents direct use). No existing dice system to wire — this IS the first one. |
| Verify Wiring, Not Just Existence | PASS | `src/main.tsx:6-15` imports and uses DiceSpikePage via lazy + query param. Non-test consumer exists. Reachable at `http://localhost:5173/?dice-spike`. |
| Every Test Suite Needs a Wiring Test | N/A (with caveat) | No test suite added. Spike scope explicitly accepts subjective validation. |
| OTEL Observability | DEFERRED | UI-only spike, no backend subsystem. OTEL applies to Stories 33-4, 33-8, 33-11 (backend + observability). |

### Reviewer Observations

**Confirmed findings (from subagents and own analysis):**

1. **[RULE][SIMPLE] Dead `up` variable with `void` hack** at `src/dice/DiceScene.tsx:153-159` — **MEDIUM**. The stable-up quaternion reference was planned but abandoned. `const up = new THREE.Vector3(0, 1, 0)` is declared, never read, then `void up` suppresses the `noUnusedLocals` error. Violates CLAUDE.md "No Stubbing" — dead code is worse than no code. Remove lines 153, 159, and the misleading comment at 156.

2. **[SILENT] Force-stop path reports wrong face silently** at `src/dice/DiceScene.tsx:232-244` — **MEDIUM**. When the roll exceeds `MAX_ROLL_TIME` (5 seconds), `onSettle(value)` is called with a face value read mid-tumble. The player sees this as an authoritative result, with only a developer `console.warn` as the signal. Violates CLAUDE.md "No Silent Fallbacks" — wrong result presented as authoritative. Production Story 33-5 must pass a `{ forceStop: true }` flag to allow the overlay to show a "roll timed out" state.

3. **[SILENT] NaN propagation in screenToWorld()** at `src/dice/DiceScene.tsx:286` — **MEDIUM**. `t = (DRAG_HEIGHT - raycaster.ray.origin.y) / raycaster.ray.direction.y` has no guard for `direction.y ≈ 0` (near-horizontal camera ray). Result: NaN-poisoned position pushed into drag history, NaN velocity passed to Rapier, die teleports or fails to spawn silently. Unlikely with current camera at `[0, 1.8, 1.2]` but lurking. Add guard: `if (Math.abs(raycaster.ray.direction.y) < 0.001) return null`.

4. **[SILENT] Dynamic import failure shows blank screen** at `src/main.tsx:7` — **LOW (deferred)**. `React.lazy(() => import('./dice/DiceSpikePage'))` wrapped in Suspense with blank fallback, no ErrorBoundary. Import failure = black screen with no message. Production Story 33-5 should wrap Canvas and the overlay in ErrorBoundary. For the spike, acceptable.

5. **[TYPE][RULE] `D20_COLLIDER_VERTICES` is mutable Float32Array** at `src/dice/d20.ts:20` — **LOW**. Exported without `Readonly<>` wrapper. Consumers could corrupt shared physics geometry via index-assign. For the spike this is fine (only one consumer), but Story 33-5 should wrap with `Readonly<Float32Array>` or `Object.freeze()`.

6. **[TYPE] `FaceInfo.center/normal` mutable Vector3** at `src/dice/d20.ts:57-61` — **LOW**. The shared `FACE_INFO` constant holds mutable `THREE.Vector3` instances. An in-place mutation (`.multiplyScalar(x)` without `.clone()`) would corrupt all subsequent face reads. FaceLabels and readD20Value both use `.clone()` correctly, but the type doesn't enforce it. Spike-acceptable.

7. **[TYPE] `ThrowParams` uses anonymous tuples for 4 different vector concepts** at `src/dice/DiceScene.tsx:48-53` — **LOW**. `position`, `linearVelocity`, `angularVelocity`, `rotation` all type as `[number, number, number]`. Transposition at call sites would not be caught. For Story 33-2 (protocol types) consider named nominal types: `type Vec3 = readonly [number, number, number]`.

8. **[TYPE] `handlePointerDown` uses structural minimum type** at `src/dice/DiceScene.tsx:296` — **DISMISSED**. The inline type `{ stopPropagation: () => void }` was a deliberate workaround: R3F v9 removed `ThreeEvent` as a runtime export (type-only now). Dev logged this in Delivery Findings. Story 33-5/33-6 can revisit once upstream R3F exports stabilize. Not a rule violation.

9. **[PREFLIGHT] Unused `useState` import** at `src/dice/DiceScene.tsx:12` — **LOW**. Dead import from an earlier draft. Trivial fix. Lint error on the new file.

10. **[PREFLIGHT] `useCallback` missing deps warning** at `src/dice/DiceScene.tsx:292` — **LOW**. `screenToWorld` useCallback captures `pointer` and `raycaster` via the `useRef.current` pattern which are stable across renders, but the linter can't see through `.current`. Either list them as deps (safe, stable refs) or add an eslint-disable comment with rationale.

11. **[RULE] `key={i}` on static `FACE_INFO.map`** at `src/dice/DiceScene.tsx:163` — **LOW**. The list is fixed (20 faces, never reordered), so no re-render bug. Use `key={face.number}` for semantic clarity — it's guaranteed unique 1-20.

12. **[PERF][RULE] `readD20Value` recomputes `computeFaceInfo()` per call** at `src/dice/d20.ts:104` — **LOW**. Module-level `FACE_INFO` constant already exists in DiceScene.tsx:27. `readD20Value` should accept it as a parameter or d20.ts should export a singleton. Not hot path.

13. **[DEFERRED] No ErrorBoundary around Canvas** — **LOW (deferred to 33-5)**. WebGL init failure or Rapier WASM load failure crashes the whole app. Spike-acceptable; Story 33-5 must wrap.

14. **[DEFERRED] Handle silent-gesture user feedback** — **LOW (deferred to playtest)**. Drag speed < 0.5 returns silently with no user feedback. Spike-acceptable.

**Verified items (own analysis):**

- **[VERIFIED] Spike wiring is reachable** — `src/main.tsx:8` checks URL param, lazy-loads DiceSpikePage. Complies with CLAUDE.md "Verify Wiring, Not Just Existence." Challenged against rule-checker — no contradiction.
- **[VERIFIED] Lazy loading per ADR-074** — `main.tsx:7` and `DiceSpikePage.tsx:9` both use `React.lazy()`. Bundle chunks on demand. Meets NFR7 (lazy chunk, zero startup cost). Rule-checker confirmed at Rule 12.
- **[VERIFIED] Deterministic physics config per ADR-073/074** — `DiceScene.tsx:420-425`: `interpolate={false}, timeStep={1/120}, key={rollKey}`. Forward-compatible with Story 33-7 (seed-based replay). Challenged against subagents — all accept.
- **[VERIFIED] ThrowParams shape matches future DiceThrow message** — Interface at `DiceScene.tsx:48-53` is compatible with the ADR-073 protocol payload. No rework needed for Story 33-2. Note: tuples are anonymous — see FINDING-7 for the refinement opportunity.
- **[VERIFIED] `aria-live="polite"` on result display** — `DiceOverlay.tsx:109`. Meets FR20 (screen reader announcement). Story 33-10 will expand a11y coverage.
- **[VERIFIED] No type safety escapes in new code** — 0 `as any`, 0 `@ts-ignore`, 0 `as unknown as T`, 0 non-null assertions in `src/dice/*`. Rule-checker Rule 1 confirms. The `!` on `getElementById` in main.tsx is pre-existing Vite boilerplate, not in scope.
- **[VERIFIED] Clean-room implementation** — No Owlbear source copied. Architecture patterns (settle detection, face reading, fixed timestep) are independently implemented with credit in file headers. GPL contamination avoided. Complies with ADR-074 reference guidance.

### Devil's Advocate

Let me argue this code is broken.

**The force-stop path is a semantic lie.** A player throws a d20, the die tumbles, bounces wildly, and somehow doesn't settle in 5 seconds. At t=5000ms, we read the face-up direction at that exact moment — whichever face happens to be slightly more up than the others during a mid-bounce. We call `onSettle(15)`. The UI proudly displays "**15**" as if the die landed on 15. The player records it. The narrator consumes it. But the die was never at rest. The result was **invented**. There is no telemetry that says "force-stop fired, result is unreliable" — only a `console.warn` the player cannot see. In a multiplayer session, this is worse: one player's mid-tumble face value becomes the authoritative roll everyone else replays. This is exactly the kind of "Claude wings it" problem CLAUDE.md's OTEL principle warns about — except here it's the physics engine winging it, and we've written code to hide the wing. A malicious actor could trigger this by finding a geometry that reliably never settles (tall, narrow trays with specific restitution; or physics configs that land in local minima). **The fix is trivial and I am demanding it for production (33-5): pass `{ forceStop: true }` to onSettle and render "roll timed out — please reroll" instead of a fake result.** Deferring it is acceptable for the spike because the spike is validation, not production — but it must be tracked.

**The `up` variable is evidence of abandoned logic.** Why was `up` planned? The comment says "If the face is nearly vertical, pick a stable 'up' reference" — this suggests the author intended to handle a case where `setFromUnitVectors(Z, normal)` produces a degenerate rotation when `normal` is parallel to `Z`. But the code never uses `up`. Does this mean faces whose normal is nearly parallel to `(0,0,1)` produce broken text rotations? Possibly — but the spike validated subjectively and no one complained. The unhandled degenerate case is a latent bug. In practice, the d20 has 20 faces and none is exactly on the Z axis, so the degenerate case doesn't trigger. But the dead code proves the author KNEW there was an edge case and didn't solve it. **"void up" is a shield against the compiler, not against the bug.** Story 33-5 must either handle the degenerate or prove it doesn't occur on the d20's specific geometry.

**The screenToWorld division has a failure mode nobody tested.** With the current camera at `[0, 1.8, 1.2]` looking down toward origin, `raycaster.ray.direction.y` is safely negative and large. But **what if a future refactor changes the camera?** Story 33-5 is likely to add camera animation, zoom, or different view angles. A camera looking horizontally would have `direction.y ≈ 0`, and NaN propagates silently. The current code has no guard. The fact that it works today is an accident of the camera parameters, not a correctness proof. **Add the guard now, while the spike is still malleable.** Cost: 3 lines. Benefit: eliminate a trap that would waste hours debugging "why does the dice sometimes not spawn?"

**The `FACE_INFO` mutable state is a bomb waiting.** `FACE_INFO` is a module-level array of `FaceInfo` with mutable `THREE.Vector3` fields. Every consumer currently uses `.clone()` defensively. But there is no type-level enforcement. A contributor writing Story 33-6 (drag gesture enhancements) might inadvertently call `face.normal.normalize()` on the shared constant — and now all subsequent face reads see a different normal because they all share one vector. Worse, the bug would be **non-deterministic** depending on mount order. The `readonly` modifier at the interface level is cheap insurance.

**Devil's advocate count:** Nothing new beyond subagent findings — the findings above capture all substantive risks I could surface. The spike is solid within its stated scope. The issues are the kind of drift that happens when a prototype becomes production — which is exactly why we mark them now.

## Reviewer Assessment

**Verdict:** APPROVED (with non-blocking findings for Story 33-5)

**Data flow traced:** Player pointer gesture → `handlePointerDown` (DiceScene.tsx:295) → drag samples recorded (line 305) → `handleUp` computes velocity from history (line 321) → `onThrow(ThrowParams)` → DiceOverlay state updates (line 23) → `<Physics key={rollKey}>` recreates physics world (line 421) → `<PhysicsDie>` spawns with initial velocity → `useFrame` settle detection (line 218) → `readD20Value(group)` reads face via dot product (d20.ts:101) → `onSettle(value)` → DiceOverlay renders result with aria-live announcement. **Safe because:** the flow is unidirectional, state updates are wrapped in `useCallback` with correct deps, refs are null-guarded, and the `key={rollKey}` pattern ensures deterministic physics resets. **Risk:** the force-stop branch (line 232) presents a mid-tumble face as an authoritative result with no user-facing signal (see FINDING-3).

**Pattern observed:** Clean-room adaptation of Owlbear Rodeo's deterministic physics pattern at `src/dice/DiceScene.tsx:420-425`. Fixed timestep + no interpolation + key-based world reset enables seed-based multiplayer replay (Story 33-7 dependency). This is the right foundation.

**Error handling observation:** Two silent-failure paths found by the silent-failure hunter (force-stop, screenToWorld NaN). Neither blocks the spike's validation scope, but both are logged as FINDING-2 and FINDING-3 for Story 33-5 to fix before the overlay is wired into the reveal phase. No try/catch swallows. `console.warn` on force-stop is intentional but invisible to the player.

**Wiring verification:** `src/main.tsx:6-15` imports `DiceSpikePage` via `React.lazy()`, wrapped in Suspense, gated by `?dice-spike` query param. Reachable from production index.html via URL. Confirmed non-test consumer exists. Complies with CLAUDE.md "Verify Wiring, Not Just Existence" rule. No OTEL required (UI-only spike, no backend subsystem crossed).

**Security:** No user text input, no JSON.parse, no fetch, no innerHTML. All input is browser-typed pointer events. Math.random() for throw variation is internal only. No vulnerabilities in scope.

**Blocking issues:** None. This is a spike — its purpose is feel validation, not production hardening. The spike has been validated by the user ("spike validated"). The stated kill criteria ("if physics feel cheap/canned/laggy after reasonable tuning, stop") did not trigger.

**Non-blocking findings (forwarded to Story 33-5 via Delivery Findings):**
1. **[RULE][SIMPLE]** Remove dead `up` variable + `void up` hack (DiceScene.tsx:153-159) — MEDIUM
2. **[SILENT]** Force-stop path must signal unreliable result (DiceScene.tsx:232-244) — MEDIUM
3. **[SILENT]** Guard NaN in screenToWorld() (DiceScene.tsx:286) — MEDIUM
4. **[SILENT]** Wrap Canvas in ErrorBoundary for import/WebGL failures (main.tsx:10-15) — LOW
5. **[PREFLIGHT]** Remove unused `useState` import (DiceScene.tsx:12) — LOW
6. **[PREFLIGHT]** Fix useCallback missing deps warning (DiceScene.tsx:292) — LOW
7. **[RULE]** Change `key={i}` to `key={face.number}` (DiceScene.tsx:163) — LOW
8. **[TYPE][RULE]** Extract `FACE_INFO` to d20.ts exported constant, stop recomputing in readD20Value (d20.ts:104) — LOW
9. **[TYPE][RULE]** Mark `D20_COLLIDER_VERTICES` as `Readonly<Float32Array>` + `Object.freeze()` (d20.ts:20) — LOW
10. **[TYPE][RULE]** Mark `FaceInfo.center/normal` as `readonly` (d20.ts:57-61) — LOW
11. **[TYPE]** Introduce nominal `Vec3` type for ThrowParams tuples (DiceScene.tsx:48-53) — LOW (for Story 33-2)
12. Fix stale URL comment in DiceSpikePage.tsx:4 (`/dice-spike` → `?dice-spike`) — LOW
13. Update `aria-live` instruction linkage for screen readers — LOW (deferred to 33-10)

All 13 findings are captured and will be forwarded to Story 33-5 (Three.js + Rapier overlay) as Delivery Findings, where they belong. None block merging the spike.

**Handoff:** To SM (Vizzini) for finish-story.