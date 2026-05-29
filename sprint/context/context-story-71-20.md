---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-20: Fail loud at startup when Postgres schema is behind alembic head — a behind-head DB is a silent landmine

## Business Context

CLAUDE.md's first critical principle is **No Silent Fallbacks** — a
misconfiguration should fail loudly, not mask itself until it surfaces hours later
as a confusing symptom. Playtest 2026-05-28 hit a textbook violation (finding
#G4): the dev DB was stamped at alembic `0001` while head was `0002` (the
`asset_ledger` migration, Story 65-2, was never applied). The server **booted
fine** and ran for many turns; the only symptom was `relation "asset_ledger" does
not exist` on every scene render's ledger write — a failure surfacing deep in a
turn, far from the root cause (a behind-head schema). This story makes a
behind-head DB fail at boot, where it's obvious and cheap to fix, instead of
limping along and exploding mid-game.

## Technical Guardrails

**Provenance — the immediate outage is already resolved** (the driver applied the
migration during the playtest). This story is the **design follow-up**: harden
startup so it can never recur silently.

### The contract to extend

- ADR-115 already fails loud when Postgres is **unreachable** (`MissingDatabaseUrlError`,
  10s pool-wait timeout) — see `sidequest/game/db_config.py` / `db_pool.py`. This
  story extends that contract from "unreachable" to "reachable but schema behind
  head."
- Alembic owns all DDL (`alembic.ini`, `alembic/versions/0001_*`, `0002_asset_ledger.py`).
  Compare `alembic current` vs `alembic heads` via the alembic API against
  `SIDEQUEST_DATABASE_URL`.
- The check belongs in the server startup path (app lifespan / db init), so it
  runs at boot — NOT lazily at first write.

### The decision this story must make and record

- **(A) Assert-and-fail (preferred):** at startup, assert the connected DB's
  alembic revision == heads; fail loud at boot if behind/divergent, naming current
  vs head revision. Migration stays an explicit operator step. Aligns with No
  Silent Fallbacks.
- **(B) Auto-upgrade on boot:** have boot / `just up` run `alembic upgrade head`.
  Convenient, but silently mutating the schema at boot is itself a silent action
  and can surprise on a shared DB.
- **Recommendation leans (A)**, optionally pairing `just up` with an EXPLICIT,
  visible `alembic upgrade head` step the operator sees — not a hidden auto-migrate.

### Constraints

- **No Silent Fallbacks:** whichever option, behavior is explicit; the failure (or
  the auto-upgrade, if B) is loud and logged. No "default open" / silent limp-along.
- **Reuse, don't reinvent:** extend the existing ADR-115 fail-loud startup
  mechanism rather than adding a parallel one.
- See `.pennyfarthing/guides/save-management.md` for migration procedures.

## Scope Boundaries

**In scope:**
- A startup schema-version check comparing alembic current vs heads against the
  configured DB.
- Fail-loud-at-boot behavior (or, if decision B, a loud/opt-outable auto-upgrade).
- A recorded decision (A vs B) with rationale.
- Startup logging of the check result; a test for the behind-head boot path.

**Out of scope:**
- Writing new migrations (the `asset_ledger` migration already exists and is
  applied).
- Changing the persistence substrate / pooling (ADR-115 is complete).
- A general health-check/readiness endpoint beyond the startup assertion.
- The `just up` recipe internals beyond optionally surfacing an explicit migrate
  step (if decision A pairs with it).

## AC Context

1. **Boot-time assertion:** server startup asserts the connected DB's alembic
   revision equals heads; if behind/divergent it fails loud AT BOOT with a clear
   error naming current vs head revision — never deferring to a mid-turn write.
   *Test:* boot against a behind-head DB → loud startup error; boot against a
   head-current DB → clean start.
2. **Actionable message:** the failure tells the operator how to fix it (e.g. run
   `alembic upgrade head` / the relevant `just` recipe).
3. **Decision recorded:** (A) fail-loud-assert vs (B) auto-upgrade, with rationale,
   written into the story/ADR/code comment. If (A): boot/`just up` does not
   silently mutate the schema. If (B): the auto-upgrade is logged loudly and is
   opt-outable.
4. **Reuses ADR-115 contract:** extends the existing fail-loud startup mechanism,
   not a parallel one.
5. **Test coverage:** behind-head DB raises the loud startup error (asserted);
   head-current DB boots clean — failure is at startup, not render-write time.
6. **Logged:** startup logs the schema-version check (current rev, head rev,
   pass/fail) so the operator can see the DB is at head.

## Assumptions

- The alembic API can be queried for current vs heads at startup without
  significant boot-time cost (a single metadata query).
- A test DB can be stamped to a prior revision (or heads withheld) to exercise the
  behind-head path — the test harness already provisions a Postgres test DB
  (`SIDEQUEST_TEST_DATABASE_URL`).
- The same behind-head schema was the sole cause of the `asset_ledger` write
  failures; if other mid-turn write failures shared the cause, this guard surfaces
  them at boot too (worth a cross-check during implementation).
