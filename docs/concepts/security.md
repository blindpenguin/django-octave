# Security

What a generated project does by default, and what you must set before production.

## Production checklist

Production settings (`config.settings.prod`) refuse to start when these are wrong, so you find out at deploy time:

| Variable | Requirement |
|----------|-------------|
| `DJANGO_SECRET_KEY` | At least 50 characters and not the `change-me…` placeholder. |
| `DJANGO_ALLOWED_HOSTS` | Set, comma separated, and never `*`. `.env.example` ships `localhost,127.0.0.1` for local use only. |
| `DATABASE_URL` | Your production database. |
| `DJANGO_NUM_PROXIES` | Number of reverse proxies in front of Django (default `0`). See [Rate limits](#rate-limits). |
| `CORS_ALLOWED_ORIGINS` | `.env.example` lists `localhost` origins for development. Replace them with your real front-end origins. |

`python manage.py check --deploy` is clean apart from `security.W021` (HSTS preload). The generated settings use a 30 day HSTS period, which does not qualify for the preload list, on purpose.

## API docs

The OpenAPI schema, Swagger UI and ReDoc are **open locally** and **admin-only in production**. Log in to `/admin/` first, then open `/api/schema/swagger-ui/` in the same browser. Anonymous and non-admin users get `401`/`403`. The docs views use session authentication; the API itself still uses JWT.

## Rate limits

| Scope | Default | Applies to |
|-------|---------|------------|
| `auth` | 10 / minute per client | `POST /api/auth/token/`, `POST /api/auth/token/refresh/`, and `POST /api/auth/register/` (with `--register`). They share one budget. |
| `anon` | 60 / minute | everything else, unauthenticated |
| `user` | 600 / minute | everything else, authenticated |

Change them in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`. Clients over the limit get `429` with a `Retry-After` header.

Clients are identified by address. **Behind a reverse proxy, set `DJANGO_NUM_PROXIES`** to the number of proxies, otherwise every user shares the proxy's address (one user can lock everyone out) or, if the header is trusted blindly, the limit can be bypassed with a forged `X-Forwarded-For`. `add-frontend` sets `DJANGO_NUM_PROXIES=1` in `.env.example`, because the SPA's nginx is one proxy. Leave it at `0` when Gunicorn is exposed directly.

!!! note "Accepted risk: account enumeration"
    Registration answers "A user with this email already exists." The SPA needs that message to show a useful error. The `auth` limit bounds how fast addresses can be probed, but it does not remove the exposure. If that matters for your product, return a generic response and confirm by email.

## Accounts and sessions

- **Registration** checks the password against the project's `AUTH_PASSWORD_VALIDATORS` *and* the new account's own email, so `alice@example.com` cannot register with `alice@example`. Rejections come back as `400` with the messages under `password`.
- **Django admin login is not rate limited.** Restrict `/admin/` at the network level (VPN, IP allow-list, a different path behind your proxy) or add a package such as `django-axes`.
- **Refresh tokens cannot be revoked.** They stay valid until they expire (SimpleJWT default: 1 day) even after a password change or logout. Shorten `REFRESH_TOKEN_LIFETIME` if that matters to you, or enable `rest_framework_simplejwt.token_blacklist` (it adds a migration and a table).

## Project names

`django-octave new` accepts project names of 1-64 characters: letters and digits (Unicode is fine), spaces, `.`, `-` and `_`, starting with a letter or digit. Anything else (quotes, brackets, backslashes, `$`, newlines, ...) is refused, because the name is copied into Python, TOML, JSON, HTML and Vue files.

`add-frontend` reads the title from the first `# ` heading of `README.md`. If that heading is not a valid name by the same rule (for example `# Bob's "Shop"`), the SPA uses the project slug as its title instead; nothing fails. The same applies to a `name` in `pyproject.toml` that is not a plain package-style identifier.

## Who can access what

These are the defaults of a generated project (checked against a real one):

- **Every API endpoint requires a valid JWT.** `DEFAULT_PERMISSION_CLASSES` is `IsAuthenticated`, and each generated viewset repeats it. The open endpoints are token obtain/refresh, and registration when you chose `--register` (all rate limited), plus the API docs, which are open locally and admin-only in production.
- **There is no ownership.** Any authenticated user can list, read, create, update and delete **every row of every generated model**. With `--multitenancy` the tenant limits this: users only see and change rows of a tenant they are a member of, but every member can touch every row of that tenant.
- **Registration is access.** With `--register`, anyone who can reach the API can create an account, and that account has the access above.
- **`AllowAny` only when you ask for it** (`add-viewset --permission AllowAny`). It allows anonymous reads **and writes** unless you restrict the methods yourself.
- **The user list** (`GET /api/users/`, created by `add-frontend`) shows the email of every user to any authenticated user, or only the current tenant's members with `--multitenancy`.

### Restricting access

| Need | How |
|------|-----|
| Staff-only writes, everyone reads | `add-permission <app> IsStaffOrRead --preset staff_or_read --viewset <Model>` |
| Admin-only endpoint | `add-viewset <app> <Model> --permission IsAdminUser --force` |
| A different rule for one action | `add-action ... --permission <Permission>` |
| Per-owner access | the `owner` preset, **plus the two steps below** |

!!! warning "The `owner` preset protects single objects, not the list"
    `add-permission --preset owner` checks the owner of an object when it is **read, changed or deleted** (anyone else gets `403`). It does **not** filter the list endpoint: `GET /api/<models>/` still returns every user's rows. Filter the queryset yourself:

    ```python
    class NoteViewSet(viewsets.ModelViewSet):
        def get_queryset(self):
            return super().get_queryset().filter(owner=self.request.user)
    ```

!!! warning "A generated owner field is writable"
    The serializer for a model with an `owner` (or `author`, ...) foreign key to the user exposes that field as writable, so a client can create a row **owned by someone else**. Make it read-only and set it on the server:

    ```python
    class Meta:
        read_only_fields = ("id", "owner", "created_at", "updated_at")

    class NoteViewSet(viewsets.ModelViewSet):
        def perform_create(self, serializer):
            serializer.save(owner=self.request.user)
    ```

## Dependencies

The generator does not lock the dependencies of a generated project (it pins version ranges). After generating, run `uv lock`, commit `uv.lock`, and check it regularly:

```bash
uv lock
uv audit        # reports known vulnerabilities in the locked packages
```

The repository of `django-octave` itself runs `uv audit` weekly and whenever its lock file changes (`.github/workflows/audit.yml`).

## Multitenancy

With `--multitenancy`, `GET /api/users/` (the user list behind FK dropdowns) lists only members of the current tenant and needs the `X-Tenant-ID` header like every other tenant endpoint. See [Multitenancy](multitenancy.md).

## The generated SPA

- Tokens are kept in `localStorage`. That is convenient, but any XSS bug can read the refresh token. Treat the SPA as part of your attack surface: keep dependencies current and avoid injecting untrusted HTML.
- The SPA's nginx sends `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: same-origin` on every response.
- **A Content-Security-Policy is recommended but not generated.** A correct policy depends on what you load, and a wrong one breaks the app. Start with `default-src 'self'` in report-only mode and tighten it.

## Docker

The production image has no compilers, `curl`, `uv` or dev dependencies, runs as a non-root user, and keeps no secret in its environment. Details are in [Docker](docker.md).
