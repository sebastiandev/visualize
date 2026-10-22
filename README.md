# visualize

Explain code, pull requests and designs as **self-contained interactive HTML pages**, written by a coding agent.

Code gathers facts (diffs, merge-base, interface changes, definitions, signatures, sources); the agent writes
the explanation as `doc.json`; the tool renders it and checks the result in headless Chrome. Pages work
offline, have light/dark themes, foldable sections, GitHub-style diffs with syntax colours, and D3 diagrams.

## Contents

- [Install](#install) · [Agent installation guide](#agent-installation-guide)
- [Output](#output) · [Commands](#commands): `facts` · `suggest` · `explain` · `views` · `config` · `design`
- [Writing the doc](#writing-the-doc) · [Views](#views) · [Configuration](#configuration) · [Design tokens](#design-tokens)
- [How it works](#how-it-works) · [Troubleshooting](#troubleshooting)

## Output

One **self-contained HTML file** per explanation, produced by `visualize explain <doc.json>` in a single call.
The doc (the explanation itself) is written by an agent; the other commands help it get there:

| Step | Command | Who | Produces |
|---|---|---|---|
| 1 | `visualize facts …` | tool | a facts folder: diff vs merge-base, changed definitions, interface changes |
| 2 | `visualize suggest <facts>` | tool | a shortlist of views (scored by Jev when configured) |
| 3 | — | agent | `doc.json`: call path, explanations, tests, diagrams, all cited |
| 4 | `visualize explain doc.json --facts <folder>` | tool | **the HTML page**, checked in headless Chrome |

## Install

```bash
git clone git@github.com:sebastiandev/visualize.git
cd visualize
./bin/visualize install
```

`install` creates symlinks (no copies) and checks prerequisites:

| Link | Points to |
|---|---|
| `~/.agents/tools/visualize` | the repo |
| `~/.agents/skills/visualize` | `<repo>/skill` (the agent skill) |
| `~/.local/bin/visualize` | `<repo>/bin/visualize` (the command) |

Requirements: `gh` (logged in), `python3` ≥ 3.11 (standard library only), `node` ≥ 18, Google Chrome
(override with `CHROME=/path/to/chrome`). `~/.local/bin` must be on `PATH`.

Update: `git pull` in the repo (links follow it). Remove: `visualize uninstall` (only removes links that point into this repo).

## Agent installation guide

Instructions for a coding agent asked to install visualize:

1. **Check prerequisites first**, without installing anything: `gh auth status`, `python3 --version` (≥ 3.11),
   `node --version` (≥ 18), Chrome present. Report anything missing to the user and stop; do not install
   system packages without explicit permission.
2. **Clone** into the user's usual source folder (ask if unknown), e.g. `~/src/visualize`.
3. **Run `./bin/visualize install`** from the clone. It refuses to replace existing real files or folders;
   if it prints `skip …`, report it to the user instead of deleting anything.
4. **Verify**: `visualize --help` works from any directory, and `ls ~/.agents/skills/visualize/SKILL.md` exists.
   A new agent session is needed for the skill to be picked up.
5. **Optional smoke test** inside any GitHub repo the user works on:
   `visualize facts --pr <recent PR number>` should print a facts folder.
6. Never commit, push or comment on GitHub while doing this; `visualize` itself is read-only on GitHub.

## Commands

| Command | Purpose |
|---|---|
| `visualize facts --local [--base REF]` | Facts for the current branch + uncommitted/untracked work vs the merge-base with the default branch. **Default.** |
| `visualize facts --diff FILE\|- --base REF [--head REF]` | Facts for a diff you already have; rejected if it doesn't match the files at those refs. |
| `visualize facts --pr N [--repo o/r]` | Facts for a PR; reads local git when its commits are present, else GitHub. |
| `visualize facts --code PATH[::Symbol]` | Facts for a part of the code (no change): sources, definitions, callers, tests. |
| `visualize suggest [FACTS] [--brief TEXT]` | Views with their "use when" rule, scored by Jev when available. |
| `visualize explain DOC.json [--facts DIR] [-o FILE] [--keep-versions]` | Render + check → the HTML page. Without `--facts`, files cited as `path:line` load from the current repo. |
| `visualize views` · `config` · `design` | List views · merged config · design tokens. |
| `visualize install` / `uninstall` | Create / remove the symlinks. |

`facts` options for `--local`/`--diff`: `--title`, `--body-file`, `-o DIR` (default `~/.cache/visualize/<repo>/<key>/facts`).
`explain` exit codes: `0` ok, `3` the check found something to fix (JSON report), `1` error.

### Minimal examples

**Explain your current changes** (run inside the repo):
```bash
visualize facts --local                       # prints the facts folder
# agent writes doc.json (see the skill)
visualize explain doc.json --facts ~/.cache/visualize/me__app/local-my-branch/facts
```

**Explain a PR you don't have locally**:
```bash
visualize facts --pr 1234
visualize explain doc.json --facts ~/.cache/visualize/me__app/pr-1234/facts
```

**A diff you already have**:
```bash
git diff main... | visualize facts --diff - --base main
```

**Free-form explanation** (several modules, a concept, any structure), no facts needed:
```bash
cat > guard.json <<'EOF'
{
  "title": "How the reprint guard works",
  "sections": [
    {"view": "tldr", "text": "Reprint only when a shipment row exists.", "ref": "app/prelabel/use_case.py:537"},
    {"view": "call-path", "title": "How the question travels", "nodes": [
      {"id": "uc", "label": "GetPrelabel._shipment_was_recorded", "layer": "use case", "status": "new",
       "ref": "app/prelabel/use_case.py:537",
       "explain": {"what": [{"text": "Delegates to the HasRecordedShipment port.", "ref": "app/prelabel/use_case.py:537"}]}},
      {"id": "db", "label": "RecordedShipmentChecker", "layer": "adapter", "status": "unchanged",
       "ref": "app/prelabel/checker.py:21"}
    ]}
  ]
}
EOF
visualize explain guard.json                  # → guard.html, with source panels for the cited files
```

**Present a design** (the agent asks you a few questions, then iterates):
```bash
visualize suggest --brief "Reserve stock per sales channel…"
visualize explain ~/.cache/visualize/_present/segmentation/doc.json --keep-versions   # v1, v2, … on every change
```

## Writing the doc

A doc is a title plus an ordered list of `sections`; each names the **view** that draws it. Full reference:
`skill/references/page-format.md`; agent workflow: `skill/SKILL.md`. Views are a vocabulary — use what serves
the explanation, in any order:

| View | Shows |
|---|---|
| `tldr` | one-sentence takeaway |
| `call-path` (+ `fork`) | a path through components with branches; per node `explain` (what / before / after / impact) and a source or diff panel |
| `sequence` · `decisions` · `entities` · `state-machine` | interactions · rules and outcomes · data shapes · lifecycles |
| `matrix` | cases × variants (tests or scenarios), with `untested` gaps |
| `interface-changes` | detected interface changes (from facts), or authored `cards` for a proposed model |
| `watch` | gotchas, open decisions, reviewer notes |

Rules: every item has a `ref` (`path:line`, `test: path:line`, `base: path:line`, `label|https://…`, or
`PR description`); nothing is invented; text stays short. Docs in the older page shape still render.

## Views

Every section is drawn by a view, and every view is a plugin folder — including the defaults in `views/`.
Add or override one **without changing code** in `~/.config/visualize/views/<name>/` or
`<repo>/.visualize/views/<name>/` (later folders win on name clashes):

| File | Role |
|---|---|
| `guideline.md` | when to use it, what to ask (present), what to extract (explain) — read by the agent and Jev |
| `schema.json` | required fields/types, validated at build |
| `render.js` | `export default function render(block, ctx) { … }` |
| `style.css` | optional, auto-scoped to the view (`@media` supported) |

`ctx` gives: `el`, `d3`, `svg()`, `token()`, `status()`, `ref()`, `components` (marker, nodeBox, chip, badge,
legend, codeBlock), `layout` (tree, layers, depth), `onResize`, `onThemeChange`, `page`, `defs`, `code`
(fileDiff, fileSource, diffTable, highlight, langOf, rows), `state`, `title()`. Use `var(--token)` colours only —
`check` fails views that draw nothing, throw, or hard-code colours. Copy any folder in `views/` as a starting point.

## Configuration

Layered: built-in defaults → `~/.config/visualize/config.toml` → `<repo>/.visualize.toml`.

```toml
[layers]           # regexes over repo paths; first match wins
domain         = ['/domain/', '/use_?cases?/', '/commands?/']
application    = ['/application/']
infrastructure = ['/infrastructure/']

[interfaces]       # surfaces for interface-change detection
graphql       = ['/(graphql|gql)/.*\.py$']
events        = ['/events/.*\.py$']
generated_sdk = ['^sdk/generated/']
feature_flags = ['/features\.py$']

[ignore]
generated = ['/generated/']

[schema]
introspection = "sdk/generated/introspection.json"   # GraphQL operation signatures

[repo]
fallback = ""      # only used outside a git repo, and announced
```

A repo-specific `.visualize.toml` you don't want to commit can be ignored locally via `.git/info/exclude`.

### Jev view hints (optional)

With a [TypeSafe](https://typesafe.ai) key, `visualize suggest` asks Jev which views fit the change
(e.g. `decisions 0.89 suggest · sequence 0.34 skip`). The agent reads it as a shortlist and
still decides, giving a reason when it disagrees. Only a summary is sent (title, description, file paths,
layers, counts), never file contents. Each view's `## Use when` section becomes the question.

- Key: `TYPESAFE_API_KEY`, or the macOS keychain item `typesafe-api-key`.
- No key → no hints; everything else works the same.

```toml
[jev]
enabled = "auto"        # auto (on when a key is found) | true | false
model   = "jev-1.13.0"
```

## Design tokens

Pages use CSS custom properties (light and dark). `visualize design` lists them; override in either config:

```toml
[design.light]
clay = "#2F6FEB"   # accent
[design.dark]
clay = "#58A6FF"
```

Unknown token names are reported and ignored.

## How it works

1. **Facts** (deterministic, local git first): diff against the **merge-base**, interface delta (added / breaking / review),
   definition diff and signatures — or, for code, sources, callers and tests.
2. **Explanation** (agent): `doc.json`, following the skill.
3. **Explain** (render): one HTML file with everything inlined (pinned D3 7.9 and highlight.js 11.10).
4. **Check** (headless Chrome): console errors, overflow (desktop/mobile), missing explanations, diff/source
   text integrity, diagram overlaps, per-view problems.

Facts folders live in `~/.cache/visualize/<owner>__<repo>/<key>/facts` (`pr-N`, `local-<branch>`, `diff-<hash>`, `code-<target>`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `not inside a GitHub repository` | run from the repo's directory or pass `--repo owner/name` |
| `gh pr view … failed` | wrong PR number, no access, or `gh auth login` needed |
| `Chrome did not start` | set `CHROME=/path/to/chrome` |
| layers look wrong | add a `.visualize.toml` (`visualize config` shows what applied) |
| skill changes not picked up | start a new agent session |
