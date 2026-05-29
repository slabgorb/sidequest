# Demo Script — 71-8

**Audience:** Engineering leadership, non-technical stakeholders
**Total time:** ~4 minutes

---

**Slide 1 — Title (0:00–0:20)**
Open on the title slide. Say: "This is a one-point cleanup story — the kind of small, precise fix that keeps our quality gates meaningful. It took four minutes to implement and two minutes to review. Here's what it was and why it matters."

---

**Slide 2 — Problem (0:20–1:00)**
Walk through the problem statement. Point out: "Our type-checker, pyright, found a function where the same variable name was being used for two different *kinds* of data — a single text string and a list of strings. That's like a grocery list that says 'apples' at the top meaning one apple, and then later 'apples' meaning a bag of apples. The function still ran, but pyright correctly refused to call it type-safe."

*If asked to show the actual error:*
```bash
cd ~/Projects/sidequest-server
git show feat/71-8-fix-pyright-reference-presenters-present-magic:sidequest/server/reference_presenters.py | grep -n "rows" | head -20
```
Show that `rows` appears first as a string assignment (`rows = ...` with HTML content) and then as `rows: list[str]` a few lines later.

*Fallback: stay on Slide 2 and describe it verbally.*

---

**Slide 3 — What We Built (1:00–2:00)**
This is a rename, not a build. Reframe: "What we delivered was a precision correction — the kind of surgical fix that only takes four minutes *because* we understood the problem completely before touching anything."

Show the before/after (see Before/After section below, or advance to the Before/After slide). Highlight:
- Old: `rows = "..."` on line 924 (a string), then `rows: list[str]` on line 940 (a list)
- New: `limit_rows = "..."` on line 924 (clearly named), `rows: list[str]` on line 940 (unchanged)

*Live demo option:*
```bash
cd ~/Projects/sidequest-server
git diff develop..feat/71-8-fix-pyright-reference-presenters-present-magic -- sidequest/server/reference_presenters.py
```
Show the diff — two lines changed, both in `present_magic`, both the same variable rename.

*Fallback: show the Before/After slide.*

---

**Slide 4 — Why This Approach (2:00–2:45)**
"We renamed rather than suppressed. A `# type: ignore` comment would have made pyright stop complaining, but it would have left the ambiguous name in place — confusing future developers and hiding the underlying imprecision. The new name, `limit_rows`, is actually clearer than the old one. It tells the next engineer exactly what that variable holds: a formatted string representing hard limits, not a list of items."

---

**Roadmap slide (2:45–3:30)**
See Roadmap & Integration section below.

---

**Questions (3:30–4:00)**
Typical question: "Why did this error exist in the first place?" Answer: "It's a pre-existing issue — the function grew over time and two different developers used the same common name `rows` for different local purposes. These things happen in fast-moving codebases. The value of systematic type-checking is that it finds them."

---
