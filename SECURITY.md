# Security policy

This policy applies to every repository in [luminare-dev](https://github.com/luminare-dev) that
does not have its own `SECURITY.md`.

## Supported versions

Security fixes go into the **latest minor release** of each project. Older minor and major
versions do not get fixes; please upgrade first and check whether the problem still exists.

| Version | Security fixes |
|---|---|
| Latest minor release (for example 1.4.x while 1.4 is current) | Yes |
| Any older release | No |
| Unreleased `main` branch | Fixed before the next release |

Before 1.0.0 the same rule applies: only the latest 0.x minor release is supported.

## Reporting a vulnerability

**Do not open a public issue, discussion or pull request for a security problem.**

1. **Preferred: GitHub private vulnerability reporting.** Open the affected repository, go to the
   **Security** tab and click **Report a vulnerability**. The direct link is
   `https://github.com/luminare-dev/<repository>/security/advisories/new`. Only the maintainers can
   see the report.
2. **Fallback: email security@luminare.tech**, if private reporting is not available for that
   repository or you cannot use GitHub. Name the repository in the subject line.

Please include:

- the repository and the version, tag or commit you tested;
- what the problem is and what an attacker could do with it;
- the steps to reproduce it, as small as possible;
- whether the issue is already public or known to others.

Redact real secrets, IP addresses, hostnames and personal data in your report. Use placeholders
instead; the maintainers will ask if they need more.

## What happens next

- **Acknowledgement:** best effort within 14 days.
- **Assessment and fix:** the maintainers confirm the problem, prepare a fix in a private fork
  where possible and agree on a disclosure date with you. A typical target is 90 days or less
  after the report.
- **Disclosure:** a GitHub security advisory is published with the fixed release, and a CVE is
  requested through GitHub when appropriate. You are credited in the advisory unless you prefer
  not to be.

There is no bug bounty programme, and reports are not rewarded.

## Out of scope

- Vulnerabilities in third-party software that a project only installs, configures or monitors.
  Please report those to the upstream project.
- Findings that need an already compromised host, or physical access, without showing a weakness
  in the project itself.
- Automated scanner output without a demonstrated impact.

## A secret was committed by mistake

If you find a credential, token or key in any repository or its history, report it privately in
the same way. Do not copy it into a public place.
