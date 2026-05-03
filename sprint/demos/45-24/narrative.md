# 45-24

## Problem

Problem: When the SideQuest app failed to load available game worlds, users relying on screen readers heard a Retry button with no context — the error message ("Could not load worlds. Is the server running?") and the button existed as separate, unconnected elements. Why it matters: A screen reader user tabbing to the Retry button had no way to know *why* they were retrying. They'd have to navigate back to find the error, then return to the button — extra steps that erode trust and usability for anyone using assistive technology.

---

## What Changed

Think of the error message and the Retry button as two sticky notes on a whiteboard. Before this fix, they were side by side but had no arrow connecting them. A sighted person could see they were related; a screen reader user couldn't. We drew the arrow. Technically, we gave the error message a unique name tag (`id="genre-load-error"`) and told the Retry button "your description lives over there" (`aria-describedby="genre-load-error"`). That's the entire change — two attributes, zero visual difference, but now a screen reader announces the error message automatically when the user lands on the Retry button.

---

## Why This Approach

The fix costs almost nothing — two static labels in one file — and follows the standard that browsers and screen readers already understand (ARIA 1.2, the same spec used by every major web platform). We didn't need to restructure the UI, add animations, or touch the server. The error message and Retry button already appeared and disappeared together as a unit; we just made that relationship visible to assistive technology. Two attributes. Zero regressions. All 1,373 existing tests still pass.

---
