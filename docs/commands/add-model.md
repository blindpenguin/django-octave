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

### Defaults

`default=` is turned into a literal, never copied into the model as code. Anything that cannot be written safely is rejected before any file changes.

| Type | Accepted `default=` | Example |
|------|---------------------|---------|
| `char`, `text`, `email`, `url`, `slug` | any text (quotes and newlines are escaped) | `title:char:default=untitled` |
| `int` | an integer | `count:int:default=0` |
| `bool` | `true`/`false` (also `1`, `0`, `yes`, `no`, `on`, `off`) | `published:bool:default=false` |
| `decimal` | a finite number | `price:decimal:default=9.99` |
| `uuid` | `uuid4` (a new UUID each time) or a UUID string | `ref:uuid:default=uuid4` |
| `date`, `datetime`, `fk`, `o2o`, `m2m` | **not supported** | set it in the model by hand |

Values cannot contain `:` because it separates options. `opens:char:default=12:30` is rejected with a hint. One caveat: a value like `default=a:unique` is read as the default `a` plus the `unique` flag.

### Field names

Python keywords (`class`, `import`, …) and Django model methods (`save`, `delete`, `clean`, `full_clean`, `validate_unique`, `refresh_from_db`, `from_db`, `check`, `serializable_value`) are rejected, as are the reserved names `id`, `pk`, `objects` and `all_objects`.

## Important options

| Option | Notes |
|--------|--------|
| `--fields` | Compact comma-separated field specs |
| `--field` / `-f` | Repeatable field specs (same DSL) |
| `--path` | Project root |
| `--force` | Replace existing model + stubs |

## What it changes

Model in `apps/<app>/models.py`, plus serializer / admin / viewset / router updates for the new model.
