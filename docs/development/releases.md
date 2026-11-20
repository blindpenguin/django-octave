# Releases

## Cutting a GitHub Release

1. Bump `version` in `pyproject.toml` (e.g. with `uv version 0.1.1`).
2. Commit the version bump.
3. Tag and push (tag must match the package version, with a `v` prefix):

```bash
git tag -a v0.1.1 -m "v0.1.1"
git push origin v0.1.1
```

That runs [`.github/workflows/release.yml`](https://github.com/blindpenguin/django-octave/blob/master/.github/workflows/release.yml): build with `uv`, smoke-test the wheel and sdist, then create a [GitHub Release](https://github.com/blindpenguin/django-octave/releases) with the artifacts attached.

PyPI publish is not part of this pipeline yet.

## Local smoke check (optional)

```bash
uv build
uv run --isolated --no-project --with dist/*.whl scripts/smoke_dist.py
uv run --isolated --no-project --with dist/*.tar.gz scripts/smoke_dist.py
```

## Docs site

Docs deploy from [`.github/workflows/docs.yml`](https://github.com/blindpenguin/django-octave/blob/master/.github/workflows/docs.yml) to GitHub Pages. One-time: repo **Settings → Pages → Source: GitHub Actions**.
