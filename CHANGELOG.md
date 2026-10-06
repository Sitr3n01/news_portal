# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Versions before 2.4.0 were tagged
retroactively on the commits that reached production; each one links to the
pull requests it shipped.

A version is cut when it is deployed: bump `version` in `pyproject.toml`, move
the *Unreleased* notes under the new number and publish a GitHub release with
the same tag (see [CONTRIBUTING.md](CONTRIBUTING.md#releases)).

## [Unreleased]

### Added
- CodeQL analysis for Actions, JavaScript/TypeScript and Python, a `pip-audit`
  job over the locked versions, a missing-migration check and an 82%
  branch-coverage floor in CI
  ([#56](https://github.com/Sitr3n01/news_portal/pull/56)).
- Portfolio README in English and Portuguese, with an animated preview recorded
  on the live Komuniki site and screenshots of both sites and the Newsroom
  panel, plus a contributing guide, issue forms and a pull request template
  ([#57](https://github.com/Sitr3n01/news_portal/pull/57)).

### Changed
- Dependencies are locked: `requirements/*.in` hold the direct dependencies and
  `requirements/*.txt` are uv-compiled locks for Python 3.12. Django is pinned
  to the 5.2 LTS series and Dependabot sends one grouped update per week
  ([#56](https://github.com/Sitr3n01/news_portal/pull/56)).
- Tailwind is compiled at build time instead of running in the browser: the
  public pages drop the 122 KB (gzipped) Play CDN runtime for 4–9 KB of CSS,
  with identical rendering, and CI fails if the committed CSS is stale
  ([#69](https://github.com/Sitr3n01/news_portal/pull/69)).
- The 2,900-line `apps/news/tests.py` is split into 13 thematic modules
  ([#65](https://github.com/Sitr3n01/news_portal/pull/65)).

### Fixed
- Long words in Komuniki titles and course cards break at a syllable, with a
  hyphen, instead of mid-word; the English course title no longer splits as
  "COMMUNICATIO / N" ([#70](https://github.com/Sitr3n01/news_portal/pull/70)).

### Removed
- Machine-specific paths from the Komuniki engineering notes
  ([#57](https://github.com/Sitr3n01/news_portal/pull/57)).

## [2.3.0] - 2026-09-25

### Security
- Five-category security audit with 7 findings, all fixed with regression tests
  ([#55](https://github.com/Sitr3n01/news_portal/pull/55)):
  - the *General Administrator* group can no longer grant superuser status,
    groups or permissions through the admin;
  - like/bookmark by ID no longer exposes unpublished articles on the reader
    dashboard (IDOR);
  - uploads reject HTML/SVG and other executable types, and Nginx refuses to
    serve them from `/media/` (stored XSS);
  - résumé downloads honour the superuser-only boundary of applications;
  - the newsletter preview checks permissions, status and site;
  - deploys refuse the placeholder secrets published in the `.env` examples,
    and development ports bind to loopback only;
  - nonce-based CSP on the public sites and the last `|safe` removed.
- Secret scanning in CI with a triaged `detect-secrets` baseline.

## [2.2.0] - 2026-09-24

### Added
- *Newsroom*: the Django admin (Unfold) and the Wagtail admin unified in one
  design and navigation, with workspaces per site, list headers, selection
  bars, a single editor bar, a *Publicação* control for status, schedule and
  lock, and toast messages
  ([#53](https://github.com/Sitr3n01/news_portal/pull/53)).
- Per-article editorial governance in the Wagtail editor (reporters write,
  editors approve) ([#53](https://github.com/Sitr3n01/news_portal/pull/53)).

### Fixed
- Scheduling no longer puts an article on the public site before its revision
  is approved ([#53](https://github.com/Sitr3n01/news_portal/pull/53)).
- iOS Safari now paints the news card covers: the templates declare the doctype
  ([#54](https://github.com/Sitr3n01/news_portal/pull/54)).

## [2.1.0] - 2026-09-17

### Added
- A detailed page for each course under `/cursos/`, with an origami-crane
  particle scene ([#51](https://github.com/Sitr3n01/news_portal/pull/51)).
- Black dark theme and circular theme reveal on the news portal
  ([#52](https://github.com/Sitr3n01/news_portal/pull/52)).

## [2.0.1] - 2026-09-15

### Fixed
- Komuniki mobile transitions, and lone grid cards are centered
  ([#50](https://github.com/Sitr3n01/news_portal/pull/50)).

## [2.0.0] - 2026-09-14

### Changed
- The Komuniki editorial site replaces the old school site
  ([#49](https://github.com/Sitr3n01/news_portal/pull/49)): WebGL particle hero,
  GSAP line reveals, animated underlines, page transitions, smooth anchor
  scrolling, English version of the course catalog and the official content.

### Removed
- The old school templates and the public job pages. Openings, departments and
  applications stay in the admin, with protected résumé downloads.

## [1.2.0] - 2026-08-13

### Fixed
- A deploy retry loop that had kept production from receiving a successful
  deploy since June, an impossible health check on `www`, and database dumps
  leaking into the Docker build context
  ([#42](https://github.com/Sitr3n01/news_portal/pull/42),
  [#46](https://github.com/Sitr3n01/news_portal/pull/46)).
- `scan_orphan_media` now scans every text field
  ([#47](https://github.com/Sitr3n01/news_portal/pull/47)).

### Changed
- VPS resource containment: cron jobs out of the web container's cgroup, leaner
  Gunicorn, less crawler, session and rendition load, and bounded growth of
  revisions, verification codes and caches
  ([#43](https://github.com/Sitr3n01/news_portal/pull/43),
  [#44](https://github.com/Sitr3n01/news_portal/pull/44),
  [#45](https://github.com/Sitr3n01/news_portal/pull/45)). Docker build cache
  went from 23.95 GB to 442 MB.
- Dependency and GitHub Actions updates
  ([#22](https://github.com/Sitr3n01/news_portal/pull/22)–[#26](https://github.com/Sitr3n01/news_portal/pull/26),
  [#29](https://github.com/Sitr3n01/news_portal/pull/29),
  [#30](https://github.com/Sitr3n01/news_portal/pull/30)) and a README refresh
  ([#35](https://github.com/Sitr3n01/news_portal/pull/35),
  [#36](https://github.com/Sitr3n01/news_portal/pull/36)).

## [1.1.0] - 2026-07-26

### Added
- Wagtail 7.4 as the editorial CMS, with a unified login for both admins
  ([#31](https://github.com/Sitr3n01/news_portal/pull/31)).
- Sign in with Google, e-mail verification and code-based password reset
  ([#33](https://github.com/Sitr3n01/news_portal/pull/33),
  [#34](https://github.com/Sitr3n01/news_portal/pull/34)).

### Fixed
- The StreamField backfill never wipes existing content
  ([#32](https://github.com/Sitr3n01/news_portal/pull/32)).

## [1.0.0] - 2026-06-11

First production release: the go-live on June 6 and the first week of
production fixes ([#1](https://github.com/Sitr3n01/news_portal/pull/1)–[#21](https://github.com/Sitr3n01/news_portal/pull/21)).

### Added
- News portal: articles in blocks, categories, tags, search, RSS, comments,
  likes, bookmarks and a newsletter with an explicit send queue.
- Komuniki institutional site, contact form and job applications.
- Django Unfold admin with operation guides for non-technical staff.
- Instagram and TikTok accounts and posts, with optional API sync.
- Cloudflare anti-bot layer (Turnstile, real IP, firewall) and pull-based,
  approval-gated deploys to the VPS.

[Unreleased]: https://github.com/Sitr3n01/news_portal/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/Sitr3n01/news_portal/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/Sitr3n01/news_portal/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/Sitr3n01/news_portal/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/Sitr3n01/news_portal/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Sitr3n01/news_portal/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/Sitr3n01/news_portal/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Sitr3n01/news_portal/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Sitr3n01/news_portal/releases/tag/v1.0.0
