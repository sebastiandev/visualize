"""Optional kind hints from Jev (TypeSafe): a scored shortlist of diagram kinds; the agent still decides.

Enabled when `[jev] enabled` is true, or "auto" (default) and a key is available: env TYPESAFE_API_KEY, else the
macOS keychain item `typesafe-api-key`. Without a key nothing happens and the tool works as before.
One request per run: each kind's `## Use when` section becomes one yes/no (noul) question. Only a summary is sent
(title, description ≤ 2,000 chars, file paths, layers, counts) — never file contents.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

from visualize.kinds import discover

URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-1.13.0"
SUGGEST, MAYBE = 0.65, 0.35
SECRET_PATH = re.compile(r"\.env|secret|\.pem$|\.key$", re.I)


def api_key() -> str | None:
    """Key from TYPESAFE_API_KEY, else the macOS keychain; None when neither exists."""
    if key := os.environ.get("TYPESAFE_API_KEY"):
        return key
    try:
        result = subprocess.run(["security", "find-generic-password", "-s", "typesafe-api-key", "-w"],
                                capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def settings(cfg) -> tuple[bool, str]:
    """(enabled, model) from `[jev]`; "auto" means enabled when a key is found."""
    section = cfg.data.get("jev", {})
    return section.get("enabled", "auto") is not False, section.get("model", DEFAULT_MODEL)


def use_when(guideline: str) -> str:
    """The `## Use when` section of a guideline, or its description line."""
    match = re.search(r"^## Use when\s*\n(.*?)(?=^## |\Z)", guideline, re.S | re.M)
    if match:
        return match.group(1).strip()
    return next((l.strip() for l in guideline.splitlines() if l.strip() and not l.startswith("#")), "")


def questions(mode: str) -> dict:
    """One noul question per kind that has a guideline."""
    out = {}
    for name, kind in discover().items():
        rule = use_when(kind.read("guideline.md"))
        if rule:
            out[name] = {"type": "noul", "instructions":
                         f"Would a '{name}' diagram help a reader understand this {mode}? It fits when:\n{rule}"}
    return out


def band(p: float) -> str:
    return "suggest" if p >= SUGGEST else "maybe" if p > MAYBE else "skip"


def hints(state: dict, cfg, mode: str) -> dict | None:
    """Scored kinds for `state`, or None when Jev is disabled, has no key, or fails (reported on stderr)."""
    enabled, model = settings(cfg)
    key = api_key() if enabled else None
    if not key:
        return None
    qs = questions(mode)
    if not qs:
        return None
    state = dict(state, file_paths=[p for p in state.get("file_paths", []) if not SECRET_PATH.search(p)][:40])
    body = json.dumps({"model": model, "state": state, "questions": qs}).encode()
    request = urllib.request.Request(URL, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            answers = json.loads(response.read())["answers"]
    except Exception as error:  # hints are optional: never fail the run
        print(f"visualize: jev hints skipped ({type(error).__name__}: {str(error)[:120]})", file=sys.stderr)
        return None
    kinds = sorted(({"kind": k, "p": round(a["noul"], 2), "band": band(a["noul"])} for k, a in answers.items()),
                   key=lambda h: -h["p"])
    return {"model": model, "kinds": kinds,
            "note": "Shortlist only. You decide; when you skip a 'suggest' or add a 'skip', give the reason in diagram_decisions."}


def summary(h: dict | None) -> str | None:
    """`decisions 0.91 suggest · sequence 0.34 skip` for CLI output."""
    return " · ".join(f"{k['kind']} {k['p']:.2f} {k['band']}" for k in h["kinds"]) if h else None
