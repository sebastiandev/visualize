"""Facts for `explain --code`: definitions, sources, callers and tests for a path/symbol at the current commit.

Reads the local working tree (the agent's repo), not GitHub. Callers and tests are found with `git grep` on the
symbol name — a heuristic the agent refines (or replaces with the code graph when available).
"""

import ast
import re
import subprocess
from pathlib import Path

from visualize.definitions import definitions


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def resolve(root: Path, target: str) -> tuple[list[str], str | None]:
    """`path[::Symbol[.method]]` → (python files under path, symbol or None)."""
    path, _, symbol = target.partition("::")
    full = root / path
    if full.is_dir():
        files = sorted(str(p.relative_to(root)) for p in full.rglob("*.py") if "__pycache__" not in p.parts)
    elif full.exists():
        files = [path]
    else:
        raise RuntimeError(f"not found in {root}: {path}")
    return files, symbol or None


def gather(root: Path, target: str, cfg, max_files: int = 25) -> dict:
    """Definitions (optionally narrowed to a symbol), their source files, callers and tests."""
    files, symbol = resolve(root, target)
    files = [f for f in files if not cfg.is_test(f) and not cfg.is_generated(f)][:max_files]
    defs, sources = [], {}
    for f in files:
        src = (root / f).read_text()
        try:
            found = definitions(src)
        except SyntaxError:
            continue
        for name, d in found.items():
            if symbol and not (name == symbol or name.startswith(symbol + ".")):
                continue
            defs.append({"file": f, "name": name, "change": "unchanged", "before": None, "after": d, "ref": f"{f}:{d['line']}"})
        if not symbol or any(e["file"] == f for e in defs):
            sources[f] = src.splitlines()
    short = (symbol or Path(files[0]).stem if files else "").split(".")[-1]
    callers, tests = [], []
    if short:
        for line in _git(root, "grep", "-n", "-w", "-I", short, "--", "*.py").splitlines()[:400]:
            path, _, rest = line.partition(":")
            num = rest.split(":", 1)[0]
            if path in sources:
                continue
            (tests if cfg.is_test(path) else callers).append(f"{path}:{num}")
    return {"target": target, "symbol": symbol, "files": list(sources), "definitions": defs, "sources": sources,
            "callers": callers[:60], "tests": tests[:60], "head": _git(root, "rev-parse", "HEAD").strip(),
            "layers": {f: cfg.layer(f) for f in sources}}
