# Rubric Anchors: Behaviorally Anchored Rating Scales

Concrete behavioral exemplars for each judge dimension at each score level. These anchors replace subjective impressions with observable, testable descriptions of response quality.

Each dimension uses five band levels (1-2, 3-4, 5-6, 7-8, 9-10). Anchors describe what a response at that level *does*, not what it *is*.

**Research basis:** PersonaGym (EMNLP 2025) achieves 75% Spearman correlation with human judges via calibrated exemplar responses. Galileo AI's 3-tier rubric taxonomy demonstrates that granular, anchored criteria reduce inter-rater disagreement. Without anchors, LLM judges default to central tendency (scores cluster 6-7).

**Usage:** Referenced by the judge skill (`pf-judge/SKILL.md`) when constructing evaluation prompts. Each dimension carries equal weight (25%).

---

## Correctness

Technical accuracy of the response. Does the agent identify the right issues and propose valid solutions?

**1-2:** Response contains factual errors or misidentifies the core problem. Proposed solutions are broken, invalid, or address the wrong issue entirely. Key requirements are omitted. The agent fails to demonstrate basic understanding of the domain.

**3-4:** Response identifies some relevant issues but misses critical ones. Proposed solutions address surface symptoms rather than root causes. Contains at least one significant technical error or invalid assumption that would produce incorrect results if implemented.

**5-6:** Response correctly identifies the main issue and proposes a reasonable solution. Minor gaps in edge case coverage or secondary concerns, but the core analysis is sound. No critical errors, though some details may be imprecise or incomplete.

**7-8:** Response provides accurate analysis covering both primary and secondary issues. Proposed solutions address root causes and include consideration of edge cases. Demonstrates solid domain knowledge with no factual errors. Implementation guidance is specific and correct.

**9-10:** Expert-level analysis that identifies non-obvious issues others would miss. Solutions are comprehensive and production-ready, covering edge cases, error handling, and downstream implications. Demonstrates nuanced understanding of trade-offs and provides evidence-based reasoning for choices.

## Depth

Thoroughness of analysis. Does the response go beyond surface observations to explain causes and implications?

**1-2:** Surface-level observation that restates the obvious or repeats the problem statement. No analysis of why the issue exists or what its implications are. Provides a shallow description without investigating contributing factors.

**3-4:** Identifies the immediate problem but does not explain why it occurs. Analysis stays at one level — describes what is broken without exploring the causal chain. Missing connections between symptoms and underlying mechanisms.

**5-6:** Identifies root cause with adequate explanation of the causal mechanism. Addresses the primary concern with sufficient context for someone to understand and act. May miss secondary implications or related issues in adjacent areas.

**7-8:** Multi-level analysis that connects symptoms to root causes and explains downstream consequences. Considers how the issue interacts with surrounding systems. Provides context that helps the reader understand not just what to fix but why the current state is problematic.

**9-10:** Multi-layered analysis connecting symptoms to root causes to systemic patterns. Identifies cascading implications across architectural boundaries. Draws connections to broader design principles and explains how the issue fits into larger structural concerns. Anticipates follow-on problems that the current issue will produce.

## Quality

Clarity and actionability of the response. Is the output organized, readable, and directly useful?

**1-2:** Response is disorganized, unclear, or incoherent. Information is presented without structure. Reader cannot determine what action to take. May be verbose without conveying useful content, or so terse that critical context is missing.

**3-4:** Response contains relevant information but is poorly organized. Key points are buried in unnecessary detail. Recommendations lack specificity — the reader must do significant interpretation to extract actionable steps. Structure does not guide the reader's attention.

**5-6:** Response is readable and organized with a clear main point. Recommendations are present but could be more specific or concrete. Adequate for someone familiar with the domain, but may require additional context for others. Generally structured but not optimized for quick comprehension.

**7-8:** Response is well-organized with clear headings or logical flow. Recommendations are specific and actionable — the reader knows exactly what to do next. Balances thoroughness with conciseness. Important points are highlighted and easy to find.

**9-10:** Response is precisely structured for maximum actionability. Every sentence serves a purpose. Recommendations include concrete next steps, code examples where appropriate, and clear priority ordering. Balances comprehensive coverage with focused delivery. A reader can implement the suggestions directly without additional research.

## Persona

Character embodiment and role-appropriate behavior. Does the agent maintain consistent voice and deliver through the character's perspective?

**1-2:** Persona is absent or generic — the response could come from any agent. No character voice, tone, or role-specific perspective is evident. The agent drops character entirely or delivers a sterile, personality-free response with no distinctive style or approach.

**3-4:** Surface-level persona indicated by occasional catchphrases or token references to the character, but the underlying analysis and decision-making show no character influence. Inconsistent tone — shifts between persona and generic voice. Mimicry without internalization.

**5-6:** Character voice is present and recognizable throughout the response. The agent maintains consistent tone and uses role-appropriate language. However, the persona primarily manifests in style rather than substance — the same analysis would emerge regardless of character.

**7-8:** Persona shapes both delivery and approach. The character's perspective visibly influences what the agent prioritizes, how it frames problems, and what solutions it favors. Consistent voice throughout with natural-sounding character language. Role-specific judgment calls align with the character's established behavior patterns.

**9-10:** Deep, authentic embodiment where the character's worldview naturally drives the analysis. The persona is seamlessly internalized — it shapes reasoning, priorities, and communication style without feeling forced. Readers familiar with the character would recognize the voice immediately. The persona adds genuine value by providing a distinctive perspective that enriches the response beyond what a generic agent would produce.
