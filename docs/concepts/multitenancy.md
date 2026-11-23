# Multitenancy

Row-level multitenancy is **opt-in at create time only** (`--multitenancy` / `--no-multitenancy`). There is no CLI to retrofit an existing project.

## What you get

- First-party tenant primitives (not django-tenants / schema-based)
- `Tenant`, `Membership` and the tenant-aware base `TenantAwareModel` in `apps/core/models.py`
- `apps/core/tenancy.py` with `TenantScopedMixin`, which binds the current tenant for each API request
- Generated viewsets for tenant-aware models inherit the mixin
- Permission preset `tenant_member` via [`add-permission`](../commands/add-permission.md)
- API tests from [`add-test`](../commands/add-test.md) with `tenant` / `tenant_client` fixtures

## How requests are scoped

Clients send a normal JWT **and** the tenant they are acting for:

```http
GET /api/notes/
Authorization: Bearer <access token>
X-Tenant-ID: 2f0c8a54-6b0e-4b8e-9d52-0a8f1b1c9f3e
```

`TenantScopedMixin` runs right after DRF authenticates the request. It looks up the tenant by that id **and** the user's membership, binds it for the request, and clears it afterwards. Reads and writes then only touch that tenant's rows.

| Request | Result |
|---------|--------|
| Valid header, user is a member | Scoped to that tenant |
| Header missing, malformed, unknown tenant, or user not a member | `403` with the same body for all four, so tenant existence is not revealed |
| Not authenticated | `401` (normal DRF behaviour) |
| Other tenant's object by id | `404` |

Clients cannot choose a tenant through the payload: generated serializers never expose `tenant`, and saving a row for a tenant other than the current one raises `PermissionDenied`.

Views that are not tenant-scoped (token endpoints, the OpenAPI schema, the admin) do not need the header.

## Writing your own viewset

Put the mixin **first** in the bases. Keep `queryset = Model.objects.all()`; the mixin rebuilds it for each request.

```python
from apps.core.tenancy import TenantScopedMixin


class NoteViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    queryset = Note.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(archived=False)
```

`Model.objects` is the tenant-scoped manager and returns nothing when no tenant is bound. `Model.all_objects` is **unscoped**: use it only in admin or maintenance code, never in request handling.

The `tenant_member` permission preset needs the mixin on the viewset. `add-permission --viewset` warns if it is missing.

## Known limitations

- The Django admin uses a browser session and cannot send `X-Tenant-ID`, so tenant-aware models show no rows there. Use `all_objects` in a custom admin `get_queryset` if you need it.
- Registration (`add-frontend --register`) does not create a membership; a new user needs one before they can use tenant endpoints.

## Upgrading an existing project

Projects generated before `TenantScopedMixin` existed bound the tenant in Django middleware, which runs before JWT authentication. In those projects tenant endpoints returned errors or empty lists for JWT clients. `add`, `add-model` and `add-viewset` refuse to run on them until you migrate:

1. Copy `apps/core/tenancy.py` from a freshly generated `--multitenancy` project into `apps/core/`.
2. Delete `apps/core/middleware.py` and remove `"apps.core.middleware.TenantMiddleware"` from `MIDDLEWARE` in `config/settings/base.py`.
3. In `apps/core/models.py`, add the foreign-tenant check to `TenantAwareModel.save()` (compare with a freshly generated project).
4. In every viewset for a tenant-aware model, add `TenantScopedMixin` as the first base class and `from apps.core.tenancy import TenantScopedMixin`.
5. Replace skipped API tests with the ones from `django-octave add-test <app> <Model> --force`.

## Practical notes

- Choose carefully at `new` — switching later is a manual migration.

!!! warning
    Multitenancy is create-time only in v1. Do not expect `django-octave` to add it to an already generated tree.
