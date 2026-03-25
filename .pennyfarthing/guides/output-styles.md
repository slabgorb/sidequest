# Output Styles

<info>
Configurable response styles that control how agents communicate. Output styles adjust verbosity, tone, and formatting without changing agent behavior or capabilities.
</info>

## Overview

Output styles are markdown files in `pennyfarthing-dist/output-styles/` that agents load to adjust their communication style. They don't change what agents do — they change how they talk about it.

## Available Styles

### Terse

Minimal, efficient output for experienced users.

- Brief responses — only what's necessary
- Skip explanations, assume context
- Bullet points over paragraphs
- Code output without commentary

### Verbose

Detailed, educational explanations throughout.

- Walk through reasoning step by step
- Explain context and trade-offs
- Document decisions and alternatives
- Cover edge cases and related considerations

### Teaching

Explain reasoning and teach as you go.

- Show your work — explain decisions
- Point out reusable patterns and principles
- Suggest alternatives with trade-offs
- Build understanding by connecting concepts
- Collaborative tone, not lecturing

## Configuration

Set the output style in `.pennyfarthing/config.local.yaml`:

```yaml
output_style: terse    # terse | verbose | teaching
```

When no style is configured, agents use their default communication patterns.

## How It Works

During prime activation, the output style file is loaded and injected into the agent's system prompt alongside the agent definition and persona. The style acts as a behavioral modifier — it constrains how the agent formats and presents its output.

## Key Files

| File | Purpose |
|------|---------|
| `pennyfarthing-dist/output-styles/terse.md` | Minimal output style |
| `pennyfarthing-dist/output-styles/verbose.md` | Detailed output style |
| `pennyfarthing-dist/output-styles/teaching.md` | Educational output style |

## Creating Custom Styles

Add a markdown file to `pennyfarthing-dist/output-styles/` with guidelines for the agent to follow. The file name (without `.md`) becomes the style identifier used in config.
