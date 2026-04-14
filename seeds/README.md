# seeds/ — Creative inputs for sq-world-builder surprise mode

Human-authored backlog of seeds that sq-world-builder can consume in surprise mode (`surprise: true` in step-01-orient). Lives in OQ-1 (NOT sidequest-content) to keep seed-bookkeeping commits separate from generated content PRs.

## Four seed formats

| Format | File | Shape |
|---|---|---|
| **Paragraph** | _inline at runtime_ | Free-form text at step 2. Default, current format. |
| **Photograph** | `photographs/*.{jpg,png}` + caption | Image file + mandatory one-line caption. Naked images are rejected — vision models miscaption without context. |
| **Question** | `questions.yaml` | Single interrogative the pipeline is forbidden from resolving. |
| **Collision pair** | `untried-pairs.yaml` | Two domains that have never been synthesized. |

## How to add seeds

**Photographs** — drop the file into `photographs/` and remember the one-line caption that names the period, place, and what to notice. Example: `1887-mysore-guards.jpg` with caption `"Guards at the Mysore palace, 1887, during the succession dispute. Note the uniform — post-British-treaty but pre-reform."`

**Questions** — append a new row to `questions.yaml`. Must end in `?`, single sentence, genuinely open.

**Collision pairs** — append a new row to `untried-pairs.yaml`. Both halves must be at instance-level granularity (NOT "medieval trade" — "the 1280s Hanseatic herring trade with the Bergen kontor"). If you can immediately imagine the output, the pair is too safe.

## How seeds are consumed

1. In surprise mode, step-02-riff accepts a seed selection (by name or `roll d20` or `surprise me`)
2. For collision pairs, the consumed row gets `consumed: {date}` set; for questions, the same
3. Consumed rows stay in the file — they're a record of what has been tried
4. The consumption commit lives in the `seeds/` path, **separate** from any content-generation commit in `sidequest-content/`

## Why this lives in OQ-1

Seeds are human-authored backlog, not generated content. Keeping them separate from `sidequest-content/genre_packs/` prevents entangling seed bookkeeping with content PRs. A new world's PR shouldn't also be updating `untried-pairs.yaml` — those are different concerns with different review cadences.
