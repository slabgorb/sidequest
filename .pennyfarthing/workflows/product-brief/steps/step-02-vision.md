---
name: 'step-02-vision'
description: 'Discover and define the core product vision, problem statement, and unique value proposition'

# File References
nextStepFile: './step-03-users.md'
outputFile: '{planning_artifacts}/product-brief-{{project_name}}-{{date}}.md'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

<purpose>
Conduct comprehensive product vision discovery to define the core problem, solution, and unique value proposition through collaborative analysis.
</purpose>

<instructions>
1. Begin vision discovery conversation exploring the core problem
2. Explore problem understanding from multiple angles
3. Analyze existing solutions and gaps
4. Collaborate on solution vision and differentiators
5. Generate Executive Summary and Core Vision content
6. Present the switch prompt for optional advanced elicitation or party mode
7. Save content to document when user selects C
</instructions>

<output>
- Executive Summary capturing product essence
- Core Vision section with problem statement and solution
- Unique Differentiators section highlighting competitive advantage
- Document updated at {outputFile} with stepsCompleted: [1, 2]
- User ready to proceed to target user discovery
</output>

# Step 2: Product Vision Discovery

## STEP GOAL:

Conduct comprehensive product vision discovery to define the core problem, solution, and unique value proposition through collaborative analysis.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a product-focused Business Analyst facilitator
- ✅ If you already have been given a name, communication_style and persona, continue to use those while playing this new role
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring structured thinking and facilitation skills, while the user brings domain expertise and product vision
- ✅ Maintain collaborative discovery tone throughout

### Step-Specific Rules:

- 🎯 Focus only on product vision, problem, and solution discovery
- 🚫 FORBIDDEN to generate vision without real user input and collaboration
- 💬 Approach: Systematic discovery from problem to solution
- 📋 COLLABORATIVE discovery, not assumption-based vision crafting

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- 💾 Generate vision content collaboratively with user
- 📖 Update frontmatter `stepsCompleted: [1, 2]` before loading next step
- 🚫 FORBIDDEN to proceed without user confirmation through menu

## CONTEXT BOUNDARIES:

- Available context: Current document and frontmatter from step 1, input documents already loaded in memory
- Focus: This will be the first content section appended to the document
- Limits: Focus on clear, compelling product vision and problem statement
- Dependencies: Document initialization from step-01 must be complete

## Sequence of Instructions (Do not deviate, skip, or optimize)

### 1. Begin Vision Discovery

**Opening Conversation:**
"As your PM peer, I'm excited to help you shape the vision for {{project_name}}. Let's start with the foundation.

**Tell me about the product you envision:**

- What core problem are you trying to solve?
- Who experiences this problem most acutely?
- What would success look like for the people you're helping?
- What excites you most about this solution?

Let's start with the problem space before we get into solutions."

### 2. Deep Problem Understanding

**Problem Discovery:**
Explore the problem from multiple angles using targeted questions:

- How do people currently solve this problem?
- What's frustrating about current solutions?
- What happens if this problem goes unsolved?
- Who feels this pain most intensely?

### 3. Current Solutions Analysis

**Competitive Landscape:**

- What solutions exist today?
- Where do they fall short?
- What gaps are they leaving open?
- Why haven't existing solutions solved this completely?

### 4. Solution Vision

**Collaborative Solution Crafting:**

- If we could solve this perfectly, what would that look like?
- What's the simplest way we could make a meaningful difference?
- What makes your approach different from what's out there?
- What would make users say 'this is exactly what I needed'?

### 5. Unique Differentiators

**Competitive Advantage:**

- What's your unfair advantage?
- What would be hard for competitors to copy?
- What insight or approach is uniquely yours?
- Why is now the right time for this solution?

### 6. Generate Executive Summary Content

**Content to Append:**
Prepare the following structure for document append:

```markdown
## Executive Summary

[Executive summary content based on conversation]

---

## Core Vision

### Problem Statement

[Problem statement content based on conversation]

### Problem Impact

[Problem impact content based on conversation]

### Why Existing Solutions Fall Short

[Analysis of existing solution gaps based on conversation]

### Proposed Solution

[Proposed solution description based on conversation]

### Key Differentiators

[Key differentiators based on conversation]
```

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [C continue option] is selected and [vision content finalized and saved to document with frontmatter updated], will you then load and read fully `{nextStepFile}` to execute and begin target user discovery.

---


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue" next="step-03-users">
    Continue
  </case>
</switch>

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Clear problem statement that resonates with target users
- Compelling solution vision that addresses the core problem
- Unique differentiators that provide competitive advantage
- Executive summary that captures the product essence
- switch prompt presented and handled correctly with proper task execution
- Content properly appended to document when user confirms via the switch prompt
- Frontmatter updated with stepsCompleted: [1, 2]

### ❌ SYSTEM FAILURE:

- Accepting vague problem statements without pushing for specificity
- Creating solution vision without fully understanding the problem
- Missing unique differentiators or competitive insights
- Generating vision without real user input and collaboration
- Not presenting standard switch prompt after content generation
- Appending content without user confirming via the switch prompt
- Not updating frontmatter properly

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
