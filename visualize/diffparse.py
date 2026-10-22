"""Parse a unified diff into files → hunks → lines with old/new line numbers."""

import re

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def parse(text: str) -> dict[str, list[dict]]:
    """Return {path: [{header, old_start, new_start, new_len, lines: [{t: ' '|'+'|'-', o, n, s}]}]}."""
    files: dict[str, list[dict]] = {}
    path, hunk, old, new = None, None, 0, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            path, hunk = line.split(" b/", 1)[1], None
            files.setdefault(path, [])
        elif line.startswith(("--- ", "+++ ", "index ", "new file", "deleted file", "similarity", "rename ", "old mode", "new mode")):
            continue
        elif (m := HUNK.match(line)) and path:
            old, new = int(m.group(1)), int(m.group(3))
            hunk = {"header": line, "old_start": old, "new_start": new, "new_len": int(m.group(4) or 1), "lines": []}
            files[path].append(hunk)
        elif hunk is not None and line[:1] in {" ", "+", "-"}:
            t = line[0]
            hunk["lines"].append({"t": t, "o": old if t != "+" else None, "n": new if t != "-" else None, "s": line[1:]})
            old += t != "+"
            new += t != "-"
    return files
