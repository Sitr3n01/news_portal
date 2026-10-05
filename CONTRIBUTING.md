# Contributing

This repository runs two production websites for a real client, so every change
goes through the same path: a branch, a pull request and green checks. The
technical documentation in `docs/` is written in Portuguese; code, commit
messages and pull requests are in English.

## Workflow

1. Branch from an up-to-date `master`: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
2. Commit with [Conventional Commits](https://www.conventionalcommits.org/) and
   a scope when it helps: `feat(news): …`, `fix(school): …`, `chore(ci): …`.
3. Open a pull request and fill in the template, including how you verified the
   change and what the deploy needs (migrations, settings, Nginx, manual steps).
4. CI must be green. The required `test` job runs Ruff, the secret scan, the
   missing-migration check, `collectstatic` and the test suite with the
   coverage floor. CodeQL and the dependency audit also report on the PR.
5. `master` only accepts commits whose `test` check passed on a branch that is up
   to date with it. Merging does not deploy anything.
6. Deploys are manual: the *Deploy Production* workflow runs the checks again,
   waits for approval on the `production` environment and moves the
   `production-approved` tag, which the VPS pulls. See
   [docs/technical/secure-deploy.md](docs/technical/secure-deploy.md).

## Local setup

Follow [Getting started](README.md#getting-started). The SQLite settings
(`config.settings.local_sqlite`) need no PostgreSQL; the Docker setup brings
PostgreSQL and Mailpit.

```bash
ruff check .
pytest --cov
```

## Project rules

These hold the security model together, and most of them are enforced by tests:

- Public views are function-based and read site-bound models through
  `Model.on_site`, never `Model.objects` (`apps/common/test_public_isolation.py`).
- User HTML goes through `apps.common.sanitization`. Templates use
  `sanitize_html`, never `|safe` (`apps/common/test_template_rules.py`).
- Every inline `<script>` carries `nonce="{{ request.csp_nonce }}"`, and there
  are no inline event handlers (`onclick=` and friends). Same test module.
- No CDNs: front-end libraries are vendored under `static/js/vendor/`, one folder
  per version, so the CSP can stay at `'self'` plus the nonce.
- Uploads validate both the extension and the MIME type.
- Admin classes inherit from `unfold.admin.ModelAdmin`, and every text the team
  sees is in Brazilian Portuguese.
- The newsletter is never sent from the publish signal: publishing queues it,
  and a command or an admin action sends it.
- New motion respects `prefers-reduced-motion`.

## Dependencies

`requirements/*.in` list the direct dependencies; `requirements/*.txt` are locks
compiled with [uv](https://docs.astral.sh/uv/). Edit the `.in` file, then
regenerate both locks and commit them together:

```bash
uv pip compile requirements/production.in --universal --python-version 3.12 -o requirements/production.txt
uv pip compile requirements/development.in --universal --python-version 3.12 -o requirements/development.txt
```

Dependabot opens one grouped pull request per week. `django-unfold`, Wagtail
outside the 7.4 series and Django 6 are excluded on purpose; upgrading them is
planned work, described in `requirements/base.in`.

## Tests and coverage

The coverage floor lives in `pyproject.toml` (`[tool.coverage.report]
fail_under`). It is a floor, not a target: when coverage goes up, raise it in the
same pull request.

## Releases

A version is cut when it reaches production:

1. Move the *Unreleased* notes in [CHANGELOG.md](CHANGELOG.md) under the new
   version and date, and bump `version` in `pyproject.toml`.
2. Merge, run the *Deploy Production* workflow and approve it.
3. Tag the deployed commit and publish the release:
   `gh release create vX.Y.Z --target <sha> --title vX.Y.Z --notes-file <notes>`.

## Security

Please do not open public issues for vulnerabilities. Follow
[SECURITY.md](.github/SECURITY.md) to report them privately.
