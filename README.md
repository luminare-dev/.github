<!-- header:begin: brand header and byline; scripts/set_byline.py switches the byline variant -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/readme-header-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/brand/readme-header-light.svg">
  <img alt="Luminare Development" src="docs/brand/readme-header-light.svg">
</picture>

<!-- byline:studio -->
*a [Luminare Development](https://luminare.tech/open-source/) open-source project*
<!-- /byline:studio -->
<!-- byline:personal
*by {{AUTHOR_NAME}} · [project page](https://luminare.tech/open-source/)*
/byline:personal -->
<!-- header:end -->

# .github

Default community health files, issue forms and shared labels for every repository in the
[luminare-dev](https://github.com/luminare-dev) organization, plus the organization's public
profile.

GitHub uses a file from this repository for any repository of the organization that does not have
its own file of the same type
([docs](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)).
A change here therefore changes every repository that relies on the default.

## What is in here

| File | Effect | Override in a project repository |
|---|---|---|
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Contributor Covenant 3.0; reports to <conduct@luminare.tech> | its own `CODE_OF_CONDUCT.md` |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Conventional Commits, DCO sign-off, issue before a large pull request, no secrets in issues | its own `CONTRIBUTING.md` |
| [`SECURITY.md`](SECURITY.md) | latest minor version supported; private vulnerability reporting first, <security@luminare.tech> as fallback; acknowledgement within 14 days, best effort | its own `SECURITY.md` |
| [`SUPPORT.md`](SUPPORT.md) | public issues and Discussions only, best effort | its own `SUPPORT.md` |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE) | bug report and feature request forms, blank issues off, links to Discussions and the security policy | **any** file in its own `.github/ISSUE_TEMPLATE/` replaces this whole folder |
| [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) | checklist: Conventional Commit title, sign-off, tests, no secrets | its own pull request template |
| [`.github/VULNERABILITY_REPORT.yml`](.github/VULNERABILITY_REPORT.yml) | fields of the private vulnerability report form | its own `.github/VULNERABILITY_REPORT.yml` |
| [`profile/README.md`](profile/README.md) | the organization's public profile page | — |
| [`labels.yml`](labels.yml), [`scripts/sync_labels.py`](scripts/sync_labels.py) | shared triage labels and the script that syncs them | — |
| [`rulesets/main.json`](rulesets/main.json) | branch ruleset to import into each repository | — |
| [`SETTINGS.md`](SETTINGS.md) | checklist for the organization, account and repository settings | — |
| [`.github/workflows/`](.github/workflows), [`scripts/`](scripts) | CI for this repository only (not inherited): the template's checks for wording, byline, workflow pins, YAML, Markdown, tests, secrets and the pull request title | — |

Licences cannot be inherited: every repository has its own `LICENSE`, and its own `README.md`.
There is deliberately no funding file here, because it would add a Sponsor button to every <!-- rule-text -->
repository. <!-- rule-text -->

## Labels

`labels.yml` defines the shared labels: `type: …`, `priority: …`, `status: …` (including
`status: needs-info`), `good first issue`, `help wanted`, and the labels that Dependabot and the
release tooling use. The issue forms set `type: bug`, `type: feature` and `status: triage`, so
those labels must exist in every repository, including this one.

`scripts/sync_labels.py` needs only Python 3.10 or later, no packages:

```bash
python scripts/sync_labels.py --repo luminare-dev/.github          # dry run: shows what would change
python scripts/sync_labels.py --org luminare-dev                   # dry run for every repository
GITHUB_TOKEN=... python scripts/sync_labels.py --org luminare-dev --apply
```

- **Dry run by default.** Nothing is written without `--apply`, and `--apply` needs a token in
  `GITHUB_TOKEN` (or the variable named by `--token-env`). Use a fine-grained token limited to the
  organization's repositories with the permission *Issues: read and write*.
- **Idempotent.** It creates missing labels and updates colour or description where they differ.
  A label listed under `aliases` (for example GitHub's default `bug`) is renamed instead of
  duplicated, so existing issues keep it. A second run reports "up to date".
- **Never deletes** unless `--prune` is given; then labels that are not in `labels.yml` are
  removed (shown first in the dry run).
- Archived repositories are skipped; forks only with `--include-forks`.
- `--fail-on-changes` makes a dry run exit with 1 when something is out of sync.

On Windows (PowerShell): `$env:GITHUB_TOKEN = "..."; py scripts\sync_labels.py --org luminare-dev --apply`.

## Ruleset

[`rulesets/main.json`](rulesets/main.json) is a repository ruleset in the format GitHub exports
and imports (Settings → Rules → Rulesets → New ruleset → Import a ruleset). It targets the
default branch and requires a pull request (no approval needed, conversations resolved, squash
merge only) and the status checks `ci / lint-test`, `secrets / gitleaks`, `pr / pr-title` and
`DCO`; it blocks force-pushes and deletion, with no bypass. Organization-wide rulesets need GitHub
Team or Enterprise, so it is imported per repository. Read [SETTINGS.md](SETTINGS.md), section 3,
before importing: the check names must match checks that actually run in that repository.

## Development

CI runs on every pull request and push to `main` with the same workflows and checks as the
repositories built from the organization's template (`luminare-dev/oss-template`); they report
`ci / lint-test`, `secrets / gitleaks` and `pr / pr-title`. Run the checks before every pull
request (Python standard library only):

```bash
python3 -m unittest discover -s tests -v            # schema tests skip without the dev tools
python3 scripts/forbidden_words.py --template-mode  # wording, names, e-mail addresses, listed placeholders
python3 scripts/set_byline.py verify                # README byline, docs/brand/ and NOTICE agree
python3 scripts/check_workflows.py                  # SHA pins, permissions, triggers
```

With the development tools (`requirements-dev.txt`, hash-pinned) in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install --require-hashes --only-binary=:all: -r requirements-dev.txt   # Windows: .venv\Scripts\pip ...
.venv/bin/yamllint --strict .
.venv/bin/zizmor --offline --min-severity=low .github/workflows
.venv/bin/python scripts/validate.py          # forms, chooser config, ruleset against their schemas
.venv/bin/python -m unittest discover -s tests -v
```

CI also runs markdownlint (`.markdownlint-cli2.jsonc`) and actionlint.

`scripts/validate.py` downloads the SchemaStore schemas `github-issue-forms` and
`github-issue-config` and the ruleset request schema from GitHub's OpenAPI description once into
`.cache/schemas/` (git-ignored). Right before the first push, run
`python3 scripts/forbidden_words.py` without `--template-mode`. This is the publish gate that CI
runs too: it also fails while a placeholder from [PLACEHOLDERS.md](PLACEHOLDERS.md) is still open.
Reviewed exceptions to the wording check are listed in `.forbidden-words-allow`, each with a
reason.

### Files copied from the template

`scripts/forbidden_words.py`, `scripts/set_byline.py`, `scripts/check_workflows.py`,
`scripts/check_pr_title.py`, `.github/workflows/pr-title.yml`,
`.github/workflows/reusable-ci.yml`, `.github/workflows/reusable-gitleaks.yml` and
`.gitleaks.toml` are byte-for-byte copies from `luminare-dev/oss-template`, so this repository
follows the same rules as every other one. `tests/test_template_copies.py` records the source
commit and pins each file's sha256. `.github/workflows/ci.yml` differs from the template only in
its test command. To update, copy the files again from the template, then update the commit and
the hashes in that test.

## Licence

Everything in this repository is licensed under the [MIT licence](LICENSE), except:

- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), adapted from the
  [Contributor Covenant 3.0](https://www.contributor-covenant.org/version/3/0/) and licensed under
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/);
- the Luminare name, logo and the files in `docs/brand/`, which are not licensed (see [NOTICE](NOTICE)).
