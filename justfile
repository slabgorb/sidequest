# SideQuest Orchestrator — Cross-repo task runner

# API (Rust backend)
api-test:
    cd sidequest-api && cargo test

api-build:
    cd sidequest-api && cargo build

api-release:
    cd sidequest-api && cargo build --release

api-run:
    cd sidequest-api && cargo run

api-lint:
    cd sidequest-api && cargo clippy -- -D warnings

api-fmt:
    cd sidequest-api && cargo fmt

api-check:
    cd sidequest-api && cargo fmt --check && cargo clippy -- -D warnings && cargo test

# UI (React frontend)
ui-dev:
    cd sidequest-ui && npm run dev

ui-test:
    cd sidequest-ui && npx vitest run

ui-build:
    cd sidequest-ui && npm run build

ui-lint:
    cd sidequest-ui && npm run lint

ui-install:
    cd sidequest-ui && npm install

# Cross-repo
check-all: api-check ui-lint ui-test

status:
    @echo "=== API ===" && cd sidequest-api && git status --short
    @echo "=== UI ===" && cd sidequest-ui && git status --short
    @echo "=== Orchestrator ===" && git status --short
