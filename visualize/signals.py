"""Deterministic view signals: facts about a change that make a view worth drawing.

A signal is evidence, not a choice: `suggest` lists it next to the view, and `explain` reports a signal the doc
neither uses nor answers in `view_decisions`. Each signal: {view, signal, evidence: ["path:line", ...]}.

    entities       the same field name is added to ≥ 3 classes (it travels across layers)
    state-machine  an Enum class gains or loses members
    decisions      ≥ 3 new `raise` sites in non-test code
    sequence       an event payload changes, or a new call crosses into another app/service
"""

import ast
import re

from visualize.diffparse import parse

ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag"}
FIELD_TRAVELS = 3
RAISES = 3


def _classes(source: str | None) -> dict[str, dict]:
    """Class name → {line, enum, fields: {name: line}} (annotated or assigned class-body names)."""
    if not source:
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        fields = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields[item.target.id] = item.lineno
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("__"):
                        fields[target.id] = item.lineno
        bases = {ast.unparse(b).split(".")[-1] for b in node.bases}
        out[node.name] = {"line": node.lineno, "enum": bool(bases & ENUM_BASES), "fields": fields}
    return out


def compute(diff_text: str, read_base, read_head, is_code) -> list[dict]:
    """Signals for a change. `read_base/read_head(path)` return file contents; `is_code(path)` excludes tests/generated."""
    files = [p for p in parse(diff_text) if p.endswith(".py") and is_code(p)]
    added: dict[str, list[str]] = {}
    enum_changes: list[str] = []
    for path in files:
        before, after = _classes(read_base(path)), _classes(read_head(path))
        for name, cls in after.items():
            old = before.get(name, {"fields": {}})
            new_fields = [f for f in cls["fields"] if f not in old["fields"]]
            if cls["enum"]:
                gone = [f for f in old["fields"] if f not in cls["fields"]]
                if new_fields or (gone and name in before):
                    enum_changes.append(f"{path}:{cls['line']}")
                continue
            for field in new_fields:
                added.setdefault(field, []).append(f"{path}:{cls['fields'][field]}")
    signals = [{"view": "entities", "signal": f"`{field}` is added to {len(refs)} classes", "evidence": refs}
               for field, refs in sorted(added.items(), key=lambda kv: -len(kv[1])) if len(refs) >= FIELD_TRAVELS]
    if enum_changes:
        signals.append({"view": "state-machine", "signal": f"{len(enum_changes)} enum(s) gain or lose members", "evidence": enum_changes})
    raises = [f"{path}:{l['n']}" for path, hunks in parse(diff_text).items() if path in files
              for h in hunks for l in h["lines"] if l["t"] == "+" and re.match(r"\s*raise\s+\w", l["s"])]
    if len(raises) >= RAISES:
        signals.append({"view": "decisions", "signal": f"{len(raises)} new raise sites", "evidence": raises[:12]})
    return signals


def from_contracts(contracts: list[dict]) -> list[dict]:
    """Signals from the interface delta: changed event payloads suggest a sequence view."""
    events = sorted({f"{e['file']}" for e in contracts if e["surface"] == "events"})
    return [{"view": "sequence", "signal": f"event payloads change in {len(events)} file(s)", "evidence": events}] if events else []


def review(signals: list[dict], doc: dict) -> dict:
    """Signals the doc did not draw: `unaddressed` (no decision) and `declined` (decision with its reason, for a human)."""
    used = {s.get("view") for s in doc.get("sections", [])} | {d.get("type") for d in doc.get("diagrams", [])}
    decisions = {d.get("view") or d.get("kind"): d for d in doc.get("view_decisions", []) or doc.get("diagram_decisions", [])}
    out = {"unaddressed": [], "declined": []}
    for s in signals:
        if s["view"] in used:
            continue
        d = decisions.get(s["view"])
        if d is None:
            out["unaddressed"].append(f"{s['view']}: {s['signal']}")
        elif d.get("added"):
            out["unaddressed"].append(f"{s['view']}: {s['signal']} — view_decisions says added, but the doc has no such section")
        else:
            out["declined"].append(f"{s['view']}: {s['signal']} — declined: {d.get('why', 'no reason given')}")
    return out
