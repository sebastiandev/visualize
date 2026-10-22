"""Design system: the template's CSS custom properties are the default tokens; config overrides them.

Override in ~/.config/visualize/config.toml or <repo>/.visualize.toml:

    [design.light]
    clay = "#2F6FEB"        # accent
    paper = "#FFFFFF"
    [design.dark]
    clay = "#58A6FF"

Keys are token names without the leading `--` (see `visualize design`). Unknown keys are reported, not applied.
"""

import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
_BLOCKS = {"light": r":root\{([^}]*)\}", "dark": r"\[data-theme=dark\]\{([^}]*)\}"}


def defaults() -> dict[str, dict[str, str]]:
    """{"light": {token: value}, "dark": {token: value}} parsed from the template's first :root / dark blocks."""
    css = TEMPLATE.read_text()
    out = {}
    for theme, pattern in _BLOCKS.items():
        block = re.search(pattern, css).group(1)
        out[theme] = dict(re.findall(r"--([\w-]+):\s*([^;]+);?", block))
    return out


def overrides_css(design: dict) -> tuple[str, list[str]]:
    """CSS that applies configured token overrides, and the list of unknown token names."""
    base, rules, unknown = defaults(), [], []
    for theme, selector in (("light", ":root"), ("dark", "[data-theme=dark]")):
        values = design.get(theme, {}) or {}
        bad = [k for k in values if k not in base[theme]]
        unknown += [f"{theme}.{k}" for k in bad]
        decls = ";".join(f"--{k}:{v}" for k, v in values.items() if k not in bad)
        if decls:
            rules.append(f"{selector}{{{decls}}}")
    return "\n".join(rules), unknown
