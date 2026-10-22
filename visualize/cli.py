"""`visualize` — explain a PR, or present a proposal, as a self-contained interactive HTML page.

    visualize explain --pr <n> [--repo owner/name] [--refresh]   reader mode: explain someone else's PR (bare <n> works)
    visualize explain --code <path[::Symbol]>                 reader mode: explain a part of the code (no PR)
    visualize render <page.json> [--out FILE]                render any page you wrote (free-form; cites resolve in the repo)
    visualize present <name> [--out FILE]                    author mode: show a proposal / design
    visualize config                                         show the merged config and its sources
    visualize design                                         show design tokens and how to override them
    visualize kinds                                          list visualization kinds (plugin folders)
    visualize install | uninstall                            link this repo into ~/.agents and ~/.local/bin

Each command does what its state needs:
  1st run  → sets up the workspace (explain: gathers facts from the PR) and says what page.json must contain
  2nd run  → page.json exists: renders the page and checks it (exit 3 = something to fix)

page.json is written by the agent following the `visualize` skill (references/page-format.md).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from visualize.build import ASSETS, build, render
from visualize.contracts import delta
from visualize.definitions import defdiff, signatures
from visualize.config import load as load_config
from visualize.workspace import CACHE_ROOT, Workspace, default_repo, gh



def gather_facts(ws: Workspace) -> dict:
    """PR metadata + diff, merge-base, contract delta, definition diff and signatures → workspace files."""
    meta = json.loads(gh("pr", "view", str(ws.number), "-R", ws.repo, "--json",
                         "number,title,body,url,author,files,baseRefOid,headRefOid,state,isDraft,additions,deletions,changedFiles"))
    ws.write_json("pr.json", meta)
    ws.path("pr.diff").write_text(gh("pr", "diff", str(ws.number), "-R", ws.repo))
    head = meta["headRefOid"]
    # Compare against the merge-base, never the current base tip: commits merged after branching would look like removals.
    base = gh("api", f"repos/{ws.repo}/compare/{meta['baseRefOid']}...{head}", "-q", ".merge_base_commit.sha").strip()
    ws.write_json("refs.json", {"base": base, "head": head, "base_tip": meta["baseRefOid"]})
    cfg = load_config()
    ws.write_json("config.json", {"sources": cfg.sources, "config": cfg.data})
    paths = [f["path"] for f in meta["files"]]
    code = [p for p in paths if p.endswith(".py") and not cfg.is_test(p) and not cfg.is_generated(p)]
    contracts = delta(ws.repo, [p for p in paths if not cfg.is_test(p)], base, head, cfg)
    ws.write_json("contracts.json", contracts)
    defs = defdiff(ws.repo, code, base, head)
    ws.write_json("defdiff.json", defs)
    ws.write_json("signatures.json", signatures(ws.repo, defs, head, set(paths), cfg.introspection))
    return {"title": meta["title"], "files": len(paths), "definitions": len(defs), "contract_entries": len(contracts),
            "breaking": sum(e["breaking"] is True for e in contracts), "merge_base_differs_from_tip": base != meta["baseRefOid"], "config": cfg.sources}


def run_check(html: Path, shots: Path) -> int:
    """Headless Chrome checks on a built page; prints the JSON report."""
    result = subprocess.run(["node", str(ASSETS / "check.js"), str(html), str(shots)], capture_output=True, text=True)
    print(result.stdout.strip() or result.stderr.strip())
    print(f"screenshots: {shots}")
    return result.returncode


def explain(pr: int, repo: str, refresh: bool, out: Path | None) -> int:
    """Reader mode for a PR: gather facts on first run (or --refresh); render + check once page.json exists."""
    ws = Workspace(repo, pr)
    if refresh or not ws.path("refs.json").exists():
        print(json.dumps(gather_facts(ws), indent=1))
    if not ws.path("page.json").exists():
        print(f"workspace: {ws.dir}\nnext: write page.json there (visualize skill), then run `visualize explain {pr}` again")
        return 0
    html = build(ws, out)
    print(f"page: {html}")
    return run_check(html, ws.path("screens"))


def _snapshot(work: Path, page_text: str, html_text: str) -> int:
    """Keep page.vN.json/.html for every changed render; returns the current version number."""
    versions = sorted(int(m.group(1)) for p in work.glob("page.v*.json") if (m := re.match(r"page\.v(\d+)\.json$", p.name)))
    if versions and (work / f"page.v{versions[-1]}.json").read_text() == page_text:
        return versions[-1]  # unchanged since the last render
    n = (versions[-1] + 1) if versions else 1
    (work / f"page.v{n}.json").write_text(page_text)
    (work / f"page.v{n}.html").write_text(html_text)
    return n


def load_cited(page_text: str, root: Path, sources: dict, defs: list) -> None:
    """Add every `path:line`-cited .py file from the working tree to `sources` (+ its definitions to `defs`)."""
    from visualize.definitions import definitions
    cited = set(re.findall(r'"(?:test:\s*)?((?:[\w.\-]+/)+[\w.\-]+\.\w+):\d+(?:-\d+)?"', page_text))
    for f in sorted(cited - set(sources)):
        if (root / f).is_file():
            src = (root / f).read_text(errors="replace")
            sources[f] = src.splitlines()
            if f.endswith(".py"):
                try:
                    defs += [{"file": f, "name": n, "change": "unchanged", "before": None, "after": d, "ref": f"{f}:{d['line']}"}
                             for n, d in definitions(src).items()]
                except SyntaxError:
                    pass


def render_page(page_path: Path, repo: str | None, out: Path | None) -> int:
    """Render any agent-written page.json; code panels come from files it cites in the current working tree."""
    from visualize.config import repo_root
    page_text = page_path.read_text()
    page = json.loads(page_text)
    root = repo_root()
    sources, defs = dict(page.get("sources") or {}), list(page.get("defdiff") or [])
    if root:
        load_cited(page_text, root, sources, defs)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
        page.setdefault("head_sha", head)
        page.setdefault("base_sha", head)
    page.setdefault("mode", "code" if sources else "proposal")
    page["sources"], page["defdiff"] = sources, defs
    repo = repo or (default_repo() if root else "")
    if repo and defs:
        page.setdefault("inputs", signatures(repo, defs, page.get("head_sha", ""), set(), ""))
    html = out or page_path.with_suffix(".html")
    html.write_text(render(page, repo))
    print(f"page: {html}")
    return run_check(html, html.parent / (html.stem + "-screens"))


def explain_code(target: str, repo: str | None, out: Path | None) -> int:
    """Reader mode for code (no PR): gather code facts once; render + check once page.json exists."""
    from visualize.codefacts import gather
    from visualize.config import repo_root
    root = repo_root()
    if not root:
        raise RuntimeError("explain --code must run inside the repo that contains the code")
    repo = repo or default_repo()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", target).strip("-")[:80]
    work = CACHE_ROOT / repo.replace("/", "__") / "code" / slug
    work.mkdir(parents=True, exist_ok=True)
    facts_path = work / "facts.json"
    if not facts_path.exists():
        cfg = load_config()
        facts = gather(root, target, cfg)
        facts_path.write_text(json.dumps(facts, indent=1))
        print(json.dumps({"target": target, "files": facts["files"], "definitions": len(facts["definitions"]),
                          "callers": len(facts["callers"]), "tests": len(facts["tests"]), "config": cfg.sources}, indent=1))
    page_json = work / "page.json"
    if not page_json.exists():
        print(f"workspace: {work}\nnext: write page.json there (visualize skill, mode \"code\"), then run `visualize explain --code {target}` again")
        return 0
    facts = json.loads(facts_path.read_text())
    page = json.loads(page_json.read_text())
    load_cited(page_json.read_text(), root, facts["sources"], facts["definitions"])
    page.update({"mode": "code", "head_sha": facts["head"], "base_sha": facts["head"], "defdiff": facts["definitions"],
                 "sources": facts["sources"], "inputs": signatures(repo, facts["definitions"], facts["head"], set(), "")})
    page.setdefault("url", f"https://github.com/{repo}/blob/{facts['head']}/{facts['files'][0]}" if facts["files"] else "")
    page.setdefault("source_label", f"{target} @ {facts['head'][:10]}")
    html = work / "page.html"
    html.write_text(render(page, repo))
    if out:
        out.write_text(html.read_text())
    print(f"page: {out or html}")
    return run_check(html, work / "screens")


def present(name: str, out: Path | None, history: bool) -> int:
    """Author mode: page.json + decisions.json in the workspace; every changed render is kept as page.vN.*."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    work = CACHE_ROOT / "_present" / slug
    work.mkdir(parents=True, exist_ok=True)
    decisions = work / "decisions.json"
    if not decisions.exists():
        # Iteration memory: questions asked + answers, author suggestions, resolved conflicts. Read before every round.
        decisions.write_text(json.dumps({"questions": [], "suggestions": [], "conflicts": []}, indent=1))
    if history:
        for p in sorted(work.glob("page.v*.html"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1))):
            print(p)
        print(f"decisions: {decisions}")
        return 0
    page_json = work / "page.json"
    if not page_json.exists():
        print(f"workspace: {work}\nnext: write page.json (mode \"proposal\") and log questions/answers/suggestions in decisions.json,"
              f" then run `visualize present {name}` again")
        return 0
    page_text = page_json.read_text()
    page = json.loads(page_text)
    page.setdefault("mode", "proposal")
    html_text = render(page)
    html = work / "page.html"
    html.write_text(html_text)
    if out:
        out.write_text(html_text)
    version = _snapshot(work, page_text, html_text)
    print(f"page: {out or html}  (version v{version}; history: `visualize present {name} --history`)")
    return run_check(html, work / "screens")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(prog="visualize", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    ex = sub.add_parser("explain", help="explain a PR (--pr) or a part of the code (--code) — reader mode")
    ex.add_argument("number", type=int, nargs="?", help="shorthand for --pr")
    ex.add_argument("--pr", type=int, default=None)
    ex.add_argument("--code", default=None, help="path[::Symbol[.method]] in the current repo")
    ex.add_argument("--repo", default=None, help="owner/name (default: repo of the current directory)")
    ex.add_argument("--refresh", action="store_true", help="re-gather facts (PR got new commits)")
    ex.add_argument("--out", type=Path, default=None, help="also write the page here")
    rd = sub.add_parser("render", help="render any page.json you wrote (free-form explanation); cites resolve in the current repo")
    rd.add_argument("page", type=Path)
    rd.add_argument("--repo", default=None)
    rd.add_argument("--out", type=Path, default=None)
    pr_ = sub.add_parser("present", help="present a proposal / design (author mode)")
    pr_.add_argument("name", help="proposal name, e.g. inventory-segmentation")
    pr_.add_argument("--out", type=Path, default=None, help="also write the page here")
    pr_.add_argument("--history", action="store_true", help="list rendered versions and the decisions log")
    sub.add_parser("config", help="show the merged config and where it came from")
    sub.add_parser("kinds", help="list visualization kinds (plugin folders) and where they come from")
    sub.add_parser("design", help="show design tokens (defaults + overrides) and how to override them")
    sub.add_parser("install", help="link this repo into ~/.agents/{tools,skills} and ~/.local/bin")
    sub.add_parser("uninstall", help="remove those links")
    args = ap.parse_args(argv)
    if args.command == "kinds":
        from visualize.kinds import BUILTIN, discover, search_dirs
        for name, kind in discover().items():
            print(f"{name:<16} {kind.dir}  — {kind.description}")
        print("search:", ", ".join(map(str, search_dirs())))
        return 0
    if args.command == "design":
        from visualize.design import __doc__ as how, defaults
        over = load_config().data.get("design", {})
        print(json.dumps({"defaults": defaults(), "overrides": over}, indent=1))
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
        if args.command == "render":
            return render_page(args.page, args.repo, args.out)
        if args.command == "explain":
            if args.code:
                return explain_code(args.code, args.repo, args.out)
            pr = args.pr or args.number
            if not pr:
                ap.error("explain needs --pr <number> or --code <path[::symbol]>")
            return explain(pr, args.repo or default_repo(), args.refresh, args.out)
        return present(args.name, args.out, args.history)
    except RuntimeError as error:  # gh failures: unknown PR, no access, network
        print(f"visualize: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
