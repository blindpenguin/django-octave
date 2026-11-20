# Tasks Document

- [x] 1.0 Nested serializers + action tags
  - [x] 1.1 Insert nested helpers before parent serializer
    - Files: `src/django_octave/models_gen/cst_util.py`, `src/django_octave/api_parts/serializer_gen.py`, tests
    - Add `before=` / `upsert_class_before`; wire `_ensure_nested_helpers` + `write_serializer`
    - Purpose: No NameError when parent references `UserNestedSerializer`
    - _Leverage: upsert_class, class_exists, design §1_
    - _Requirements: 1.1–1.3_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python/libcst generator engineer | Task: Nested serializer helpers must be defined before the parent that references them | Restrictions: Do not break force-replace; do not invent a full import sorter | Success: Unit test proves UserNested (or equivalent) appears above parent; log-implementation then mark [x] in tasks.md_

  - [x] 1.2 Fix detect_viewset_tag + action route shape
    - Files: `src/django_octave/api_parts/action_gen.py`, tests
    - Tag window = previous class → target class; use last tags= match; route hint `/api/<plural>/…`
    - Purpose: Actions tagged with target viewset; hints match real URLs
    - _Leverage: existing _TAG_RE, default_tag_for_viewset, design §2_
    - _Requirements: 2.1–2.4, 3.3_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: DRF/OpenAPI generator engineer | Task: Fix action tag detection and route-shape strings | Restrictions: --tag still wins; no change to @action body stubs | Success: Two-viewset unit test; second viewset action gets second tag; log + mark complete_

- [x] 2.0 URLs, ordering, imports
  - [x] 2.1 Shared api/ URL mount
    - Files: `src/django_octave/project/patch.py`, `src/django_octave/rendering/app_context.py`, related tests
    - New includes use `path("api/", include(...))`; legacy `api/<app>/` still counts as wired; update api_mount / add summary
    - Purpose: `/api/tickets/` not `/api/tickets/tickets/`
    - _Leverage: patch_urls, AppContext, design §3_
    - _Requirements: 3.1–3.6_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django project wiring engineer | Task: Mount domain apps under shared api/ | Restrictions: Do not auto-rewrite legacy mounts; keep basename/plural registration | Success: Unit/CLI tests for new include form + legacy idempotency; log + mark complete_

  - [x] 2.2 Smarter str_field_name / Meta.ordering
    - Files: `src/django_octave/fields/codegen.py`, tests
    - Prefer name/title/subject/slug then char-like; never prefer text when char exists
    - Purpose: TicketMessage-like models order by note not body
    - _Leverage: str_field_name, design §4_
    - _Requirements: 4.1–4.3_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Django model DSL engineer | Task: Tighten str_field_name preference order | Restrictions: Keep pk fallback when no suitable field | Success: Unit tests for preference cases; log + mark complete_

  - [x] 2.3 Coalesce duplicate from-imports
    - Files: `src/django_octave/models_gen/cst_util.py`, call sites in viewset_gen / action_gen (and ensure_import_lines), tests
    - Merge `from M import A` + `from M import B`; avoid duplicate lines on ensure
    - Purpose: Clean views.py after repeated upserts
    - _Leverage: add_to_import, ensure_import_lines, design §5_
    - _Requirements: 5.1–5.4_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Python tooling engineer | Task: Coalesce same-module from-imports in generator output | Restrictions: Best-effort single-line imports only; no full isort dependency | Success: Unit test merges two permission imports; log + mark complete_

- [x] 3.0 Starter model + docs/regression
  - [x] 3.1 add --model starter name
    - Files: `commands/add.py`, `prompts/add_app.py`, `rendering/app_context.py`, `docs/commands/add.md`, tests
    - Optional `--model` / interactive default; validate PascalCase; wire AppContext
    - Purpose: `add accounts --model Customer` avoids orphan Account
    - _Leverage: validate_model_name, model_name_from_app, design §6_
    - _Requirements: 6.1–6.6_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: CLI/UX engineer | Task: Add optional starter model name to django-octave add | Restrictions: Default remains derive-from-app; do not delete other models | Success: CLI test Customer not Account; docs note; log + mark complete_

  - [x] 3.2 Full suite green + roadmap note
    - Files: any failing tests from above, `docs/roadmap.md` shipped row if appropriate
    - Run full pytest; fix fallout from api_mount / route-shape assertion changes
    - Purpose: Lock heuristics; suite green
    - _Requirements: 7.1–7.2_
    - _Prompt: Implement the task for spec generator-heuristics, first run spec-workflow-guide to get the workflow guide then implement the task: Role: QA | Task: Ensure full pytest green and brief roadmap shipped note | Restrictions: No drive-by refactors | Success: uv run pytest green; log + mark complete_
