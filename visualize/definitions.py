"""Definition diff (functions, methods, module constants) and node signatures, from base and head sources."""

import ast
import json

from visualize.workspace import fetch



def _params(args: ast.arguments) -> list[str]:
    """Parameters as `name: annotation` strings; `self`/`cls` dropped; keyword-only marker kept."""
    out = []
    for a in args.posonlyargs + args.args:
        if a.arg not in {"self", "cls"}:
            out.append(a.arg + (f": {ast.unparse(a.annotation)}" if a.annotation else ""))
    if args.vararg:
        out.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        out.append("*")
    out += [a.arg + (f": {ast.unparse(a.annotation)}" if a.annotation else "") for a in args.kwonlyargs]
    if args.kwarg:
        out.append("**" + args.kwarg.arg)
    return out


def definitions(source: str) -> dict[str, dict]:
    """`Class.method` / `function` / CONSTANT → {kind, params, returns, line, end}."""
    found: dict[str, dict] = {}

    def walk(nodes, prefix=""):
        for n in nodes:
            if isinstance(n, ast.ClassDef):
                walk(n.body, f"{prefix}{n.name}.")
            elif isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef):
                start = min([n.lineno] + [d.lineno for d in n.decorator_list])
                found[prefix + n.name] = {"kind": "def", "params": _params(n.args),
                                          "returns": ast.unparse(n.returns) if n.returns else None, "line": start, "end": n.end_lineno}
            elif isinstance(n, ast.Assign) and not prefix and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper():
                found[n.targets[0].id] = {"kind": "const", "value": ast.unparse(n.value), "line": n.lineno, "end": n.end_lineno}

    walk(ast.parse(source).body)
    return found


def _same(a: dict, b: dict) -> bool:
    """Equal ignoring line positions."""
    drop = {"line", "end"}
    return {k: v for k, v in a.items() if k not in drop} == {k: v for k, v in b.items() if k not in drop}


def defdiff(repo: str, paths: list[str], base: str, head: str) -> list[dict]:
    """Added / removed / changed definitions per Python file (tests excluded by the caller)."""
    out = []
    for path in paths:
        b_src, h_src = fetch(repo, path, base), fetch(repo, path, head)
        try:
            b, h = (definitions(b_src) if b_src else {}), (definitions(h_src) if h_src else {})
        except SyntaxError:
            continue
        for name in sorted(b.keys() | h.keys(), key=lambda n: (h.get(n) or b.get(n))["line"]):
            before, after = b.get(name), h.get(name)
            if before and after and _same(before, after):
                continue
            change = "added" if not before else "removed" if not after else "changed"
            out.append({"file": path, "name": name, "change": change, "before": before, "after": after,
                        "ref": f"{path}:{after['line']}" if after else None})
    return out


def _gql_type(ref: dict) -> str:
    """GraphQL type reference → SDL string."""
    if ref["kind"] == "NON_NULL":
        return _gql_type(ref["ofType"]) + "!"
    if ref["kind"] == "LIST":
        return f"[{_gql_type(ref['ofType'])}]"
    return ref["name"]


def _camel(name: str) -> str:
    """snake_case → camelCase."""
    head, *rest = name.split("_")
    return head + "".join(p.title() for p in rest)


def _graphql_line(schema: dict, operation: str) -> str | None:
    """`mutation name(args): Type` for a root field named like the resolver, else None."""
    types = {t["name"]: t for t in schema["types"]}
    for root, keyword in ((schema.get("mutationType") or {}, "mutation"), (schema.get("queryType") or {}, "query")):
        for f in types.get(root.get("name"), {}).get("fields") or []:
            if f["name"] in {operation, _camel(operation)}:
                return f"{keyword} {f['name']}({', '.join(a['name'] + ': ' + _gql_type(a['type']) for a in f['args'])}): {_gql_type(f['type'])}"
    return None


def signatures(repo: str, entries: list[dict], head: str, changed_paths: set[str], introspection: str = "") -> dict[str, dict]:
    """Per definition: the expanded Python signature, or the GraphQL operation line when it is a root resolver."""
    schema = None
    if introspection and introspection in changed_paths and (raw := fetch(repo, introspection, head)):
        data = json.loads(raw)
        schema = data.get("__schema") or data.get("data", {}).get("__schema")
    out = {}
    for e in entries:
        d = e.get("after")
        if not d or d["kind"] != "def":
            continue
        short = e["name"].split(".")[-1]
        sdl = _graphql_line(schema, short) if schema else None
        sig = f"def {short}(\n" + "".join(f"    {p},\n" for p in d["params"]) + ")" + (f" -> {d['returns']}" if d.get("returns") else "")
        out[e["name"]] = {"kind": "graphql" if sdl else "call", "sdl": sdl, "signature": sig}
    return out
