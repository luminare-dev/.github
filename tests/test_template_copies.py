"""The files copied from luminare-dev/oss-template must stay byte-for-byte copies (one source of truth).

Run: python -m unittest discover -s tests -v

To update them: copy the files again from the template, then set SOURCE_COMMIT and the hashes
below. When a checkout of the template sits next to this repository (../oss-template), the copies
are also compared with the files of SOURCE_COMMIT there.
"""

from __future__ import annotations

import hashlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT.parent / "oss-template"
SOURCE_COMMIT = "d917a85a876c5f5e83b5001002ed777056655c52"  # luminare-dev/oss-template#2, 2026-10-21
COPIES = {
    "scripts/forbidden_words.py": "dd4773373f182e457c0200036e0a010f6df880f506e6b5087f7935255300834e",
    "scripts/set_byline.py": "7655a30b5d00ccdb88fa468e97055ffac8dcf74fa4c6c3f0695eb0af8787f0e1",
    "scripts/check_workflows.py": "3c0a075411d2f0e0143ab130be638d3de7ba3dedc2ce64af19d7f3afb664b247",
    "scripts/check_pr_title.py": "a20da7141a68c291c1c023fab0cd1fb077b718132beae5d69db187bd7322a71d",
    ".github/workflows/pr-title.yml": "2e6c2aa6b2eef94c5c2a22a30482d9650aab86ff9de88a6a18ba4c7ebf61db6b",
    ".github/workflows/reusable-ci.yml": "c9c99667f9389f4c64f8716ea36623a72db682e996d6d1c2f7b6f6f3f3a65af9",
    ".github/workflows/reusable-gitleaks.yml": "696a42a07731eaa36bd2237e7f7853cb1c664306b51a7d84e156d3d0f069abf6",
    ".gitleaks.toml": "0e9a0915d0bc2636c6b59f8d0c8631fb64def2d9224f7c99b9e4709dc7d62d72",
}


def _template_file(rel: str) -> bytes | None:
    try:
        out = subprocess.run(["git", "-C", str(TEMPLATE), "show", f"{SOURCE_COMMIT}:{rel}"],
                             capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout


class TestTemplateCopies(unittest.TestCase):
    def test_copies_match_the_pinned_hashes(self):
        for rel, want in COPIES.items():
            got = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(got, want, f"{rel} differs from the template copy; copy it again instead of editing it")

    @unittest.skipUnless((TEMPLATE / ".git").exists(), "no ../oss-template checkout next to this repository")
    def test_copies_match_the_source_commit(self):
        if _template_file("README.md") is None:
            self.skipTest(f"../oss-template does not contain commit {SOURCE_COMMIT[:12]}")
        for rel in COPIES:
            self.assertEqual((ROOT / rel).read_bytes(), _template_file(rel), rel)

    @unittest.skipUnless((TEMPLATE / ".git").exists(), "no ../oss-template checkout next to this repository")
    def test_ci_caller_differs_from_the_template_only_in_the_test_command(self):
        template_ci = _template_file(".github/workflows/ci.yml")
        if template_ci is None:
            self.skipTest(f"../oss-template does not contain commit {SOURCE_COMMIT[:12]}")
        ours = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8").splitlines()
        extra = [i for i, line in enumerate(ours) if line.startswith("# From luminare-dev/oss-template")]
        start = ours.index("    with:")
        extra += range(start, start + 3)  # "with:", its comment and "test-command:"
        stripped = [line for i, line in enumerate(ours) if i not in extra]
        self.assertEqual(stripped, template_ci.decode("utf-8").splitlines())

    def test_ci_caller_keeps_the_job_ids_of_the_required_checks(self):
        # rulesets/main.json requires "ci / lint-test", "secrets / gitleaks" and "pr / pr-title".
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        pr = (ROOT / ".github/workflows/pr-title.yml").read_text(encoding="utf-8")
        self.assertRegex(ci, r"(?m)^  ci:\n    uses: \./\.github/workflows/reusable-ci\.yml$")
        self.assertRegex(ci, r"(?m)^  secrets:\n    uses: \./\.github/workflows/reusable-gitleaks\.yml$")
        self.assertRegex(pr, r"(?m)^  pr:\n    uses: \./\.github/workflows/reusable-ci\.yml$")


if __name__ == "__main__":
    unittest.main()
