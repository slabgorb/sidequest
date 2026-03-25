---
name: 'step-e-01b-legacy-conversion'
description: 'Legacy PRD Conversion Assessment - Analyze legacy PRD and propose conversion strategy'

# File references (ONLY variables used in this step)
nextStepFile: './step-e-02-review.md'
prdFile: '{prd_file_path}'
prdPurpose: '{project_root}/src/modules/bmm/workflows/2-plan-workflows/prd/data/prd-purpose.md'
---

# Step E-1B: Legacy PRD Conversion Assessment

<purpose>Analyze legacy PRD against BMAD standards, identify gaps and improvement opportunities, propose conversion strategy, and let user choose conversion approach.</purpose>

<instructions>Load and analyze legacy PRD structure; compare against BMAD standard sections and formatting; identify missing sections, gaps, and improvement opportunities; propose conversion strategy options; present user with conversion choices (full conversion, incremental editing, hybrid approach).</instructions>

<output>Comprehensive legacy PRD analysis with gap assessment, conversion strategy proposal, and user-selected approach for proceeding with edits.</output>

## STEP GOAL:

Analyze legacy PRD against BMAD standards, identify gaps, propose conversion strategy, and let user choose how to proceed.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a Validation Architect and PRD Improvement Specialist
- ✅ If you already have been given communication or persona patterns, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring BMAD standards expertise and conversion guidance
- ✅ User brings domain knowledge and edit requirements

### Step-Specific Rules:

- 🎯 Focus ONLY on conversion assessment and proposal
- 🚫 FORBIDDEN to perform conversion yet (that comes in edit step)
- 💬 Approach: Analytical gap analysis with clear recommendations
- 🚪 This is a branch step - user chooses conversion path

## EXECUTION PROTOCOLS:

- 🎯 Analyze legacy PRD against BMAD standard
- 💾 Identify gaps and estimate conversion effort
- 📖 Present conversion options with effort estimates
- 🚫 FORBIDDEN to proceed without user selection

## CONTEXT BOUNDARIES:

- Available context: Legacy PRD, user's edit requirements, prd-purpose standards
- Focus: Conversion assessment only (not actual conversion)
- Limits: Don't convert yet, don't validate yet
- Dependencies: Step e-01 detected legacy format and routed here

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Attempt Sub-Process Assessment

**Try to use Task tool with sub-agent:**

"Perform legacy PRD conversion assessment:

**Load the PRD and prd-purpose.md**

**For each BMAD PRD section, analyze:**
1. Does PRD have this section? (Executive Summary, Success Criteria, Product Scope, User Journeys, Functional Requirements, Non-Functional Requirements)
2. If present: Is it complete and well-structured?
3. If missing: What content exists that could migrate to this section?
4. Effort to create/complete: Minimal / Moderate / Significant

**Identify:**
- Core sections present: {count}/6
- Content gaps in each section
- Overall conversion effort: Quick / Moderate / Substantial
- Recommended approach: Full restructuring vs targeted improvements

Return conversion assessment with gap analysis and effort estimate."

**Graceful degradation (if no Task tool):**
- Manually check PRD for each BMAD section
- Note what's present and what's missing
- Estimate conversion effort
- Identify best conversion approach

### 2. Build Gap Analysis

**For each BMAD core section:**

**Executive Summary:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**Success Criteria:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**Product Scope:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**User Journeys:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**Functional Requirements:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**Non-Functional Requirements:**
- Present: [Yes/No/Partial]
- Gap: [what's missing or incomplete]
- Effort to Complete: [Minimal/Moderate/Significant]

**Overall Assessment:**
- Sections Present: {count}/6
- Total Conversion Effort: [Quick/Moderate/Substantial]
- Recommended: [Full restructuring / Targeted improvements]

### 3. Present Conversion Assessment

Display:

"**Legacy PRD Conversion Assessment**

**Current PRD Structure:**
- Core sections present: {count}/6
{List which sections are present/missing}

**Gap Analysis:**

{Present gap analysis table showing each section's status and effort}

**Overall Conversion Effort:** {effort level}

**Your Edit Goals:**
{Reiterate user's stated edit requirements}

**Recommendation:**
{Based on effort and user goals, recommend best approach}

**How would you like to proceed?**"

### 5. Document Conversion Strategy

Store conversion decision for next step:

- **Conversion mode:** [Full restructuring / Targeted improvements / Both]
- **Edit requirements:** [user's requirements from step e-01]
- **Gap analysis:** [summary of gaps identified]

Display: "**Conversion Strategy Documented**

Mode: {conversion mode}
Edit goals: {summary}

**Proceeding to deep review...**"

Load and execute {nextStepFile} (step-e-02-review.md)

---

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All 6 BMAD core sections analyzed for gaps
- Effort estimates provided for each section
- Overall conversion effort assessed correctly
- Clear recommendation provided based on effort and user goals
- User chooses conversion strategy (restructure/targeted/both)
- Conversion strategy documented for next step

### ❌ SYSTEM FAILURE:

- Not analyzing all 6 core sections
- Missing effort estimates
- Not providing clear recommendation
- Auto-proceeding without user selection
- Not documenting conversion strategy

**Master Rule:** Legacy PRDs need conversion assessment so users understand the work involved and can choose the best approach.
