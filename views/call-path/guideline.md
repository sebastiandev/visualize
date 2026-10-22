# call-path

A path through components (3–6 boxes) with an optional fork; select a box to see what it does, before/after, impact, signature and its diff or source.

## Use when
- explain: the change (or the code) sits on a path a request or job takes through layers.
- present: the design adds a step to an existing flow.
Not for a pure data-shape change (use entities) or a set of rules (use decisions).

## Ask (present)
- Which entry point should the path start from?

## Extract (explain)
Real path through what changed, exact names; statuses new|changed|moved|unchanged; `defs` = names from defdiff.json so the panel shows the diff; `explain` on every non-unchanged node: new → what, changed → before/after (+ impact), ≤ 16 words per item; `fork` only when the code really branches.
