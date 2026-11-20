# Install

## Requirements

- **Python 3.14+** (generator package)
- [uv](https://docs.astral.sh/uv/)

Generated projects target the newest Python version that the pinned Django release supports (see `src/django_octave/rendering/versions.py`).

## From a git checkout

```bash
git clone https://github.com/blindpenguin/django-octave.git
cd django-octave
uv sync
uv run django-octave --help
```

## From a release asset

GitHub Releases publish a wheel and sdist. Install into an isolated env, for example:

```bash
uv run --isolated --with path/to/django_octave-*.whl django-octave --help
```

PyPI publish is not part of the pipeline yet.

## Next

[Create your first project →](first-project.md)
