# v2 explain page (`page-<N>.json`) — authored content only

The renderer computes the definition diff, the GitHub-style code diff and the interface table from code.
You write only: the call path (which components, in order), the test matrix (from tests), and ≤ 3 watch items.
Reference example: `/Users/seba/src/visualize/spikes/v2/page-50660.json`.

## Rules
1. **Visual first, almost no text.** `summary` ≤ 8 words. Table `case` ≤ 12 words. Watch items ≤ 16 words. No paragraphs.
2. **Nothing invented.** Every node, row and watch item has a `ref`: head `path:line`, `test: path:line`, or `PR description`.
3. **Call path = the real path a request takes through the code that this PR touches**, top to bottom, 3–6 nodes.
   Use the exact names from the code (class / function). Link each node to its definitions by name in `defs`
   (names as listed in `defdiff-<N>.json`, e.g. `RecordedShipmentChecker.__call__`). Statuses:
   `new` · `changed` · `moved` (code moved from elsewhere) · `unchanged` (context only, keep ≤ 1).
4. **Fork only when the PR really branches** (feature flag, old vs new path). `fork.at` is the node id where it splits;
   `off` / `on` each have `label`, `layer` (e.g. "flag off"), `status`, `summary`, `ref`, optional `defs`. Omit `fork` otherwise.
5. **Test matrix = what tests assert**, not what the code might do. One row per case; one column per path/variant
   (or a single "Result" column). A cell is a string (`yes`, `no`, `error`, `untested`, `n/a`) or
   `{"text": "...", "tone": "ok|no|err|untested|na|plain"}` (use `plain` for enum values / reasons).
   `untested` = no test covers that case on that path. Mark rows added by this PR with `"new": true`.
   `question` states what each cell answers, in one sentence.
6. **Watch** = things a reviewer should check (gaps, risky behaviour, description ≠ code). ≤ 3.

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

## Diagrams (optional, `diagrams: [...]`)
Add a diagram **only when it shows something the call path, test matrix and cards do not**. For each one you add
(or consider and reject), record why in `diagram_decisions: [{"kind": "...", "added": true|false, "why": "≤ 20 words"}]`.
Every element carries a `ref`. ≤ 3 diagrams per page.

**sequence** — who talks to whom, in time order (API → command → DB → events → external). Use for new/changed
operations that cross components, publish events, or call external services.
```jsonc
{"type": "sequence", "title": "…", "question": "one sentence",
 "actors": [{"id": "api", "label": "GraphQL API", "kind": "client|api|command|action|db|events|external", "file": "path"}],   // 3–6 actors
 "steps": [{"from": "api", "to": "cmd", "label": "≤ 6 words", "kind": "call|return|event|write|read",
            "status": "new|changed|unchanged", "branch": "optional frame label, e.g. 'flag on'", "ref": "path:line"}]}  // ≤ 14 steps
```
**decisions** — the checks a request goes through and the outcome of each (guards, failure reasons, flag forks).
Use when there are ≥ 3 distinct outcomes or the order of checks matters.
```jsonc
{"type": "decisions", "title": "…", "question": "one sentence",
 "root": {"label": "check, ≤ 6 words?", "ref": "path:line",
          "children": [{"edge": "yes|no|condition ≤ 4 words", "label": "next check?", "ref": "…", "children": [...]},
                       {"edge": "no", "outcome": "REASON or result", "tone": "ok|err|plain", "ref": "test: path:line"}]}}  // ≤ 16 nodes
```
**entities** — types / tables / inputs / events and their relations, with field-level changes.
Use when the PR adds or changes data shapes (inputs, events, models, migrations).
```jsonc
{"type": "entities", "title": "…", "question": "one sentence",
 "entities": [{"id": "x", "label": "TypeName", "kind": "input|type|event|table|enum|model", "status": "new|changed|unchanged",
               "file": "path", "ref": "path:line",
               "fields": [{"name": "f", "type": "int | None", "status": "new|changed|removed|unchanged", "note": "≤ 8 words"}]}],  // ≤ 8 entities, ≤ 10 fields each; unchanged fields only when needed for context
 "relations": [{"from": "x", "to": "y", "label": "has / becomes / emits …"}]}
```

## Shape
```jsonc
{
  "number": 0, "title": "short title", "url": "https://github.com/<owner>/<repo>/pull/N",
  "kind": "new feature | bugfix | migration behind flag | …",
  "tldr": {"text": "≤ 16 words", "ref": "PR description"},
  "flag": {"name": "flag_name", "scope": "per account / global", "ref": "path:line"},          // omit when no flag
  "locator": {"title": "Where it changed",
              "nodes": [{"id": "x", "label": "ExactName", "layer": "entry|api|command|action|port|adapter|query|db",
                         "status": "new|changed|moved|unchanged", "summary": "≤ 8 words", "defs": ["Name.method"], "ref": "path:line"}],
              "fork": {"at": "node id", "off": {...}, "on": {...}}},                                // optional
  "examples": {"title": "Test matrix: …", "question": "one sentence", "case_header": "When…",
               "columns": ["…"], "new_label": "new in this PR",
               "rows": [{"case": "…", "cells": ["yes" | {"text": "REASON", "tone": "plain"}], "new": true, "ref": "test: path:line"}],
               "footnote": {"text": "…", "ref": "…"}},                                            // footnote optional
  "watch": [{"text": "…", "ref": "…"}]
}
```
