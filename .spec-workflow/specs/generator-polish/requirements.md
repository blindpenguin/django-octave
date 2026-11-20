# Requirements Document

## Introduction

A recipe-site benchmark built **only** with django-octave generators exposed four product gaps: router **basename** mismatch vs `add-test` reverses, **cross-app FK** factories left as TODOs, smoke tests that always expect auth denial even for `AllowAny` viewsets, and **squashed** Python (no blank lines between top-level classes in `models.py` and similar).

This spec fixes those generator defects so a multi-app project with relations and mixed permissions can `makemigrations` / `pytest` with far less hand-editing.

## Alignment with Product Vision

- Solo-dev ergonomics: generators should produce runnable, testable stubs.
- Consistency: basename / reverse names / factory wiring must agree across `add`, `add-model`, `add-viewset`, and `add-test`.
- Production-ready defaults include readable generated code (formatting), not only correct AST.

## Requirements

### Requirement 1 — Consistent router basename / reverse names

**User Story:** As a developer running `add-test`, I want `reverse("<model_snake>-list")` to resolve for every generated viewset, so that smoke tests work without hand-editing `urls.py`.

#### Acceptance Criteria

1. WHEN an app is created via `add` THEN the initial viewset registration SHALL use `basename="<model_snake>"` (PascalCase model → snake_case), **not** the app module name.
2. WHEN `add-model` / `add-viewset` / API sync registers or updates a viewset THEN `basename` SHALL be `"<model_snake>"` and the URL prefix SHALL remain the pluralized snake (empty `""` only for the app’s first/default route is allowed **if** basename is still the model snake).
3. WHEN a viewset is already registered under a wrong basename (legacy `basename="<app>"`) and the user regenerates with `--force` (or sync runs) THEN the registration line SHALL be **updated** to the correct basename (and consistent path), not left stale because the ViewSet name already appears.
4. WHEN `add-test` generates API tests THEN reverse names SHALL match the basename convention above (`{snake}-list` / `{snake}-detail`).

### Requirement 2 — Cross-app FK SubFactories

**User Story:** As a developer with `ForeignKey("other_app.Model")`, I want factories to SubFactory the related model’s factory, so that `ModelFactory()` does not hit NOT NULL / IntegrityError.

#### Acceptance Criteria

1. WHEN a FK/O2O points at `app_label.Model` in another installed domain app THEN the factory SHALL emit `factory.SubFactory("tests.factories.<app>_<model_snake>.<Model>Factory")` using the same stem convention as same-app relations.
2. WHEN the related factory module does not yet exist THEN the generator MAY still emit the SubFactory string (lazy import path) OR create a minimal related factory — emitting a working SubFactory path is required; a TODO comment alone is **not** acceptable for resolvable `app.Model` targets.
3. User / `AUTH_USER_MODEL` relations SHALL continue to use `UserFactory` as today.
4. M2M SHALL remain omitted from factory fields (unchanged).

### Requirement 3 — Auth smoke tests respect viewset permissions

**User Story:** As a developer using `AllowAny` (or other open permissions), I want generated tests to match that policy, so that `pytest` is not red by default.

#### Acceptance Criteria

1. WHEN the target `<Model>ViewSet` uses `AllowAny` (alone or as the effective list permission) THEN `test_list_requires_auth` SHALL **not** expect 401/403; it SHALL assert anonymous list returns 200 (or the test SHALL be omitted/replaced with an equivalent open-access assertion).
2. WHEN the viewset requires authentication (default `IsAuthenticated`, `IsOwner`, custom non-AllowAny, etc.) THEN existing deny-anonymous behavior SHALL remain.
3. Retrieve/list authenticated happy-path tests SHALL continue to expect 200 when a factory instance can be created.
4. Detection SHALL read the generated `views.py` (or equivalent resolved permission_classes) rather than guessing from CLI flags alone when regenerating tests.

### Requirement 4 — Readable generated Python (spacing / format)

**User Story:** As a developer opening `models.py` after several `add-model` runs, I want blank lines between top-level classes (and similarly readable stubs elsewhere), so that files are not visually squashed.

#### Acceptance Criteria

1. WHEN a second (or Nth) model class is appended to `models.py` THEN there SHALL be at least one blank line between consecutive top-level class definitions.
2. WHEN a class is replaced with `--force` THEN surrounding spacing SHALL remain PEP8-reasonable (no glued `class A` / `class B`).
3. The same spacing expectation SHOULD apply to other multi-class generated modules touched by upserts (`serializers.py`, `admin.py`, `views.py`, `permissions.py`) when classes are appended.
4. IF the implementation runs an external formatter (e.g. Ruff) THEN it SHALL be best-effort (skip cleanly if unavailable) and SHALL NOT require Ruff as a hard runtime dependency of the published wheel unless already accepted; primary guarantee is correct blank lines from the writers.

### Requirement 5 — Regression coverage

**User Story:** As a maintainer, I want tests that lock these behaviors, so that the recipe-style benchmark does not regress.

#### Acceptance Criteria

1. Unit/integration tests SHALL cover: basename on `add` + after `add-model`/`add-viewset`; cross-app FK SubFactory emission; AllowAny vs auth test generation; blank line between two models in `models.py`.
2. Existing pytest suite SHALL remain green.

## Non-Functional Requirements

### Code Architecture and Modularity

- Prefer fixing shared helpers (`ensure_router_registration`, factory line builder, model writer) over one-off command patches.
- Keep commands thin.

### Performance

- No meaningful slowdown; optional format subprocess only on files just written.

### Reliability

- Fail closed on unparseable targets as today; do not silently leave wrong basename when force/sync can fix it.

## Out of Scope

- Auto-fixing already-generated projects on disk without re-running generators (no migrate/upgrade command).
- Changing public URL path layout beyond basename consistency (e.g. nested routers).
- Full Black-style formatting of entire projects.
- Fixing the external `recipe_site` tree in this repo (user generators there separately if desired).
