"""Embedded generation only discovers trusted executable views."""
import unittest
import tempfile
import subprocess
import os
from pathlib import Path
from visualize import views


class EmbeddedViewsTest(unittest.TestCase):
    """PR-controlled plugins must not be executable in trusted-only mode."""

    def tearDown(self):
        views.TRUSTED_ONLY = False

    def test_trusted_mode_excludes_repository_views(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(["git", "init", "--quiet", folder], check=True)
            previous = os.getcwd()
            try:
                os.chdir(folder)
                views.TRUSTED_ONLY = True
                self.assertNotIn(Path(folder) / ".visualize/views", views.search_dirs())
                self.assertIn(views.TOOL / "views", views.search_dirs())
            finally:
                os.chdir(previous)

    def test_standalone_mode_retains_repository_views(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(["git", "init", "--quiet", folder], check=True)
            previous = os.getcwd()
            try:
                os.chdir(folder)
                self.assertIn(Path(folder).resolve() / ".visualize/views", views.search_dirs())
            finally:
                os.chdir(previous)
