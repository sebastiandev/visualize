"""An explicit repository must not bypass revision-pinned facts loading."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


class ExplicitRepoTest(unittest.TestCase):
    """Exercise the real CLI, renderer and browser checker together."""

    def test_explain_merges_facts_with_explicit_repo(self):
        """Citations retain their facts revision even when --repo is supplied."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            facts = root / "facts"
            facts.mkdir()
            head = "a" * 40
            (facts / "facts.json").write_text(json.dumps({
                "repo": "acme/widgets", "kind": "code", "base": head,
                "head_sha": head, "url": "", "label": "Pinned source",
            }))
            (facts / "code.json").write_text(json.dumps({
                "definitions": [], "sources": {"src/a.py": ["value = 1"]},
            }))
            doc = root / "doc.json"
            doc.write_text(json.dumps({"title": "Pinned source", "sections": [
                {"view": "tldr", "text": "A pinned value.", "ref": "src/a.py:1"},
            ]}))
            output = root / "page.html"
            result = subprocess.run([
                "visualize", "--trusted-views-only", "explain", str(doc),
                "--facts", str(facts), "--repo", "acme/widgets", "-o", str(output),
            ], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            embedded = re.search(r'<script id="page" type="application/json">(.*?)</script>', output.read_text(), re.S)
            self.assertIsNotNone(embedded)
            page = json.loads(embedded.group(1))
            self.assertEqual(page["head_sha"], head)
            self.assertEqual(page["sources"]["src/a.py"], ["value = 1"])
