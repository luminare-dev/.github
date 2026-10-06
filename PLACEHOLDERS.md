# Placeholders

Values that are left open on purpose. Fill each one in before the first push; the check in
`scripts/check_public_text.py` lists any `{{…}}` that is still present.

| Placeholder | Where | Fill with |
|---|---|---|
| `{{AUTHOR_NAME}}` | `LICENSE` (copyright line), `NOTICE` (copyright line) | The copyright holder, a natural person. Use the same form of the name in every repository. |

## Values to confirm (not placeholders)

| Value | Where | Why |
|---|---|---|
| `lint-test`, `gitleaks`, `DCO` | `rulesets/main.json` (required status checks) | They must match the check names that the CI workflows and the DCO app report in each repository. A required check that never runs blocks every merge. |
| Branch `main` | `profile/README.md` (header image URLs) | The images load from `raw.githubusercontent.com/luminare-dev/.github/main/docs/brand/`. |
| `https://luminare.tech` | `profile/README.md` | The link should answer before the profile goes public. |
| `oss@`, `conduct@`, `security@luminare.tech` | profile, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` | The addresses must receive mail before the first push (`SETTINGS.md`, section 5). |
| Organization Discussions | issue chooser, `SUPPORT.md`, `CONTRIBUTING.md`, profile | The links point to `https://github.com/orgs/luminare-dev/discussions`, which exists only after organization Discussions are turned on (`SETTINGS.md`, section 2). |
