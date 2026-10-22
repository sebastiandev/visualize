"""Render the self-contained page: authored doc + computed diff, definitions, contract cards + assets."""

import ast
import json
import re
from pathlib import Path

from visualize.diffparse import parse
from visualize.workspace import fetch

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


def _authored_cards(cards: list[dict], diff: dict) -> list[dict]:
    """Authored definitions → interface cards: new → definition; changed → before/after diff (added to `diff`)."""
    import difflib
    out = []
    for c in cards:
        key = c.get("file") or f"proposal/{c['name']}.{c.get('ext', 'py')}"
        card = {"surface": c.get("surface", "model"), "name": c["name"], "file": key, "change": c.get("change", "added"),
                "breaking": c.get("breaking", False), "members": 0, "ref": c.get("ref")}
        if card["change"] == "added":
            card["code"] = [{"n": i, "s": s} for i, s in enumerate(c["after"].splitlines(), start=c.get("start", 1))]
        else:
            before, after = c["before"].splitlines(), c["after"].splitlines()
            text = "\n".join(["diff --git a/x b/" + key] + list(difflib.unified_diff(before, after, "a/x", "b/x", n=max(len(before), len(after)), lineterm="")))
            diff[key] = parse(text).get(key, [])
            card["members"] = sum(1 for h in diff[key] for l in h["lines"] if l["t"] != " ")
        out.append(card)
    return out


def sections_of(page: dict) -> list[dict]:
    """The doc's ordered sections; an old-shape page (tldr/locator/diagrams/examples/cards/watch) is converted."""
    if "sections" in page:
        return page["sections"]
    out = []
    if page.get("tldr"):
        out.append({"view": "tldr", **page["tldr"]})
    if page.get("locator"):
        out.append({"view": "call-path", **page["locator"]})
    out += [{**{k: v for k, v in d.items() if k != "type"}, "view": d["type"]} for d in page.get("diagrams", [])]
    if page.get("examples"):
        out.append({"view": "matrix", **page["examples"]})
    if page.get("model_cards"):
        out.append({"view": "interface-changes", "cards": page["model_cards"]})
    elif page.get("show_contract", True) and page.get("contract_cards"):
        out.append({"view": "interface-changes"})
    if page.get("watch"):
        out.append({"view": "watch", "items": page["watch"], **({"title": page["watch_title"]} if page.get("watch_title") else {})})
    return out


def render(page: dict, repo: str = "") -> str:
    """Self-contained HTML for a page dict (PR explain page or proposal page)."""
    for key, empty in (("diff", {}), ("defdiff", []), ("inputs", {}), ("contract_cards", [])):
        page.setdefault(key, empty)
    page["sections"] = sections_of(page)
    for sec in page["sections"]:
        if sec.get("view") == "interface-changes" and sec.get("cards"):
            sec["cards_built"] = _authored_cards(sec["cards"], page["diff"])
    hl_js = "".join((VENDOR / f).read_text() + ";\n" for f in ("highlight-11.10.0.min.js", "graphql-11.10.0.min.js", "dockerfile-11.10.0.min.js"))
    hl_css = _scoped_theme((VENDOR / "github.min.css").read_text(), "light") + "\n" + _scoped_theme((VENDOR / "github-dark.min.css").read_text(), "dark")
    html = (ASSETS / "template.html").read_text()
    html = html.replace("/*D3*/", (VENDOR / "d3.v7.9.0.min.js").read_text()).replace("/*HLJS*/", hl_js).replace("/*HLCSS*/", hl_css)
    html = html.replace("https://github.com/__REPO__/", f"https://github.com/{repo}/" if repo else "#")
    from visualize.views import bundle
    views_js, views_css, view_errors = bundle(page["sections"])
    for err in view_errors:
        print("visualize:", err)
    html = html.replace("/*VIEWS*/", views_js).replace("/*VIEWCSS*/", views_css)
    from visualize.config import load
    from visualize.design import overrides_css
    css, unknown = overrides_css(load().data.get("design", {}))
    if unknown:
        print("visualize: unknown design tokens ignored:", ", ".join(unknown))
    if css:
        html = html.replace("</head>", f"<style id=\"design-overrides\">{css}</style></head>", 1)
    return html.replace("/*PAGE*/", json.dumps(page).replace("</", "<\\/"))


def from_facts(page: dict, facts_dir: Path) -> str:
    """Merge a facts folder into the page (diffs, definitions, signatures, interface cards); returns the repo."""
    facts = json.loads((facts_dir / "facts.json").read_text())
    repo = facts["repo"]
    page.update({"base_sha": facts["base"], "head_sha": facts["head_sha"]})
    if facts["kind"] == "code":
        code = json.loads((facts_dir / "code.json").read_text())
        page.update({"mode": page.get("mode", "code"), "defdiff": code["definitions"], "sources": {**code["sources"], **page.get("sources", {})}})
    else:
        read = lambda name: json.loads((facts_dir / name).read_text())
        page.update({"diff": parse((facts_dir / "change.diff").read_text()), "defdiff": read("defdiff.json"),
                     "inputs": read("signatures.json"),
                     "contract_cards": _contract_cards(repo, facts["head"], read("contracts.json")) if page.get("show_contract", True) else []})
        if facts.get("number"):
            page.setdefault("number", facts["number"])
    page.setdefault("url", facts["url"] or f"https://github.com/{repo}/tree/{facts['head_sha']}")
    page.setdefault("source_label", facts["label"])
    return repo
