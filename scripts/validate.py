#!/usr/bin/env python3
"""Validate the issue forms, the template chooser config and the ruleset JSON against schemas.

Needs the development tools (requirements-dev.txt: jsonschema, PyYAML). Schemas are downloaded
once into .cache/schemas/ (git-ignored) with plain HTTPS GET requests:

  * SchemaStore "github-issue-forms" and "github-issue-config" (the schemas editors use for
    .github/ISSUE_TEMPLATE/*.yml); the private vulnerability report form uses the same syntax;
  * the request-body schema of "Create a repository ruleset" (POST /repos/{owner}/{repo}/rulesets),
    cut out of GitHub's OpenAPI description (github/rest-api-description).

Usage:
    python scripts/validate.py              # use cached schemas, download missing ones
    python scripts/validate.py --refresh    # download all schemas again
    python scripts/validate.py --offline    # never download; fail if a schema is missing
Exit codes: 0 valid, 1 validation errors, 2 setup problem (missing tool or schema).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "schemas"
SCHEMAS = {
    "github-issue-forms.json": "https://www.schemastore.org/github-issue-forms.json",
    "github-issue-config.json": "https://www.schemastore.org/github-issue-config.json",
}
OPENAPI_URL = ("https://raw.githubusercontent.com/github/rest-api-description/main/"
               "descriptions/api.github.com/api.github.com.json")
RULESET_SCHEMA = "repo-ruleset-request.json"
REQUIRED_CHECKBOX = "I removed all secrets, tokens, licence keys, IPs and player data."
USER_AGENT = "luminare-dev-validate/1.0"

try:
    import jsonschema
    import yaml
except ImportError as exc:  # pragma: no cover - depends on the environment
    print(f"error: {exc.name} is missing; install requirements-dev.txt into a virtual environment", file=sys.stderr)
    sys.exit(2)


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - fixed https URLs
        return resp.read()


def _nullable_to_jsonschema(node):
    """OpenAPI 3.0 'nullable: true' -> JSON Schema type union with 'null'."""
    if isinstance(node, dict):
        out = {k: _nullable_to_jsonschema(v) for k, v in node.items()}
        if out.pop("nullable", False):
            t = out.get("type")
            if isinstance(t, str):
                out["type"] = [t, "null"]
            elif "type" not in out:
                out = {"anyOf": [out, {"type": "null"}]}
        return out
    if isinstance(node, list):
        return [_nullable_to_jsonschema(v) for v in node]
    return node


def _collect_refs(node, found: set[str]):
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[1])
        for v in node.values():
            _collect_refs(v, found)
    elif isinstance(node, list):
        for v in node:
            _collect_refs(v, found)


def build_ruleset_schema(openapi: dict) -> dict:
    op = openapi["paths"]["/repos/{owner}/{repo}/rulesets"]["post"]
    body = op["requestBody"]["content"]["application/json"]["schema"]
    all_schemas = openapi["components"]["schemas"]
    needed: set[str] = set()
    _collect_refs(body, needed)
    done: set[str] = set()
    while needed - done:
        name = sorted(needed - done)[0]
        done.add(name)
        _collect_refs(all_schemas[name], needed)
    schema = dict(body)
    schema["components"] = {"schemas": {n: all_schemas[n] for n in sorted(done)}}
    schema["$comment"] = (f"Request body of POST /repos/{{owner}}/{{repo}}/rulesets from {OPENAPI_URL} "
                          f"(OpenAPI info.version {openapi.get('info', {}).get('version')}), nullable converted.")
    return _nullable_to_jsonschema(schema)


def ensure_schemas(refresh: bool, offline: bool) -> dict[str, dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    loaded: dict[str, dict] = {}
    for name, url in SCHEMAS.items():
        path = CACHE / name
        if refresh or not path.exists():
            if offline:
                raise FileNotFoundError(f"{path} is missing and --offline was given")
            path.write_bytes(_download(url))
        data = path.read_bytes()
        print(f"schema  {name}  sha256={hashlib.sha256(data).hexdigest()[:16]}…  ({url})")
        loaded[name] = json.loads(data)
    path = CACHE / RULESET_SCHEMA
    if refresh or not path.exists():
        if offline:
            raise FileNotFoundError(f"{path} is missing and --offline was given")
        openapi = json.loads(_download(OPENAPI_URL))
        path.write_text(json.dumps(build_ruleset_schema(openapi), indent=1), encoding="utf-8")
        del openapi
    data = path.read_bytes()
    print(f"schema  {RULESET_SCHEMA}  sha256={hashlib.sha256(data).hexdigest()[:16]}…  (cut from {OPENAPI_URL})")
    loaded[RULESET_SCHEMA] = json.loads(data)
    return loaded


def _errors(validator, instance) -> list[str]:
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))]


def form_rules(form: dict, is_issue_form: bool) -> list[str]:
    """Rules GitHub enforces that the JSON schema does not fully express, plus our own rules."""
    problems = []
    ids = [el.get("id") for el in form.get("body", []) if el.get("id")]
    if len(ids) != len(set(ids)):
        problems.append("element ids are not unique")
    if is_issue_form:
        found = False
        for el in form.get("body", []):
            if el.get("type") == "checkboxes":
                for opt in el.get("attributes", {}).get("options", []):
                    if opt.get("label") == REQUIRED_CHECKBOX:
                        found = found or opt.get("required") is True
        if not found:
            problems.append(f"missing the required checkbox {REQUIRED_CHECKBOX!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate issue forms, chooser config and rulesets.")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args(argv)
    try:
        schemas = ensure_schemas(args.refresh, args.offline)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    forms_v = jsonschema.Draft7Validator(schemas["github-issue-forms.json"])
    config_v = jsonschema.Draft7Validator(schemas["github-issue-config.json"])
    ruleset_v = jsonschema.Draft4Validator(schemas[RULESET_SCHEMA])

    failures = 0
    checked = 0

    def report(path: Path, problems: list[str]):
        nonlocal failures, checked
        checked += 1
        rel = path.relative_to(ROOT)
        if problems:
            failures += 1
            for prob in problems:
                print(f"FAIL    {rel}: {prob}")
        else:
            print(f"ok      {rel}")

    templates = ROOT / ".github" / "ISSUE_TEMPLATE"
    for path in sorted(templates.glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.stem == "config":
            report(path, _errors(config_v, data))
        else:
            report(path, _errors(forms_v, data) + form_rules(data, is_issue_form=True))
    for name in ("VULNERABILITY_REPORT.yml", "VULNERABILITY_REPORT.yaml"):
        path = ROOT / ".github" / name
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            report(path, _errors(forms_v, data) + form_rules(data, is_issue_form=False))
    for path in sorted((ROOT / "rulesets").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        extra = []
        if data.get("source_type") not in (None, "Repository"):
            extra.append("source_type must be 'Repository' (organization rulesets need GitHub Team)")
        if "repository_name" in data.get("conditions", {}):
            extra.append("conditions.repository_name is only valid in organization rulesets")
        report(path, _errors(ruleset_v, data) + extra)
    print(f"{checked} file(s) checked, {failures} with errors")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
