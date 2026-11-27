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

**Relations:** `fk`, `o2o`, `m2m` with required `to=Model` or `to=app_label.Model`. Optional `on_delete=cascade|protect|set_null|…` for fk/o2o and `related_name=` (see [Reverse names](#reverse-names-related_name)).

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

### Reverse names (`related_name`)

Every relation gets a reverse accessor on the model it points at (`user.note_set`). Two relations from one model to the same target would claim the same accessor, and Django's system check fails (`fields.E304`, `fields.E305`). `add-model` handles that for you: when a model has two or more relations to the same target and you gave no name, each of them gets `<model>_<field>` and the command tells you which:

```bash
uv run django-octave add-model notes Note \
  --fields title:char,owner:fk:to=users.User,assignee:fk:to=users.User
# owner    -> related_name="note_owner"
# assignee -> related_name="note_assignee"
```

To choose a name yourself, add `related_name=`. Use `+` for no reverse relation at all:

```bash
uv run django-octave add-model notes Note \
  --fields "title:char,owner:fk:to=users.User:related_name=owned_notes,assignee:fk:to=users.User:related_name=+"
```

- The value is `+` or an identifier of up to 64 ASCII letters, digits and `_` that is not a Python keyword, does not end with `_` and has no `__` (Django rejects both for query names). Anything else is refused before any file is written.
- `related_name=` works on `fk`, `o2o` and `m2m` only. Two fields in one model cannot share a name (`+` can repeat).
- A name you set is never changed, and a field with a name (or `+`) does not count as a clash.
- A foreign key, a one-to-one and a many-to-many field to the same target all share the accessor namespace, so any mix of them counts. A bare `Author` and `<this app>.Author` are the same target, and so is a model pointing at itself twice.
- A model with at most one relation per target gets no `related_name`; its output is the same as before.
- Generated names do not include the app. Two apps that each define a model with the same name and the same field names pointing at one target would clash, as they already do with a single relation (`note_set`). Set `related_name=` on one of them.

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

The generated admin lists the model's fields in `list_display`, except many-to-many fields, which Django's admin does not allow there.
