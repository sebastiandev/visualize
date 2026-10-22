# The doc (`doc.json`) — what you write; `visualize explain doc.json [--facts DIR]` renders it

A doc is a title plus an **ordered list of sections**. Each section names the **view** that draws it
(`visualize views`); its other fields follow that view's `schema.json`, and its `guideline.md` says when to use
it. Pick the views and the order that tell the story; skip the rest. With `--facts`, the renderer adds the
diff, definitions and interface delta from code — you write only judgement.

## Shape
```jsonc
{
  "title": "short title",
  "kind": "new feature | bugfix | migration behind flag | …",            // optional chip
  "flag": {"name": "flag_name", "scope": "per account / global", "ref": "path:line"},   // optional
  "mode": "proposal",                                                   // only for designs (no facts)
  "facts": "../pr-123/facts",                                           // optional: only if not in facts/ beside the doc
  "sections": [
    {"view": "tldr", "text": "≤ 16 words", "ref": "PR description"},
    {"view": "call-path", "title": "Where it changed", "nodes": [...], "fork": {...}},
    {"view": "sequence", "title": "…", "question": "one sentence", "actors": [...], "steps": [...]},
    {"view": "matrix", "title": "Test matrix: …", "question": "…", "columns": [...], "rows": [...]},
    {"view": "interface-changes"},                                       // cards from facts (or authored "cards")
    {"view": "watch", "items": [{"text": "…", "ref": "…"}]}
  ],
  "view_decisions": [{"view": "sequence", "added": true, "why": "≤ 20 words", "jev": 0.73}]
}
```
Every section may have `title` (foldable heading) and `question` (one line under it). Pages written in the
older shape (`tldr`/`locator`/`diagrams`/`examples`/`model_cards`/`watch` at top level) still render.

## Rules
1. **Visual first, almost no text.** `summary` ≤ 8 words. Table `case` ≤ 12 words. Watch items ≤ 16 words. No paragraphs.
2. **Nothing invented.** Every node, row and watch item has a `ref`: head `path:line`, `test: path:line`, or `PR description`.
3. **Call path (`call-path`) = the real path a request takes through the code that this PR touches**, top to bottom, 3–6 nodes.
   Use the exact names from the code (class / function). Link each node to its definitions by name in `defs`
   (names as listed in the facts' `defdiff.json`, e.g. `RecordedShipmentChecker.__call__`). Statuses:
   `new` · `changed` · `moved` (code moved from elsewhere) · `unchanged` (context only, keep ≤ 1).
4. **Fork only when the PR really branches** (feature flag, old vs new path). `fork.at` is the node id where it splits;
   `off` / `on` each have `label`, `layer` (e.g. "flag off"), `status`, `summary`, `ref`, optional `defs`. Omit `fork` otherwise.
5. **Test matrix (`matrix`) = what tests assert**, not what the code might do. One row per case; one column per path/variant
   (or a single "Result" column). A cell is a string (`yes`, `no`, `error`, `untested`, `n/a`) or
   `{"text": "...", "tone": "ok|no|err|untested|na|plain"}` (use `plain` for enum values / reasons).
   `untested` = no test covers that case on that path. Mark rows added by this PR with `"new": true`.
   `question` states what each cell answers, in one sentence.
6. **Watch (`watch`)** = things a reviewer should check (gaps, risky behaviour, description ≠ code). ≤ 3.

Call-path node: `{"id": "x", "label": "ExactName", "layer": "entry|api|command|action|port|adapter|query|db",
"status": "new|changed|moved|unchanged", "summary": "≤ 8 words", "defs": ["Name.method"], "ref": "path:line", "explain": {…}}`.

## Node explanations (`explain`, on every node and fork branch that is not `unchanged`)
Explain the *behaviour*, not the code. ≤ 16 words per item, every item with a `ref`
(head `path:line`; for previous behaviour cite the base side as `base: path:line` or the removed diff line).
```jsonc
"explain": {
  "what":   [{"text": "what it does now", "ref": "path:line"}],          // new: 1–3 items
  "before": [{"text": "previous behaviour", "ref": "base: path:line"}],   // changed / moved: 1–2 items
  "after":  [{"text": "new behaviour", "ref": "path:line"}],              // changed / moved: 1–2 items
  "impact": [{"text": "who/what is affected: callers, data, flag-off path, events", "ref": "…"}]  // 0–3 items
}
```
- `new` → `what` (+ `impact` if callers/data are affected). `changed` → `before` + `after` + `impact`.
- `moved` → `before` says where it lived; `after` says whether behaviour changed while moving (say "no behaviour change" if so).
- No speculation: if the effect isn't visible in code or tests, leave it out.

## Diagram views (optional)
Add a diagram **only when it shows something the call path, test matrix and cards do not**. For each one you add
(or consider and reject), record why in `view_decisions: [{"view": "...", "added": true|false, "why": "≤ 20 words"}]`.
Every element carries a `ref`. ≤ 3 diagrams per page.

**sequence** — who talks to whom, in time order (API → command → DB → events → external). Use for new/changed
operations that cross components, publish events, or call external services.
```jsonc
{"view": "sequence", "title": "…", "question": "one sentence",
 "actors": [{"id": "api", "label": "GraphQL API", "kind": "client|api|command|action|db|events|external", "file": "path"}],   // 3–6 actors
 "steps": [{"from": "api", "to": "cmd", "label": "≤ 6 words", "kind": "call|return|event|write|read",
            "status": "new|changed|unchanged", "branch": "optional frame label, e.g. 'flag on'", "ref": "path:line"}]}  // ≤ 14 steps
```
**decisions** — the checks a request goes through and the outcome of each (guards, failure reasons, flag forks).
Use when there are ≥ 3 distinct outcomes or the order of checks matters.
```jsonc
{"view": "decisions", "title": "…", "question": "one sentence",
 "root": {"label": "check, ≤ 6 words?", "ref": "path:line",
          "children": [{"edge": "yes|no|condition ≤ 4 words", "label": "next check?", "ref": "…", "children": [...]},
                       {"edge": "no", "outcome": "REASON or result", "tone": "ok|err|plain", "ref": "test: path:line"}]}}  // ≤ 16 nodes
```
**entities** — types / tables / inputs / events and their relations, with field-level changes.
Use when the PR adds or changes data shapes (inputs, events, models, migrations).
```jsonc
{"view": "entities", "title": "…", "question": "one sentence",
 "entities": [{"id": "x", "label": "TypeName", "kind": "input|type|event|table|enum|model", "status": "new|changed|unchanged",
               "file": "path", "ref": "path:line",
               "fields": [{"name": "f", "type": "int | None", "status": "new|changed|removed|unchanged", "note": "≤ 8 words"}]}],  // ≤ 8 entities, ≤ 10 fields each; unchanged fields only when needed for context
 "relations": [{"from": "x", "to": "y", "label": "has / becomes / emits …"}]}
```
