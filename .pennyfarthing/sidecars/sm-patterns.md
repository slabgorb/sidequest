## SM Patterns

- **Verify wiring before claiming done.** After `pf sprint story finish`, grep for new exports in production code (exclude tests/). Report wiring check as part of completion summary. Do this automatically — never make Keith ask.
- **Dirty work comparison.** When local dirty files conflict with remote: commit to temp branch → pull clean on default → compare per-file local vs remote diffs → categorize (identical/remote-better/local-has-value/no-remote-change).
- **Gitflow is not optional.** Feature branch → push → PR → merge. Never merge directly to develop or main. All subrepos use develop as base, never main.
- **When a hook blocks a commit:** Run `git status`. Your changes are still there. Fix the issue and recommit. Don't stash, don't blame a linter, don't assume code was lost.
