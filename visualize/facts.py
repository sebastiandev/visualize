"""`visualize facts`: deterministic facts about a change (or a part of the code) → a facts folder.

Sources, local first:
  --local            current branch + uncommitted/untracked files vs the merge-base with the default branch
  --diff F --base R  a diff the agent already has; must apply to the files at R (and head, default: working tree)
  --pr N             a GitHub PR; files are read from local git when its commits exist here, else from GitHub
  --code path::Sym   no change: sources, definitions, callers and tests at HEAD

Folder contents: facts.json (source, refs, title, summary), change.diff, defdiff.json, contracts.json,
signatures.json — or, for --code, code.json (definitions, sources, callers, tests).
"""

import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from visualize.config import load as load_config, repo_root
from visualize.contracts import delta
from visualize.definitions import defdiff, signatures
from visualize.diffparse import parse
from visualize.workspace import CACHE_ROOT, WORKTREE, fetch, gh, has_commit, read_counts, use_local


def git(root: Path, *args: str, codes=(0,)) -> str:
    """stdout of a git command in `root`; raises when the exit code is not in `codes`."""
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, errors="replace")
    if result.returncode not in codes:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def default_base(root: Path) -> str:
    """The default branch ref to compare against: origin/HEAD, else origin/main, main, origin/master, master."""
    head = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD", codes=(0, 1)).strip()
    for ref in [head.removeprefix("refs/remotes/")] if head else []:
        return ref
    for ref in ("origin/main", "main", "origin/master", "master"):
        if git(root, "rev-parse", "-q", "--verify", ref, codes=(0, 1)).strip():
            return ref
    raise RuntimeError("no default branch found: pass --base <ref>")


def default_dir(repo: str, key: str) -> Path:
    return CACHE_ROOT / repo.replace("/", "__") / key / "facts"


# ---- sources: each returns (meta, diff_text, base_sha, head_ref, head_sha) ----

def from_pr(repo: str, number: int, root: Path | None) -> tuple:
    meta = json.loads(gh("pr", "view", str(number), "-R", repo, "--json",
                         "number,title,body,url,author,baseRefOid,headRefOid,state,isDraft"))
    head, tip = meta["headRefOid"], meta["baseRefOid"]
    local = root and has_commit(head) and has_commit(tip)
    # Compare against the merge-base, never the current base tip: commits merged after branching would look like removals.
    if local:
        base = git(root, "merge-base", tip, head).strip()
        text = git(root, "diff", "--no-color", base, head)
    else:
        base = gh("api", f"repos/{repo}/compare/{tip}...{head}", "-q", ".merge_base_commit.sha").strip()
        text = gh("pr", "diff", str(number), "-R", repo)
    meta.update(source=f"pr #{number} ({'local git' if local else 'GitHub'})", label=f"#{number} on GitHub",
                merge_base_differs_from_tip=base != tip)
    return meta, text, base, head, head


def _untracked_diff(root: Path) -> str:
    files = git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return "".join(git(root, "diff", "--no-color", "--no-index", "--", "/dev/null", f, codes=(0, 1)) for f in files)


def from_local(root: Path, base_ref: str | None, title: str | None, body: str) -> tuple:
    base_ref = base_ref or default_base(root)
    base = git(root, "merge-base", base_ref, "HEAD").strip()
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    text = git(root, "diff", "--no-color", base) + _untracked_diff(root)
    dirty = len(git(root, "status", "--porcelain").splitlines())
    meta = {"title": title or branch, "body": body, "branch": branch, "base_ref": base_ref,
            "source": f"local {branch} vs merge-base with {base_ref} ({base[:10]}), {dirty} uncommitted file(s)",
            "label": f"{branch} (local)"}
    return meta, text, base, WORKTREE, git(root, "rev-parse", "HEAD").strip()


def mismatches(repo: str, files: dict, base: str, head: str) -> list[str]:
    """Files whose hunks do not match the base (old side) or head (new side) contents."""
    bad = []
    for path, hunks in files.items():
        before, after = fetch(repo, path, base), fetch(repo, path, head)
        b, a = (before or "").splitlines(), (after or "").splitlines()
        for h in hunks:
            if any((l["t"] != "+" and (l["o"] > len(b) or b[l["o"] - 1] != l["s"])) or
                   (l["t"] != "-" and (l["n"] > len(a) or a[l["n"] - 1] != l["s"])) for l in h["lines"]):
                bad.append(path)
                break
    return bad


def from_diff(repo: str, root: Path, text: str, base_ref: str, head_ref: str | None, title: str | None, body: str) -> tuple:
    base = git(root, "rev-parse", "--verify", base_ref + "^{commit}").strip()
    head = git(root, "rev-parse", "--verify", head_ref + "^{commit}").strip() if head_ref else WORKTREE
    bad = mismatches(repo, parse(text), base, head)
    if bad:
        raise RuntimeError(f"the diff does not apply to {base_ref}..{head_ref or 'working tree'} in {', '.join(bad[:5])}"
                           " — wrong --base/--head, or the files changed since; try `visualize facts --local`")
    head_sha = head if head != WORKTREE else git(root, "rev-parse", "HEAD").strip()
    meta = {"title": title or "Change", "body": body, "source": f"provided diff vs {base_ref} ({base[:10]})",
            "label": f"diff vs {base_ref}"}
    return meta, text, base, head, head_sha


# ---- writers ----

def write_change(out: Path, repo: str, meta: dict, text: str, base: str, head: str, head_sha: str) -> dict:
    """Common facts for a change: diff, definitions, interface delta, signatures, summary."""
    cfg = load_config()
    out.mkdir(parents=True, exist_ok=True)
    (out / "change.diff").write_text(text)
    paths = list(parse(text))
    code = [p for p in paths if p.endswith(".py") and not cfg.is_test(p) and not cfg.is_generated(p)]
    contracts = delta(repo, [p for p in paths if not cfg.is_test(p)], base, head, cfg)
    defs = defdiff(repo, code, base, head)
    sigs = signatures(repo, defs, head, set(paths), cfg.introspection)
    adds = sum(l.startswith("+") and not l.startswith("+++") for l in text.splitlines())
    dels = sum(l.startswith("-") and not l.startswith("---") for l in text.splitlines())
    summary = {"files": len(paths), "additions": adds, "deletions": dels, "layers": dict(Counter(cfg.layer(p) for p in paths)),
               "definitions": len(defs), "interface_changes": len(contracts), "breaking": sum(e["breaking"] is True for e in contracts),
               "changed_definitions": [f'{d["change"]} {d["name"]}' for d in defs][:40]}
    facts = {"kind": "change", "repo": repo, "source": meta.pop("source"), "label": meta.pop("label"),
             "base": base, "head": head, "head_sha": head_sha, "title": meta.get("title", ""),
             "description": (meta.get("body") or "")[:2000], "url": meta.get("url", ""), "number": meta.get("number"),
             "file_paths": paths, "summary": summary, "meta": meta, "config": cfg.sources, "reads": read_counts()}
    for name, data in (("facts.json", facts), ("defdiff.json", defs), ("contracts.json", contracts), ("signatures.json", sigs)):
        (out / name).write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return facts


def write_code(out: Path, repo: str, root: Path, target: str) -> dict:
    from visualize.codefacts import gather
    cfg = load_config()
    out.mkdir(parents=True, exist_ok=True)
    code = gather(root, target, cfg)
    (out / "code.json").write_text(json.dumps(code, indent=1, ensure_ascii=False))
    summary = {"files": len(code["files"]), "definitions": len(code["definitions"]), "callers": len(code["callers"]),
               "tests": len(code["tests"]), "layers": code["layers"]}
    facts = {"kind": "code", "repo": repo, "source": f"code {target} @ {code['head'][:10]}", "label": f"{target} @ {code['head'][:10]}",
             "base": code["head"], "head": code["head"], "head_sha": code["head"], "title": target, "description": "",
             "url": f"https://github.com/{repo}/blob/{code['head']}/{code['files'][0]}" if code["files"] else "",
             "file_paths": code["files"], "summary": summary | {"definition_names": [d["name"] for d in code["definitions"]][:60]},
             "config": cfg.sources}
    (out / "facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False))
    return facts


def gather(args, repo: str) -> tuple[Path, dict]:
    """Dispatch on the chosen source; returns (facts folder, facts.json)."""
    root = repo_root()
    use_local(root)
    body = Path(args.body_file).read_text() if getattr(args, "body_file", None) else ""
    if args.code:
        if not root:
            raise RuntimeError("--code must run inside the repo that contains the code")
        key = "code-" + re.sub(r"[^A-Za-z0-9]+", "-", args.code).strip("-")[:80]
        out = args.out or default_dir(repo, key)
        return out, write_code(out, repo, root, args.code)
    if args.pr:
        src, key = from_pr(repo, args.pr, root), f"pr-{args.pr}"
    elif not root:
        raise RuntimeError("--local/--diff must run inside the repo; use --pr <n> for code that is not checked out")
    elif args.diff:
        text = (Path("/dev/stdin") if args.diff == "-" else Path(args.diff)).read_text()
        if not args.base:
            raise RuntimeError("--diff needs --base <ref> (the commit the diff was made against)")
        src = from_diff(repo, root, text, args.base, args.head, args.title, body)
        key = "diff-" + hashlib.sha1((args.base + text).encode()).hexdigest()[:10]
    else:
        src = from_local(root, args.base, args.title, body)
        key = "local-" + re.sub(r"[^A-Za-z0-9]+", "-", src[0]["branch"]).strip("-")
    out = args.out or default_dir(repo, key)
    return out, write_change(out, repo, *src)
