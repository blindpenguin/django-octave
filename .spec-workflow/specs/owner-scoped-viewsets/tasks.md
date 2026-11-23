# Tasks Document

- [x] 1.0 The proof first, then the mixin
  - [x] 1.1 E2E scenarios that fail today (plain and multitenant)
    - Files: `tests/e2e/test_owner_scoping.py` (new), `tests/e2e/owner_scenarios.py.tmpl` (new), `tests/e2e/helpers.py` (extend if needed)
    - Opt-in (`OCTAVE_E2E=1`). Generate a project (plain, and `--multitenancy`) with an app whose model has `owner` and `assignee` foreign keys to the user; run `add-permission <app> IsOwner --preset owner --viewset <Model>`; copy the scenario file into the project and run its pytest. Scenarios: own rows only in the list; another user's row returns 404 on retrieve/patch/delete; create ignores `owner` in the payload (row owned by the requester); PATCH cannot change the owner; `assignee` stays writable; the schema marks `owner` read-only (admin session); anonymous gets 401/403; in the multitenant project a second tenant's rows and another user's rows in the same tenant are both invisible. Run it now and record which scenarios fail on the current code (expected: list scoping, create/patch owner, schema readOnly)
    - Purpose: Evidence before the change; reused as the after-proof
    - _Leverage: `tests/e2e/helpers.py` (`build_project`-style helpers), `hardening_scenarios.py.tmpl` structure_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.5, 4.1, 7.4_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA automation engineer with a security focus | Task: Write the opt-in e2e scenarios per design.md 'End-to-End Testing' and run them against the current code | Restrictions: Never runs by default; use tmp dirs only; clear throttle cache per test; do not change generator code in this task | Success: Scenarios run end to end and the failures on current code are logged by name (list scoping, owner on create/patch, schema readOnly; the 404-vs-403 and assignee scenarios behave as described); log-implementation then mark [x] in tasks.md_

  - [x] 1.2 `OwnerScopedMixin`, the permission contract and the generator function
    - Files: `src/django_octave/templates/project/apps/core/ownership.py.j2` (new), `src/django_octave/api_parts/permission_gen.py`, `src/django_octave/api_parts/ownership_gen.py` (new), `src/django_octave/models_gen/cst_util.py`, `src/django_octave/tenancy.py` (`viewset_bases`), `tests/api_parts/test_ownership_gen.py` (new), `tests/models_gen/test_cst_util.py`, `tests/api_parts/test_permission_gen.py`, `tests/rendering/test_render_project.py`
    - Add the mixin template (always generated); make the owner preset class carry `owner_attr` (same behaviour); add `ensure_class_base`, `set_class_attribute`, `ensure_read_only_field` (libcst, idempotent, errors name the file); add `OWNER_IMPORT`, `OwnershipModuleMissingError`, `OwnershipWireError`, `ensure_ownership_module`, `owner_attr_of_permission`, `viewset_owner_field`, `apply_owner_scoping`; extend `viewset_bases(scoped, owned)` with the order `OwnerScopedMixin, TenantScopedMixin, ModelViewSet`
    - Purpose: All the building blocks, tested in isolation
    - _Leverage: `cst_util` conventions, `ensure_tenancy_module`, `TenantScopedMixin`_
    - _Requirements: 1.1, 1.3, 1.5, 2.1, 2.2, 2.4, 3.1, 3.5, 3.6, 4.2_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/DRF engineer | Task: Implement the mixin template, permission contract, cst helpers and apply_owner_scoping per design.md sections 1-4 | Restrictions: Behaviour of the owner permission check must not change; other presets and non-owner output byte-identical; libcst only (no string slicing) for the new edits; idempotent; no new dependencies | Success: Unit tests cover base insertion (first, idempotent, several bases, comments), attribute set/replace/insert, read_only_fields (tuple, list, absent, present, not in fields, __all__), unparsable file errors naming the path, apply_owner_scoping (viewset only, with tenant mixin, missing serializer, missing module, re-run, --force), viewset_bases order table, permission template contract; log + mark [x]_

- [x] 2.0 Wiring and tests
  - [x] 2.1 Wire `add-permission` and `add-viewset`
    - Files: `src/django_octave/commands/add_permission.py`, `src/django_octave/api_parts/viewset_gen.py`, `src/django_octave/commands/add_viewset.py`, `tests/commands/test_owner_wiring.py` (new)
    - `add-permission --preset owner --viewset`: after wiring, call `apply_owner_scoping` inside the existing rollback and print the notes; without `--viewset` print the exact next commands. `add-viewset --permission <Class>`: when the class in the app's `permissions.py` declares `owner_attr`, build the viewset with the owner mixin and `owner_field`, and make the serializer field read-only. No change when no owner permission is involved (compare generated output with a worktree of `HEAD`)
    - Purpose: Every path to an owner viewset is scoped
    - _Leverage: `rollback_on_error`, `resolve_permission`, `viewset_bases`_
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 7.1_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python engineer | Task: Wire apply_owner_scoping into add-permission and add-viewset per design.md section 5 | Restrictions: No behaviour change for any command that does not involve an owner permission; failures leave the tree unchanged and print no traceback; do not guess owner attributes for classes without owner_attr | Success: CLI tests for both paths, the no---viewset hint, re-run/--force idempotency, missing ownership.py error with unchanged tree, tenant+owner base order, and a byte-identical comparison for non-owner generation; the probe guard stays green; log + mark [x]_

  - [x] 2.2 Frontend CRUD treats the owner as read-only
    - Files: `src/django_octave/frontend_gen/crud_types.py`, `crud_discover.py`, `crud_fields.py`, `tests/frontend_gen/`
    - `ResourceSpec.owner_field`; discovery reads `owner_field = "<x>"` from the viewset body; `build_crud_fields` emits that field as `readonly`. Non-owner viewsets unchanged
    - Purpose: The SPA does not ask who owns a new row
    - _Leverage: existing `readonly` kind, discovery regexes_
    - _Requirements: 5.1, 5.2_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Carry owner_field through discovery to the CRUD fields as in design.md section 6 | Restrictions: Do not change output for viewsets without owner_field; keep ResourceSpec construction sites consistent | Success: Tests: owner field is readonly and absent from writable forms/list, detail shows it, other fields unchanged, non-owner snapshot identical; log + mark [x]_

  - [x] 2.3 Generated owner tests (`add-test`)
    - Files: `src/django_octave/api_parts/test_gen.py`, `tests/api_parts/test_test_gen.py`, `tests/commands/test_add_test.py`
    - Detect `owner_field` on the viewset; add the four tests from design.md section 7 (with tenant fixtures when multitenant); output unchanged for non-owner viewsets. Run the generated tests inside a real generated project (in the e2e of task 3.1)
    - Purpose: The generated project guards its own isolation
    - _Leverage: `build_api_test_source`, `_owner_factory_kw`, tenant test fixtures_
    - _Requirements: 6.1, 6.2, 6.3_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Test-generation engineer | Task: Generate the owner isolation tests per design.md section 7 | Restrictions: Non-owner output byte-identical; the create test may skip only with a clear reason when the model needs related objects the factory cannot give as ids; generated code must parse | Success: Unit tests assert the four tests (plain and tenant variants) and unchanged non-owner output; log + mark [x]_

- [x] 3.0 Prove it, document it
  - [x] 3.1 Re-run the e2e, before/after proof
    - Files: none new (maybe small fixes in the generator found by the e2e)
    - Run the 1.1 e2e on the new code (it must pass, including the generated project's own `pytest` with the generated owner tests), then copy it into a worktree of `HEAD` and show the same scenarios fail there. Fix any generator defect it reveals in the task that owns it
    - Purpose: Evidence that N5 and N6 are closed on real Django
    - _Leverage: the e2e from 1.1, `git worktree` (never `git stash`)_
    - _Requirements: 7.4, 1.1, 2.1, 4.1_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Release engineer | Task: Run the e2e before and after and report the evidence | Restrictions: Use a throwaway worktree and remove it; do not commit | Success: e2e passes on the working tree and fails on HEAD for the scenarios logged in 1.1; log + mark [x]_

  - [x] 3.2 Docs, audit and final verification
    - Files: `docs/concepts/security.md`, `docs/commands/add-permission.md`, `docs/commands/add-viewset.md`, `docs/commands/add-test.md`, `src/django_octave/templates/project/README.md.j2`, `docs/code-audit-2026-11-23.md`
    - Replace the two warnings with the accurate description (what the owner preset now does; what it does not: other user FKs writable, staff scoped too, default viewsets open) and the manual upgrade steps for earlier projects; update README wording and the command pages; mark N5 and N6 fixed. Verify the doc recipes against a real project. Run CI's commands (`ruff check src tests`, `pytest`, `mkdocs build --strict`), `uv audit --locked`, both e2e suites
    - Purpose: Documented, verified, audit current
    - _Leverage: existing docs structure, audit Status section_
    - _Requirements: 7.2, 7.3_
    - _Prompt: Implement the task for spec owner-scoped-viewsets, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Technical writer and release engineer | Task: Update docs and audit, run the full verification | Restrictions: Do not commit; mkdocs output to the scratchpad; state limits honestly; keep docs short | Success: Everything green, upgrade steps verified on a project generated by the previous commit, audit accurate, summary reported; log + mark [x]_
