"""Offline structure checks for the community health files (Python standard library only).

Run: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("forbidden_words", ROOT / "scripts" / "forbidden_words.py")
forbidden_words = importlib.util.module_from_spec(_spec)
sys.modules["forbidden_words"] = forbidden_words
_spec.loader.exec_module(forbidden_words)

SECRETS_BOX = "I removed all secrets, tokens, licence keys, IPs and player data."


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestLayout(unittest.TestCase):
    def test_files_sit_where_github_reads_them(self):
        # docs.github.com "Creating a default community health file" (checked 2026-10-06):
        # issue templates and config in .github/ISSUE_TEMPLATE; VULNERABILITY_REPORT.yml and
        # FUNDING.yml only in .github/; the others in the root, .github/ or docs/.  (rule-text)
        # The organization profile is profile/README.md in the public .github repository.
        for rel in ("CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md",
                    ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml",
                    ".github/ISSUE_TEMPLATE/config.yml", ".github/PULL_REQUEST_TEMPLATE.md",
                    ".github/VULNERABILITY_REPORT.yml", "profile/README.md", "LICENSE", "NOTICE",
                    "PLACEHOLDERS.md", "SETTINGS.md", "labels.yml", "rulesets/main.json",
                    "docs/brand/readme-header-dark.svg", "docs/brand/readme-header-light.svg",
                    "docs/brand/social-preview-1280x640.png", "docs/brand/KIT_VERSION"):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_funding_file_anywhere(self):  # rule-text
        hits = [p for p in ROOT.rglob("*") if ".git" not in p.parts and re.fullmatch(r"(?i)funding\.ya?ml", p.name)]  # rule-text
        self.assertEqual(hits, [])

    def test_one_copy_of_each_health_file(self):
        # A second copy in .github/ or docs/ would silently win or lose by precedence.
        for name in ("CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "PULL_REQUEST_TEMPLATE.md"):
            copies = [p for p in (ROOT / name, ROOT / ".github" / name, ROOT / "docs" / name) if p.exists()]
            self.assertEqual(len(copies), 1, f"{name}: {copies}")


class TestCodeOfConduct(unittest.TestCase):
    def test_contributor_covenant_3_with_contact_and_attribution(self):
        text = read("CODE_OF_CONDUCT.md")
        self.assertIn("# Contributor Covenant 3.0 Code of Conduct", text)
        for heading in ("## Our Pledge", "## Encouraged Behaviors", "## Restricted Behaviors", "### Other Restrictions",
                        "## Reporting an Issue", "## Addressing and Repairing Harm", "## Scope", "## Attribution"):
            self.assertIn(heading, text)
        self.assertIn("conduct@luminare.tech", text)
        self.assertNotIn("[NOTE", text)
        self.assertIn("licensed under CC BY-SA 4.0", text)
        self.assertIn("https://www.contributor-covenant.org/version/3/0/", text)


class TestIssueForms(unittest.TestCase):
    def test_every_issue_form_has_the_required_secrets_checkbox(self):
        for form in sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
            if form.stem == "config":
                continue
            text = form.read_text(encoding="utf-8")
            m = re.search(r"- label: " + re.escape(SECRETS_BOX) + r"\n\s+required: (\w+)", text)
            self.assertIsNotNone(m, form.name)
            self.assertEqual(m.group(1), "true", form.name)

    def test_blank_issues_off_and_contact_links(self):
        text = read(".github/ISSUE_TEMPLATE/config.yml")
        self.assertRegex(text, r"(?m)^blank_issues_enabled: false$")
        self.assertIn("https://github.com/orgs/luminare-dev/discussions", text)
        self.assertIn("SECURITY.md", text)

    def test_pr_template_asks_for_dco_tests_and_no_secrets(self):
        text = read(".github/PULL_REQUEST_TEMPLATE.md")
        for needle in ("git commit -s", "Conventional Commits", "test", "No secrets"):
            self.assertIn(needle, text)


class TestRuleset(unittest.TestCase):
    def test_main_ruleset(self):
        data = json.loads(read("rulesets/main.json"))
        self.assertEqual(data["target"], "branch")
        self.assertEqual(data["enforcement"], "active")
        self.assertEqual(data["conditions"]["ref_name"]["include"], ["~DEFAULT_BRANCH"])
        self.assertNotIn("repository_name", data["conditions"])  # org-level only
        self.assertEqual(data["bypass_actors"], [])
        types = [r["type"] for r in data["rules"]]
        for t in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
            self.assertIn(t, types)
        pr = next(r for r in data["rules"] if r["type"] == "pull_request")["parameters"]
        self.assertEqual(pr["allowed_merge_methods"], ["squash"])
        checks = next(r for r in data["rules"] if r["type"] == "required_status_checks")["parameters"]
        # Reusable workflows report as "<caller job> / <called job>": the caller jobs ci, secrets
        # and pr in the template's ci.yml and pr-title.yml. 15368 = GitHub Actions, 1861 = DCO app.
        self.assertEqual({(c["context"], c["integration_id"]) for c in checks["required_status_checks"]},
                         {("ci / lint-test", 15368), ("secrets / gitleaks", 15368), ("pr / pr-title", 15368),
                          ("DCO", 1861)})


class TestPublicText(unittest.TestCase):
    """scripts/forbidden_words.py, the organization's wording check (copied from the template)."""

    def run_check(self, root: Path, **kw):
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "luminare-dev/.github"}):
            return forbidden_words.run(root, **kw)

    def test_repository_passes_in_template_mode(self):
        report = self.run_check(ROOT, template_mode=True)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])  # also: no stale .forbidden-words-allow entry

    def test_publish_gate_finds_only_the_listed_placeholders(self):
        # Before the push the only findings are the open placeholders; once they are filled in,
        # the publish gate (the CI step outside template mode) is clean.
        listed = set(forbidden_words.PLACEHOLDER_RE.findall(read("PLACEHOLDERS.md")))
        self.assertTrue(listed)
        for error in self.run_check(ROOT, template_mode=False).errors:
            m = re.search(r"unfilled placeholder \{\{(\w+)\}\}", error)
            self.assertIsNotNone(m, error)
            self.assertIn(m.group(1), listed, error)

    def test_checker_catches_problems(self):
        # Built from pieces so that this test file itself passes the repository-wide check.
        bad_mail = "jane.doe" + "@" + "gmail.example.com"
        bad_placeholder = "{" + "{UNLISTED}" + "}"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github").mkdir()
            (root / ".github" / "FUNDING.yml").write_text("github: [x]\n", encoding="utf-8")  # rule-text
            (root / "README.md").write_text(
                "Pro version coming soon, see our web shop.\n"  # rule-text
                f"Contact {bad_mail}\n"
                f"Hello {bad_placeholder}\n"
                "Not affiliated with or endorsed by anyone. Keep the token in a key-value store.\n",
                encoding="utf-8")
            joined = "\n".join(self.run_check(root, template_mode=True).errors)
            for rule in ("[pro-version]", "[coming-soon]", "[shop-store]", "funding file"):  # rule-text
                self.assertIn(rule, joined)
            self.assertIn(bad_mail, joined)
            self.assertIn("UNLISTED", joined)
            self.assertNotIn("affiliated", joined)
            self.assertNotIn("key-value store", joined)


class TestProfile(unittest.TestCase):
    def test_profile_rules(self):
        text = read("profile/README.md")
        self.assertIn("<picture>", text)
        self.assertIn("raw.githubusercontent.com/luminare-dev/.github/main/docs/brand/readme-header-dark.svg", text)
        self.assertIn("https://luminare.tech", text)
        self.assertIn("oss@luminare.tech", text)
        self.assertIn("Not affiliated with or endorsed by Cfx.re, Rockstar Games or Take-Two.", text)
        # planned projects carry no dates
        self.assertNotRegex(text, r"\b(20\d\d|Q[1-4]|January|February|March|April|May|June|July|August|"
                                  r"September|October|November|December)\b")
        # no platform trademark as a project name (first column of the table)
        names = re.findall(r"(?m)^\| (?:\[)?([^|\]]+?)(?:\]\([^)]*\))? \|", text)
        self.assertGreaterEqual(len(names), 6)
        banned = re.compile(r"(?i)fivem|cfx|citizenfx|redm|txadmin|gta|rockstar|\bfx|proxmox|windows|microsoft|"
                            r"prometheus|grafana")
        for name in names:
            self.assertIsNone(banned.search(name), name)

    def test_brand_files_are_the_studio_variant(self):
        self.assertIn("variant: studio", read("docs/brand/KIT_VERSION"))


if __name__ == "__main__":
    unittest.main()
