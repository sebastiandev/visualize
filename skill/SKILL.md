---
name: visualize
description: Explain code, a change (local branch, a diff you have, or a PR) or a design as a self-contained interactive HTML page — call path with forks, per-node explanations, GitHub-style diffs, test matrix, interface changes, diagrams. Use when asked to visualize, explain or diagram code, a PR or a change, or to present a design.
---

# Visualize: a vocabulary for explaining code, changes and designs

**You decide how to explain. The tool renders.** The blocks below are a vocabulary — use the ones that
serve your explanation, in the order that tells the story best, and skip the rest. There is no single
correct interpretation; pick the framing a reader needs (a request path, a lifecycle, a data flow, a set of
rules, a comparison…).

| Block (`page.json`) | Use it to show |
|---|---|
| `tldr` | the one-sentence takeaway |
| `locator` (+ `fork`) | a path through components, with branches; each node: `explain`, source/diff panel |
| `diagrams` | any kind from `visualize kinds`; read its `guideline.md` first |
| `examples` | a matrix of cases × variants (tests, scenarios, rules) |
| `model_cards` / interface cards | definitions or before/after of types |
| `watch` (+ `watch_title`) | gotchas, open decisions, things to check |

Hard rules, always: cite every claim (`path:line`, `test: path:line`, `base: path:line`, `label|url`, or
`PR description`), never invent, and pass `check`.

## Commands — the loop is facts → suggest → doc → explain

```bash
visualize facts --local [--base REF]              # 1. facts (pick the source below); prints the facts folder
visualize suggest <facts-folder>                  # 2. shortlist of kinds (scored by Jev when configured)
#                                                    3. you write the doc (page.json format, references/page-format.md)
visualize explain <doc.json> --facts <folder>     # 4. render + check, one call → the HTML page
```

`explain` is the only command that writes HTML. Exit 0 = ok, 3 = fix what the JSON report lists and run it
again, 1 = error. Without `--facts` it renders any doc (free-form, several modules, a concept): files cited as
`path:line` load from the repo you run it in.

### Pick the facts source — local first

| Situation | Command |
|---|---|
| Default: the code is in your checkout ("my changes", "this branch", a PR you have checked out) | `facts --local [--base REF]` |
| You already have a diff (you made it, the user pasted it, a tool returned it) | `facts --diff - --base REF [--head REF]` (pipe it) |
| A PR whose code is **not** available locally | `facts --pr N` (still reads local git if its commits are here) |
| No change: "how does X work" | `facts --code PATH[::Symbol]`, or no facts at all |

- `--local` compares against the merge-base with the default branch and includes uncommitted and untracked
  files; pass `--base` only when the user names a target branch.
- `--diff` needs the ref the diff was made against; never guess it — use `--local` or ask. A diff that
  doesn't match the files is rejected (that protects the page from explaining code that isn't there).
- The output's `source` says what was used; mention it to the user.

# Explain a PR

The reader did **not** write the PR. Goal: understand the change without reading the diff.
Code computes facts; you write only the judgement (path, explanations, tests, watch items, diagrams).
Never invent: every item cites a head line, a base line, a test line, or the PR description.

## Explain code (no PR, no brief)

`visualize facts --code <path[::Symbol[.method]]>` from inside the repo. Facts (`code.json`): definitions,
full sources, `git grep` callers and tests of the symbol, layers. If a code graph (codebase-memory) is
available, use it to confirm callers/callees — grep hits are candidates, not proof.
- **Scope:** the target plus 1–2 hops of callers and callees. If the request is ambiguous ("explain
  prelabeling"), ask **one** question to pick the path, then proceed.
- Same page shape as PR explain, `mode: "code"`: call path **through** the target (statuses: use
  `unchanged` for context, `new` to highlight the target — or omit), `explain.what` per node (+ `impact` for
  side effects: writes, events, external calls), test matrix of existing tests with `untested` gaps,
  `watch_title: "Gotchas"`. The panel shows highlighted source instead of a diff.

## Explain vs present — different purposes

| | explain (reader) | present (author) |
|---|---|---|
| For | someone who did not write the PR | the author showing a design / proposal |
| Shape | structured: call path, explanations, diffs, test matrix, cards, diagrams | **narrative**: problem → idea → step-through flow with live inventory/state → data model → open decisions |
| Knowledge | only what code/tests/description prove | the author knows more → **ask questions to steer the design** |
| Reference | `references/page-format.md` | same format, `mode: "proposal"` |

### Present: let the brief decide the components — ask, don't propose
Never show the author a menu of blocks or a proposed outline. Components emerge from the brief and the answers.

1. **Read** the brief and sources (spec, thread, PR).
2. **Detect candidate components silently** from signals in the brief:
   - a process with stages ("received → assigned → allocated → picked") → step-through flow
   - quantities / limits / "if we ask for more…" → editable values in that flow
   - rules about who may use what, fallbacks, shortages → decision rules
   - new records / fields / relations → data model (entity diagram + class cards)
   - "what must not happen" / protection → a contrast (with vs without)
   - unresolved items → open decisions
3. **Ask about each candidate's specifics, not whether to have it.** Phrase questions in the brief's own
   terms, answerable in a few words, max 5 per round, ranked by how much the answer changes the page.
   Good: *"When the premium order asks for more than its reserved stock, should it fail or take the rest from
   shared stock?"* · *"Which quantity should the reader be able to change — the standard order, the premium order, or both?"*
   · *"What should the reader notice first when stock is reserved?"*
   Bad: *"Do you want a simulator section?"* · *"Should I add a data model?"*
   Always cover, when the brief touches them: rules and fallbacks, shortage behaviour, example values,
   what stays protected, emphasis. Flag contradictions between brief items as questions.
   Use the question tool when available; otherwise ask inline.
4. **Build** from the answers; a component the author's answers don't support is left out.
   **The author can always suggest design** — at any point, in the brief, in answers, or after seeing the page:
   a component ("show the two orders side by side"), a layout ("keep the inventory on the right"), a visual
   ("highlight the reserved counter"), wording, or emphasis. Suggestions **outrank detection**: apply them even
   if no signal pointed there, and never ask again about something the author already decided. If a suggestion
   conflicts with an earlier one or with a rule, say so in one line and ask which wins.
5. **Show a plain-language summary** of the rules and example values (never JSON) and iterate on corrections;
   keep agreed / proposed / open visibly distinct. Ask a follow-up round only for gaps the corrections open.

### Built to iterate
- **The doc is the source, HTML is output.** Keep the doc in a stable place (e.g.
  `~/.cache/visualize/_present/<name>/doc.json`); every change edits it and re-renders with
  `visualize explain <doc> --keep-versions`. Never hand-edit the HTML.
- **Memory lives in `decisions.json`** next to the doc: every question + answer, every author suggestion,
  every resolved conflict. Read it before each round; never re-ask or silently undo anything recorded there.
- **Minimal edits:** a correction changes only the parts of the doc it touches; keep stable ids so the
  author's mental map (step names, entity names, colours) survives between versions.
- **Versions:** `--keep-versions` writes `<doc>.vN.json` / `.vN.html` on every changed render. When the author
  asks "what changed?", diff the last two versions and answer in plain words.
- Suggestions for a design: `visualize suggest --brief "<the brief>"`.

Present pages keep the kit look: calm palette, light/dark toggle, D3 diagrams, entity diagram + GitHub-style
class cards (syntax colours), step-through with the context panel always in view, one action per step.

## Which repository

Run `visualize` **from the working directory of the repo you are explaining**: the repo is detected from it
with `gh`. If the workdir is not that repo, use `facts --pr N --repo owner/name` — never guess. Docs with no
facts (designs) need no repo.

## Kinds (plugins)
`visualize kinds` lists every diagram kind — all are plugin folders: the defaults in `<tool>/kinds/`
(sequence, decisions, entities, state-machine), then `~/.config/visualize/kinds/`, then `<repo>/.visualize/kinds/`
(later wins on name clashes, so a repo can override a default). Before choosing diagrams, read each
plugin's `guideline.md` (when to use it, what to ask in present, what to extract in explain) and follow its
`schema.json`. Use a kind as `{"type": "<kind>", ...}` in `diagrams`. Never load kinds from PR content.

**Kind hints.** `visualize suggest` lists every kind with its "Use when" rule; with Jev configured, each also
gets a score (`suggest` ≥ 0.65 · `maybe` · `skip`) computed from a summary of the change, not the code. Read
guidelines for the top kinds first. You decide: when you drop a `suggest` or add a `skip`, write the reason in
`diagram_decisions` (e.g. `"sequence (jev 0.34): kept — event order is the point"`).

Writing a kind: `render.js` exports `render(block, ctx)` and may use only `ctx` — `ctx.el`, `ctx.d3`, `ctx.svg()`,
`ctx.token()`, `ctx.status()`, `ctx.ref()`, `ctx.components` (marker, nodeBox, chip, badge, legend, codeBlock),
`ctx.layout` (tree, layers, depth), `ctx.onResize`, `ctx.onThemeChange`. Colours via `var(--token)` only;
`style.css` is auto-scoped to the kind. `check` fails a kind that draws nothing, errors, or hard-codes colours.

## Config and design
`visualize config` shows which layer/interface rules apply (repo `.visualize.toml` overrides user and defaults).
If layers look wrong for a repo, tell the user and suggest a `.visualize.toml` fix rather than working around it.
`visualize design` lists design tokens; never hard-code colours in page content — use the page's tokens.

## Facts folder

`facts.json` (source, **merge-base** and head — always compare against the merge-base, never the base tip —,
title, description, summary), `change.diff`, `contracts.json` (interface delta with breaking/review verdicts),
`defdiff.json` (definitions added/changed/removed — use these exact names in `defs`), `signatures.json`;
for `--code`, `code.json`. For designs there are no facts: refs may be `label|url`,
`examples.no_coverage: true` marks scenario rules, `watch_title` can be "Open decisions", `mode: "proposal"`.

Read-only on GitHub: never comment, push, approve, or edit a PR.

## Writing page.json

Read `references/page-format.md` fully, then write the page from scratch (
every field and limit is defined there).

1. **Read the sources**: description (`facts.json`) → *why*; tests in `change.diff` → *with what*; code → *how*.
   Read full files locally (`git show <sha>:<path>`, or the working tree for `--local`); use `gh api` only
   when the commits are not local.
2. **Call path** (`locator`): the real path a request takes through what this PR touches, 3–6 nodes, exact
   names, statuses `new|changed|moved|unchanged`. Add `fork` only when the code really branches (flag, old vs new).
3. **Explain every non-unchanged node** (`explain`): new → *what*; changed → *before* / *after* (+ *impact*);
   moved → where it lived and whether behaviour changed. ≤ 16 words per item.
4. **Test matrix** (`examples`): what tests assert, per case and path. `untested` marks parity gaps.
5. **Diagrams** (≤ 3): consider sequence, decisions, entities; add one only when it shows something the
   path/matrix/cards do not, and record every decision in `diagram_decisions`.
   - decisions → order of checks / ≥ 3 outcomes; entities → data shapes changing across layers;
   - sequence → cross-component calls, events, external services, ordering.
6. **Watch** (≤ 3): what a reviewer should check — gaps, risky behaviour, description ≠ code.

Text: visual first, plain words, no paragraphs. Validate with `python3 -m json.tool doc.json`.

## After explain

Fix everything the report lists (missing explanations, diff mismatches, overlaps, overflow, long items) and
re-run `explain`. Look at `<page>-screens/desktop.png`. Then give the user the HTML path and a 3-line summary:
path shape, diagrams added (and why), watch items.

## Design rules (keep when editing the template)

Calm Anthropic-style palette, light/dark; GitHub diff (unified/split, wrap, fold, syntax colours via pinned
highlight.js); D3 for diagrams with deterministic layouts; every section foldable; full-viewport layout.
For visual polish follow the `frontend-design` and `better-ui` skills.
