# Contributing

This applies to every [luminare-dev](https://github.com/luminare-dev) repository without its own
`CONTRIBUTING.md`.

- Questions and ideas go to [Discussions](https://github.com/orgs/luminare-dev/discussions).
  Security problems go through [SECURITY.md](https://github.com/luminare-dev/.github/blob/main/SECURITY.md), never in public.
- Please open an issue before a large change (new feature, new dependency, changed behaviour or
  interface). Small fixes can go straight to a pull request.
- Each repository's README explains how to run its tests. Run them before you push.

## Pull requests

Pull requests are squash-merged, so the title becomes the commit message and a changelog line.
It must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
lower-case imperative summary, no full stop, at most 100 characters.

```text
fix(backup): retry the upload after a timeout
```

`feat` makes a minor release, `fix`, `perf`, `security` and `revert` a patch release; `docs`,
`refactor`, `test`, `style`, `build`, `ci` and `chore` do not release on their own. A breaking
change adds `!` (`feat!: ...`). Do not edit `CHANGELOG.md`; release-please writes it.

Keep one topic per pull request. Add or update tests and docs for every behaviour change.

## Sign-off (DCO)

Every commit needs a `Signed-off-by` line (`git commit -s`), which certifies the
[Developer Certificate of Origin](https://developercertificate.org/). Forgot it? Run
`git rebase --signoff main` and force-push your branch. There is no CLA; your contribution is
licensed under the repository's licence.

## No secrets or personal data

Issues, pull requests, logs and screenshots are public. Never post passwords, tokens, keys,
`.env` files, IP addresses, hostnames or user data; use placeholders like `<redacted>`. If you
leaked a secret, rotate it right away.

## Response times

Replies are best effort, usually within a week. Everyone follows the
[Code of Conduct](https://github.com/luminare-dev/.github/blob/main/CODE_OF_CONDUCT.md).
