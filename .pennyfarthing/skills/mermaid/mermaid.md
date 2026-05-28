---
name: mermaid
description: Generate diagrams using Mermaid syntax. Use this skill when creating architecture diagrams, sequence diagrams, ER diagrams, flowcharts, or any visual documentation in markdown files.
---

<run>
Generate Mermaid diagrams by writing code blocks with the `mermaid` language identifier in markdown files. Mermaid syntax is rendered natively by GitHub, GitLab, and most markdown editors. Choose the appropriate diagram type (flowchart, sequence, ER, class, or state) based on what you need to visualize.
</run>

<output>
Mermaid code blocks that render as diagrams. Example output format:

```mermaid
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
```

The diagram renders visually in GitHub, GitLab, and compatible markdown viewers.
</output>

# Mermaid Diagram Skill

## When to Use This Skill

- Documenting system architecture or component relationships
- Visualizing API request/response flows
- Creating database schema diagrams from models
- Illustrating state machines or workflows
- Adding visual documentation to markdown files

## Overview

Mermaid is a JavaScript-based diagramming tool that renders markdown-like syntax into diagrams. GitHub, GitLab, and many markdown editors render Mermaid blocks natively.

**No installation required** for GitHub rendering - just use fenced code blocks with `mermaid` language identifier.

## Prerequisites

### Option 1: GitHub/GitLab (Recommended)
No setup needed. Wrap diagrams in triple backticks with `mermaid` language:

~~~markdown
```mermaid
flowchart LR
    A --> B
```
~~~

### Option 2: Mermaid CLI (Local Rendering)
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i input.mmd -o output.svg
```

### Option 3: VS Code Extension
Install "Markdown Preview Mermaid Support" extension for live preview.

## Flowchart Diagrams

Use for architecture, decision trees, and process flows.

### Basic Syntax
```mermaid
flowchart TD
    A[Rectangle] --> B(Rounded)
    B --> C{Diamond}
    C -->|Yes| D[Result 1]
    C -->|No| E[Result 2]
```

### Direction Options
- `TD` or `TB` - Top to bottom
- `LR` - Left to right
- `BT` - Bottom to top
- `RL` - Right to left

### Architecture Example
```mermaid
flowchart TD
    subgraph Client
        UI[React App]
    end
    subgraph Server
        API[Express API]
        Auth[Auth Service]
    end
    subgraph Data
        DB[(PostgreSQL)]
        Cache[(Redis)]
    end

    UI -->|HTTP| API
    API --> Auth
    API --> DB
    API --> Cache
```

## Sequence Diagrams

Use for API flows, authentication sequences, and message passing.

### Basic Syntax
```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    participant DB as Database

    C->>S: POST /api/users
    S->>DB: INSERT user
    DB-->>S: OK
    S-->>C: 201 Created
```

### Arrow Types
- `->>` Solid line with arrowhead
- `-->>` Dotted line with arrowhead
- `-x` Solid line with X (async)
- `--x` Dotted line with X

### With Loops and Conditionals
```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant Auth as Auth Service

    U->>A: Login request
    A->>Auth: Validate credentials

    alt Valid credentials
        Auth-->>A: Token
        A-->>U: 200 OK + Token
    else Invalid
        Auth-->>A: Error
        A-->>U: 401 Unauthorized
    end

    loop Every 15 minutes
        U->>A: Refresh token
        A-->>U: New token
    end
```

## ER Diagrams

Use for database schemas and entity relationships.

### Basic Syntax
```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : "ordered in"
```

### Cardinality Notation
- `||` - Exactly one
- `o|` - Zero or one
- `}|` - One or more
- `}o` - Zero or more

### With Attributes
```mermaid
erDiagram
    USER {
        int id PK
        string email UK
        string name
        timestamp created_at
    }
    ORDER {
        int id PK
        int user_id FK
        decimal total
        string status
    }
    USER ||--o{ ORDER : places
```

## Class Diagrams

Use for object models and component relationships.

### Basic Syntax
```mermaid
classDiagram
    class User {
        +int id
        +string email
        +login()
        +logout()
    }
    class Order {
        +int id
        +decimal total
        +submit()
    }
    User "1" --> "*" Order : places
```

### Relationship Types
- `<|--` Inheritance
- `*--` Composition
- `o--` Aggregation
- `-->` Association
- `..>` Dependency

## State Diagrams

Use for state machines and workflow states.

### Basic Syntax
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Review : submit
    Review --> Approved : approve
    Review --> Draft : reject
    Approved --> Published : publish
    Published --> [*]
```

### With Nested States
```mermaid
stateDiagram-v2
    [*] --> Active

    state Active {
        [*] --> Idle
        Idle --> Processing : start
        Processing --> Idle : complete
    }

    Active --> Suspended : suspend
    Suspended --> Active : resume
    Active --> [*] : terminate
```

## Best Practices

1. **Keep diagrams focused** - One concept per diagram, split complex systems into multiple diagrams
2. **Use meaningful labels** - `API` not `A`, `Database` not `DB` (unless space-constrained)
3. **Add subgraphs** for grouping related components in flowcharts
4. **Use aliases** in sequence diagrams (`participant C as Client`) for readability
5. **Include cardinality** in ER diagrams - relationships are ambiguous without it
6. **Test rendering** on GitHub before committing - some syntax varies between versions
7. **Link to details** - Diagrams show structure; link to docs for implementation details

## Reference Documentation

- **Official Docs:** https://mermaid.js.org/
- **Live Editor:** https://mermaid.live/
- **GitHub Support:** https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams
- **Syntax Reference:** https://mermaid.js.org/syntax/flowchart.html
