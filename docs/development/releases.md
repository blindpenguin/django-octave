# Releases

## Cutting a GitHub Release

1. Ensure user-facing work is already on `master` with [Conventional Commits](contributing.md#commits) (`feat` / `fix` / `docs` / `perf`).
   Mark breaking changes with `!` after the type (`feat(api)!: ...`) or a `BREAKING CHANGE:` footer in the commit body. The release notes list them first, under **Breaking changes**; a footer's text (up to the next blank line or trailer such as `Co-Authored-By:`) is used in place of the subject, so say there what breaks and what to do about it.
2. Bump `version` in `pyproject.toml` (e.g. `uv version 0.2.3`).
3. Commit **only** the bump: `chore(release): 0.2.3`.
4. Preview notes (optional):

```bash
python3 scripts/release-notes.py
# or since a tag:
python3 scripts/release-notes.py v0.2.2..HEAD
```

5. Tag and push (tag must match the package version, with a `v` prefix):

```bash
git tag -a v0.2.3 -m "v0.2.3"
git push origin master
git push origin v0.2.3
```

That runs [`.github/workflows/release.yml`](https://github.com/blindpenguin/django-octave/blob/master/.github/workflows/release.yml): build with `uv`, smoke-test the wheel and sdist, generate notes from conventional commits since the previous tag, then create a [GitHub Release](https://github.com/blindpenguin/django-octave/releases) with the artifacts attached.

PyPI publish is not part of this pipeline yet.

## Local smoke check (optional)

```bash
uv build
uv run --isolated --no-project --with dist/*.whl scripts/smoke_dist.py
uv run --isolated --no-project --with dist/*.tar.gz scripts/smoke_dist.py
```

## Docs site

The public docs site tracks the **latest GitHub Release**, not `master`.

| Event | What happens |
|-------|----------------|
| PR / push to `master` | `mkdocs build --strict` only (CI) |
| GitHub Release published (`v*`) | Build from that tag → deploy GitHub Pages |
| Manual `workflow_dispatch` | Rebuild/redeploy a **specific release tag** (input required; not `master`) |

Workflow: [`.github/workflows/docs.yml`](https://github.com/blindpenguin/django-octave/blob/master/.github/workflows/docs.yml).  
One-time: repo **Settings → Pages → Source: GitHub Actions**.

Edit docs on `master` as usual; they go live on the **next** release (or a manual dispatch from the release tag).

!!! warning "Known issue: the deploy does not start by itself"
    The workflow is meant to deploy when a release is published, but the release is created with the workflow's own `GITHUB_TOKEN`, and GitHub does not start other workflows from events created that way. After every release, deploy the docs by hand:

    ```bash
    gh workflow run Docs -f tag=v0.3.0   # use the new tag
    ```

    Then check that <https://blindpenguin.github.io/django-octave/> shows the new pages. The fix is on the [roadmap](../roadmap.md) (item 14).
