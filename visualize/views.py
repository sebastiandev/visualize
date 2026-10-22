"""Views (plugins): every section of a doc is drawn by a view folder — guideline.md, schema.json, render.js, style.css.

Discovery order (later wins on name clashes): bundled `<tool>/views/` → `~/.config/visualize/views/` →
`<repo>/.visualize/views/`. Defaults: tldr, call-path, matrix, interface-changes, watch, sequence, decisions,
entities, state-machine. Only views a doc uses are inlined. Views are never loaded from PR content.

render.js contract:
    export default function render(block, ctx) { ... }    // or: module.render = (block, ctx) => { ... }
`block` is the doc section (validated against schema.json); `ctx` is the render API (see SKILL.md).
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from visualize.config import repo_root

TOOL = Path(__file__).resolve().parent.parent


@dataclass
class View:
    """One discovered view folder."""

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
    return [TOOL / "views", Path.home() / ".config" / "visualize" / "views"] + ([root / ".visualize" / "views"] if root else [])


def discover() -> dict[str, View]:
    """name → View, later directories overriding earlier ones."""
    found: dict[str, View] = {}
    for base in search_dirs():
        if base.is_dir():
            for d in sorted(base.iterdir()):
                if (d / "render.js").exists():
                    found[d.name] = View(d.name, d)
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


def _scope_rules(css: str, view: str) -> str:
    out = []
    for rule in css.split("}"):
        if "{" not in rule:
            continue
        sel, body = rule.split("{", 1)
        sel = re.sub(r"/\*.*?\*/", "", sel, flags=re.S).strip()
        if sel:
            out.append(",".join(f'[data-view="{view}"] {s.strip()}' for s in sel.split(",")) + "{" + body + "}")
    return "\n".join(out)


def _scope_css(css: str, view: str) -> str:
    """Prefix every selector with [data-view="<view>"] so a view cannot restyle the page; one level of @media is kept."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, pos = [], 0
    for m in re.finditer(r"@media[^{]+\{((?:[^{}]*\{[^{}]*\})*)\s*\}", css):
        out.append(_scope_rules(css[pos:m.start()], view))
        out.append(css[m.start():css.index("{", m.start())] + "{" + _scope_rules(m.group(1), view) + "}")
        pos = m.end()
    out.append(_scope_rules(css[pos:], view))
    return "\n".join(x for x in out if x)


def bundle(sections: list[dict]) -> tuple[str, str, list[str]]:
    """(js, css, errors) for the views used by the doc's sections."""
    available, js, css, errors = discover(), [], [], []
    for name in sorted({s.get("view") for s in sections}):
        view = available.get(name)
        if not view:
            errors.append(f"unknown view '{name}' (searched: {', '.join(map(str, search_dirs()))})")
            continue
        schema = json.loads(view.read("schema.json") or "{}")
        for s in sections:
            if s.get("view") == name:
                errors += _validate(s, schema, name)
        code = re.sub(r"\bexport\s+default\s+", "module.render = ", view.read("render.js"), count=1)
        js.append(f"window.VISUALIZE_VIEWS=window.VISUALIZE_VIEWS||{{}};"
                  f"window.VISUALIZE_VIEWS[{json.dumps(name)}]=(function(){{const module={{}};\n{code}\n;return module.render;}})();")
        css.append(_scope_css(view.read("style.css"), name))
    return "\n".join(js).replace("</script", "<\\/script"), "\n".join(css), errors
