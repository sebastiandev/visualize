"""`visualize` — explain code, a change or a design as one self-contained interactive HTML page.

    visualize facts --local [--base REF]                 facts for your branch + uncommitted work (default)
    visualize facts --diff FILE|- --base REF [--head REF] facts for a diff you already have
    visualize facts --pr N                               facts for a PR (local git when its commits are here, else GitHub)
    visualize facts --code PATH[::Symbol]                facts for a part of the code (no change)
    visualize suggest [FACTS_DIR | --brief TEXT]         shortlist of views for the doc (Jev scores when available)
    visualize explain DOC.json [--facts DIR] [-o FILE] [--keep-versions]   render + check → the HTML page
    visualize views | config | design                    list views · merged config · design tokens
    visualize install | uninstall                        link this repo into ~/.agents and ~/.local/bin

The agent loop: facts → suggest → write the doc (visualize skill) → explain. `explain` is the only command that
writes HTML; exit 0 = ok, 3 = the check found something to fix (JSON report), 1 = error.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from visualize.build import ASSETS, from_facts, render
from visualize.config import load as load_config, repo_root
from visualize.definitions import definitions, signatures
from visualize.workspace import default_repo, fetch, use_local


def run_check(html: Path, shots: Path) -> int:
    """Headless Chrome checks on a built page; prints the JSON report."""
    result = subprocess.run(["node", str(ASSETS / "check.js"), str(html), str(shots)], capture_output=True, text=True)
    print(result.stdout.strip() or result.stderr.strip())
    print(f"screenshots: {shots}")
    return result.returncode


def load_cited(page_text: str, read, sources: dict, defs: list) -> None:
    """Add every `path:line`-cited file to `sources` (+ its Python definitions to `defs`, never overriding known names).

    `read(path)` returns the file at the doc's commit (head of the change, or the working tree), else None.
    """
    known = {d["name"] for d in defs}
    cited = set(re.findall(r'"(?:test:\s*)?((?:[\w.\-]+/)+[\w.\-]+\.\w+):\d+(?:-\d+)?"', page_text))
    for f in sorted(cited - set(sources)):
        src = read(f)
        if src is None:
            continue
        sources[f] = src.splitlines()
        if f.endswith(".py"):
            try:
                defs += [{"file": f, "name": n, "change": "unchanged", "before": None, "after": d, "ref": f"{f}:{d['line']}"}
                         for n, d in definitions(src).items() if n not in known]
            except SyntaxError:
                pass


def _snapshot(doc: Path, doc_text: str, html_text: str) -> int:
    """Keep <doc>.vN.json/.html for every changed render; returns the current version number."""
    stem = doc.with_suffix("").name
    versions = sorted(int(m.group(1)) for p in doc.parent.glob(f"{stem}.v*.json") if (m := re.match(rf"{re.escape(stem)}\.v(\d+)\.json$", p.name)))
    if versions and (doc.parent / f"{stem}.v{versions[-1]}.json").read_text() == doc_text:
        return versions[-1]
    n = (versions[-1] + 1) if versions else 1
    (doc.parent / f"{stem}.v{n}.json").write_text(doc_text)
    (doc.parent / f"{stem}.v{n}.html").write_text(html_text)
    return n


def explain(doc: Path, facts_dir: Path | None, out: Path | None, keep_versions: bool, repo: str | None) -> int:
    """Render one doc (+ optional facts folder) into a checked HTML page, in one call."""
    doc_text = doc.read_text()
    page = json.loads(doc_text)
    root = repo_root()
    use_local(root)
    if facts_dir:
        repo = repo or from_facts(page, facts_dir)
    sources, defs = dict(page.get("sources") or {}), list(page.get("defdiff") or [])
    if facts_dir and page.get("diff"):
        pass  # a change: panels show the diff; cited files are not loaded (they would not be at the change's commit)
    elif facts_dir:
        load_cited(doc_text, lambda f: fetch(repo, f, page["head_sha"]), sources, defs)
    elif root:
        load_cited(doc_text, lambda f: (root / f).read_text(errors="replace") if (root / f).is_file() else None, sources, defs)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
        page.setdefault("head_sha", head)
        page.setdefault("base_sha", head)
    page["sources"], page["defdiff"] = sources, defs
    page.setdefault("mode", "pr" if page.get("diff") else "code" if sources else "proposal")
    if not repo and root:
        try:
            repo = default_repo()
        except RuntimeError:
            repo = ""
    if repo and not facts_dir and page.get("head_sha"):
        page.setdefault("url", f"https://github.com/{repo}/tree/{page['head_sha']}")
        page.setdefault("source_label", f"{repo} @ {page['head_sha'][:10]}")
    if repo and defs and not page.get("inputs"):
        page["inputs"] = signatures(repo, [d for d in defs if d.get("after")], page.get("head_sha", ""), set(), "")
    html = out or doc.with_suffix(".html")
    html_text = render(page, repo or "")
    html.write_text(html_text)
    version = f"  (version v{_snapshot(doc, doc_text, html_text)})" if keep_versions else ""
    print(f"page: {html}{version}")
    return run_check(html, html.parent / (html.stem + "-screens"))


def suggest(facts_dir: Path | None, brief: str | None) -> int:
    """Views with their 'Use when' rule; scored by Jev when a key is available."""
    from visualize import jev
    from visualize.views import discover
    cfg = load_config()
    if facts_dir:
        f = json.loads((facts_dir / "facts.json").read_text())
        state = {"change" if f["kind"] == "change" else "code": {"title": f["title"], "description": f["description"], **f["summary"]},
                 "file_paths": f["file_paths"]}
        mode = "change" if f["kind"] == "change" else "part of the code"
    else:
        state, mode = {"design_brief": (brief or "")[:4000]}, "design proposal"
    scored = {h["view"]: h for h in (jev.hints(state, cfg, mode) or {}).get("views", [])}
    rows = [{"view": name, "p": scored.get(name, {}).get("p"), "band": scored.get(name, {}).get("band"),
             "use_when": jev.use_when(k.read("guideline.md")), "guideline": str(k.dir / "guideline.md")}
            for name, k in discover().items()]
    rows.sort(key=lambda r: -(r["p"] or 0))
    print(json.dumps({"scored_by": "jev" if scored else None, "views": rows,
                      "note": "Shortlist only: you decide. Explain disagreements with a 'suggest' in view_decisions."},
                     indent=1, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(prog="visualize", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    fa = sub.add_parser("facts", help="gather facts about a change (--local default, --diff, --pr) or code (--code)")
    src = fa.add_mutually_exclusive_group()
    src.add_argument("--local", action="store_true", help="current branch + uncommitted work (default)")
    src.add_argument("--diff", help="unified diff file, or - for stdin")
    src.add_argument("--pr", type=int)
    src.add_argument("--code", help="PATH[::Symbol[.method]] in the current repo")
    fa.add_argument("--base", help="ref to compare against (--local: default branch; --diff: required)")
    fa.add_argument("--head", help="--diff only: ref the diff ends at (default: working tree)")
    fa.add_argument("--title", help="title for --local/--diff (default: branch name)")
    fa.add_argument("--body-file", help="description for --local/--diff")
    fa.add_argument("--repo", help="owner/name (default: the repo of the current directory)")
    fa.add_argument("-o", "--out", type=Path, help="facts folder (default: ~/.cache/visualize/<repo>/<key>/facts)")
    sg = sub.add_parser("suggest", help="shortlist views for a facts folder or a design brief")
    sg.add_argument("facts", type=Path, nargs="?")
    sg.add_argument("--brief", help="design brief text (present / proposal docs)")
    ex = sub.add_parser("explain", help="render a doc (+ facts) into a checked HTML page")
    ex.add_argument("doc", type=Path)
    ex.add_argument("--facts", type=Path, help="facts folder from `visualize facts`")
    ex.add_argument("-o", "--out", type=Path, help="HTML path (default: next to the doc)")
    ex.add_argument("--keep-versions", action="store_true", help="keep <doc>.vN.json/.html for every changed render")
    ex.add_argument("--repo", help="owner/name for links (default: from facts or the current repo)")
    sub.add_parser("views", help="list views (plugin folders) and where they come from")
    sub.add_parser("config", help="show the merged config and where it came from")
    sub.add_parser("design", help="show design tokens (defaults + overrides) and how to override them")
    sub.add_parser("install", help="link this repo into ~/.agents/{tools,skills} and ~/.local/bin")
    sub.add_parser("uninstall", help="remove those links")
    args = ap.parse_args(argv)
    if args.command == "views":
        from visualize.views import discover, search_dirs
        for name, view in discover().items():
            print(f"{name:<18} {view.dir}  — {view.description}")
        print("search:", ", ".join(map(str, search_dirs())))
        return 0
    if args.command == "design":
        from visualize.design import __doc__ as how, defaults
        print(json.dumps({"defaults": defaults(), "overrides": load_config().data.get("design", {})}, indent=1))
        print(how)
        return 0
    if args.command == "config":
        cfg = load_config()
        print(json.dumps({"sources": cfg.sources, "config": cfg.data}, indent=1))
        return 0
    if args.command in {"install", "uninstall"}:
        from visualize.install import install, uninstall
        return install() if args.command == "install" else uninstall()
    try:
        if args.command == "facts":
            from visualize.facts import gather
            out, f = gather(args, args.repo or default_repo())
            print(json.dumps({"facts": str(out), "source": f["source"], "title": f["title"], "summary": f["summary"],
                              "reads": f.get("reads")}, indent=1, ensure_ascii=False))
            return 0
        if args.command == "suggest":
            return suggest(args.facts, args.brief)
        return explain(args.doc, args.facts, args.out, args.keep_versions, args.repo)
    except RuntimeError as error:  # git/gh failures, a diff that does not apply, missing refs
        print(f"visualize: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
