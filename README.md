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
*by Paul Pasaurek · [project page](https://luminare.tech/open-source/)*
/byline:personal -->
<!-- header:end -->

# .github

Default community health files, issue forms and shared labels for the
[luminare-dev](https://github.com/luminare-dev) repositories, plus the organization profile.
GitHub uses these files for any repository that has no file of its own
([docs](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)).

## Contents

- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md),
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [ACCESSIBILITY.md](ACCESSIBILITY.md)
- `.github/`: issue and discussion forms, the pull request template, the vulnerability report form
- `profile/README.md`: the organization profile
- `labels.yml` and `scripts/sync_labels.py`: shared labels
- `rulesets/main.json`: branch ruleset to import per repository (Settings → Rules → Rulesets → Import)

## Labels

`scripts/sync_labels.py` needs Python 3.10+ and no packages. It is a dry run unless `--apply`
is given, and it only deletes labels with `--prune`.

```bash
python scripts/sync_labels.py --org luminare-dev                   # dry run
GITHUB_TOKEN=... python scripts/sync_labels.py --org luminare-dev --apply
```

The token needs *Issues: read and write* on the target repositories.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 scripts/forbidden_words.py
python3 scripts/set_byline.py verify
python3 scripts/check_workflows.py
```

`scripts/validate.py` checks the forms and the ruleset against their schemas and needs the tools
from `requirements-dev.txt`. Some scripts and workflows are copies from
`luminare-dev/oss-template`; `tests/test_template_copies.py` pins their hashes.

## Licence

[MIT](LICENSE), except `CODE_OF_CONDUCT.md` (Contributor Covenant 3.0,
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)) and the Luminare name, logo and
`docs/brand/` files, which are not licensed (see [NOTICE](NOTICE)).
