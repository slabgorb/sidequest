# Demo Script — 37-7

**Slide 2: Problem**
Start here. Say: "Before this fix, if you were building a character and changed your mind about something on the previous screen, clicking Back did absolutely nothing." Open the pre-fix recording or screenshot showing the button click with no state change.

**Slide 3: What We Built**
Transition: "We wired the back button end-to-end." Walk through the character creation flow live (or via recording):
1. Launch the game and start a new character. (~0:30)
2. Advance past the first screen — pick a name or class. (~0:45)
3. Click Back. (~1:00)
4. Show the player returning to the previous screen with their prior selections intact. (~1:15)

*Fallback if live demo fails:* Show Slide 3 with a before/after screenshot pair — left side shows the stuck state, right side shows the working back navigation.

**Slide 4: Why This Approach**
"We fixed it on the server, not with a workaround. Now the UI and server both agree on what 'back' means." No terminal commands needed for this story.

---
