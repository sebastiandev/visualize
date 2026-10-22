"""Visualization kinds (plugins): folders with guideline.md, schema.json, render.js and optional style.css.

Discovery order (later wins on name clashes): bundled `<tool>/kinds/` → `~/.config/visualize/kinds/` →
`<repo>/.visualize/kinds/`. Default kinds (sequence, decisions, entities, state-machine) ship as plugins in `<tool>/kinds/`.
Only kinds a page actually uses are inlined into it. Kinds are never loaded from PR content.

render.js contract:
    export default function render(block, ctx) { ... }    // or: module.render = (block, ctx) => { ... }
`block` is the page.json diagram (validated against schema.json); `ctx` is the render API (see SKILL.md).
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from visualize.config import repo_root

TOOL = Path(__file__).resolve().parent.parent
BUILTIN: set[str] = set()  # every kind, including the defaults, is a plugin folder


@dataclass
class Kind:
    """One discovered plugin kind."""

    name: str
    dir: Path

    def read(self, name: str) -> str:
        path = self.dir / name
        return path.read_text() if path.exists() else ""

    @property
    def description(self) -> str:
        """First non-heading line of guideline.md."""
        for line in self.read("guideline.md").splitlines():
            if line.strip() and not line.startswith("#"):
                return line.strip()
        return ""


def search_dirs() -> list[Path]:
    root = repo_root()
    return [TOOL / "kinds", Path.home() / ".config" / "visualize" / "kinds"] + ([root / ".visualize" / "kinds"] if root else [])


def discover() -> dict[str, Kind]:
    """name → Kind, later directories overriding earlier ones."""
    found: dict[str, Kind] = {}
    for base in search_dirs():
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "render.js").exists():
                    found[d.name] = Kind(d.name, d)
    return found


def _validate(block: dict, schema: dict, kind: str) -> list[str]:
    """Minimal check: required keys and top-level JSON types (no external dependency)."""
    types = {"string": str, "array": list, "object": dict, "number": (int, float), "boolean": bool}
    errors = [f"{kind}: missing '{k}'" for k in schema.get("required", []) if k not in block]
    for key, spec in schema.get("properties", {}).items():
        t = types.get(spec.get("type")) if isinstance(spec, dict) else None
        if key in block and t and not isinstance(block[key], t):
            errors.append(f"{kind}: '{key}' should be {spec['type']}")
    return errors


def _scope_css(css: str, kind: str) -> str:
    """Prefix every selector with [data-kind="<kind>"] so a kind cannot restyle the page."""
    out = []
    for rule in css.split("}"):
        if "{" not in rule:
            continue
        sel, body = rule.split("{", 1)
        sel = re.sub(r"/\*.*?\*/", "", sel, flags=re.S).strip()
        if sel:
            out.append(",".join(f'[data-kind="{kind}"] {s.strip()}' for s in sel.split(",")) + "{" + body + "}")
    return "\n".join(out)


def bundle(diagrams: list[dict]) -> tuple[str, str, list[str]]:
    """(js, css, errors) for the kinds used by `diagrams` (every kind is a plugin folder)."""
    available, js, css, errors = discover(), [], [], []
    for name in sorted({d.get("type") for d in diagrams} - BUILTIN):
        kind = available.get(name)
        if not kind:
            errors.append(f"unknown kind '{name}' (searched: {', '.join(map(str, search_dirs()))})")
            continue
        schema = json.loads(kind.read("schema.json") or "{}")
        for d in diagrams:
            if d.get("type") == name:
                errors += _validate(d, schema, name)
        code = re.sub(r"\bexport\s+default\s+", "module.render = ", kind.read("render.js"), count=1)
        js.append(f"window.VISUALIZE_KINDS=window.VISUALIZE_KINDS||{{}};"
                  f"window.VISUALIZE_KINDS[{json.dumps(name)}]=(function(){{const module={{}};\n{code}\n;return module.render;}})();")
        css.append(_scope_css(kind.read("style.css"), name))
    return "\n".join(js).replace("</script", "<\\/script"), "\n".join(css), errors
