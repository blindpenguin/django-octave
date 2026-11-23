# Tasks Document

- [x] 1.0 Generator context for list row fields
  - [x] 1.1 Expose primary_field + secondary_fields in crud_pages context
    - Files: `src/django_octave/frontend_gen/crud_pages.py`, optionally a small unit assert in `tests/frontend_gen/test_crud_pages.py` once ListView exists
    - Derive `primary_field` from `spec.label_field` (fallback first list/writable/`id`); `secondary_fields` = up to 2 from list_fields excluding primary
    - Purpose: Template has clear primary/secondary without heavy Jinja logic
    - _Leverage: `_template_context`, `ResourceSpec.label_field`, existing `list_fields` selection_
    - _Requirements: 2.1–2.4_
    - _Prompt: Implement the task for spec responsive-crud-list, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Generator engineer | Task: Add primary_field and secondary_fields to CRUD page template context | Restrictions: Do not change API discovery; keep StrictUndefined-safe keys always present | Success: Context keys available to ListView Jinja; log-implementation then mark [x] in tasks.md_

- [x] 2.0 Gmail-style ListView template
  - [x] 2.1 Rewrite ListView.vue.j2 as vertical tappable rows
    - Files: `src/django_octave/templates/frontend_crud/pages/ListView.vue.j2`
    - Remove UTable/columns; full-width rows with primaryLabel + secondary · join + chevron; row → detail; loading/error/empty; keep New header
    - Purpose: Mobile-friendly collection UI
    - _Leverage: design.md row sketch; useCrudResource; Nuxt UIcon/UAlert/UButton_
    - _Requirements: 1.1–1.4, 2.1–2.4, 3.1–3.3, 4.1–4.3_
    - _Prompt: Implement the task for spec responsive-crud-list, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Vue UI engineer | Task: Replace table ListView with inbox-style list rows | Restrictions: No UTable; no desktop dual-mode table; no nested row action buttons required | Success: Template renders without AppLayout wrap; primary/secondary helpers present; log + mark complete_

- [x] 3.0 Tests + docs
  - [x] 3.1 Update generator tests and add-frontend-crud docs
    - Files: `tests/frontend_gen/test_crud_pages.py`, other tests asserting UTable/columns if any, `docs/commands/add-frontend-crud.md`, optionally `docs/roadmap.md` one line
    - Assert no UTable; assert list-row markers / primaryLabel; document responsive list briefly
    - Purpose: Regression safety + discoverability
    - _Leverage: existing test_crud_pages patterns_
    - _Requirements: 5.1–5.3_
    - _Prompt: Implement the task for spec responsive-crud-list, first run spec-workflow-guide to get the workflow guide then implement the task: Role: Docs + QA | Task: Align tests/docs with list UI | Restrictions: Keep suite reasonably fast; no E2E required | Success: pytest green; docs mention list not table; log + mark complete_
