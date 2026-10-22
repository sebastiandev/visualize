"""Render the self-contained explain page: authored page.json + computed diff, definitions, contract cards + assets."""

import ast
import json
import re
from pathlib import Path

from visualize.diffparse import parse
from visualize.workspace import Workspace, fetch

ASSETS = Path(__file__).resolve().parent.parent / "assets"
VENDOR = ASSETS / "vendor"


def _scoped_theme(css: str, theme: str) -> str:
    """Prefix every selector of a highlight.js theme with [data-theme=…]; drop the .hljs block background."""
    out = []
    for rule in css.split("}"):
        if "{" not in rule:
            continue
        selectors, body = rule.split("{", 1)
        selectors = re.sub(r"/\*.*?\*/", "", selectors, flags=re.S).strip()
        if not selectors:
            continue
        if selectors == ".hljs":
            body = re.sub(r"background(-color)?:[^;]+;?", "", body)
        out.append(",".join(f"[data-theme={theme}] {s.strip()}" for s in selectors.split(",")) + "{" + body + "}")
    return "\n".join(out)


def _span(source: str, name: str) -> tuple[int, int] | None:
    """Head line range of a top-level class (whole), function (signature + docstring) or constant."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return min([node.lineno] + [d.lineno for d in node.decorator_list]), node.end_lineno
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            first = node.body[0]
            doc = isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str)
            return min([node.lineno] + [d.lineno for d in node.decorator_list]), max(first.end_lineno if doc else first.lineno - 1, node.lineno)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.lineno, node.end_lineno
    return None


def _contract_cards(repo: str, head: str, entries: list[dict]) -> list[dict]:
    """One card per changed interface type: new → definition source; changed → diff range; generated SDK folds into one card."""
    cards: dict[tuple, dict] = {}
    sdk_files, sdk_count = set(), 0
    for e in entries:
        if e["surface"] == "generated_sdk":
            sdk_files.add(e["file"]); sdk_count += 1
            continue
        top = e["name"].split(".")[0].rstrip("()")
        c = cards.setdefault((e["surface"], top, e["file"]), {"surface": e["surface"], "name": top, "file": e["file"], "change": None, "breaking": False, "members": 0})
        if e["name"].rstrip("()") == top:
            c["change"] = e["change"]
        else:
            c["members"] += 1
        if e["breaking"] is True or (e["breaking"] == "review" and c["breaking"] is not True):
            c["breaking"] = e["breaking"]
    out = []
    for c in cards.values():
        c["change"] = c["change"] or "changed"
        src = fetch(repo, c["file"], head) or ""
        try:
            rng = _span(src, c["name"]) if src.strip() else None
        except SyntaxError:
            rng = None
        if rng:
            c["range"] = list(rng)
            if c["change"] == "added":
                lines = src.splitlines()
                c["code"] = [{"n": i, "s": lines[i - 1]} for i in range(rng[0], min(rng[1], len(lines)) + 1)]
        out.append(c)
    out.sort(key=lambda c: (c["change"] != "added", c["surface"], c["name"]))
    if sdk_count:
        out.append({"surface": "generated_sdk", "name": "Generated SDK", "file": ", ".join(sorted(sdk_files)), "change": "changed",
                    "breaking": False, "members": sdk_count, "generated": True})
    return out


def _proposal_cards(page: dict) -> None:
    """Turn authored `model_cards` (proposal mode) into interface cards: new → definition; changed → before/after diff."""
    import difflib
    page.setdefault("diff", {})
    cards = []
    for c in page.get("model_cards", []):
        key = c.get("file") or f"proposal/{c['name']}.{c.get('ext', 'py')}"
        card = {"surface": c.get("surface", "model"), "name": c["name"], "file": key, "change": c.get("change", "added"),
                "breaking": c.get("breaking", False), "members": 0, "ref": c.get("ref")}
        if card["change"] == "added":
            card["code"] = [{"n": i, "s": s} for i, s in enumerate(c["after"].splitlines(), start=c.get("start", 1))]
        else:
            before, after = c["before"].splitlines(), c["after"].splitlines()
            text = "\n".join(["diff --git a/x b/" + key] + list(difflib.unified_diff(before, after, "a/x", "b/x", n=max(len(before), len(after)), lineterm="")))
            page["diff"][key] = parse(text).get(key, [])
            card["members"] = sum(1 for h in page["diff"][key] for l in h["lines"] if l["t"] != " ")
        cards.append(card)
    if cards:
        page["contract_cards"] = cards


def render(page: dict, repo: str = "") -> str:
    """Self-contained HTML for a page dict (PR explain page or proposal page)."""
    if page.get("model_cards"):
        _proposal_cards(page)
    for key, empty in (("diff", {}), ("defdiff", []), ("inputs", {}), ("contract_cards", [])):
        page.setdefault(key, empty)
    hl_js = "".join((VENDOR / f).read_text() + ";\n" for f in ("highlight-11.10.0.min.js", "graphql-11.10.0.min.js", "dockerfile-11.10.0.min.js"))
    hl_css = _scoped_theme((VENDOR / "github.min.css").read_text(), "light") + "\n" + _scoped_theme((VENDOR / "github-dark.min.css").read_text(), "dark")
    html = (ASSETS / "template.html").read_text()
    html = html.replace("/*D3*/", (VENDOR / "d3.v7.9.0.min.js").read_text()).replace("/*HLJS*/", hl_js).replace("/*HLCSS*/", hl_css)
    html = html.replace("https://github.com/__REPO__/", f"https://github.com/{repo}/" if repo else "#")
    from visualize.kinds import bundle
    kinds_js, kinds_css, kind_errors = bundle(page.get("diagrams", []))
    for err in kind_errors:
        print("visualize:", err)
    html = html.replace("/*KINDS*/", kinds_js).replace("/*KINDCSS*/", kinds_css)
    from visualize.config import load
    from visualize.design import overrides_css
    css, unknown = overrides_css(load().data.get("design", {}))
    if unknown:
        print("visualize: unknown design tokens ignored:", ", ".join(unknown))
    if css:
        html = html.replace("</head>", f"<style id=\"design-overrides\">{css}</style></head>", 1)
    return html.replace("/*PAGE*/", json.dumps(page).replace("</", "<\\/"))


def build(ws: Workspace, out: Path | None = None) -> Path:
    """Write the page HTML (default: workspace/page.html) and return its path."""
    page = ws.read_json("page.json")
    refs = ws.refs
    page.update({
        "base_sha": refs["base"], "head_sha": refs["head"],
        "diff": parse(ws.path("pr.diff").read_text()),
        "defdiff": ws.read_json("defdiff.json"),
        "inputs": ws.read_json("signatures.json"),
        "contract_cards": _contract_cards(ws.repo, refs["head"], ws.read_json("contracts.json")) if page.get("show_contract", True) else [],
    })
    page.setdefault("url", f"https://github.com/{ws.repo}/pull/{ws.number}")
    page.setdefault("number", ws.number)
    target = out or ws.path("page.html")
    target.write_text(render(page, ws.repo))
    return target
