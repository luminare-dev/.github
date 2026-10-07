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
SOURCE_COMMIT = "5560ba9bd19967bbaddd1322dcaf0289e996ad93"  # luminare-dev/oss-template, 2026-10-06
COPIES = {
    "scripts/forbidden_words.py": "353c9b562e0d734e744f60843ed960f167f8334dd659dd63d18145373eecd512",
    "scripts/set_byline.py": "c18bbe6dd8b60428950118f524452969239dde155cc7a12ef3575cc0ed7e2381",
    "scripts/check_workflows.py": "3c0a075411d2f0e0143ab130be638d3de7ba3dedc2ce64af19d7f3afb664b247",
    "scripts/check_pr_title.py": "221eb575efadf16fd93556b93768786125961fe08fab0d35e47cf60919abd157",
    ".github/workflows/pr-title.yml": "2e6c2aa6b2eef94c5c2a22a30482d9650aab86ff9de88a6a18ba4c7ebf61db6b",
    ".github/workflows/reusable-ci.yml": "377426a9f5b64960698693b2a04d6b9846c9fab37689d497e2b2346df15e134d",
    ".github/workflows/reusable-gitleaks.yml": "696a42a07731eaa36bd2237e7f7853cb1c664306b51a7d84e156d3d0f069abf6",
    ".gitleaks.toml": "bfe39b8eb8b9f3255b1d5d69d88bf756b65d2284ebdc00921a096240810a5883",
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

    def test_ci_caller_keeps_the_job_ids_of_the_required_checks(self):
        # rulesets/main.json requires "ci / lint-test", "secrets / gitleaks" and "pr / pr-title".
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        pr = (ROOT / ".github/workflows/pr-title.yml").read_text(encoding="utf-8")
        self.assertRegex(ci, r"(?m)^  ci:\n    uses: \./\.github/workflows/reusable-ci\.yml$")
        self.assertRegex(ci, r"(?m)^  secrets:\n    uses: \./\.github/workflows/reusable-gitleaks\.yml$")
        self.assertRegex(pr, r"(?m)^  pr:\n    uses: \./\.github/workflows/reusable-ci\.yml$")


if __name__ == "__main__":
    unittest.main()
