---
name: 'step-11-polish'
description: 'Optimize and polish the complete PRD document for flow, coherence, and readability'

# File References
nextStepFile: './step-12-complete.md'
outputFile: '{planning_artifacts}/prd.md'
purposeFile: './data/prd-purpose.md'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 11: Document Polish

<purpose>Optimize and polish the complete PRD document for flow, coherence, and readability while preserving all content and requirements.</purpose>

<instructions>Load the entire PRD document; review structure and organization; improve cross-section flow and coherence; enhance readability and clarity; verify all requirements are traceable; polish without removing or modifying core content; optionally gather feedback.</instructions>

<output>Polished PRD document with improved structure, enhanced flow and coherence, clearer writing, and verified completeness of all sections and requirements.</output>

**Progress: Step 11 of 12** - Next: Complete PRD

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 CRITICAL: Load the ENTIRE document before making changes
- 📖 CRITICAL: Read complete step file before taking action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- ✅ This is a POLISH step - optimize existing content
- 📋 IMPROVE flow, coherence, and readability
- 💬 PRESERVE user's voice and intent
- 🎯 MAINTAIN all essential information while improving presentation
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

## EXECUTION PROTOCOLS:

- 🎯 Load complete document first
- 📝 Review for flow and coherence issues
- ✂️ Reduce duplication while preserving essential info
- 📖 Ensure proper ## Level 2 headers throughout
- 💾 Save optimized document
- ⚠️ Present the switch prompt after polish
- 🚫 DO NOT skip review steps

## CONTEXT BOUNDARIES:

- Complete PRD document exists from all previous steps
- Document may have duplication from progressive append
- Sections may not flow smoothly together
- Level 2 headers ensure document can be split if needed
- Focus on readability and coherence

## YOUR TASK:

Optimize the complete PRD document for flow, coherence, and professional presentation while preserving all essential information.

## DOCUMENT POLISH SEQUENCE:

### 1. Load Context and Document

**CRITICAL:** Load the PRD purpose document first:

- Read `{purposeFile}` to understand what makes a great BMAD PRD
- Internalize the philosophy: information density, traceability, measurable requirements
- Keep the dual-audience nature (humans + LLMs) in mind

**Then Load the PRD Document:**

- Read `{outputFile}` completely from start to finish
- Understand the full document structure and content
- Identify all sections and their relationships
- Note areas that need attention

### 2. Document Quality Review

Review the entire document with PRD purpose principles in mind:

**Information Density:**
- Are there wordy phrases that can be condensed?
- Is conversational padding present?
- Can sentences be more direct and concise?

**Flow and Coherence:**
- Do sections transition smoothly?
- Are there jarring topic shifts?
- Does the document tell a cohesive story?
- Is the progression logical for readers?

**Duplication Detection:**
- Are ideas repeated across sections?
- Is the same information stated multiple times?
- Can redundant content be consolidated?
- Are there contradictory statements?

**Header Structure:**
- Are all main sections using ## Level 2 headers?
- Is the hierarchy consistent (##, ###, ####)?
- Can sections be easily extracted or referenced?
- Are headers descriptive and clear?

**Readability:**
- Are sentences clear and concise?
- Is the language consistent throughout?
- Are technical terms used appropriately?
- Would stakeholders find this easy to understand?

### 3. Optimization Actions

Make targeted improvements:

**Improve Flow:**
- Add transition sentences between sections
- Smooth out jarring topic shifts
- Ensure logical progression
- Connect related concepts across sections

**Reduce Duplication:**
- Consolidate repeated information
- Keep content in the most appropriate section
- Use cross-references instead of repetition
- Remove redundant explanations

**Enhance Coherence:**
- Ensure consistent terminology throughout
- Align all sections with product differentiator
- Maintain consistent voice and tone
- Verify scope consistency across sections

**Optimize Headers:**
- Ensure all main sections use ## Level 2
- Make headers descriptive and action-oriented
- Check that headers follow consistent patterns
- Verify headers support document navigation

### 4. Preserve Critical Information

**While optimizing, ensure NOTHING essential is lost:**

**Must Preserve:**
- All user success criteria
- All functional requirements (capability contract)
- All user journey narratives
- All scope decisions (MVP, Growth, Vision)
- All non-functional requirements
- Product differentiator and vision
- Domain-specific requirements
- Innovation analysis (if present)

**Can Consolidate:**
- Repeated explanations of the same concept
- Redundant background information
- Multiple versions of similar content
- Overlapping examples

### 5. Generate Optimized Document

Create the polished version:

**Polishing Process:**
1. Start with original document
2. Apply all optimization actions
3. Review to ensure nothing essential was lost
4. Verify improvements enhance readability
5. Prepare optimized version for review

## SUCCESS METRICS:

✅ Complete document loaded and reviewed
✅ Flow and coherence improved
✅ Duplication reduced while preserving essential information
✅ All main sections use ## Level 2 headers
✅ Transitions between sections are smooth
✅ User's voice and intent preserved
✅ Document is more readable and professional
✅ switch prompt presented and handled correctly
✅ Polished document saved when user confirms via the switch prompt

## FAILURE MODES:

❌ Loading only partial document (leads to incomplete polish)
❌ Removing essential information while reducing duplication
❌ Not preserving user's voice and intent
❌ Changing content instead of improving presentation
❌ Not ensuring ## Level 2 headers for main sections
❌ Making arbitrary style changes instead of coherence improvements
❌ Not presenting switch prompt for user approval
❌ Saving polished document without user confirming via the switch prompt

❌ **CRITICAL**: Reading only partial step file - leads to incomplete understanding and poor decisions
❌ **CRITICAL**: Proceeding with 'C' without fully reading and understanding the next step file
❌ **CRITICAL**: Making changes without complete understanding of document requirements

<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue-to-complete-prd" next="step-12-complete">
    Continue to Complete PRD (Step 12 of 12)
  </case>
</switch>
