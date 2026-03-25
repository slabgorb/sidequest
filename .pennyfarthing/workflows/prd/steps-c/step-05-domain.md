---
name: 'step-05-domain'
description: 'Explore domain-specific requirements for complex domains (optional step)'

# File References
nextStepFile: './step-06-innovation.md'
outputFile: '{planning_artifacts}/prd.md'
domainComplexityCSV: '../data/domain-complexity.csv'

# Task References
advancedElicitationTask: '{project_root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{project_root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 5: Domain-Specific Requirements (Optional)

<purpose>Explore domain-specific constraints, compliance requirements, and technical considerations for complex domains that shape product requirements.</purpose>

<instructions>Check if domain is marked as high-complexity; if simple domain, skip this step; for complex domains, explore regulatory constraints, industry standards, and technical domain considerations through collaborative dialogue; document domain-specific requirements.</instructions>

<output>Domain-specific requirements documentation including applicable regulatory constraints, industry standards, technical domain considerations, and compliance requirements relevant to the project domain.</output>

**Progress: Step 5 of 13** - Next: Innovation Focus

## STEP GOAL:

For complex domains only that have a mapping in {domainComplexityCSV}, explore domain-specific constraints, compliance requirements, and technical considerations that shape the product.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure the entire file is read
- ✅ ALWAYS treat this as collaborative discovery between PM peers
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a product-focused PM facilitator collaborating with an expert peer
- ✅ We engage in collaborative dialogue, not command-response
- ✅ You bring structured thinking and facilitation skills, while the user brings domain expertise

### Step-Specific Rules:

- 🎯 This step is OPTIONAL - only needed for complex domains
- 🚫 SKIP if domain complexity is "low" from step-02
- 💬 APPROACH: Natural conversation to discover domain-specific needs
- 🎯 Focus on constraints, compliance, and domain patterns

## EXECUTION PROTOCOLS:

- 🎯 Check domain complexity from step-02 classification first
- ⚠️ If complexity is "low", offer to skip this step
- ⚠️ Present the switch prompt after domain requirements defined (or skipped)
- 💾 ONLY save when user confirms via the switch prompt
- 📖 Update output file frontmatter, adding this step name to the end of the list of stepsCompleted
- 🚫 FORBIDDEN to load next step until user confirms via the switch prompt

## CONTEXT BOUNDARIES:

- Domain classification from step-02 is available
- If complexity is low, this step may be skipped
- Domain CSV data provides complexity reference
- Focus on domain-specific constraints, not general requirements

## YOUR TASK:

For complex domains, explore what makes this domain special:
- **Compliance requirements** - regulations, standards, certifications
- **Technical constraints** - security, privacy, integration requirements
- **Domain patterns** - common patterns, best practices, anti-patterns
- **Risks and mitigations** - what could go wrong, how to prevent it

## DOMAIN DISCOVERY SEQUENCE:

### 1. Check Domain Complexity

**Review classification from step-02:**

- What's the domain complexity level? (low/medium/high)
- What's the specific domain? (healthcare, fintech, education, etc.)

**If complexity is LOW:**

Offer to skip:
"The domain complexity from our discovery is low. We may not need deep domain-specific requirements. Would you like to:
- [D] Do domain exploration anyway"

**If complexity is MEDIUM or HIGH:**

Proceed with domain exploration.

### 2. Load Domain Reference Data

**Attempt subprocess data lookup:**

"Your task: Lookup data in {domainComplexityCSV}

**Search criteria:**
- Find row where domain matches {{domainFromStep02}}

**Return format:**
Return ONLY the matching row as a YAML-formatted object with these fields:
domain, complexity, typical_concerns, compliance_requirements

**Do NOT return the entire CSV - only the matching row.**"

**Graceful degradation (if Task tool unavailable):**
- Load the CSV file directly
- Find the matching row manually
- Extract required fields
- Understand typical concerns and compliance requirements

### 3. Explore Domain-Specific Concerns

**Start with what you know:**

Acknowledge the domain and explore what makes it complex:
- What regulations apply? (HIPAA, PCI-DSS, GDPR, SOX, etc.)
- What standards matter? (ISO, NIST, domain-specific standards)
- What certifications are needed? (security, privacy, domain-specific)
- What integrations are required? (EMR systems, payment processors, etc.)

**Explore technical constraints:**
- Security requirements (encryption, audit logs, access control)
- Privacy requirements (data handling, consent, retention)
- Performance requirements (real-time, batch, latency)
- Availability requirements (uptime, disaster recovery)

### 4. Document Domain Requirements

**Structure the requirements around key concerns:**

```markdown
### Compliance & Regulatory
- [Specific requirements]

### Technical Constraints
- [Security, privacy, performance needs]

### Integration Requirements
- [Required systems and data flows]

### Risk Mitigations
- [Domain-specific risks and how to address them]
```

### 5. Validate Completeness

**Check with the user:**

"Are there other domain-specific concerns we should consider? For [this domain], what typically gets overlooked?"

### N. Present MENU OPTIONS

## Domain-Specific Requirements

{{discovered domain requirements}}
```

If step was skipped, append nothing and proceed.

## CRITICAL STEP COMPLETION NOTE

ONLY WHEN [C continue option] is selected and [content saved or skipped], will you then load and read fully `{nextStepFile}` to explore innovation.

---


<switch tool="AskUserQuestion">
  <case value="advanced-elicitation" next="LOOP">
    Advanced Elicitation
  </case>
  <case value="party-mode" next="LOOP">
    Party Mode
  </case>
  <case value="continue" next="step-06-innovation">
    Continue — Save and Proceed to Innovation (Step 6 of 13)
  </case>
</switch>

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Domain complexity checked before proceeding
- Offered to skip if complexity is low
- Natural conversation exploring domain concerns
- Compliance, technical, and integration requirements identified
- Domain-specific risks documented with mitigations
- User validated completeness
- Content properly saved (or step skipped) when user confirms via the switch prompt

### ❌ SYSTEM FAILURE:

- Not checking domain complexity first
- Not offering to skip for low-complexity domains
- Missing critical compliance requirements
- Not exploring technical constraints
- Not asking about domain-specific risks
- Being generic instead of domain-specific
- Proceeding without user validation

**Master Rule:** This step is OPTIONAL for simple domains. For complex domains, focus on compliance, constraints, and domain patterns. Natural conversation, not checklists.
