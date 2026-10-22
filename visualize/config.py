"""Layered configuration: built-in defaults → ~/.config/visualize/config.toml → <repo>/.visualize.toml.

Later layers override earlier ones key by key (lists are replaced, not merged). Rules are regexes searched in
repo-relative file paths; for `layers` and `interfaces` the first matching entry wins, in file order.
"""

import copy
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS: dict = {
    "repo": {"fallback": ""},  # used only outside a git repo, and announced
    "layers": {
        "tests": [r"(^|/)tests?/", r"(^|/)test_[^/]*\.py$", r"_test\.py$", r"conftest\.py$"],
        "db": [r"(^|/)migrations?/"],
        "api": [r"/(graphql|gql|routers?|resolvers?|api)/"],
        # Commands / use cases are domain (first match wins, so domain precedes application).
        "domain": [r"/domain/", r"/use_?cases?/", r"/commands?/"],
        "application": [r"/application/"],
        "infrastructure": [r"/infrastructure/", r"/adapters?/"],
    },
    "interfaces": {
        "db": [r"/migrations?/versions/.*\.py$"],
        "graphql": [r"/(graphql|gql)/.*\.py$"],
        "events": [r"/events?/.*\.py$"],
    },
    "ignore": {"generated": [r"/generated/"]},
    "schema": {"introspection": ""},  # GraphQL introspection JSON (repo-relative) for operation signatures
}

USER_CONFIG = Path.home() / ".config" / "visualize" / "config.toml"
REPO_CONFIG = ".visualize.toml"


def _merge(base: dict, over: dict) -> dict:
    """Recursive dict merge; non-dict values (including lists) from `over` replace `base`."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        out[key] = _merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def repo_root(start: Path | None = None) -> Path | None:
    """Top of the git working tree containing `start` (default: cwd), else None."""
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start or Path.cwd(), capture_output=True, text=True)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


@dataclass
class Config:
    """Merged configuration plus where each layer came from."""

    data: dict
    sources: list[str] = field(default_factory=list)

    def _rules(self, section: str) -> list[tuple[str, list[re.Pattern]]]:
        return [(name, [re.compile(p) for p in patterns]) for name, patterns in self.data.get(section, {}).items()]

    def first_match(self, section: str, path: str) -> str | None:
        """Name of the first entry in `section` whose rules match `path`."""
        for name, rules in self._rules(section):
            if any(r.search(path) for r in rules):
                return name
        return None

    def layer(self, path: str) -> str:
        """Layer of a file (tests/db/api/application/domain/infrastructure/…), else "other"."""
        return self.first_match("layers", path) or "other"

    def interface(self, path: str) -> str | None:
        """Interface surface of a file (graphql/events/db/generated_sdk/feature_flags/…), else None."""
        return self.first_match("interfaces", path)

    def is_test(self, path: str) -> bool:
        return self.layer(path) == "tests"

    def is_generated(self, path: str) -> bool:
        return any(re.search(p, path) for p in self.data.get("ignore", {}).get("generated", []))

    @property
    def introspection(self) -> str:
        return self.data.get("schema", {}).get("introspection", "")


def load(start: Path | None = None) -> Config:
    """Defaults, then the user config, then the repo config (if the cwd is inside a repo)."""
    data, sources = copy.deepcopy(DEFAULTS), ["built-in defaults"]
    root = repo_root(start)
    for path in (USER_CONFIG, root / REPO_CONFIG if root else None):
        if path and path.exists():
            data = _merge(data, tomllib.loads(path.read_text()))
            sources.append(str(path))
    return Config(data, sources)
