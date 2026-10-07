# Contributing

Thank you for helping. This guide applies to every repository in
[luminare-dev](https://github.com/luminare-dev) that does not have its own `CONTRIBUTING.md`.
If a repository has one, that file wins.

## Before you start

- **Questions and ideas** go to [Discussions](https://github.com/orgs/luminare-dev/discussions),
  not to issues.
- **Security problems** are never reported in public. Follow [SECURITY.md](https://github.com/luminare-dev/.github/blob/main/SECURITY.md).
- **Search first.** Look through the open and closed issues of the repository before you open a new one.
- **Open an issue before a large pull request.** Large means a new feature, a change in behaviour,
  a new dependency, a change to a public interface (variables, role defaults, metrics, file
  formats), or more than about 100 changed lines. Agreeing on the approach first saves you work.
  Typo fixes, documentation fixes and small, obvious bug fixes can go straight to a pull request.

## Development setup and tests

Every repository explains its own setup in the **Development** section of its `README.md` (or in
its own `CONTRIBUTING.md`, if it has one). That section names:

- the tools and versions you need;
- the one command that runs the linters and tests (the same command CI runs);
- any extra checks, for example Molecule scenarios or rule tests.

Run that command before you push. A pull request is reviewed once CI is green. For contributors
outside the organization, a maintainer starts the CI run after a first look.

## Commit messages: Conventional Commits

Commit messages and pull request titles follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/). Release notes and
version numbers are generated from them, so the type matters.

```text
<type>(<optional scope>): <short summary in the imperative>

<optional body: what and why>

Signed-off-by: Your Name <you@example.com>
```

| Type | Use it for | Changelog section | Release effect |
|---|---|---|---|
| `feat` | a new feature | Added | minor version |
| `fix` | a bug fix | Fixed | patch version |
| `perf` | a performance improvement without a change in behaviour | Changed | patch version |
| `security` | the fix for a security problem, used once the advisory is public | Security | patch version |
| `revert` | reverting an earlier commit | Reverted | patch version |
| `docs` | documentation only | not listed | no release on its own |
| `refactor`, `test`, `style` | code changes that do not change behaviour | not listed | no release on their own |
| `build`, `ci`, `chore` | build system, CI, maintenance | not listed | no release on their own |

A breaking change adds `!` after the type (`feat!: drop support for …`) or a
`BREAKING CHANGE:` footer. It means a major version, or a minor version before 1.0.0. The
sections and release effects are those of the release tooling (release-please) in repositories
built from the organization's template.

Pull requests are squash-merged, so **the pull request title becomes the commit message** and must
follow the same format. The `pr / pr-title` check also requires:

- the summary starts with a lower-case letter (an acronym such as `TLS` is fine) and uses the
  imperative: "add", not "added";
- no full stop at the end;
- at most 100 characters for the whole title;
- a scope, if any, in lower case;
- wording that describes the change only: the title becomes a line of the release notes, so it
  goes through the same wording check as the repository's files.

Do not edit `CHANGELOG.md` by hand; the release tooling writes it.

## Developer Certificate of Origin (DCO)

Every commit must be signed off. The sign-off certifies that you wrote the change or otherwise
have the right to submit it under the project's licence, as described in the
[Developer Certificate of Origin 1.1](https://developercertificate.org/).

```bash
git commit -s -m "fix(scope): correct the retry delay"
```

`-s` adds a line like `Signed-off-by: Your Name <you@example.com>` with the name and email from
your Git configuration. Use your real name or a known identity; anonymous sign-offs cannot be
accepted. You may use your GitHub `noreply` email address.

- **Forgot the sign-off on the last commit?** `git commit --amend --no-edit -s`, then
  `git push --force-with-lease` to your branch.
- **On several commits?** `git rebase --signoff main`, then `git push --force-with-lease`.

A DCO check runs on every pull request. There is no Contributor License Agreement.

**Inbound = outbound.** Your contribution is licensed under the same licence as the repository you
contribute to (see its `LICENSE` file). You keep your copyright.

You are responsible for everything you submit, including code produced with tools or generators.
Only submit code you have the right to license this way. Do not copy code from projects whose
licence is incompatible with the repository's licence.

## Pull requests

- One topic per pull request. Keep unrelated refactoring out.
- Add or update tests for every behaviour change, and update the documentation in the same pull
  request.
- Fill in the pull request template. Link the issue it closes (`Closes #123`).
- Be ready for review comments. A maintainer may push small fixes to your branch if you allow edits
  from maintainers.

## Never post secrets or personal data

Issues, discussions, pull requests, logs, screenshots and test fixtures are public. **Never
include:**

- passwords, API tokens, SSH or TLS private keys, licence keys or server keys;
- `.env` files, vault passwords or unredacted configuration files;
- public IP addresses, internal hostnames or tenant IDs;
- player or user data: names, account identifiers, IP addresses, chat logs.

Replace each value with a placeholder such as `<redacted>` or `203.0.113.10` (a documentation
address). If you posted a secret by accident, **revoke or rotate it at once**. Deleting or editing
the post does not remove copies that were already sent in notifications.

## Response times

Maintainers aim to give a first reply to new issues and pull requests within 7 days. This is best
effort, not a guarantee. Please do not ping repeatedly; a polite bump after 14 days is fine.

## Code of Conduct

Everyone who takes part follows the [Code of Conduct](https://github.com/luminare-dev/.github/blob/main/CODE_OF_CONDUCT.md). Report problems to
<conduct@luminare.tech>.
