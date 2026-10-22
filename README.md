# visualize

Explain code, pull requests and designs as **self-contained interactive HTML pages**, written by a coding agent.

Code gathers facts (diffs, merge-base, interface changes, definitions, signatures, sources); the agent writes
the explanation as `page.json`; the tool renders it and checks the result in headless Chrome. Pages work
offline, have light/dark themes, foldable sections, GitHub-style diffs with syntax colours, and D3 diagrams.

## Contents

- [Install](#install) · [Agent installation guide](#agent-installation-guide)
- [Commands](#commands): `render` · `explain --pr` · `explain --code` · `present` · `kinds` · `config` · `design`
- [Writing page.json](#writing-pagejson) · [Diagrams and kinds](#diagrams-and-kinds) · [Configuration](#configuration) · [Design tokens](#design-tokens)
- [How it works](#how-it-works) · [Troubleshooting](#troubleshooting)

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
   `visualize explain --pr <recent PR number>` should print a workspace path (facts gathered).
6. Never commit, push or comment on GitHub while doing this; `visualize` itself is read-only on GitHub.

## Commands

| Command | Purpose |
|---|---|
| `visualize render <page.json> [--out F] [--repo o/r]` | Render **any** page you (or the agent) wrote. Files cited as `path:line` load from the current repo. |
| `visualize explain --pr <n> [--repo o/r] [--refresh]` | Reader mode for a PR: gathers facts, then renders once `page.json` exists. Bare `explain <n>` works too. |
| `visualize explain --code <path[::Symbol]>` | Reader mode for a part of the code (no PR): sources, callers, tests. |
| `visualize present <name> [--out F] [--history]` | Author mode for a design/proposal: versioned renders + decision log. |
| `visualize kinds` | List diagram kinds (all plugin folders) and where each comes from. |
| `visualize config` | Show the merged configuration and its sources. |
| `visualize design` | Show design tokens and how to override them. |
| `visualize install` / `uninstall` | Create / remove the symlinks. |

Every page command renders and then runs the checks; exit code `0` = ok, `3` = something to fix (the JSON
report says what), `1` = error (e.g. unknown PR).

### Minimal examples

**Explain a PR** (run inside the repo):
```bash
visualize explain --pr 1234          # 1st run: gathers facts, prints the workspace path
# agent writes page.json in that workspace (see the skill)
visualize explain --pr 1234          # 2nd run: renders page.html and checks it
```

**Explain a part of the code**:
```bash
visualize explain --code "app/billing/invoice.py::InvoiceBuilder"
```

**Free-form explanation** (several modules, a concept, any structure):
```bash
cat > guard.page.json <<'EOF'
{
  "title": "How the reprint guard works",
  "tldr": {"text": "Reprint only when a shipment row exists.", "ref": "app/prelabel/use_case.py:537"},
  "locator": {"title": "How the question travels", "nodes": [
    {"id": "uc", "label": "GetPrelabel._shipment_was_recorded", "layer": "use case", "status": "new",
     "ref": "app/prelabel/use_case.py:537",
     "explain": {"what": [{"text": "Delegates to the HasRecordedShipment port.", "ref": "app/prelabel/use_case.py:537"}]}},
    {"id": "db", "label": "RecordedShipmentChecker", "layer": "adapter", "status": "unchanged",
     "ref": "app/prelabel/checker.py:21"}
  ]}
}
EOF
visualize render guard.page.json      # → guard.page.html, with source panels for the cited files
```

**Present a design** (agent asks you a few questions first):
```bash
visualize present inventory-segmentation        # creates the workspace
# agent writes page.json + logs questions/answers in decisions.json
visualize present inventory-segmentation        # renders v1, v2, … on every change
visualize present inventory-segmentation --history
```

## Writing page.json

The full field reference is `skill/references/page-format.md`; the agent workflow is `skill/SKILL.md`.
Blocks are a vocabulary — use what serves the explanation:

| Block | Shows |
|---|---|
| `tldr` | one-sentence takeaway |
| `locator` (+ `fork`) | a path through components with branches; per node `explain` (what / before / after / impact) and a source or diff panel |
| `diagrams` | any kind from `visualize kinds` (sequence, decisions, entities, state-machine, yours) |
| `examples` | matrix of cases × variants (tests or scenarios), with `untested` gaps |
| `model_cards` | proposed definitions (new) or before/after diffs (changed), GitHub-style |
| `watch` (+ `watch_title`) | gotchas, open decisions, reviewer notes |

Rules: every item has a `ref` (`path:line`, `test: path:line`, `base: path:line`, `label|https://…`, or
`PR description`); nothing is invented; text stays short.

## Diagrams and kinds

Every kind is a plugin folder — including the defaults shipped in `kinds/`: `sequence`, `decisions`,
`entities`, `state-machine`. Add or override one **without changing code** in `~/.config/visualize/kinds/<name>/`
or `<repo>/.visualize/kinds/<name>/` (later folders win on name clashes):

| File | Role |
|---|---|
| `guideline.md` | when to use it, what to ask (present), what to extract (explain) — read by the agent |
| `schema.json` | required fields/types, validated at build |
| `render.js` | `export default function render(block, ctx) { … }` |
| `style.css` | optional, auto-scoped to the kind |

`ctx` gives: `el`, `d3`, `svg()`, `token()`, `status()`, `ref()`, `components` (marker, nodeBox, chip, badge,
legend, codeBlock), `layout` (tree, layers, depth), `onResize`, `onThemeChange`. Use `var(--token)` colours
only — `check` fails kinds that draw nothing, throw, or hard-code colours. Copy any folder in `kinds/` as a starting point.

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

### Jev kind hints (optional)

With a [TypeSafe](https://typesafe.ai) key, `explain` also asks Jev which diagram kinds fit the change and writes
`kind_hints.json` (e.g. `decisions 0.89 suggest · sequence 0.34 skip`). The agent reads it as a shortlist and
still decides, giving a reason when it disagrees. Only a summary is sent (title, description, file paths,
layers, counts), never file contents. Each kind's `## Use when` section becomes the question.

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

1. **Facts** (deterministic): PR diff against the **merge-base**, interface delta (added / breaking / review),
   definition diff and signatures — or, for code, sources, callers and tests.
2. **Explanation** (agent): `page.json`, following the skill.
3. **Render**: one HTML file with everything inlined (pinned D3 7.9 and highlight.js 11.10).
4. **Check** (headless Chrome): console errors, overflow (desktop/mobile), missing explanations, diff/source
   text integrity, diagram overlaps, per-kind problems.

Workspaces live in `~/.cache/visualize/` (one folder per PR, code target, or presentation).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `not inside a GitHub repository` | run from the repo's directory or pass `--repo owner/name` |
| `gh pr view … failed` | wrong PR number, no access, or `gh auth login` needed |
| `Chrome did not start` | set `CHROME=/path/to/chrome` |
| layers look wrong | add a `.visualize.toml` (`visualize config` shows what applied) |
| skill changes not picked up | start a new agent session |
