# Settings checklist

Manual settings for the organization [luminare-dev](https://github.com/luminare-dev), the
maintainer's personal account and every public repository. None of this can be stored in a file
that GitHub reads, so it is a checklist. Work through it top to bottom and tick each box.

The links to GitHub's documentation were checked on 2026-10-06. Items marked ⚠ need a check in
the GitHub interface, because the documentation does not settle them.

## 0. Before the first push of this repository

- [ ] The role addresses receive mail (section 5): `oss@luminare.tech`, `conduct@luminare.tech`,
      `security@luminare.tech`, all aliases of the one `hello@luminare.tech` inbox. The code of
      conduct, security policy and profile name them.
- [ ] Every placeholder in [PLACEHOLDERS.md](PLACEHOLDERS.md) is filled in.
- [ ] `https://luminare.tech` answers; the organization profile links to it.
- [ ] Sections 1 and 2 are done (at least two-factor authentication and the Actions policy).
- [ ] Create the **public** repository `.github` in `luminare-dev` without a generated README,
      licence or `.gitignore`, then push this repository. The default branch must be `main`,
      because the profile header uses `raw.githubusercontent.com/luminare-dev/.github/main/...`.
- [ ] Section 3 for this repository, then the acceptance tests in section 4.

## 1. Personal account

- [ ] **Two-factor authentication:** a passkey as the main method plus an authenticator app as a
      backup. No SMS. ([docs](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa))
- [ ] **Recovery codes** downloaded and kept offline (printed, or in an offline password
      manager), never on a server or in a repository.
- [ ] **Email privacy:** Settings → Emails → *Keep my email addresses private* and *Block command
      line pushes that expose my email*. Commits use the GitHub `noreply` address
      (`<id>+<login>@users.noreply.github.com`).
- [ ] **SSH commit signing** (Git 2.34 or later). On your own computer:

      ```bash
      ssh-keygen -t ed25519 -C "git commit signing" -f ~/.ssh/id_ed25519_signing
      git config --global gpg.format ssh
      git config --global user.signingkey ~/.ssh/id_ed25519_signing.pub
      git config --global commit.gpgsign true
      git config --global tag.gpgsign true
      ```

      Then GitHub → Settings → SSH and GPG keys → **New SSH key** → key type **Signing Key**, and
      paste the `.pub` file (or `gh ssh-key add ~/.ssh/id_ed25519_signing.pub --type signing`).
      A key used for both login and signing must be added twice, once per type. Check that the
      next pushed commit shows **Verified**. On a shared or server machine, set these options per
      repository (`git config` without `--global`) instead.
      ([docs](https://docs.github.com/en/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key))
- [ ] Optional: **vigilant mode** (Settings → SSH and GPG keys) marks unsigned commits as
      *Unverified*.
- [ ] **Push protection for yourself** is on (Settings → Code security). It is on by default and
      blocks secrets in pushes to any public repository.
- [ ] No GitHub Sponsors profile. <!-- rule-text -->

## 2. Organization `luminare-dev`

**Plan:** Free. Organization-wide rulesets need GitHub Team or Enterprise
([docs](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization)),
so the branch ruleset is imported per repository (section 3).

### Profile (Settings → General)

- [ ] Display name **Luminare Development**, URL `https://luminare.tech`. Leave the public email
      empty, or set `oss@luminare.tech` once it receives mail.
- [ ] Optional: verify the domain `luminare.tech` (Settings → Verified and approved domains; one
      DNS TXT record). The profile then shows a *Verified* badge.

### People and security

- [ ] Owner role for the maintainer's personal account. A single owner is a single point of
      failure: keep that account's recovery codes safe.
- [ ] Authentication security: **Require two-factor authentication** and **Only allow secure
      two-factor methods**.
      ([docs](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-two-factor-authentication-for-your-organization/requiring-two-factor-authentication-in-your-organization))
- [ ] Member privileges: base permission **Read**; members cannot create, delete, transfer or
      change the visibility of repositories; forking of private repositories off.

### Actions (Settings → Actions → General)

[Documentation](https://docs.github.com/en/organizations/managing-organization-settings/disabling-or-limiting-github-actions-for-your-organization)

- [ ] Policy **Allow luminare-dev, and select non-luminare-dev, actions and reusable workflows**,
      with **Allow actions created by GitHub** ticked (it covers `actions/*` and `github/*`) and
      the third-party actions of the template workflows listed explicitly:
      `googleapis/release-please-action@*, ossf/scorecard-action@*, DavidAnson/markdownlint-cli2-action@*`.
      When a template workflow adds a third-party action, add it here.
- [ ] **Require actions to be pinned to a full-length commit SHA.**
- [ ] Fork pull request workflows: **Require approval for all external contributors**.
- [ ] Workflow permissions: **Read repository contents and packages permissions**, and tick
      **Allow GitHub Actions to create and approve pull requests** (release-please opens its
      release pull request with `GITHUB_TOKEN`; each workflow asks for write permissions per
      job). New organizations do not allow this by default, and new repositories inherit the
      organization's setting.

### Code security (Settings → Advanced Security → Configurations)

- [ ] Apply one security configuration to all repositories, and as the default for new ones:
      Dependabot alerts and security updates, secret scanning, push protection, private
      vulnerability reporting. Secret scanning and push protection are free for public
      repositories, not for private ones
      ([docs](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security));
      private repositories rely on the gitleaks check in CI.

### Community

- [ ] **Discussions** for the organization, with `.github` as the source repository, categories
      *Announcements*, *Q&A*, *Ideas* and *Show and tell*. The issue chooser and `SUPPORT.md`
      link to `https://github.com/orgs/luminare-dev/discussions`. The forms in
      `.github/DISCUSSION_TEMPLATE/` are named after the category slugs (`q-a.yml`, `ideas.yml`);
      keep the default category names, or rename the files to match.
- [ ] Install the **DCO** app (`https://github.com/apps/dco`, app ID 1861) for all repositories.
      Its check is called `DCO`.
- [ ] No Sponsors profile for the organization, and no `FUNDING.yml` in this repository: <!-- rule-text -->
      such a file would add a Sponsor button to every repository. <!-- rule-text -->
- [ ] Default branch name for new repositories: `main`.

## 3. Every public repository

### General

- [ ] `LICENSE` with an SPDX licence, `NOTICE`, and a README built from the template.
- [ ] Description, website (the project page), topics. Platform names belong in the description
      and topics, never in the repository name.
- [ ] Social preview: upload `docs/brand/social-preview-1280x640.png` (Settings → General).
- [ ] Features: Issues on; Wiki off; Projects off unless used; **Sponsorships unticked**. <!-- rule-text -->
      Discussions: the organization's Discussions by default; a repository's own Discussions
      only for projects that need their own space (the Ansible collections and the observability
      pack).
- [ ] Pull requests: **Allow squash merging** only, default message **Pull request title and
      commit details** (keeps the `Signed-off-by` lines), *Always suggest updating pull request
      branches* and *Automatically delete head branches* on.
- [ ] Releases: turn on **immutable releases** (tags and assets cannot change after
      publication). The template's release workflow creates a draft release, attaches every file
      and publishes last, which is the order immutable releases need.
- [ ] Release pull requests: **close and reopen** each one once before merging. Pull requests
      opened with `GITHUB_TOKEN` start no workflows, so the required checks would never report
      (template `PUBLISHING.md`, part C).

### Security (Settings → Advanced Security)

- [ ] Private vulnerability reporting **on**.
      ([docs](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository))
- [ ] Dependabot alerts and security updates **on**.
- [ ] Secret scanning and **push protection on**.
- [ ] Code scanning default setup on, where the repository contains a supported language.

### Branch ruleset (Settings → Rules → Rulesets → New ruleset → Import a ruleset)

- [ ] Import [`rulesets/main.json`](rulesets/main.json). It protects the default branch: pull
      request required (0 approvals, so a single maintainer can merge; conversations resolved;
      squash only), required status checks, no force-push, no deletion, no bypass.
- [ ] Before importing, make sure each required check name matches a check that already ran on
      a pull request in that repository: `ci / lint-test`, `secrets / gitleaks` and
      `pr / pr-title` (GitHub Actions, app ID 15368) and `DCO` (app ID 1861). Reusable workflows
      report as `<caller job> / <called job>`; renaming the caller jobs in `ci.yml` or
      `pr-title.yml` changes these names. Edit the names in the ruleset form if a repository's
      CI jobs are named differently. A required check that never reports blocks every merge, so
      in a repository without these workflows, remove the *Require status checks to pass* rule
      in the form and add it back once the checks have run.

### Labels and triage

- [ ] Run `python scripts/sync_labels.py --repo luminare-dev/<repo>` (dry run), then again with
      `--apply` (README.md, "Labels").
- [ ] Watch the repository (Custom: Issues, Pull requests, Discussions, Security alerts) with
      email notifications on. Target: a first reply within 7 days.
- [ ] Look at the Actions tab once a month: GitHub disables scheduled workflows in public
      repositories after 60 days without activity.

## 4. Acceptance tests (manual)

Run these once after the first push, in the organization:

1. **Defaults apply.** Create an empty public test repository (README only) in `luminare-dev`.
   Insights → Community standards lists the code of conduct, contributing guide, security policy,
   support file, issue templates and pull request template from `.github`, and the repository
   shows an *Accessibility* tab. Licence and README are per repository by design.
2. **Issue chooser.** *New issue* in the test repository shows *Bug report*, *Feature request*
   and the two contact links. A non-member sees no blank issue.
3. **No Sponsor button** on any repository. <!-- rule-text -->
4. **Push protection.** On a scratch branch of the test repository, commit a test token and
   push: the push must be rejected by push protection. Do not bypass the block. Use a
   fine-grained personal access token with no repository access, no permissions and a 1-day
   expiry, and revoke it right after the test. A random made-up string may not be detected,
   because GitHub tokens contain a checksum. Afterwards reset the scratch branch.
5. **Discussion forms.** *New discussion* → *Q&A* and *Ideas* in the organization's Discussions
   show the fields from `.github/DISCUSSION_TEMPLATE/`, including the redaction checkbox.
6. **Private reporting.** *Security → Report a vulnerability* in the test repository (with private
   reporting on) shows the fields from `.github/VULNERABILITY_REPORT.yml`.
7. **DCO.** A test pull request with a commit without `-s` fails the `DCO` check; after
   `git commit --amend -s` and a force-push to the branch, the check passes.
8. **Ruleset.** A direct push and a force-push to `main` are both rejected.
9. **Profile.** `https://github.com/luminare-dev` shows the header in light and dark mode, the
   project table and working links.

Delete the test repository after the last test.

## 5. Role addresses

All addresses deliver into **one inbox**, `hello@luminare.tech`, which only the maintainer reads.
The role addresses are aliases of it, so a report never depends on a second mailbox. They are
created on the `luminare.tech` mail server by the maintainer, then tested by sending a message
from an outside address to each one.

| Address | Type | Delivers to | Used in |
|---|---|---|---|
| `hello@luminare.tech` | mailbox | the maintainer | general contact on the studio website |
| `oss@luminare.tech` | alias | `hello@luminare.tech` | profile, `SUPPORT.md`, `ACCESSIBILITY.md` |
| `conduct@luminare.tech` | alias | `hello@luminare.tech` | `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SUPPORT.md` |
| `security@luminare.tech` | alias | `hello@luminare.tech` | `SECURITY.md` (fallback) |

Mail to these addresses is never answered with private support; see `SUPPORT.md`.
