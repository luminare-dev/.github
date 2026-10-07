"""Negative tests for scripts/validate.py: broken files must fail the schema checks.

Needs the development tools (requirements-dev.txt) and the cached schemas in .cache/schemas/
(created by one run of scripts/validate.py). Skipped otherwise. No network.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "schemas"

try:
    import jsonschema  # noqa: F401
    import yaml
    HAVE_TOOLS = True
except ImportError:
    HAVE_TOOLS = False

HAVE_SCHEMAS = all((CACHE / n).exists() for n in
                   ("github-issue-forms.json", "github-issue-config.json", "github-discussion.json",
                    "repo-ruleset-request.json"))


@unittest.skipUnless(HAVE_TOOLS and HAVE_SCHEMAS, "needs requirements-dev.txt and one run of scripts/validate.py")
class TestValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("validate", ROOT / "scripts" / "validate.py")
        cls.v = importlib.util.module_from_spec(spec)
        sys.modules["validate"] = cls.v
        spec.loader.exec_module(cls.v)
        cls.schemas = cls.v.ensure_schemas(refresh=False, offline=True)
        cls.forms = jsonschema.Draft7Validator(cls.schemas["github-issue-forms.json"])
        cls.config = jsonschema.Draft7Validator(cls.schemas["github-issue-config.json"])
        cls.discussion = jsonschema.Draft7Validator(cls.schemas["github-discussion.json"])
        cls.ruleset = jsonschema.Draft4Validator(cls.schemas["repo-ruleset-request.json"])

    def load_yaml(self, rel):
        return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))

    def test_real_files_are_valid(self):
        self.assertEqual(list(self.forms.iter_errors(self.load_yaml(".github/ISSUE_TEMPLATE/bug_report.yml"))), [])
        self.assertEqual(list(self.config.iter_errors(self.load_yaml(".github/ISSUE_TEMPLATE/config.yml"))), [])
        for rel in (".github/DISCUSSION_TEMPLATE/q-a.yml", ".github/DISCUSSION_TEMPLATE/ideas.yml"):
            form = self.load_yaml(rel)
            self.assertEqual(list(self.discussion.iter_errors(form)), [], rel)
            self.assertEqual(self.v.form_rules(form, needs_secrets_checkbox=True), [], rel)
        main = json.loads((ROOT / "rulesets/main.json").read_text(encoding="utf-8"))
        self.assertEqual(list(self.ruleset.iter_errors(main)), [])

    def test_broken_form_fails(self):
        form = self.load_yaml(".github/ISSUE_TEMPLATE/bug_report.yml")
        no_desc = copy.deepcopy(form)
        del no_desc["description"]
        self.assertTrue(list(self.forms.iter_errors(no_desc)))
        bad_type = copy.deepcopy(form)
        bad_type["body"][1]["type"] = "text"
        self.assertTrue(list(self.forms.iter_errors(bad_type)))

    def test_missing_secrets_checkbox_is_reported(self):
        form = self.load_yaml(".github/ISSUE_TEMPLATE/feature_request.yml")
        for el in form["body"]:
            if el["type"] == "checkboxes":
                el["attributes"]["options"] = [o for o in el["attributes"]["options"]
                                               if o["label"] != self.v.REQUIRED_CHECKBOX]
        self.assertTrue(self.v.form_rules(form, needs_secrets_checkbox=True))

    def test_broken_discussion_form_fails(self):
        form = self.load_yaml(".github/DISCUSSION_TEMPLATE/q-a.yml")
        with_name = copy.deepcopy(form)
        with_name["name"] = "Q&A"  # issue-form key, not allowed in a discussion category form
        self.assertTrue(list(self.discussion.iter_errors(with_name)))
        markdown_only = {"body": [el for el in form["body"] if el["type"] == "markdown"]}
        self.assertTrue(self.v.form_rules(markdown_only, needs_secrets_checkbox=False))

    def test_broken_config_fails(self):
        cfg = self.load_yaml(".github/ISSUE_TEMPLATE/config.yml")
        cfg["contact_links"][0]["url"] = "mailto:oss@luminare.tech"
        self.assertTrue(list(self.config.iter_errors(cfg)))

    def test_broken_ruleset_fails(self):
        main = json.loads((ROOT / "rulesets/main.json").read_text(encoding="utf-8"))
        bad_rule = copy.deepcopy(main)
        bad_rule["rules"].append({"type": "force_push"})
        self.assertTrue(list(self.ruleset.iter_errors(bad_rule)))
        bad_pr = copy.deepcopy(main)
        pr = next(r for r in bad_pr["rules"] if r["type"] == "pull_request")
        del pr["parameters"]["required_approving_review_count"]
        self.assertTrue(list(self.ruleset.iter_errors(bad_pr)))
        bad_enf = copy.deepcopy(main)
        bad_enf["enforcement"] = "on"
        self.assertTrue(list(self.ruleset.iter_errors(bad_enf)))


if __name__ == "__main__":
    unittest.main()
