#!/usr/bin/env python3
"""Sync the shared issue labels in labels.yml to GitHub repositories.

Python standard library only. Dry run by default: it reads the current labels and prints what it
would change. Nothing is written unless --apply is given, and labels are never deleted unless
--prune is given as well.

Examples:
    python scripts/sync_labels.py --repo luminare-dev/.github
    python scripts/sync_labels.py --org luminare-dev
    GITHUB_TOKEN=... python scripts/sync_labels.py --org luminare-dev --apply
    GITHUB_TOKEN=... python scripts/sync_labels.py --repo luminare-dev/oss-template --apply --prune

Token: a fine-grained personal access token with "Issues: read and write" on the target
repositories ("Metadata: read" is added automatically). It is read from the environment variable
named by --token-env (default GITHUB_TOKEN), never from the command line, and it is only ever sent
to the --api-url host.

Exit codes: 0 ok, 1 a GitHub API call failed (or --fail-on-changes found pending changes),
2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

API_URL = "https://api.github.com"
# Newest REST API version on 2026-10-06 (GET https://api.github.com/versions). The label and
# repository-list fields used here are the same in 2022-11-28.
API_VERSION = "2026-03-10"
USER_AGENT = "luminare-dev-label-sync/1.0"
TIMEOUT_SECONDS = 30
MAX_DESCRIPTION = 100  # GitHub rejects longer label descriptions
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "labels.yml"

_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_OWNER_RE = re.compile(r"^[A-Za-z0-9-]+$")
_KEY_RE = re.compile(r"^(?P<key>[a-z_]+):(?:\s+(?P<value>.*))?$")


class ConfigError(Exception):
    """labels.yml is malformed or breaks a rule."""


class ApiError(Exception):
    """A GitHub API call failed."""

    def __init__(self, method: str, url: str, status: int | None, message: str):
        self.method, self.url, self.status = method, url, status
        super().__init__(f"{method} {url} failed ({status if status is not None else 'no response'}): {message}")


# --------------------------------------------------------------------------------------------
# labels.yml: a small, strict YAML subset (no PyYAML needed)
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Label:
    name: str
    color: str
    description: str = ""
    aliases: tuple[str, ...] = ()


def _strip_comment(line: str) -> str:
    """Remove a trailing '# comment' that is outside quotes."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i].rstrip()
    return line.rstrip()


def _parse_scalar(text: str, where: str) -> str:
    text = text.strip()
    if not text:
        raise ConfigError(f"{where}: empty value")
    if text[0] in "\"'":
        q = text[0]
        if len(text) < 2 or text[-1] != q:
            raise ConfigError(f"{where}: unterminated quoted string {text!r}")
        inner = text[1:-1]
        if q == "'":
            return inner.replace("''", "'")
        if "\\" in inner:
            raise ConfigError(f"{where}: escape sequences are not supported in {text!r}")
        if '"' in inner:
            raise ConfigError(f"{where}: unexpected quote in {text!r}")
        return inner
    if text[0] in "[]{}&*!|>%@`" or text.startswith("- "):
        raise ConfigError(f"{where}: unsupported YAML syntax {text!r}; quote the value")
    return text


def _parse_inline_list(text: str, where: str) -> list[str]:
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        raise ConfigError(f"{where}: expected an inline list like [\"a\", \"b\"], got {text!r}")
    inner = text[1:-1].strip()
    if not inner:
        return []
    items, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(_parse_scalar(buf, where))
            buf = ""
        else:
            buf += ch
    if quote:
        raise ConfigError(f"{where}: unterminated quoted string in list {text!r}")
    items.append(_parse_scalar(buf, where))
    return items


def parse_labels_yaml(text: str) -> list[dict]:
    """Parse the labels.yml subset into a list of dicts (keys: name, color, description, aliases)."""
    items: list[dict] = []
    current: dict | None = None
    seen_root = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        where = f"labels.yml line {lineno}"
        if "\t" in raw:
            raise ConfigError(f"{where}: tabs are not allowed")
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        if indent == 0:
            if body != "labels:" or seen_root:
                raise ConfigError(f"{where}: expected a single top-level 'labels:' key, got {body!r}")
            seen_root = True
            continue
        if not seen_root:
            raise ConfigError(f"{where}: content before 'labels:'")
        if body.startswith("- "):
            if indent != 2:
                raise ConfigError(f"{where}: list items must be indented by 2 spaces")
            current = {}
            items.append(current)
            body = body[2:].strip()
        elif indent != 4 or current is None:
            raise ConfigError(f"{where}: keys must be indented by 4 spaces inside a list item")
        m = _KEY_RE.match(body)
        if not m:
            raise ConfigError(f"{where}: expected 'key: value', got {body!r}")
        key, value = m.group("key"), m.group("value")
        if key not in ("name", "color", "description", "aliases"):
            raise ConfigError(f"{where}: unknown key {key!r}")
        if key in current:
            raise ConfigError(f"{where}: duplicate key {key!r}")
        if value is None:
            raise ConfigError(f"{where}: {key!r} needs a value on the same line")
        current[key] = _parse_inline_list(value, where) if key == "aliases" else _parse_scalar(value, where)
    if not seen_root:
        raise ConfigError("labels.yml: missing top-level 'labels:' key")
    return items


def validate_labels(items: Iterable[dict]) -> list[Label]:
    labels: list[Label] = []
    names: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for i, item in enumerate(items, start=1):
        where = f"label #{i}"
        for key in ("name", "color"):
            if not item.get(key):
                raise ConfigError(f"{where}: missing {key!r}")
        name = item["name"]
        if name != name.strip() or len(name) > 50:
            raise ConfigError(f"{where}: name {name!r} has outer spaces or is longer than 50 characters")
        color = item["color"]
        if not _COLOR_RE.match(color):
            raise ConfigError(f"{where} ({name}): color {color!r} must be 6 hex digits without '#'")
        description = item.get("description", "")
        if len(description) > MAX_DESCRIPTION:
            raise ConfigError(f"{where} ({name}): description is {len(description)} characters, the limit is {MAX_DESCRIPTION}")
        key = name.lower()
        if key in names or key in aliases:
            raise ConfigError(f"{where}: name {name!r} is used twice (names and aliases are case-insensitive)")
        names[key] = name
        label_aliases = tuple(item.get("aliases", []) or ())
        for alias in label_aliases:
            akey = alias.lower()
            if akey in names or akey in aliases or akey == key:
                raise ConfigError(f"{where} ({name}): alias {alias!r} collides with another name or alias")
            aliases[akey] = name
        labels.append(Label(name=name, color=color.upper(), description=description, aliases=label_aliases))
    # an alias declared before the label that owns that name
    for akey, owner in aliases.items():
        if akey in names:
            raise ConfigError(f"alias {akey!r} of {owner!r} is also a label name")
    if not labels:
        raise ConfigError("labels.yml defines no labels")
    return labels


def load_labels(path: Path) -> list[Label]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    return validate_labels(parse_labels_yaml(text))


# --------------------------------------------------------------------------------------------
# Planning (pure; no network)
# --------------------------------------------------------------------------------------------

@dataclass
class Action:
    kind: str                 # create | update | rename | delete
    target: str               # the label name after the action (the deleted name for delete)
    current: str | None = None  # the existing label's name (update/rename/delete)
    payload: dict = field(default_factory=dict)

    def describe(self) -> str:
        if self.kind == "create":
            return f'create  "{self.target}"  color={self.payload["color"]}'
        if self.kind == "delete":
            return f'delete  "{self.target}"'
        changes = []
        if "new_name" in self.payload:
            changes.append(f'name "{self.current}" -> "{self.payload["new_name"]}"')
        if "color" in self.payload:
            changes.append(f'color={self.payload["color"]}')
        if "description" in self.payload:
            changes.append("description")
        return f'{self.kind:<7} "{self.current}"  ' + ", ".join(changes)


def plan(desired: list[Label], current: list[dict], prune: bool = False) -> tuple[list[Action], list[str]]:
    """Return the actions that make `current` match `desired`, plus human-readable notes."""
    by_key = {c["name"].lower(): c for c in current}
    used: set[str] = set()
    actions: list[Action] = []
    notes: list[str] = []
    for label in desired:
        key = label.name.lower()
        existing = by_key.get(key)
        if existing is not None:
            used.add(key)
            payload: dict = {}
            if existing["name"] != label.name:
                payload["new_name"] = label.name
            if (existing.get("color") or "").upper() != label.color:
                payload["color"] = label.color
            if (existing.get("description") or "") != label.description:
                payload["description"] = label.description
            if payload:
                actions.append(Action("update", label.name, existing["name"], payload))
            for alias in label.aliases:
                if alias.lower() in by_key:
                    notes.append(
                        f'"{by_key[alias.lower()]["name"]}" (alias of "{label.name}") also exists; '
                        f"move its issues by hand, then remove it (or use --prune)"
                    )
            continue
        alias_hit = next((by_key[a.lower()] for a in label.aliases
                          if a.lower() in by_key and a.lower() not in used), None)
        if alias_hit is not None:
            used.add(alias_hit["name"].lower())
            actions.append(Action("rename", label.name, alias_hit["name"],
                                  {"new_name": label.name, "color": label.color,
                                   "description": label.description}))
            continue
        actions.append(Action("create", label.name, None,
                              {"name": label.name, "color": label.color,
                               "description": label.description}))
    leftovers = sorted((c["name"] for c in current if c["name"].lower() not in used), key=str.lower)
    if prune:
        actions.extend(Action("delete", name, name) for name in leftovers)
    elif leftovers:
        notes.append(f"{len(leftovers)} label(s) not in labels.yml are kept (use --prune to delete): "
                     + ", ".join(f'"{n}"' for n in leftovers))
    return actions, notes


# --------------------------------------------------------------------------------------------
# GitHub REST client (urllib; the opener is injectable for tests)
# --------------------------------------------------------------------------------------------

Opener = Callable[..., object]


class GitHubClient:
    def __init__(self, token: str | None = None, api_url: str = API_URL, opener: Opener | None = None):
        self.api_url = api_url.rstrip("/")
        parsed = urllib.parse.urlsplit(self.api_url)
        if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise ConfigError(f"--api-url must use https: {api_url}")
        self._origin = (parsed.scheme, parsed.netloc)
        self.token = token
        self._open = opener or urllib.request.urlopen

    def _same_origin(self, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        return (parsed.scheme, parsed.netloc) == self._origin

    def request(self, method: str, url: str, body: dict | None = None) -> tuple[int, object, dict]:
        if not url.startswith("http"):
            url = self.api_url + url
        if not self._same_origin(url):
            raise ApiError(method, url, None, "refusing to follow a URL on another host")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            resp = self._open(req, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                payload = json.loads(exc.read().decode("utf-8") or "{}")
                detail = payload.get("message", "")
                errors = payload.get("errors")
                if errors:
                    detail += " " + json.dumps(errors)
            except (ValueError, AttributeError):
                pass
            if exc.code in (403, 429) and (exc.headers or {}).get("X-RateLimit-Remaining") == "0":
                detail = "rate limit exhausted; try again later or set a token. " + detail
            raise ApiError(method, url, exc.code, detail.strip() or exc.reason) from None
        except urllib.error.URLError as exc:
            raise ApiError(method, url, None, str(exc.reason)) from None
        with resp:
            status = getattr(resp, "status", 200)
            raw = resp.read()
            resp_headers = dict(resp.headers.items()) if getattr(resp, "headers", None) else {}
        parsed_body = json.loads(raw.decode("utf-8")) if raw else None
        return status, parsed_body, resp_headers

    @staticmethod
    def _next_link(headers: dict) -> str | None:
        link = next((v for k, v in headers.items() if k.lower() == "link"), None)
        if not link:
            return None
        for part in link.split(","):
            m = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', part)
            if m and m.group(2) == "next":
                return m.group(1)
        return None

    def paginate(self, path: str) -> list:
        sep = "&" if "?" in path else "?"
        url: str | None = f"{path}{sep}per_page=100"
        out: list = []
        pages = 0
        while url:
            pages += 1
            if pages > 100:
                raise ApiError("GET", url, None, "more than 100 pages; stopping")
            _, body, headers = self.request("GET", url)
            if not isinstance(body, list):
                raise ApiError("GET", url, None, "expected a JSON list")
            out.extend(body)
            url = self._next_link(headers)
        return out

    @staticmethod
    def _q(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    def list_labels(self, full_name: str) -> list[dict]:
        owner, repo = full_name.split("/", 1)
        return [{"name": item["name"], "color": item.get("color", ""), "description": item.get("description") or ""}
                for item in self.paginate(f"/repos/{self._q(owner)}/{self._q(repo)}/labels")]

    def list_org_repos(self, org: str) -> list[dict]:
        return self.paginate(f"/orgs/{self._q(org)}/repos?type=all&sort=full_name")

    def apply(self, full_name: str, action: Action) -> None:
        owner, repo = full_name.split("/", 1)
        base = f"/repos/{self._q(owner)}/{self._q(repo)}/labels"
        if action.kind == "create":
            self.request("POST", base, action.payload)
        elif action.kind in ("update", "rename"):
            self.request("PATCH", f"{base}/{self._q(action.current)}", action.payload)
        elif action.kind == "delete":
            self.request("DELETE", f"{base}/{self._q(action.current)}")
        else:  # pragma: no cover - plan() only creates the kinds above
            raise ValueError(action.kind)


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------

def _targets(client: GitHubClient, args: argparse.Namespace, out) -> list[str]:
    if args.repo:
        return [args.repo]
    repos = client.list_org_repos(args.org)
    targets = []
    for repo in repos:
        name = repo["full_name"]
        if repo.get("archived"):
            print(f"skip    {name} (archived)", file=out)
        elif repo.get("fork") and not args.include_forks:
            print(f"skip    {name} (fork; use --include-forks)", file=out)
        else:
            targets.append(name)
    return targets


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sync labels.yml to GitHub repositories (dry run unless --apply).")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--org", help="every non-archived repository of this organization, e.g. luminare-dev")
    target.add_argument("--repo", help="one repository, e.g. luminare-dev/.github")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="labels file (default: labels.yml next to scripts/)")
    p.add_argument("--apply", action="store_true", help="make the changes (needs a token)")
    p.add_argument("--prune", action="store_true", help="also delete labels that are not in labels.yml")
    p.add_argument("--include-forks", action="store_true", help="with --org: also sync forked repositories")
    p.add_argument("--token-env", default="GITHUB_TOKEN", help="environment variable that holds the token (default: GITHUB_TOKEN)")
    p.add_argument("--api-url", default=API_URL, help=argparse.SUPPRESS)
    p.add_argument("--fail-on-changes", action="store_true", help="dry run: exit 1 if any change is pending (for CI)")
    return p


def main(argv: list[str] | None = None, opener: Opener | None = None, env: dict | None = None, out=None) -> int:
    out = out or sys.stdout
    env = os.environ if env is None else env
    args = build_parser().parse_args(argv)
    if args.repo and not _REPO_RE.match(args.repo):
        print(f"error: --repo must look like owner/name, got {args.repo!r}", file=sys.stderr)
        return 2
    if args.org and not _OWNER_RE.match(args.org):
        print(f"error: --org must be an organization login, got {args.org!r}", file=sys.stderr)
        return 2
    try:
        desired = load_labels(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    token = env.get(args.token_env) or None
    if args.apply and not token:
        print(f"error: --apply needs a token in the environment variable {args.token_env}", file=sys.stderr)
        return 2
    if args.fail_on_changes and args.apply:
        print("error: --fail-on-changes is for dry runs; do not combine it with --apply", file=sys.stderr)
        return 2
    try:
        client = GitHubClient(token=token, api_url=args.api_url, opener=opener)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not token:
        print(f"note: no token in {args.token_env}; read-only and limited to public repositories", file=out)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{mode}: {len(desired)} labels from {args.config.name}" + (" (with --prune)" if args.prune else ""), file=out)
    failures = 0
    pending = 0
    try:
        targets = _targets(client, args, out)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not targets:
        print("no repositories to sync", file=out)
    for full_name in targets:
        try:
            current = client.list_labels(full_name)
        except ApiError as exc:
            failures += 1
            print(f"error   {full_name}: {exc}", file=out)
            continue
        actions, notes = plan(desired, current, prune=args.prune)
        counts = {k: sum(1 for a in actions if a.kind == k) for k in ("create", "update", "rename", "delete")}
        summary = ", ".join(f"{v} to {k}" for k, v in counts.items())
        print(f"{full_name}: " + (summary if actions else "up to date"), file=out)
        for note in notes:
            print(f"  note: {note}", file=out)
        for action in actions:
            if args.apply:
                try:
                    client.apply(full_name, action)
                    print(f"  done    {action.describe()}", file=out)
                except ApiError as exc:
                    failures += 1
                    print(f"  FAILED  {action.describe()}: {exc}", file=out)
            else:
                pending += 1
                print(f"  would   {action.describe()}", file=out)
    if not args.apply and pending:
        print("DRY RUN: nothing was changed. Re-run with --apply to make these changes.", file=out)
    if failures:
        print(f"{failures} API call(s) failed", file=out)
        return 1
    if args.fail_on_changes and pending:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
