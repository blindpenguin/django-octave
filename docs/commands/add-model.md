# add-model

Add a Django model with a field DSL and sync related stubs (serializer, admin, viewset, router).

## Examples

```bash
uv run django-octave add-model blog Post \
  --fields title:char:max=200,published:bool:default=false
```

```bash
uv run django-octave add-model blog Post \
  --field title:char \
  --field author:fk:to=Author \
  --field tags:m2m:to=Tag
```

Repeatable `--field` / `-f` and compact `--fields` can be combined; specs are concatenated in that order.

## Field DSL

Form: `name:type[:option=value…]`.

**Scalars:** `char`, `text`, `int`, `bool`, `decimal`, `date`, `datetime`, `email`, `url`, `slug`, `uuid`.

**Relations:** `fk`, `o2o`, `m2m` with required `to=Model` or `to=app_label.Model`. Optional `on_delete=cascade|protect|set_null|…` for fk/o2o.

If neither `--field` nor `--fields` is given, defaults to `name:char:max=255`.

## Important options

| Option | Notes |
|--------|--------|
| `--fields` | Compact comma-separated field specs |
| `--field` / `-f` | Repeatable field specs (same DSL) |
| `--path` | Project root |
| `--force` | Replace existing model + stubs |

## What it changes

Model in `apps/<app>/models.py`, plus serializer / admin / viewset / router updates for the new model.
