"""Offline tests for scripts/sync_labels.py. No network: every HTTP call goes to FakeGitHub.

Run: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
import unittest.mock
import urllib.error
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sync_labels", ROOT / "scripts" / "sync_labels.py")
sync_labels = importlib.util.module_from_spec(_spec)
sys.modules["sync_labels"] = sync_labels
_spec.loader.exec_module(sync_labels)

API = "https://api.github.com"
TOKEN = "test-token-not-real-0000"


class FakeResponse:
    def __init__(self, status: int, body, headers: dict | None = None):
        self.status = status
        self._raw = b"" if body is None else json.dumps(body).encode("utf-8")
        self.headers = _Headers(headers or {})

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Headers(dict):
    def items(self):  # same interface as http.client.HTTPMessage.items()
        return list(super().items())


class FakeGitHub:
    """A tiny in-memory GitHub: org repo listing and label CRUD, with Link-header pagination."""

    def __init__(self, repos: dict, fail: dict | None = None, link_override: str | None = None):
        self.repos = repos                    # full_name -> {"labels": [...], "archived": bool, "fork": bool}
        self.calls: list[tuple[str, str, dict | None, str | None]] = []
        self.fail = fail or {}                # (method, label name) -> (status, message)
        self.link_override = link_override

    def __call__(self, req, timeout=None):
        method = req.get_method()
        url = req.full_url
        body = json.loads(req.data.decode("utf-8")) if req.data else None
        self.calls.append((method, url, body, req.get_header("Authorization")))
        parts = urllib.parse.urlsplit(url)
        assert parts.netloc == "api.github.com", url
        query = urllib.parse.parse_qs(parts.query)
        segs = [urllib.parse.unquote(s) for s in parts.path.strip("/").split("/")]

        if segs[:1] == ["orgs"] and segs[2:] == ["repos"] and method == "GET":
            org = segs[1]
            items = [{"full_name": n, "name": n.split("/")[1], "archived": r.get("archived", False),
                      "fork": r.get("fork", False)} for n, r in sorted(self.repos.items()) if n.startswith(org + "/")]
            return self._page(url, items, query)

        if segs[:1] == ["repos"] and len(segs) >= 4 and segs[3] == "labels":
            full = f"{segs[1]}/{segs[2]}"
            if full not in self.repos:
                raise self._error(url, 404, "Not Found")
            labels = self.repos[full]["labels"]
            name = segs[4] if len(segs) > 4 else None
            key = (method, (body or {}).get("name") or name)
            if key in self.fail:
                status, msg = self.fail[key]
                raise self._error(url, status, msg)
            if method == "GET" and name is None:
                return self._page(url, labels, query)
            if method == "POST":
                if any(l["name"].lower() == body["name"].lower() for l in labels):
                    raise self._error(url, 422, "Validation Failed")
                labels.append({"name": body["name"], "color": body["color"], "description": body.get("description", "")})
                return FakeResponse(201, labels[-1])
            target = next((l for l in labels if l["name"].lower() == (name or "").lower()), None)
            if target is None:
                raise self._error(url, 404, "Not Found")
            if method == "PATCH":
                if "new_name" in body:
                    target["name"] = body["new_name"]
                for k in ("color", "description"):
                    if k in body:
                        target[k] = body[k]
                return FakeResponse(200, target)
            if method == "DELETE":
                labels.remove(target)
                return FakeResponse(204, None)
        raise AssertionError(f"unexpected request {method} {url}")

    def _page(self, url, items, query):
        per_page = int(query.get("per_page", ["30"])[0])
        page = int(query.get("page", ["1"])[0])
        chunk = items[(page - 1) * per_page: page * per_page]
        headers = {}
        if page * per_page < len(items):
            parts = urllib.parse.urlsplit(url)
            q = {k: v[0] for k, v in query.items()}
            q["page"] = str(page + 1)
            nxt = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(q), ""))
            headers["Link"] = self.link_override or f'<{nxt}>; rel="next", <{nxt}>; rel="last"'
        return FakeResponse(200, chunk, headers)

    @staticmethod
    def _error(url, status, message, headers=None):
        return urllib.error.HTTPError(url, status, message, headers or {}, io.BytesIO(json.dumps({"message": message}).encode()))

    def writes(self):
        return [c for c in self.calls if c[0] != "GET"]


def run(argv, fake, env=None):
    out = io.StringIO()
    code = sync_labels.main(argv, opener=fake, env=env if env is not None else {}, out=out)
    return code, out.getvalue()


def desired():
    return sync_labels.load_labels(sync_labels.DEFAULT_CONFIG)


def as_current(labels):
    return [{"name": l.name, "color": l.color, "description": l.description} for l in labels]


# --------------------------------------------------------------------------------------------

class TestRealConfig(unittest.TestCase):
    def test_labels_yml_is_valid_and_has_the_shared_set(self):
        labels = desired()
        names = {l.name for l in labels}
        for required in ("type: bug", "type: feature", "type: docs", "priority: high", "status: triage",
                         "status: needs-info", "good first issue", "help wanted", "dependencies",
                         "autorelease: pending", "autorelease: tagged"):
            self.assertIn(required, names)
        for l in labels:
            self.assertLessEqual(len(l.description), 100, l.name)
            self.assertRegex(l.color, r"^[0-9A-F]{6}$")

    def test_no_product_line_colours(self):
        # Ember/Orchid/Verdant/Amber (and their bright and mark variants) are product-line colours.
        tokens = {"B71920", "FF5147", "A333B5", "EF8DEF", "028844", "58DD70", "B15204", "FFB334"}
        self.assertFalse(tokens & {l.color for l in desired()})

    def test_issue_form_labels_exist(self):
        names = {l.name for l in desired()}
        forms = sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
        checked = 0
        for form in forms:
            m = re.search(r"^labels:\s*\[(.*)\]\s*$", form.read_text(encoding="utf-8"), re.M)
            if not m:
                continue
            for item in sync_labels._parse_inline_list(f"[{m.group(1)}]", form.name):
                self.assertIn(item, names, f"{form.name} sets label {item!r}, which labels.yml lacks")
                checked += 1
        self.assertGreaterEqual(checked, 4)

    def test_parser_matches_pyyaml_when_available(self):
        try:
            import yaml  # noqa: PLC0415 - optional cross-check, only in the dev venv
        except ImportError:
            self.skipTest("PyYAML not installed (optional cross-check)")
        text = sync_labels.DEFAULT_CONFIG.read_text(encoding="utf-8")
        ours = sync_labels.parse_labels_yaml(text)
        theirs = yaml.safe_load(text)["labels"]
        self.assertEqual(ours, theirs)


class TestParserErrors(unittest.TestCase):
    def check_error(self, text, fragment):
        with self.assertRaises(sync_labels.ConfigError) as ctx:
            sync_labels.validate_labels(sync_labels.parse_labels_yaml(text))
        self.assertIn(fragment, str(ctx.exception))

    def test_errors(self):
        ok = 'labels:\n  - name: "a"\n    color: "AABBCC"\n'
        self.assertEqual(sync_labels.validate_labels(sync_labels.parse_labels_yaml(ok))[0].name, "a")
        self.check_error("labels:\n\t- name: a\n", "tabs")
        self.check_error('other:\n', "top-level")
        self.check_error('labels:\n  - name: "a"\n    colour: "AABBCC"\n', "unknown key")
        self.check_error('labels:\n  - name: "a"\n    color: "#AABBCC"\n', "6 hex digits")
        self.check_error('labels:\n  - name: "a"\n    color: "AABBCC"\n  - name: "A"\n    color: "AABBCC"\n', "used twice")
        self.check_error('labels:\n  - name: "a"\n    color: "AABBCC"\n    aliases: ["b"]\n'
                         '  - name: "b"\n    color: "AABBCC"\n', "used twice")
        self.check_error('labels:\n  - name: "a"\n    color: "AABBCC"\n    description: "' + "x" * 101 + '"\n', "limit is 100")
        self.check_error('labels:\n  - name: "a"\n   color: "AABBCC"\n', "indented by 4")
        self.check_error('labels:\n  - name: "a\n    color: "AABBCC"\n', "unterminated")
        self.check_error('labels:\n  - name: "a"\n', "missing 'color'")
        self.check_error('labels:\n', "no labels")

    def test_comments_and_quotes(self):
        text = ('# head\nlabels:\n  - name: "x # not a comment"   # a comment\n'
                "    color: 'AABBCC'\n    aliases: [\"p, q\", r]\n")
        item = sync_labels.parse_labels_yaml(text)[0]
        self.assertEqual(item, {"name": "x # not a comment", "color": "AABBCC", "aliases": ["p, q", "r"]})


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.d = [sync_labels.Label("type: bug", "1F47C4", "Bug", ("bug",)),
                  sync_labels.Label("help wanted", "008672", "Help", ())]

    def test_creates_everything_on_an_empty_repo(self):
        actions, _ = sync_labels.plan(self.d, [])
        self.assertEqual([a.kind for a in actions], ["create", "create"])

    def test_up_to_date_is_a_no_op(self):
        actions, notes = sync_labels.plan(self.d, as_current(self.d))
        self.assertEqual(actions, [])
        self.assertEqual(notes, [])

    def test_colour_case_does_not_count_as_a_change(self):
        cur = as_current(self.d)
        cur[0]["color"] = "1f47c4"
        self.assertEqual(sync_labels.plan(self.d, cur)[0], [])

    def test_updates_colour_description_and_name_case(self):
        cur = [{"name": "Type: Bug", "color": "000000", "description": None},
               {"name": "help wanted", "color": "008672", "description": "Help"}]
        actions, _ = sync_labels.plan(self.d, cur)
        self.assertEqual(len(actions), 1)
        a = actions[0]
        self.assertEqual((a.kind, a.current), ("update", "Type: Bug"))
        self.assertEqual(a.payload, {"new_name": "type: bug", "color": "1F47C4", "description": "Bug"})

    def test_renames_an_alias_instead_of_creating_a_duplicate(self):
        cur = [{"name": "bug", "color": "d73a4a", "description": "Something isn't working"}]
        actions, _ = sync_labels.plan(self.d, cur)
        kinds = {(a.kind, a.current) for a in actions}
        self.assertIn(("rename", "bug"), kinds)
        self.assertIn(("create", None), kinds)

    def test_keeps_unknown_labels_without_prune(self):
        cur = as_current(self.d) + [{"name": "custom", "color": "000000", "description": ""}]
        actions, notes = sync_labels.plan(self.d, cur)
        self.assertEqual(actions, [])
        self.assertTrue(any('"custom"' in n for n in notes))

    def test_prune_deletes_unknown_but_not_renamed_aliases(self):
        cur = [{"name": "bug", "color": "d73a4a", "description": ""},
               {"name": "custom", "color": "000000", "description": ""}]
        actions, _ = sync_labels.plan(self.d, cur, prune=True)
        deletes = [a.target for a in actions if a.kind == "delete"]
        self.assertEqual(deletes, ["custom"])

    def test_alias_next_to_target_is_reported(self):
        cur = as_current(self.d) + [{"name": "bug", "color": "d73a4a", "description": ""}]
        actions, notes = sync_labels.plan(self.d, cur)
        self.assertEqual(actions, [])
        self.assertTrue(any("alias" in n for n in notes))


class TestCli(unittest.TestCase):
    def repo(self, labels=None, **kw):
        return {"labels": list(labels or []), **kw}

    def test_dry_run_never_writes_even_with_a_token(self):
        fake = FakeGitHub({"luminare-dev/.github": self.repo([{"name": "bug", "color": "d73a4a", "description": ""},
                                                             {"name": "custom", "color": "000000", "description": ""}])})
        code, out = run(["--repo", "luminare-dev/.github", "--prune"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0)
        self.assertEqual(fake.writes(), [])
        self.assertIn("would   rename", out)
        self.assertIn('would   delete  "custom"', out)
        self.assertIn("DRY RUN: nothing was changed", out)

    def test_apply_needs_a_token(self):
        fake = FakeGitHub({"luminare-dev/.github": self.repo()})
        with unittest.mock.patch("sys.stderr", new=io.StringIO()) as err:
            code, _ = run(["--repo", "luminare-dev/.github", "--apply"], fake, env={})
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])
        self.assertIn("needs a token", err.getvalue())

    def test_apply_then_second_run_is_idempotent(self):
        fake = FakeGitHub({"luminare-dev/.github": self.repo([{"name": "bug", "color": "d73a4a", "description": "x"},
                                                             {"name": "enhancement", "color": "a2eeef", "description": ""}])})
        code, out = run(["--repo", "luminare-dev/.github", "--apply"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0, out)
        state = {l["name"]: l for l in fake.repos["luminare-dev/.github"]["labels"]}
        for l in desired():
            self.assertEqual(state[l.name]["color"], l.color)
            self.assertEqual(state[l.name]["description"], l.description)
        self.assertNotIn("bug", state)  # renamed to "type: bug", issues keep their label
        writes_before = len(fake.writes())
        code, out = run(["--repo", "luminare-dev/.github", "--apply"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.writes()), writes_before)
        self.assertIn("up to date", out)

    def test_token_is_sent_as_header_and_never_printed(self):
        fake = FakeGitHub({"luminare-dev/.github": self.repo()})
        code, out = run(["--repo", "luminare-dev/.github", "--apply"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0)
        self.assertTrue(all(c[3] == f"Bearer {TOKEN}" for c in fake.calls))
        self.assertNotIn(TOKEN, out)

    def test_no_token_sends_no_auth_header(self):
        fake = FakeGitHub({"luminare-dev/.github": self.repo()})
        code, out = run(["--repo", "luminare-dev/.github"], fake, env={})
        self.assertEqual(code, 0)
        self.assertTrue(all(c[3] is None for c in fake.calls))
        self.assertIn("no token", out)

    def test_org_mode_skips_archived_and_forks(self):
        fake = FakeGitHub({"luminare-dev/a": self.repo(), "luminare-dev/old": self.repo(archived=True),
                           "luminare-dev/forked": self.repo(fork=True), "other/x": self.repo()})
        code, out = run(["--org", "luminare-dev"], fake)
        self.assertEqual(code, 0)
        self.assertIn("skip    luminare-dev/old (archived)", out)
        self.assertIn("skip    luminare-dev/forked (fork", out)
        label_gets = [c[1] for c in fake.calls if "/labels" in c[1]]
        self.assertEqual(len(label_gets), 1)
        self.assertIn("/repos/luminare-dev/a/labels", label_gets[0])
        code, out = run(["--org", "luminare-dev", "--include-forks"], fake)
        self.assertIn("luminare-dev/forked:", out)

    def test_pagination_reads_every_page(self):
        many = [{"name": f"l{i:03d}", "color": "000000", "description": ""} for i in range(250)]
        fake = FakeGitHub({"luminare-dev/big": self.repo(many)})
        code, out = run(["--repo", "luminare-dev/big", "--prune"], fake)
        self.assertEqual(code, 0)
        self.assertEqual(sum(1 for c in fake.calls if "/labels" in c[1]), 3)
        self.assertEqual(out.count("would   delete"), 250)

    def test_refuses_to_follow_a_link_to_another_host(self):
        many = [{"name": f"l{i:03d}", "color": "000000", "description": ""} for i in range(150)]
        fake = FakeGitHub({"luminare-dev/big": self.repo(many)},
                          link_override='<https://evil.example/steal?page=2>; rel="next"')
        code, out = run(["--repo", "luminare-dev/big"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 1)
        self.assertIn("another host", out)
        self.assertTrue(all("evil.example" not in c[1] for c in fake.calls))

    def test_api_error_is_reported_and_exit_code_1(self):
        fake = FakeGitHub({"luminare-dev/a": self.repo()}, fail={("POST", "type: bug"): (422, "Validation Failed")})
        code, out = run(["--repo", "luminare-dev/a", "--apply"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 1)
        self.assertIn('FAILED  create  "type: bug"', out)
        self.assertIn("Validation Failed", out)
        # the other labels were still created
        self.assertGreater(len(fake.repos["luminare-dev/a"]["labels"]), 10)

    def test_label_names_are_url_encoded(self):
        fake = FakeGitHub({"luminare-dev/a": self.repo([{"name": "type: bug", "color": "000000", "description": ""}])})
        run(["--repo", "luminare-dev/a", "--apply"], fake, env={"GITHUB_TOKEN": TOKEN})
        patch = [c for c in fake.calls if c[0] == "PATCH"]
        self.assertEqual(len(patch), 1)
        self.assertTrue(patch[0][1].endswith("/repos/luminare-dev/a/labels/type%3A%20bug"), patch[0][1])

    def test_prune_with_apply_deletes(self):
        cur = as_current(desired()) + [{"name": "custom", "color": "000000", "description": ""}]
        fake = FakeGitHub({"luminare-dev/a": self.repo(cur)})
        code, out = run(["--repo", "luminare-dev/a", "--apply", "--prune"], fake, env={"GITHUB_TOKEN": TOKEN})
        self.assertEqual(code, 0)
        self.assertEqual([c[0] for c in fake.writes()], ["DELETE"])
        self.assertTrue(fake.writes()[0][1].endswith("/labels/custom"))

    def test_fail_on_changes(self):
        fake = FakeGitHub({"luminare-dev/a": self.repo()})
        self.assertEqual(run(["--repo", "luminare-dev/a", "--fail-on-changes"], fake)[0], 1)
        fake = FakeGitHub({"luminare-dev/a": self.repo(as_current(desired()))})
        self.assertEqual(run(["--repo", "luminare-dev/a", "--fail-on-changes"], fake)[0], 0)

    def test_bad_arguments_and_config(self):
        fake = FakeGitHub({})
        with unittest.mock.patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(run(["--repo", "not-a-repo"], fake)[0], 2)
            self.assertEqual(run(["--org", "bad/org"], fake)[0], 2)
            with tempfile.TemporaryDirectory() as tmp:
                bad = Path(tmp) / "labels.yml"
                bad.write_text('labels:\n  - name: "a"\n    color: "red"\n', encoding="utf-8")
                self.assertEqual(run(["--repo", "a/b", "--config", str(bad)], fake)[0], 2)
            self.assertEqual(run(["--repo", "a/b", "--api-url", "http://api.example"], fake)[0], 2)
        self.assertEqual(fake.calls, [])

    def test_rate_limit_message(self):
        class Limited(FakeGitHub):
            def __call__(self, req, timeout=None):
                self.calls.append((req.get_method(), req.full_url, None, None))
                raise self._error(req.full_url, 403, "API rate limit exceeded", {"X-RateLimit-Remaining": "0"})
        code, out = run(["--repo", "luminare-dev/a"], Limited({}))
        self.assertEqual(code, 1)
        self.assertIn("rate limit exhausted", out)


if __name__ == "__main__":
    unittest.main()
