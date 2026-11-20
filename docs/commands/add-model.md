# add-model

Add a Django model with a field DSL and sync related stubs (serializer, admin, viewset, router).

## Examples

```bash
uv run django-octave add-model blog Post \
  --field title:char:max=200 \
  --field published:bool:default=false
```

```bash
uv run django-octave add-model blog Post \
  --field title:char \
  --field author:fk:to=Author \
  --field tags:m2m:to=Tag
```

## Field DSL

Form: `name:type[:option=value…]`.

**Scalars:** `char`, `text`, `int`, `bool`, `decimal`, `date`, `datetime`, `email`, `url`, `slug`, `uuid`.

**Relations:** `fk`, `o2o`, `m2m` with required `to=Model` or `to=app_label.Model`. Optional `on_delete=cascade|protect|set_null|…` for fk/o2o.

If no `--field` is given, defaults to `name:char:max=255`.

## Important options

| Option | Notes |
|--------|--------|
| `--field` | Repeatable field specs |
| `--path` | Project root |
| `--force` | Replace existing model + stubs |

## What it changes

Model in `apps/<app>/models.py`, plus serializer / admin / viewset / router updates for the new model.
