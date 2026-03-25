# Scale Levels Guide

Pennyfarthing uses scale levels (0-4) to route work to appropriate workflows. Scale levels are aligned with BMAD 6.0 methodology.

## Scale Level Definitions

| Level | Scope | Story Count | Workflow | Required Artifacts |
|-------|-------|-------------|----------|-------------------|
| **0** | fix, bug, typo, small change, patch | 1 | `trivial` | None |
| **1** | simple, basic, small feature, add | 1-10 | `prd` | tech-spec |
| **2** | dashboard, several features, admin panel | 5-15 | `prd` | PRD |
| **3** | platform, integration, complex, system | 12-40 | `prd` | PRD + architecture |
| **4** | enterprise, multi-tenant, multiple products | 40+ | `prd` | Full BMAD process |

## Automatic Detection

When you describe work to Pennyfarthing, the scale level is detected from keywords:

### Level 0 Keywords
- fix, bug, typo, patch, hotfix, small change

### Level 1 Keywords
- simple, basic, small, add, minor

### Level 2 Keywords
- dashboard, admin panel, several, multiple features

### Level 3 Keywords
- platform, integration, complex, system

### Level 4 Keywords
- enterprise, multi-tenant, multiple products

**Priority:** Higher levels take precedence. "Enterprise dashboard" → Level 4.

## Workflow Routing

| Level | Workflow | Description |
|-------|----------|-------------|
| 0 | `trivial` | Direct fix, no planning artifacts |
| 1-4 | `prd` | PRD workflow with gates |

## Required Artifacts

### Level 0: None
Just fix it. No planning documents required.

### Level 1: Tech-Spec
Lightweight PRD producing implementation-ready technical specification.

### Level 2: PRD
Product Requirements Document. Architecture is optional.

### Level 3: PRD + Architecture
Both PRD and architecture documents required. System-level changes need design review.

### Level 4: Full BMAD
Complete BMAD process:
- PRD
- Architecture
- Epics and Stories breakdown
- Implementation Readiness checklist

## User Override

You can always override the detected level:

```bash
# Explicitly set scale level
/pf-workflow start prd --scale 3
```

Or when asked during workflow initiation, specify your preferred level.

## Python API

```python
from pf.workflow import (
    detect_scale_level,
    get_workflow_for_scale_level,
    get_required_artifacts,
    get_scale_level_info,
)

# Detect from description
level = detect_scale_level("build an enterprise platform")  # Returns 4

# Get recommended workflow
workflow = get_workflow_for_scale_level(level)  # Returns "prd"

# Get required artifacts
artifacts = get_required_artifacts(level)  # Returns ["prd", "architecture", "epics-and-stories"]

# Get full metadata
info = get_scale_level_info(level)
# Returns: {"level": 4, "scope": "...", "stories_min": 40, ...}
```

## Examples

| Description | Detected Level | Workflow |
|-------------|----------------|----------|
| "Fix the login bug" | 0 | trivial |
| "Add a logout button" | 1 | prd |
| "Build an admin dashboard" | 2 | prd |
| "New platform for data processing" | 3 | prd |
| "Enterprise multi-tenant SaaS" | 4 | prd |

## Related

- [Workflow Skill](/pf-workflow) - Workflow management commands
- [PRD Workflow](../workflows/prd/) - Full PRD stepped workflow
