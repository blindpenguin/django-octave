# Releases

## Cutting a GitHub Release

1. Ensure user-facing work is already on `master` with [Conventional Commits](contributing.md#commits) (`feat` / `fix` / `docs` / `perf`).
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

Docs deploy from [`.github/workflows/docs.yml`](https://github.com/blindpenguin/django-octave/blob/master/.github/workflows/docs.yml) to GitHub Pages. One-time: repo **Settings → Pages → Source: GitHub Actions**.
