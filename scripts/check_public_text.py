#!/usr/bin/env python3
"""Pre-publication text checks for this repository (Python standard library only).

Fails (exit 1) on:
  * a FUNDING.yml / FUNDING.yaml file anywhere (it would add a Sponsor button to every  (rule-text)
    repository of the organization);
  * offer, price or funding wording in any text file (list below), except on lines  (rule-text)
    marked as quoted rule text with the marker "rule-text" (in an HTML or code comment on the
    same line);
  * an email address other than the role addresses and documentation examples;
  * a placeholder in double braces that PLACEHOLDERS.md does not list.
With --strict it also fails while any placeholder is still unfilled (use it right before the push).

Usage: python scripts/check_public_text.py [--strict] [ROOT]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".cache", "__pycache__", ".venv", "node_modules"}
TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".py", ".txt", ".svg", ".toml", ".cfg", ".ini", ".sh", ".ps1"}
TEXT_NAMES = {"LICENSE", "NOTICE", ".gitignore", "KIT_VERSION"}
MARKER = "rule-text"

# Case-insensitive, whole words. Plan rule list (English); the template repository adds German.  # rule-text
FORBIDDEN = [  # rule-text
    r"\bprices?\b", r"\bpricing\b", "€", r"\bEUR\b", r"\bhire\b", r"\bhiring\b", r"\bbuy\b",  # rule-text
    r"\bpro\s+version\b", r"\bpremium\b", r"\bsponsor\w*", r"\bdonat\w*", r"\bcoming\s+soon\b",  # rule-text
    r"\btebex\b", r"\bstore\b", r"\bshop\b", r"\bwait-?list\b", r"\baffiliates?\b",  # rule-text
    r"\bpatreon\b", r"\bko-?fi\b", r"\bopen\s*collective\b", r"\bavailable\s+for\s+(projects|hire|freelance)",  # rule-text
]  # rule-text
FORBIDDEN_RE = re.compile("|".join(f"(?:{p})" for p in FORBIDDEN), re.IGNORECASE)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_EMAILS = {"oss@luminare.tech", "conduct@luminare.tech", "security@luminare.tech", "you@example.com"}
ALLOWED_EMAIL_DOMAINS = ("@users.noreply.github.com",)
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES):
            yield path


def check(root: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if re.fullmatch(r"funding\.ya?ml", path.name, re.IGNORECASE):
            errors.append(f"{rel}: FUNDING file must not exist")  # rule-text
    listed = set()
    placeholders_md = root / "PLACEHOLDERS.md"
    if placeholders_md.exists():
        listed = set(PLACEHOLDER_RE.findall(placeholders_md.read_text(encoding="utf-8")))
    for path in iter_text_files(root):
        rel = path.relative_to(root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            errors.append(f"{rel}: not UTF-8 text")
            continue
        for no, line in enumerate(lines, start=1):
            if MARKER not in line:
                for m in FORBIDDEN_RE.finditer(line):
                    errors.append(f"{rel}:{no}: forbidden wording {m.group(0)!r}")
            for m in EMAIL_RE.finditer(line):
                addr = m.group(0)
                if addr in ALLOWED_EMAILS or addr.endswith(ALLOWED_EMAIL_DOMAINS):
                    continue
                errors.append(f"{rel}:{no}: email address {addr!r} is not an allowed role or example address")
            if rel.name == "PLACEHOLDERS.md":
                continue
            for name in PLACEHOLDER_RE.findall(line):
                if name not in listed:
                    errors.append(f"{rel}:{no}: placeholder {{{{{name}}}}} is not listed in PLACEHOLDERS.md")
                elif strict:
                    errors.append(f"{rel}:{no}: placeholder {{{{{name}}}}} is not filled in")
                else:
                    warnings.append(f"{rel}:{no}: placeholder {{{{{name}}}}} still open")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--strict", action="store_true", help="also fail on unfilled placeholders")
    p.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = p.parse_args(argv)
    errors, warnings = check(args.root.resolve(), strict=args.strict)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
