"""Per-PR workspace on disk and read-only GitHub access through the `gh` CLI."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

CACHE_ROOT = Path.home() / ".cache" / "visualize"


@dataclass(frozen=True)
class Workspace:
    """Files for one PR: `~/.cache/visualize/<owner>__<repo>/<number>/`."""

    repo: str
    number: int

    @property
    def dir(self) -> Path:
        """Workspace directory (created on first use)."""
        path = CACHE_ROOT / self.repo.replace("/", "__") / str(self.number)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def path(self, name: str) -> Path:
        """Path of a workspace file."""
        return self.dir / name

    def read_json(self, name: str):
        """Load a JSON workspace file."""
        return json.loads(self.path(name).read_text())

    def write_json(self, name: str, data) -> Path:
        """Write a JSON workspace file (indented, UTF-8)."""
        target = self.path(name)
        target.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        return target

    @property
    def refs(self) -> dict:
        """`{"base": merge_base_sha, "head": head_sha}` written by `prepare`."""
        return self.read_json("refs.json")


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


def fetch(repo: str, path: str, ref: str) -> str | None:
    """File content at `ref`, cached under the cache root; None when it does not exist there."""
    cache = CACHE_ROOT / "_files" / repo.replace("/", "__") / ref[:12] / path
    if cache.exists():
        return cache.read_text()
    result = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw", f"repos/{repo}/contents/{path}?ref={ref}"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(result.stdout)
    return result.stdout
