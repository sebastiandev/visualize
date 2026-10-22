"""Contract delta: deterministic interface changes between merge-base and head.

Parses base and head versions of interface-surface files with `ast` and diffs the public surface: GraphQL
(graphene/strawberry classes: fields, arguments, enum values), shared event payloads, a generated client SDK,
feature flags and DB migrations. Verdicts: additive, breaking, or "review".
"""

import ast
import re

from visualize.workspace import fetch as _fetch

SCHEMA_BASES = re.compile(r"ObjectType|InputObjectType|Mutation|Enum|Interface|Union|Connection|Graphity\w*|Input\b|Type\b")
GRAPHENE_CALL = re.compile(r"^(graphene\.)?(Field|List|NonNull|String|Int|Float|Boolean|ID|Date|DateTime|Decimal|JSONString|Argument|Enum\w*|ConnectionField|\w+Connection|\w+Field|\w+Type|\w+Input)$")


def call_name(node: ast.AST) -> str:
    """Dotted name of a call's function, e.g. `graphene.Field`."""
    func = node.func if isinstance(node, ast.Call) else node
    return ast.unparse(func)


def class_surface(source: str) -> dict[str, str]:
    """Public surface of every class: `Class.attr` → normalised declaration source.

    Covers graphene fields (`x = graphene.String(...)`), nested `Arguments` classes, enum values (`A = "a"`),
    dataclass / pydantic fields (`x: int = ...`), and public method signatures.
    """
    surface: dict[str, str] = {}
    def visit(cls: ast.ClassDef, prefix: str) -> None:
        bases = ",".join(ast.unparse(b) for b in cls.bases)
        surface[f"{prefix}{cls.name}"] = f"class({bases})"
        for item in cls.body:
            if isinstance(item, ast.ClassDef):
                visit(item, f"{prefix}{cls.name}.")
            elif isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                name, value = item.targets[0].id, item.value
                if name.startswith("_"):
                    continue
                if isinstance(value, ast.Call) and GRAPHENE_CALL.match(call_name(value).split(".")[-1]) or isinstance(value, ast.Constant):
                    surface[f"{prefix}{cls.name}.{name}"] = ast.unparse(value)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and not item.target.id.startswith("_"):
                surface[f"{prefix}{cls.name}.{item.target.id}"] = ast.unparse(item.annotation) + (f" = {ast.unparse(item.value)}" if item.value else "")
            elif isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and not item.name.startswith("_") and not item.name.startswith("resolve_"):
                surface[f"{prefix}{cls.name}.{item.name}()"] = ast.unparse(item.args)
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            visit(node, "")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            surface[f"{node.name}()"] = ast.unparse(node.args)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id.isupper():
            surface[node.targets[0].id] = ast.unparse(node.value)
    return surface


def migration_ops(source: str) -> list[str]:
    """`op.<operation>(table, ...)` calls in `upgrade()`."""
    tree = ast.parse(source)
    upgrade = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "upgrade"), None)
    ops = []
    for node in ast.walk(upgrade) if upgrade else []:
        if isinstance(node, ast.Call) and call_name(node).startswith("op."):
            first = ast.unparse(node.args[0]) if node.args else ""
            ops.append(f"{call_name(node)[3:]}({first})")
    return ops


def call_parts(source: str) -> tuple[str, list[str], dict[str, str]] | None:
    """Split a declaration like `Field(T, a=String(required=True))` into (func, positional, keywords)."""
    try:
        node = ast.parse(source, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(node, ast.Call):
        return None
    return (call_name(node), [ast.unparse(a) for a in node.args],
            {k.arg: ast.unparse(k.value) for k in node.keywords if k.arg and k.arg != "description"})


def union_members(source: str) -> set[str] | None:
    """Members of a `A | B | C` annotation, else None."""
    parts = [p.strip() for p in source.split("=")[0].split("|")]
    return set(parts) if len(parts) > 1 else None


def classify_change(change: str, name: str, before: str | None, after: str | None) -> tuple[bool, str]:
    """Return (breaking, explanation) for one surface entry, at argument / union-member level."""
    if change == "removed":
        return True, "removed"
    if change == "added":
        required = bool(after) and ".Arguments." in name and "required=True" in after
        return required, "added (required argument)" if required else "added"
    # Annotated fields (`x: T` / `x: T = Field(...)`): same type and only description/default-docs changed → not breaking.
    split = lambda s: (s.split(" = ", 1) + [""])[:2] if s else ["", ""]
    (bt, bv), (at, av) = split(before), split(after)
    if bt and bt == at and ":" not in bt.split("(")[0] and (bv or av):
        bk, ak = (call_parts(bv)[2] if bv and call_parts(bv) else {}), (call_parts(av)[2] if av and call_parts(av) else {})
        if bk == ak and (not bv or call_parts(bv)) and (not av or call_parts(av)):
            return False, "description only"
        if (bk.get("default") or bk.get("default_factory")) and not (ak.get("default") or ak.get("default_factory")):
            return True, "default removed"
        return False, "field options changed"
    b, a = call_parts(before or ""), call_parts(after or "")
    if b and a and b[0] == a[0] and b[1] == a[1]:
        added = {k: v for k, v in a[2].items() if k not in b[2]}
        removed = [k for k in b[2] if k not in a[2]]
        retyped = [k for k in b[2] if k in a[2] and b[2][k] != a[2][k]]
        added_required = [k for k, v in added.items() if "required=True" in v]
        notes = [f"+arg {k}" for k in added] + [f"-arg {k}" for k in removed] + [f"~arg {k}" for k in retyped]
        return bool(removed or retyped or added_required), ", ".join(notes) or "description only"
    bu, au = union_members(before or ""), union_members(after or "")
    if bu and au:
        return bool(bu - au), ", ".join([f"+{m}" for m in sorted(au - bu)] + [f"-{m}" for m in sorted(bu - au)])
    return True, "declaration changed"


def is_schema(kind: str, name: str, surface: dict[str, str]) -> bool:
    """GraphQL entries count only when their top-level class is a graphene schema type."""
    if kind != "graphql":
        return True
    top = name.split(".")[0]
    if SCHEMA_BASES.search(surface.get(top, "")):
        return True
    # Query/mutation mixins are plain classes: they count when they declare graphene fields.
    for key, value in surface.items():
        if key.startswith(top + ".") and not key.endswith("()"):
            parts = call_parts(value)
            if parts and GRAPHENE_CALL.match(parts[0].split(".")[-1]):
                return True
    return False


def delta(repo: str, files: list[str], base: str, head: str, cfg) -> list[dict]:
    """Contract delta entries for every interface-surface file the PR touches."""
    entries = []
    fetch = lambda path, ref: _fetch(repo, path, ref)
    for path in files:
        if cfg.is_test(path):
            continue
        kind = cfg.interface(path)
        if kind is None:
            continue
        before_src, after_src = fetch(path, base), fetch(path, head)
        if kind == "db":
            for op in migration_ops(after_src or ""):
                # drop_* is breaking; alter_column may only widen a type/enum → needs review, not a verdict.
                verdict = True if op.startswith("drop_") else ("review" if op.startswith("alter_column") else False)
                entries.append({"surface": "db", "file": path, "name": op, "change": "added", "breaking": verdict, "note": "needs review" if verdict == "review" else "", "before": None, "after": op})
            continue
        try:
            before = class_surface(before_src) if before_src else {}
            after = class_surface(after_src) if after_src else {}
        except SyntaxError as error:
            entries.append({"surface": kind, "file": path, "name": "<unparsable>", "change": "unknown", "breaking": False, "before": None, "after": str(error)})
            continue
        for name in sorted(before.keys() | after.keys()):
            b, a = before.get(name), after.get(name)
            if b == a or not is_schema(kind, name, after if a is not None else before):
                continue
            change = "added" if b is None else "removed" if a is None else "changed"
            is_breaking, note = (False, change) if kind == "feature_flags" else classify_change(change, name, b, a)
            entries.append({"surface": kind, "file": path, "name": name, "change": change,
                            "breaking": is_breaking, "note": note, "before": b, "after": a})
    return entries
