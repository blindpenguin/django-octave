# Requirements Document

## Introduction

Two findings from the last review, both verified on a real generated project and currently only *documented*:

- **N5 — the `owner` permission preset does not scope list endpoints.** `add-permission --preset owner` generates a permission class that implements only `has_object_permission`. User A gets `403` on B's note, but `GET /api/notes/` still returns B's rows to A.
- **N6 — the owner field is writable.** The generated serializer exposes a foreign key to the user as a writable field, so A can `POST /api/notes/ {"owner": <B>}` and receive `201`, creating a row owned by B. A can also `PATCH` the owner of their own row to someone else.

Both are the same gap: the generator offers an "owner" access model but implements only a third of it (the single-object check). This spec makes the owner preset a complete, safe model **when it is used**, without changing the open default for projects that do not use it (that default is documented separately).

Design direction (decided in the review): **the owner preset carries its own knowledge.** The generated permission class records `owner_attr`, and everything that wires an owner permission to a viewset adds a small reusable mixin that scopes the queryset, assigns the owner on the server, and keeps the serializer field read-only. No field-name guessing: only the attribute the developer named with `--owner-attr` is affected, and other user foreign keys (for example `assignee`) stay writable.

Out of scope: changing the default permission of viewsets that do not use the owner preset; auto-detecting ownership from field names; making staff or superusers bypass ownership; non-user owners; retrofitting existing projects automatically (documented upgrade steps instead).

## Alignment with Product Vision

An access model the generator advertises should hold for every endpoint of the resource it is applied to. "Owner" must mean: I see only my rows, I cannot hand rows to someone else, and I cannot create rows on someone else's behalf.

## Requirements

### Requirement 1 — owner-scoped viewsets see only the caller's rows (N5)

**User Story:** As a developer who chose per-owner access, I want every endpoint of the resource limited to the caller's own rows, so that listing is not a way around the object check.

#### Acceptance Criteria

1. WHEN a viewset is owner-scoped THEN `list`, `retrieve`, `update`, `partial_update`, `destroy` and every custom action that uses `get_queryset()` SHALL operate only on rows whose owner attribute equals the requesting user.
2. WHEN a user requests another user's row by id THEN the response SHALL be `404` (the row is not visible), and the object permission class SHALL remain in place as a second layer.
3. WHEN the request is unauthenticated THEN the queryset SHALL be empty (fail closed) in addition to the permission class rejecting it.
4. WHEN filtering, search and ordering backends are configured THEN they SHALL apply on top of the scoped queryset.
5. WHEN staff or superusers call the API THEN they SHALL be scoped like anyone else (no implicit bypass).

### Requirement 2 — the owner cannot be set or changed by the client (N6)

**User Story:** As an operator, I want the server to decide who owns a row, so that clients cannot create or transfer rows on someone else's behalf.

#### Acceptance Criteria

1. WHEN a client creates a row THEN the system SHALL set the owner to the requesting user, ignoring any owner value in the payload.
2. WHEN a client updates a row (PUT or PATCH) with a different owner value THEN the stored owner SHALL NOT change.
3. WHEN the OpenAPI schema is generated THEN the owner field SHALL be `readOnly` and not required on create.
4. WHEN the owner attribute is not part of the serializer's fields THEN nothing SHALL be changed and no error raised.
5. Other foreign keys to the user model (for example `assignee`, `reviewer`) SHALL remain writable; only the declared owner attribute is affected.

### Requirement 3 — every wiring path makes the viewset owner-scoped

**User Story:** As a developer, I want owner scoping to follow from choosing the owner permission, however I wire it, so that I cannot end up with the check but not the scoping.

#### Acceptance Criteria

1. WHEN `add-permission <app> <Class> --preset owner` generates a class THEN it SHALL carry `owner_attr = "<attr>"` as a class attribute and use it in its object check (behaviour of the check unchanged).
2. WHEN `add-permission ... --preset owner --viewset <Model>` runs THEN the viewset SHALL gain the owner mixin (first in its bases), `owner_field = "<attr>"`, and the serializer for the model SHALL list the owner attribute in `read_only_fields`; the command output SHALL say what was changed.
3. WHEN `add-viewset <app> <Model> --permission <Class>` runs and `<Class>` is a generated owner permission (has `owner_attr`) THEN the new viewset SHALL be owner-scoped as in 3.2.
4. WHEN `add-permission --preset owner` runs **without** `--viewset` THEN the output SHALL state the exact commands that complete the scoping.
5. WHEN a permission class has no `owner_attr` (hand-written, or generated by an older version) THEN generators SHALL NOT guess; behaviour SHALL be unchanged and documented.
6. WHEN the same wiring runs twice (or `--force`) THEN the result SHALL be identical, with no duplicated base class, attribute or `read_only_fields` entry.
7. WHEN any of these steps fails THEN the project tree SHALL be unchanged (the existing all-or-nothing rollback applies) and no traceback SHALL be shown.

### Requirement 4 — composes with multitenancy

**User Story:** As a developer using multitenancy and per-owner access, I want both to apply, so that I get my rows within my tenant.

#### Acceptance Criteria

1. WHEN a viewset is both tenant-scoped and owner-scoped THEN a request SHALL see only rows that belong to the current tenant **and** to the user.
2. WHEN the bases are generated THEN the owner mixin SHALL come before the tenant mixin; generated tests SHALL prove the combined behaviour.

### Requirement 5 — the SPA treats the owner as read-only

**User Story:** As a user of the generated SPA, I want not to be asked who owns a new row, so that the form matches what the server enforces.

#### Acceptance Criteria

1. WHEN frontend CRUD pages are generated for an owner-scoped viewset THEN the owner attribute SHALL NOT be an editable field in the create and edit forms, and SHALL be shown read-only in the detail view.
2. WHEN a viewset is not owner-scoped THEN CRUD generation SHALL be unchanged.

### Requirement 6 — generated tests prove it

**User Story:** As a maintainer of a generated project, I want tests that fail if scoping is lost, so that a later edit cannot silently reopen the hole.

#### Acceptance Criteria

1. WHEN `add-test` runs for an owner-scoped viewset THEN the generated API tests SHALL cover: own rows listed and others' not, another user's row returns 404, owner in the payload is ignored on create, owner cannot be changed on update.
2. WHEN the project is also multitenant THEN the tests SHALL run with the tenant fixtures.
3. WHEN a viewset is not owner-scoped THEN generated tests SHALL be unchanged.

### Requirement 7 — nothing changes unless the owner preset is used; docs and audit

**User Story:** As an existing user, I want my generated code to stay as it is, and I want clear upgrade steps.

#### Acceptance Criteria

1. WHEN no owner permission is involved THEN every generator's output SHALL be byte-identical to before (verified against the previous version).
2. WHEN the docs describe ownership THEN `docs/concepts/security.md` SHALL replace the two warnings with an accurate description of what the owner preset now does, what it still does not do (other user foreign keys stay writable, staff are scoped too, default viewsets remain open), and the manual upgrade steps for projects generated earlier.
3. WHEN the work is finished THEN `docs/code-audit-2026-11-23.md` SHALL record N5 and N6 as fixed.
4. WHEN verified THEN an end-to-end scenario on a real generated project (plain and multitenant) SHALL demonstrate every acceptance criterion in R1, R2 and R4 and SHALL fail against the previous version.

## Non-Functional Requirements

### Code Architecture and Modularity
- **Single Responsibility Principle**: one generated mixin owns scoping and owner assignment; the generator has one function that applies "owner scoping" to a viewset/serializer pair, used by both wiring paths.
- **Modular Design**: no duplicated queryset code in generated viewsets; the mixin lives in `apps/core` next to the tenancy and throttling helpers and is always generated (it is small and inert unless used).
- **Dependency Management**: no new dependencies.
- **Clear Interfaces**: the contract is `owner_field` on the viewset and `owner_attr` on the permission class.

### Performance
- Scoping is a single indexed-FK `WHERE` clause; no extra queries.

### Security
- Fail closed (unauthenticated → empty). The client never controls ownership. The object permission remains as defence in depth.

### Reliability
- Idempotent wiring; all-or-nothing on failure; no change for projects that do not use the preset.

### Usability
- The command output lists exactly what was changed and, when the viewset was not wired, the next command to run.
