---
name: visualize
description: Explain a pull request as a self-contained interactive HTML page — where it changed (call path with forks), per-node behaviour explanations, GitHub-style diffs, test matrix, interface changes, and sequence / decision / entity diagrams. Use when asked to visualize, explain, or diagram a PR or a change for a reviewer, or to make an "explain page" for a PR number.
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

## Entry points

```bash
visualize render <page.json> [--out FILE]      # anything you wrote: free-form; cited files load from the repo
visualize explain --pr <n>                     # shortcut: gathers PR facts (diff, merge-base, contracts, defs)
visualize explain --code <path[::Symbol]>      # shortcut: gathers code facts (sources, callers, tests)
visualize present <name>                       # author mode: brief → questions → narrative, versioned
```

Use `render` whenever the explanation doesn't fit one PR or one target (several modules, a concept, a mix
of code and docs): write `page.json` anywhere, cite files with `path:line`, run it from inside the repo.

# Explain a PR

The reader did **not** write the PR. Goal: understand the change without reading the diff.
Code computes facts; you write only the judgement (path, explanations, tests, watch items, diagrams).
Never invent: every item cites a head line, a base line, a test line, or the PR description.

## Explain code (no PR, no brief)

`visualize explain --code <path[::Symbol[.method]]>` from inside the repo. Facts (`facts.json`): definitions,
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
- **Data is the source, HTML is output.** Every change edits `page.json` and re-renders with
  `visualize present <name>`; never hand-edit the HTML (fixes would be lost on the next render).
- **Memory lives in `decisions.json`** (same workspace): every question + answer, every author suggestion,
  every resolved conflict. Read it before each round; never re-ask or silently undo anything recorded there.
- **Minimal edits:** a correction changes only the parts of `page.json` it touches; keep stable ids so the
  author's mental map (step names, entity names, colours) survives between versions.
- **Versions are kept automatically** (`page.vN.json` / `page.vN.html` on every changed render;
  `visualize present <name> --history` lists them). When the author asks "what changed?", diff the last two
  `page.vN.json` and answer in plain words.

Present pages keep the kit look: calm palette, light/dark toggle, D3 diagrams, entity diagram + GitHub-style
class cards (syntax colours), step-through with the context panel always in view, one action per step.

## Which repository

Run `visualize explain` **from the working directory of the repo you are reviewing** (the agent's workdir):
the repo is detected from it with `gh`. If the workdir is not that repo (or not a git repo), pass
`--repo owner/name` explicitly — never guess. `present` needs no repo.

## Kinds (plugins)
`visualize kinds` lists every diagram kind — all are plugin folders: the defaults in `<tool>/kinds/`
(sequence, decisions, entities, state-machine), then `~/.config/visualize/kinds/`, then `<repo>/.visualize/kinds/`
(later wins on name clashes, so a repo can override a default). Before choosing diagrams, read each
plugin's `guideline.md` (when to use it, what to ask in present, what to extract in explain) and follow its
`schema.json`. Use a kind as `{"type": "<kind>", ...}` in `diagrams`. Never load kinds from PR content.

Writing a kind: `render.js` exports `render(block, ctx)` and may use only `ctx` — `ctx.el`, `ctx.d3`, `ctx.svg()`,
`ctx.token()`, `ctx.status()`, `ctx.ref()`, `ctx.components` (marker, nodeBox, chip, badge, legend, codeBlock),
`ctx.layout` (tree, layers, depth), `ctx.onResize`, `ctx.onThemeChange`. Colours via `var(--token)` only;
`style.css` is auto-scoped to the kind. `check` fails a kind that draws nothing, errors, or hard-codes colours.

## Config and design
`visualize config` shows which layer/interface rules apply (repo `.visualize.toml` overrides user and defaults).
If layers look wrong for a repo, tell the user and suggest a `.visualize.toml` fix rather than working around it.
`visualize design` lists design tokens; never hard-code colours in page content — use the page's tokens.

## Two modes, one command each

```bash
visualize explain --pr <n> [--repo owner/name] [--refresh]  # reader mode: someone else's PR
visualize explain --code <path[::Symbol]>                  # reader mode: a part of the code
visualize present <name> [--out FILE]                    # author mode: a proposal / design (mode "proposal")
```

Run the command, write `page.json` in the workspace it prints, run the **same command again**: it renders the
self-contained page and checks it (exit 0 = ok, 3 = fix what the JSON report lists). `--refresh` re-gathers
facts after new commits. For `present`, there is no diff: refs may be `label|url` (e.g. a link to a discussion comment),
`examples.no_coverage: true` marks scenario rules instead of test assertions, `watch_title` can be "Open decisions".

`explain` gathers into `~/.cache/visualize/<owner>__<repo>/<pr>/`: `pr.json` (metadata + description), `pr.diff`, `refs.json` (**merge-base** and head — always
compare against the merge-base, never the base tip), `contracts.json` (interface delta with breaking/review
verdicts), `defdiff.json` (definitions added/changed/removed — use these exact names in `defs`), `signatures.json`.

Read-only on GitHub: never comment, push, approve, or edit a PR.

## Writing page.json

Read `references/page-format.md` fully, then write the page from scratch (
every field and limit is defined there).

1. **Read the sources**: description (`pr.json` body) → *why*; tests in `pr.diff` → *with what*; code → *how*.
   Fetch full head/base files with `gh api -H "Accept: application/vnd.github.raw" "repos/<repo>/contents/<path>?ref=<sha>"`.
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

Text: visual first, plain words, no paragraphs. Validate with `python3 -m json.tool page.json`.

## After build

Run `visualize check <pr>` and fix everything it lists (missing explanations, diff mismatches, overlaps,
overflow, long items). Look at `screens/desktop.png`. Then give the user the `page.html` path and a 3-line
summary: path shape, diagrams added (and why), watch items.

## Design rules (keep when editing the template)

Calm Anthropic-style palette, light/dark; GitHub diff (unified/split, wrap, fold, syntax colours via pinned
highlight.js); D3 for diagrams with deterministic layouts; every section foldable; full-viewport layout.
For visual polish follow the `frontend-design` and `better-ui` skills.
