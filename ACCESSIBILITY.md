# Accessibility

This applies to every repository in [luminare-dev](https://github.com/luminare-dev) that does not
have its own `ACCESSIBILITY.md`.

The projects here are mostly command-line tools, configuration and documentation. The maintainers
want them to work with screen readers, keyboard-only use, zoom and high-contrast settings. This is
best effort, not a formal conformance claim.

## What the projects aim for

- Documentation in plain Markdown with real headings, lists and tables, so that it can be read
  and navigated with assistive technology.
- Alt text for every image, and a text description of what every GIF or video demo shows.
- Dashboards, charts and terminal output that do not rely on colour alone: values, labels or
  symbols carry the same information.
- Examples as copyable text, never only as screenshots.

## Reporting a barrier

- Open an issue in the affected repository (form "Bug report") and describe what you tried, the
  assistive technology or setting you use, and what stopped you. If you are not sure which
  repository it belongs to, start a [discussion](https://github.com/orgs/luminare-dev/discussions).
- If GitHub itself is the barrier, write to <oss@luminare.tech> instead.

Reports are handled like bug reports: the maintainers aim for a first reply within 7 days, best
effort.
