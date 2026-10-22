"""`visualize install` / `uninstall`: link this repo into the agent folders and PATH (no copies)."""

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
LINKS = {
    HOME / ".agents" / "tools" / "visualize": REPO,
    HOME / ".agents" / "skills" / "visualize": REPO / "skill",
    HOME / ".local" / "bin" / "visualize": REPO / "bin" / "visualize",
}
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _prerequisites() -> list[str]:
    """Missing or misconfigured prerequisites, as readable lines (nothing is installed)."""
    problems = []
    for cmd in ("gh", "python3", "node"):
        if not shutil.which(cmd):
            problems.append(f"missing `{cmd}` on PATH")
    if shutil.which("gh") and subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        problems.append("`gh` is not logged in (run `gh auth login`)")
    if not Path(CHROME).exists() and not shutil.which("google-chrome"):
        problems.append("Google Chrome not found (needed by the page check; set CHROME=/path/to/chrome)")
    if str(HOME / ".local" / "bin") not in subprocess.os.environ.get("PATH", ""):
        problems.append("~/.local/bin is not on PATH")
    return problems


def install() -> int:
    """Create (or repoint) the symlinks; refuse to replace real files/folders."""
    for link, target in LINKS.items():
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            print(f"skip {link}: exists and is not a symlink (move it away first)")
            continue
        link.symlink_to(target)
        print(f"{link} -> {target}")
    problems = _prerequisites()
    print("prerequisites: ok" if not problems else "prerequisites:\n  " + "\n  ".join(problems))
    print("update later with `git pull` in", REPO)
    return 0


def uninstall() -> int:
    """Remove only symlinks that point into this repo."""
    for link, target in LINKS.items():
        if link.is_symlink() and link.resolve() == target.resolve():
            link.unlink()
            print(f"removed {link}")
    return 0
