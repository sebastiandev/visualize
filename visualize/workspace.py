"""Workspaces on disk and file access: local git first, read-only GitHub (`gh`) only when the code is not local."""

import subprocess
from pathlib import Path

CACHE_ROOT = Path.home() / ".cache" / "visualize"


def gh(*args: str) -> str:
    """Run a read-only `gh` command and return stdout; raises on failure."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def default_repo() -> str:
    """`owner/name` of the GitHub repository in the current directory."""
    try:
        return gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    except RuntimeError as error:
        from visualize.config import load
        fallback = load().data.get("repo", {}).get("fallback", "")
        if fallback:
            import sys
            print(f"visualize: not in a GitHub repo; using configured fallback {fallback}", file=sys.stderr)
            return fallback
        raise RuntimeError("not inside a GitHub repository: run from the repo's working directory or pass --repo owner/name") from error


WORKTREE = "WORKTREE"  # ref meaning "the files on disk now" (uncommitted changes included)
_local: dict = {"root": None, "commits": {}, "reads": {"local": 0, "github": 0}}


def use_local(root: Path | None) -> None:
    """Read files from this checkout whenever the requested commit exists in it (set once per run)."""
    _local["root"] = root


def has_commit(ref: str) -> bool:
    """True when `ref` resolves to a commit in the local checkout."""
    root = _local["root"]
    if not root or not ref:
        return False
    if ref not in _local["commits"]:
        result = subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=root, capture_output=True)
        _local["commits"][ref] = result.returncode == 0
    return _local["commits"][ref]


def read_counts() -> dict:
    """How many file reads were served locally vs from GitHub in this run."""
    return dict(_local["reads"])


def fetch(repo: str, path: str, ref: str) -> str | None:
    """File content at `ref` (None when absent there): disk for WORKTREE, local git when the commit is local, else GitHub."""
    root = _local["root"]
    if ref == WORKTREE and root:
        _local["reads"]["local"] += 1
        full = root / path
        return full.read_text(errors="replace") if full.is_file() else None
    if has_commit(ref):
        _local["reads"]["local"] += 1
        result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True, text=True, errors="replace")
        return result.stdout if result.returncode == 0 else None
    cache = CACHE_ROOT / "_files" / repo.replace("/", "__") / ref[:12] / path
    _local["reads"]["github"] += 1  # cached copies count too: the content came from GitHub
    if cache.exists():
        return cache.read_text()
    result = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/{repo}/contents/{path}?ref={ref}"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(result.stdout)
    return result.stdout
