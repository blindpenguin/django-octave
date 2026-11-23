# Tasks Document

- [x] 1.0 Generated project: tenant binding in DRF
  - [x] 1.1 Add `tenancy.py` template; drop the middleware
    - Files: `src/django_octave/templates/project/apps/core/tenancy.py.j2` (new), `src/django_octave/templates/project/apps/core/middleware.py.j2` (delete), `src/django_octave/templates/project/config/settings/base.py.j2`, `src/django_octave/rendering/writer.py`, `src/django_octave/project/detect.py`
    - Implement `TenantRequired` (DRF 403) and `TenantScopedMixin` (`perform_authentication`, `get_queryset`, `dispatch` with `finally` reset) exactly as in design.md. Remove the `TenantMiddleware` line from settings and its special case in `_should_skip`. Add `tenancy.py` to the multitenancy-only skip rule. `detect_project` treats `apps/core/tenancy.py` OR the old middleware OR a `TenantAwareModel` as multitenant
    - Purpose: Bind the tenant after JWT authentication, before permission checks
    - _Leverage: `apps/core/models.py.j2` (`Tenant`, `set_current_tenant`), `rendering/writer.py::_should_skip`, `project/detect.py::_has_tenant_middleware`_
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.2, 2.5_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django/DRF engineer | Task: Create the generated `apps/core/tenancy.py` mixin and remove TenantMiddleware from the generated project, updating writer skip rules and project detection | Restrictions: One identical 403 for missing/malformed/unknown/non-member tenant; no new dependencies; keep `get_current_tenant`/`set_current_tenant` signatures; non-multitenancy output must not change | Success: Rendered MT project has tenancy.py and no middleware or MIDDLEWARE entry; non-MT render unchanged; detect works for old and new layouts; tests from 1.3 pass; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Reject foreign-tenant saves (guard in `save()`)
    - Files: `src/django_octave/templates/project/apps/core/models.py.j2`
    - `TenantAwareModel.save()` raises `django.core.exceptions.PermissionDenied` when `tenant_id` is set and differs from a bound current tenant. _Deviation from design §5:_ no serializer change; `inspect` never lists the inherited `tenant` field, so generated serializers cannot expose it. A test (1.3) locks that invariant in
    - Purpose: A client can never write into another tenant
    - _Leverage: existing `read_only_fields` handling in `serializer_gen.py`, `inspect/model_fields.py` (`has_tenant_aware`)_
    - _Requirements: 2.3, 2.4_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django security engineer | Task: Add the foreign-tenant guard to TenantAwareModel.save and make the tenant field read-only in generated serializers | Restrictions: Do not change fields or migrations; `all_objects` stays available; non-tenant models unaffected | Success: Unit tests show `tenant` in read_only_fields only for tenant-aware models; rendered models.py contains the guard; log + mark [x]_

  - [x] 1.3 Unit tests for the generated-project changes
    - Files: `tests/rendering/test_render_project.py`, `tests/project/test_detect_patch.py`, `tests/api_parts/test_serializer_gen.py`
    - Assert: MT render has `apps/core/tenancy.py`, no middleware file, no `MIDDLEWARE` entry; non-MT render has neither; every rendered `.py` passes `ast.parse`; detect recognises old (middleware) and new (tenancy) layouts; serializer read-only behaviour
    - Purpose: Lock the structure in before the generators change
    - _Leverage: existing helpers in `tests/rendering/test_render_project.py`_
    - _Requirements: 1.3, 2.5, 5.1_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA engineer | Task: Add unit tests covering render output, project detection and serializer read-only tenant | Restrictions: No network, no uv sync, keep suite fast; follow test naming `test_<unit>_<condition>_<expected>` | Success: Tests fail without 1.1/1.2 and pass with them; log + mark [x]_

- [x] 2.0 Generators: tenant-aware viewsets and permission
  - [x] 2.1 Shared `viewset_bases` helper and three emitters
    - Files: `src/django_octave/api_parts/viewset_gen.py`, `src/django_octave/models_gen/api_sync.py`, `src/django_octave/templates/app/views.py.j2` (plus `rendering/app_context.py` if a new flag is needed)
    - Add `viewset_bases(use_mt, tenant_aware, permission)` returning `"TenantScopedMixin, viewsets.ModelViewSet"` or `"viewsets.ModelViewSet"`; add the `from apps.core.tenancy import TenantScopedMixin` import only when used. Keep `queryset = Model.objects.all()` unchanged. If the project is MT but `apps/core/tenancy.py` is missing, raise a clear error pointing to the migration docs
    - Purpose: Every generated tenant viewset scopes per request; single source of truth
    - _Leverage: `project/detect.py` (`use_multitenancy`), `inspect/model_fields.py` (`has_tenant_aware`), `frontend_gen/crud_discover.py` regex (must still match)_
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 6.2_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Introduce viewset_bases and use it in all three viewset emitters, with the missing-tenancy error | Restrictions: Non-MT output byte-identical to today; do not touch crud_discover; no duplication of the base-class logic across emitters | Success: Golden-output tests for non-MT, MT+tenant-aware, and MT+tenant_member; crud_discover still finds the model; error test for old projects; log + mark [x]_

  - [x] 2.2 `tenant_member` permission works with the mixin
    - Files: `src/django_octave/api_parts/permission_gen.py`, `src/django_octave/commands/add_permission.py` (only if wiring needs it)
    - Update the preset docstring (`request.tenant` is set by `TenantScopedMixin`); `add-permission --viewset` warns when the wired viewset lacks `TenantScopedMixin` (the permission would deny everything). _Deviation from design §6:_ the permission is a custom class resolved by name, so `add-viewset` cannot know it is the preset; adding the mixin to non-tenant models was dropped as over-engineering
    - Purpose: The preset actually works for JWT requests
    - _Leverage: `viewset_bases` from 2.1_
    - _Requirements: 4.1, 4.2, 4.3_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Align the tenant_member preset and its docs with the mixin | Restrictions: Keep the permission logic simple; no behaviour change outside multitenancy projects | Success: Tests in tests/api_parts/test_permission_gen.py and test_viewset_gen.py cover the preset; log + mark [x]_

- [x] 3.0 Generated API tests for tenant models
  - [x] 3.1 Replace `skip_tenant` with real tenant tests
    - Files: `src/django_octave/api_parts/test_gen.py`, generated `tests/conftest.py` content in the same module (`ensure_test_fixtures`), `tests/api_parts/test_test_gen.py`
    - In MT projects add `tenant` and `tenant_client` fixtures (Tenant + Membership for `user`, JWT/force-auth client sending `X-Tenant-ID`). For tenant-aware models generate: list/retrieve scoped to the tenant, 403 without header, a second tenant's row invisible. Update model factories so tenant-aware models get a `tenant`
    - Purpose: The generated projects test the isolation the generator promises
    - _Leverage: `build_api_test_source`, `build_model_factory_source`, `ensure_test_fixtures`_
    - _Requirements: 5.2_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Test-generation engineer | Task: Remove the tenant skip and emit working tenant/isolation tests and fixtures | Restrictions: Non-MT output unchanged; generated tests must pass in a real generated project (verified in task 4.1) | Success: Generator tests assert no skip marker and presence of header/isolation tests; log + mark [x]_

- [x] 4.0 End-to-end proof and docs
  - [x] 4.1 Opt-in end-to-end test
    - Files: `tests/e2e/test_multitenancy_jwt.py` (new), `tests/e2e/__init__.py`, `pyproject.toml` (register the `e2e` marker)
    - Marker `e2e`, skipped unless `OCTAVE_E2E=1`. Generate an MT project, add an app, `uv sync`, migrate, then with `APIClient`: JWT login; create + list with header; two tenants isolated; missing header → 403; non-member and unknown tenant → identical 403 body; foreign `tenant` in payload ignored; contextvar cleared after an exception. Also run the generated project's own pytest
    - Purpose: Reproduce the original 500 and prove it is gone
    - _Leverage: the reproduction used in the audit (sqlite, `new demo --multitenancy`, `add notes`)_
    - _Requirements: 5.1, 5.3, 1.1–1.4, 2.1–2.4_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA automation engineer | Task: Write the opt-in e2e test and register the marker | Restrictions: Never run by default; use tmp_path; no state outside the temp dir; clear skip reason when OCTAVE_E2E is unset | Success: Test passes with OCTAVE_E2E=1 on this branch and demonstrably fails against the pre-fix templates (git stash check); log + mark [x]_

  - [x] 4.2 Docs and migration notes
    - Files: `docs/` multitenancy page (find the existing one, else `docs/commands/new.md` section), `docs/roadmap.md` (one line), `docs/development/` e2e how-to
    - Document: sending `X-Tenant-ID`, scoping a hand-written viewset (mixin + `get_queryset` super), `all_objects` is unscoped, admin gap, and steps for existing projects (add `tenancy.py`, remove middleware, add mixin to viewsets, `tenant` read-only). Document running the e2e test
    - Purpose: Existing users can adopt the fix; new users understand the model
    - _Leverage: existing docs structure, `mkdocs.yml` nav_
    - _Requirements: 6.1, 6.2, 5.3_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer | Task: Write the multitenancy usage and migration docs | Restrictions: Keep it short; match existing doc style; do not edit unrelated pages | Success: Migration steps verified against a project generated from the previous commit; `mkdocs build` has no new warnings; log + mark [x]_

  - [x] 4.3 Final check
    - Files: none new
    - Run `uv run pytest`, `uv run ruff check src tests` (only touched files may add findings), and the e2e test; confirm git diff contains only spec-related files
    - Purpose: Close the spec
    - _Leverage: existing test suite_
    - _Requirements: All_
    - _Prompt: Implement the task for spec fix-multitenancy-jwt, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Release engineer | Task: Run the full verification and report results | Restrictions: Do not commit; do not fix unrelated Ruff findings | Success: Suite green, e2e green, summary reported to the user; log + mark [x]_
